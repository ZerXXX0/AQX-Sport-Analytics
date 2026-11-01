"""Visualization contract checks. Fixtures are tests, never application data."""
import json

import numpy as np
import pandas as pd
import pytest

from charts import COURT, prepare_chart_data


def attempts(**changes):
    data = dict(LOC_X=[-225, 0, 225, 0], LOC_Y=[0, 0, 0, 600],
                SHOT_MADE_FLAG=[1, 0, 1, 0], shot_value=[3, 2, 3, 3],
                PLAYER_NAME=['A', 'B', 'A', 'B'],
                SHOT_ZONE_BASIC=['Left Corner 3', 'Restricted Area', 'Right Corner 3', 'Backcourt'],
                SHOT_TYPE=['3PT Field Goal', '2PT Field Goal', '3PT Field Goal', '3PT Field Goal'],
                PERIOD=[1, 4, 5, 4], MINUTES_REMAINING=[11, 5, 1, 0], SECONDS_REMAINING=[7, 0, 2, 0])
    return pd.DataFrame({**data, **changes})


def test_original_coordinates_are_preserved_and_off_court_counted():
    data = attempts(x_ft=[100] * 4, y_ft=[100] * 4)
    packet = prepare_chart_data(data)
    assert [row[:2] for row in packet['rows']] == [[-22.5, 0.], [0., 0.], [22.5, 0.], [0., 60.]]
    assert packet['meta']['outsideCourt'] == 1
    assert packet['meta']['coordinateMismatches'] == 4
    assert packet['meta']['attempts'] == 4
    assert data.x_ft.eq(100).all()  # plotting must not mutate the source
    assert COURT['half'] - COURT['baseline'] == 47
    assert COURT['backboardY'] == -1.25


def test_invalid_coordinates_never_move_to_basket_or_break_json():
    packet = prepare_chart_data(attempts(LOC_X=[None, np.inf, 'bad', 0]))
    assert packet['meta']['invalidCoordinates'] == 3
    assert packet['meta']['outsideCourt'] == 1
    assert len(packet['rows']) == 4
    assert all(row[0] is None for row in packet['rows'][:3])
    json.dumps(packet, allow_nan=False)


@pytest.mark.parametrize('column,values,scale', [
    ('predicted_probability', [0, .5, 1, 1.2], None),
    ('predicted_probability_pct', [0, 50, 100, 120], None),
    ('external_probability', [0, 50, 100, 120], 100),
])
def test_probability_units_invalid_values_and_genuine_zero(column, values, scale):
    data = attempts(**{column: values})
    packet = prepare_chart_data(data, column, scale)
    assert [row[10] for row in packet['rows']] == [0., .5, 1., None]
    assert packet['meta']['predictions'] == 3
    assert packet['meta']['expectedPoints'] == 3
    assert packet['meta']['invalidPredictions'] == 1


def test_no_invented_predictions_and_no_guessed_percent_scale():
    packet = prepare_chart_data(attempts())
    assert all(row[10] is None for row in packet['rows'])
    assert packet['meta']['predictions'] == 0
    ambiguous = prepare_chart_data(attempts(external=[.2, .4, .5, .8]), 'external')
    assert ambiguous['meta']['predictions'] == 0
    assert 'unspecified' in ambiguous['meta']['predictionStatus']
    # A bare fraction column containing 50 is invalid, not silently rescaled.
    assert prepare_chart_data(attempts(predicted_probability=[50] * 4))['meta']['predictions'] == 0


def test_missing_fields_empty_data_invalid_outcomes_and_clock_fallback():
    data = attempts(seconds_remaining=[None, 300, 62, 0])
    packet = prepare_chart_data(data)
    assert packet['rows'][0][8] == 667
    assert prepare_chart_data(data.iloc[:0])['rows'] == []
    invalid = prepare_chart_data(attempts(SHOT_MADE_FLAG=[1, None, 'bad', 0]))
    assert invalid['meta']['invalidResults'] == 2
    assert invalid['meta']['attempts'] == 2
    with pytest.raises(ValueError, match='coordinates'):
        prepare_chart_data(pd.DataFrame({'SHOT_MADE_FLAG': [1]}))


def test_filter_revision_and_league_benchmark_are_independent():
    data = attempts()
    packet = prepare_chart_data(data.iloc[:1], league=data)
    assert packet['meta']['attempts'] == 1
    assert packet['benchmarks']['Restricted Area'] == {'attempts': 1, 'fg': 0.}
    changed = data.copy()
    changed.loc[1, 'SHOT_MADE_FLAG'] = 1
    assert prepare_chart_data(changed)['revision'] != prepare_chart_data(data)['revision']


def test_real_data_alignment_and_packet_totals():
    from core import ROOT
    path = ROOT / 'data/shots.parquet'
    if not path.exists():
        pytest.skip('Build actual dataset before the data integration check.')
    data = pd.read_parquet(path)
    packet = prepare_chart_data(data)
    rows = pd.DataFrame(packet['rows'], columns=packet['fields'])
    assert len(rows) == len(data)
    np.testing.assert_allclose(rows.x, data.LOC_X / 10)
    np.testing.assert_allclose(rows.y, data.LOC_Y / 10)
    assert rows.made.sum() == data.SHOT_MADE_FLAG.sum()
    assert packet['meta']['coordinateMismatches'] == 0
    left = data[data.SHOT_ZONE_BASIC.eq('Left Corner 3')]
    right = data[data.SHOT_ZONE_BASIC.eq('Right Corner 3')]
    assert left.LOC_X.max() <= -220 and right.LOC_X.min() >= 220
    # Source distance is rounded to whole feet. It independently confirms the
    # basket origin and decifeet units without imposing a new location.
    radius = np.hypot(data.LOC_X / 10, data.LOC_Y / 10)
    assert (np.abs(radius - data.SHOT_DISTANCE) < 1.5).mean() > .99
