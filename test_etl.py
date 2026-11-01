import io
import json
import tarfile

import numpy as np
import pandas as pd
import pytest

from analytics_store import connect, query_overview, query_shots, query_zones
from etl import prepare, read_archive, write_outputs
from etl.pipeline import transform


def shot(event=2, game='22300001', **changes):
    row = dict(GAME_ID=game, GAME_EVENT_ID=event, PLAYER_ID=1, PLAYER_NAME='Player',
               TEAM_ID=10, TEAM_NAME='Team', PERIOD=4, MINUTES_REMAINING=5,
               SECONDS_REMAINING=0, SHOT_MADE_FLAG=1, SHOT_ATTEMPTED_FLAG=1,
               SHOT_TYPE='2PT Field Goal', SHOT_DISTANCE=6, GAME_DATE=20231101,
               LOC_X=-26, LOC_Y=64, SHOT_ZONE_BASIC=' In The Paint (Non-RA) ',
               SHOT_ZONE_AREA='Center(C)', SHOT_ZONE_RANGE='Less Than 8 ft.')
    return {**row, **changes}


def event(number, score=None, game='22300001', **changes):
    return dict(GAME_ID=game, EVENTNUM=number, SCORE=score,
                **{'EVENTMSGTYPE': 1 if score is not None else 2,
                   'PERIOD': 4, 'PCTIMESTRING': '5:00', **changes})


def frames(shots=None, events=None):
    return (pd.DataFrame(shots if shots is not None else [shot()]),
            pd.DataFrame(events if events is not None else [event(1, '95 - 100'), event(2, '95 - 102')]))


def test_pre_shot_score_not_outcome_and_game_boundary():
    shots, pbp = frames(
        [shot(), shot(3, MINUTES_REMAINING=4, SECONDS_REMAINING=59),
         shot(2, game='0022300002'), shot(4, PERIOD=5)],
        [event(1, '95 - 100'), event(2, '95 - 102'),
         event(3, PCTIMESTRING='4:59'), event(4, PERIOD=5),
         event(2, '0 - 2', game='22300002')],
    )
    result, _ = transform(shots, pbp.sample(frac=1, random_state=42))
    game = result[result.GAME_ID == '22300001'].set_index('GAME_EVENT_ID')
    assert game.score_margin_before.to_dict() == {2: 5., 3: 7., 4: 7.}
    assert game.is_clutch.to_dict() == {2: True, 3: False, 4: False}
    assert result[result.GAME_ID == '22300002'].score_margin_before.iloc[0] == 0
    assert game.loc[2, 'x_ft'] == -2.6 and game.loc[2, 'y_ft'] == 6.4
    assert game.loc[2, 'SHOT_ZONE_BASIC'] == 'In The Paint (Non-RA)'


def test_unknown_context_and_clutch_boundary_overtime():
    shots, pbp = frames(
        [shot(2, PERIOD=5), shot(3), shot(4, MINUTES_REMAINING=5, SECONDS_REMAINING=1)],
        [event(1, '100 - 95'), event(2, PERIOD=5), event(4, PCTIMESTRING='5:01')],
    )
    result, report = transform(shots, pbp)
    assert result.is_clutch.tolist() == [True, False, False]
    assert result.has_score_context.tolist() == [True, False, True]
    assert report['missing_score_context'] == report['unmatched_shot_rows'] == 1


def test_exact_duplicates_and_conflicting_shots():
    shots, pbp = frames([shot(), shot(), shot(3), shot(3, SHOT_MADE_FLAG=0)],
                        [event(1, '95 - 100'), event(1, '95 - 100'), event(2)])
    result, report = transform(shots, pbp)
    assert result.GAME_EVENT_ID.tolist() == [2]
    assert report['exact_duplicate_shots_rows'] == 1
    assert report['exact_duplicate_pbp_rows'] == 1
    assert report['ambiguous_shot_keys'] == 1
    assert report['ambiguous_shot_rows_removed'] == 2


def test_conflicting_pbp_invalidates_following_scores_until_recovery():
    shots, pbp = frames([shot(i) for i in range(2, 6)], [
        event(1, '95 - 100'), event(2, '95 - 102'), event(2, '95 - 103'),
        event(3), event(4, '97 - 103'), event(5),
    ])
    result, report = transform(shots, pbp)
    assert result.has_score_context.tolist() == [False, False, False, True]
    assert result.score_margin_before.iloc[-1] == 6
    assert report['ambiguous_pbp_keys'] == 1
    assert report['missing_score_context'] == 3


@pytest.mark.parametrize('bad_score', ['invalid', None])
def test_bad_scoring_event_does_not_forward_fill_stale_score(bad_score):
    shots, pbp = frames([shot(3), shot(4), shot(5)], [
        event(1, '95 - 100'), event(2, bad_score, EVENTMSGTYPE=1), event(3),
        event(4, '97 - 103'), event(5),
    ])
    result, report = transform(shots, pbp)
    assert result.has_score_context.tolist() == [False, False, True]
    assert report['invalid_pbp_score_events'] == 1


@pytest.mark.parametrize('changes', [{'PERIOD': 3}, {'PCTIMESTRING': '4:59'},
                                   {'PCTIMESTRING': '4:60'}])
def test_join_clock_and_period_must_agree(changes):
    result, report = transform(*frames(events=[event(1, '95 - 100'), event(2, **changes)]))
    assert not result.has_score_context.iloc[0]
    assert report['context_clock_or_period_mismatch'] == 1


@pytest.mark.parametrize('changes', [
    {'SECONDS_REMAINING': 60}, {'MINUTES_REMAINING': -1},
    {'MINUTES_REMAINING': 13}, {'PERIOD': 5, 'MINUTES_REMAINING': 6},
    {'PERIOD': 4.5}, {'LOC_X': np.inf}, {'GAME_DATE': 'bad date'}, {'PLAYER_ID': None},
])
def test_invalid_shot_rows_are_counted_and_removed(changes):
    result, report = transform(*frames(shots=[shot(), shot(3, **changes)]))
    assert result.GAME_EVENT_ID.tolist() == [2]
    assert report['invalid_shot_rows_removed'] == 1


def test_ineligible_shots_and_unknown_zones():
    result, report = transform(*frames(shots=[
        shot(SHOT_ZONE_BASIC='unexpected'), shot(3, SHOT_ATTEMPTED_FLAG=0),
        shot(4, SHOT_TYPE='Free Throw'),
    ]))
    assert result.SHOT_ZONE_BASIC.tolist() == ['Unknown']
    assert report['unknown_zone_rows'] == 1
    assert report['ineligible_shot_rows_removed'] == 2


def test_missing_columns_bad_keys_and_empty_output_fail_clearly():
    shots, pbp = frames()
    with pytest.raises(ValueError, match='missing required columns: LOC_X'):
        transform(shots.drop(columns='LOC_X'), pbp)
    with pytest.raises(ValueError, match='invalid GAME_ID'):
        transform(shots.assign(GAME_ID=None), pbp)
    with pytest.raises(ValueError, match='invalid EVENTNUM'):
        transform(shots, pbp.assign(EVENTNUM=1.5))
    with pytest.raises(ValueError, match='No valid field-goal attempts'):
        transform(shots.assign(SHOT_ATTEMPTED_FLAG=0), pbp)


def write_archive(path, members):
    with tarfile.open(path, 'w:xz') as archive:
        for name, content in members:
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))


def test_local_archive_pipeline_reproducible_and_reports_provenance(tmp_path):
    shots, pbp = frames()
    for name, frame in [('shotdetail', shots), ('nbastats', pbp)]:
        write_archive(tmp_path / f'{name}_2023.tar.xz', [
            ('nested/data.csv', frame.to_csv(index=False).encode()),
        ])
    first, report = prepare(tmp_path)
    second, again = prepare(tmp_path)
    pd.testing.assert_frame_equal(first, second)
    assert report == again
    assert len(report['inputs']) == 2
    assert all(len(item['sha256']) == 64 for item in report['inputs'])
    with pytest.raises(ValueError, match='Only season 2023'):
        prepare(tmp_path, 2024)
    with pytest.raises(FileNotFoundError, match='Required local archive'):
        prepare(tmp_path / 'missing')


@pytest.mark.parametrize('members', [[], [('a.csv', b'a\n1'), ('b.csv', b'a\n2')]])
def test_archive_rejects_missing_or_multiple_csvs(tmp_path, members):
    path = tmp_path / 'bad.tar.xz'
    write_archive(path, members)
    with pytest.raises(ValueError, match='exactly one regular CSV'):
        read_archive(path)


def test_parquet_duckdb_filters_aggregates_and_unknown_context(tmp_path):
    shots, pbp = frames([shot(), shot(3, PLAYER_ID=2, SHOT_MADE_FLAG=0), shot(4)],
                        [event(1, '95 - 100'), event(2, '95 - 102'), event(3)])
    clean, report = transform(shots, pbp)
    manifest = write_outputs(clean, report, tmp_path)
    assert json.loads((tmp_path / 'manifest.json').read_text()) == manifest
    pd.testing.assert_frame_equal(pd.read_parquet(tmp_path / 'shots.parquet'), clean)
    with connect(tmp_path / 'shots.parquet') as connection:
        assert query_overview(connection).attempts.iloc[0] == 3
        assert query_overview(connection).missing_score_context.iloc[0] == 1
        assert query_shots(connection, is_clutch=True).GAME_EVENT_ID.tolist() == [2]
        assert query_shots(connection, is_clutch=False).GAME_EVENT_ID.tolist() == [3]
        assert query_shots(connection, player_id=2, team_id=10, season='2023/24',
                           period=4, zone='In The Paint (Non-RA)').GAME_EVENT_ID.tolist() == [3]
        assert query_shots(connection, limit=1, offset=1).GAME_EVENT_ID.tolist() == [3]
        zone = query_zones(connection).iloc[0]
        assert zone.attempts == 3 and zone.makes == 2 and zone.points == 4
        assert zone.fg_pct == pytest.approx(200/3)
        assert query_shots(connection, zone="' OR 1=1 --").empty
        assert query_overview(connection, team_id=999).attempts.iloc[0] == 0
        assert pd.isna(query_overview(connection, team_id=999).fg_pct.iloc[0])
        for kwargs in [{'limit': 0}, {'offset': -1}, {'is_clutch': 'false'},
                       {'period': 1.5}, {'player_id': True}]:
            with pytest.raises(ValueError):
                query_shots(connection, **kwargs)
    with pytest.raises(FileNotFoundError, match='python -m etl'):
        connect(tmp_path / 'missing.parquet')
