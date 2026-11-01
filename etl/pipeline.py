"""ETL contract for the two NBA 2023/24 archives in data/raw."""

import hashlib
import json
from pathlib import Path
import tarfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SHOT_KEYS = ['GAME_ID', 'GAME_EVENT_ID']
PBP_KEYS = ['GAME_ID', 'EVENTNUM']
SHOT_COLUMNS = {
    *SHOT_KEYS, 'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_NAME', 'PERIOD',
    'MINUTES_REMAINING', 'SECONDS_REMAINING', 'SHOT_MADE_FLAG',
    'SHOT_ATTEMPTED_FLAG', 'SHOT_TYPE', 'SHOT_DISTANCE', 'GAME_DATE',
    'LOC_X', 'LOC_Y', 'SHOT_ZONE_BASIC', 'SHOT_ZONE_AREA', 'SHOT_ZONE_RANGE',
}
PBP_COLUMNS = {*PBP_KEYS, 'SCORE', 'EVENTMSGTYPE', 'PERIOD', 'PCTIMESTRING'}
ZONES = {
    'Restricted Area', 'In The Paint (Non-RA)', 'Mid-Range', 'Left Corner 3',
    'Right Corner 3', 'Above the Break 3', 'Backcourt',
}


def read_archive(path):
    """Read exactly one regular CSV member without extracting archive paths."""
    with tarfile.open(path, 'r:xz') as archive:
        members = [m for m in archive if m.isfile() and m.name.endswith('.csv')]
        if len(members) != 1:
            raise ValueError(f'{path}: expected exactly one regular CSV member')
        with archive.extractfile(members[0]) as stream:
            return pd.read_csv(stream, dtype={'GAME_ID': str})


def clutch(period, seconds, margin, limit=300, gap=5):
    return ((period >= 4) & (seconds >= 0) & (seconds <= limit)
            & (margin.abs() <= gap) & margin.notna())


def _require(frame, columns, name):
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f'{name}: missing required columns: {", ".join(missing)}')


def _keys(frame, event_column, name):
    """Canonical digit-string game IDs; numeric event IDs must be unambiguous."""
    frame = frame.copy()
    ids = frame.GAME_ID.astype('string').str.strip()
    if not ids.str.fullmatch(r'\d+(?:\.0+)?', na=False).all():
        raise ValueError(f'{name}: invalid GAME_ID')
    frame['GAME_ID'] = ids.str.replace(r'\.0+$', '', regex=True).str.lstrip('0').replace('', '0').astype(str)
    events = pd.to_numeric(frame[event_column], errors='coerce')
    if not (events.notna() & np.isfinite(events) & events.ge(0) & events.mod(1).eq(0)).all():
        raise ValueError(f'{name}: invalid {event_column}')
    frame[event_column] = events.astype('int64')
    return frame


def transform(shots, pbp, season=2023):
    """Transform frames; return clean attempts and deterministic quality counts."""
    if season != 2023:
        raise ValueError('Only season 2023 (2023/24) is supported by the local raw contract')
    _require(shots, SHOT_COLUMNS, 'shots')
    _require(pbp, PBP_COLUMNS, 'play-by-play')
    report = {'schema_version': 1, 'source': 'https://github.com/shufinskiy/nba_data',
              'season': '2023/2024', 'raw_shots': len(shots), 'raw_pbp_rows': len(pbp)}
    shots = _keys(shots, 'GAME_EVENT_ID', 'shots')
    pbp = _keys(pbp, 'EVENTNUM', 'play-by-play')
    for frame, name in [(shots, 'shots'), (pbp, 'pbp')]:
        report[f'exact_duplicate_{name}_rows'] = int(frame.duplicated().sum())
    shots = shots.drop_duplicates()
    pbp = pbp.drop_duplicates()
    conflicts = shots.duplicated(SHOT_KEYS, keep=False)
    report['ambiguous_shot_keys'] = len(shots.loc[conflicts, SHOT_KEYS].drop_duplicates())
    report['ambiguous_shot_rows_removed'] = int(conflicts.sum())
    shots = shots.loc[~conflicts].copy()

    numeric = ['PLAYER_ID', 'TEAM_ID', 'PERIOD', 'MINUTES_REMAINING',
               'SECONDS_REMAINING', 'SHOT_MADE_FLAG', 'SHOT_ATTEMPTED_FLAG',
               'SHOT_DISTANCE', 'LOC_X', 'LOC_Y']
    for col in numeric:
        shots[col] = pd.to_numeric(shots[col], errors='coerce')
    eligible = (shots.SHOT_MADE_FLAG.isin([0, 1]) & shots.SHOT_ATTEMPTED_FLAG.eq(1)
                & shots.SHOT_TYPE.isin(['2PT Field Goal', '3PT Field Goal']))
    report['ineligible_shot_rows_removed'] = int((~eligible).sum())
    shots = shots.loc[eligible].copy()
    shots['GAME_DATE'] = pd.to_datetime(shots.GAME_DATE.astype(str), format='%Y%m%d', errors='coerce')
    shots['seconds_remaining'] = shots.MINUTES_REMAINING * 60 + shots.SECONDS_REMAINING
    integral = ['PLAYER_ID', 'TEAM_ID', 'PERIOD', 'MINUTES_REMAINING', 'SECONDS_REMAINING']
    valid = (np.isfinite(shots[numeric]).all(axis=1)
             & shots[integral].mod(1).eq(0).all(axis=1)
             & shots.PLAYER_ID.gt(0) & shots.TEAM_ID.gt(0) & shots.PERIOD.ge(1)
             & shots.MINUTES_REMAINING.ge(0) & shots.SECONDS_REMAINING.between(0, 59)
             & shots.seconds_remaining.le(np.where(shots.PERIOD.gt(4), 300, 720))
             & shots.SHOT_DISTANCE.ge(0) & shots.GAME_DATE.notna())
    for col in ['PLAYER_NAME', 'TEAM_NAME']:
        shots[col] = shots[col].astype('string').str.strip()
        valid &= shots[col].notna() & shots[col].ne('')
    report['invalid_shot_rows_removed'] = int((~valid).sum())
    shots = shots.loc[valid].copy()
    if shots.empty:
        raise ValueError('No valid field-goal attempts remain after validation')
    for col in integral + ['SHOT_MADE_FLAG', 'SHOT_ATTEMPTED_FLAG']:
        shots[col] = shots[col].astype('int64')
    shots['seconds_remaining'] = shots.MINUTES_REMAINING * 60 + shots.SECONDS_REMAINING
    for col in ['SHOT_ZONE_BASIC', 'SHOT_ZONE_AREA', 'SHOT_ZONE_RANGE']:
        shots[col] = shots[col].astype('string').str.strip().replace('', pd.NA).fillna('Unknown')
    unknown = ~shots.SHOT_ZONE_BASIC.isin(ZONES)
    report['unknown_zone_rows'] = int(unknown.sum())
    shots.loc[unknown, 'SHOT_ZONE_BASIC'] = 'Unknown'

    # Collapse conflicting event IDs into barriers, never select one conflicting score.
    pbp['_ambiguous'] = pbp.duplicated(PBP_KEYS, keep=False)
    report['ambiguous_pbp_keys'] = len(pbp.loc[pbp._ambiguous, PBP_KEYS].drop_duplicates())
    pbp = pbp.drop_duplicates(PBP_KEYS).sort_values(PBP_KEYS, kind='stable').copy()
    score_text = pbp.SCORE.astype('string').str.strip()
    parsed = score_text.str.extract(r'^(\d+)\s*-\s*(\d+)$').astype(float)
    malformed = score_text.notna() & score_text.ne('') & parsed[0].isna()
    missing_made_score = pd.to_numeric(pbp.EVENTMSGTYPE, errors='coerce').eq(1) & parsed[0].isna()
    barrier = pbp._ambiguous | malformed | missing_made_score
    report['invalid_pbp_score_events'] = int((malformed | missing_made_score).sum())
    # -1 propagates unknown state until a new, valid score is observed.
    for column, index in [('away_score_before', 0), ('home_score_before', 1)]:
        after = parsed[index].mask(barrier, -1).groupby(pbp.GAME_ID).ffill().fillna(0)
        before = after.groupby(pbp.GAME_ID).shift(fill_value=0)
        pbp[column] = before.mask(before.eq(-1))
    pbp['_pbp_period'] = pd.to_numeric(pbp.PERIOD, errors='coerce')
    clock = pbp.PCTIMESTRING.astype('string').str.extract(r'^(\d+):(\d{2})$').astype(float)
    pbp['_pbp_seconds'] = (clock[0] * 60 + clock[1]).where(clock[1].between(0, 59))
    context = pbp.loc[~pbp._ambiguous, PBP_KEYS + [
        'away_score_before', 'home_score_before', '_pbp_period', '_pbp_seconds']]
    shots = shots.merge(context, left_on=SHOT_KEYS, right_on=PBP_KEYS,
                        how='left', validate='one_to_one', indicator=True)
    matched = shots['_merge'].eq('both')
    consistent = shots.PERIOD.eq(shots._pbp_period) & shots.seconds_remaining.eq(shots._pbp_seconds)
    report['unmatched_shot_rows'] = int((~matched).sum())
    report['context_clock_or_period_mismatch'] = int((matched & ~consistent).sum())
    shots.loc[~consistent, ['away_score_before', 'home_score_before']] = np.nan
    shots = shots.drop(columns=['_merge', '_pbp_period', '_pbp_seconds'])
    shots['score_margin_before'] = shots.home_score_before - shots.away_score_before
    shots['has_score_context'] = shots.score_margin_before.notna()
    shots['is_clutch'] = clutch(shots.PERIOD, shots.seconds_remaining, shots.score_margin_before)
    shots['shot_value'] = np.where(shots.SHOT_TYPE.str.startswith('3'), 3, 2)
    shots['points'] = shots.shot_value * shots.SHOT_MADE_FLAG
    shots['x_ft'] = shots.LOC_X / 10
    shots['y_ft'] = shots.LOC_Y / 10
    shots['season'] = '2023/24'
    shots = shots.sort_values(['GAME_DATE', *SHOT_KEYS], kind='stable').reset_index(drop=True)
    report.update(eligible_shots=len(shots), games=shots.GAME_ID.nunique(),
                  missing_score_context=int((~shots.has_score_context).sum()),
                  date_min=str(shots.GAME_DATE.min()), date_max=str(shots.GAME_DATE.max()),
                  clutch_attempts=int(shots.is_clutch.sum()))
    return shots, report


def prepare(source=ROOT / 'data/raw', season=2023):
    """Read local archives only; this function never downloads data."""
    if season != 2023:
        raise ValueError('Only season 2023 is available in the raw contract')
    paths = [Path(source) / f'{name}_{season}.tar.xz' for name in ('shotdetail', 'nbastats')]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f'Required local archive not found: {path}')
    shots, report = transform(*(read_archive(path) for path in paths), season=season)
    report['inputs'] = [
        {'file': path.name, 'bytes': path.stat().st_size,
         'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for path in paths
    ]
    return shots, report


def write_outputs(shots, report, output=ROOT / 'data'):
    """Publish ordered Parquet and its quality/schema report, without training."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    parquet = output / 'shots.parquet'
    temporary = output / 'shots.parquet.tmp'
    shots.to_parquet(temporary, engine='pyarrow', index=False, compression='zstd', row_group_size=50000)
    temporary.replace(parquet)
    report = {**report, 'columns': {name: str(dtype) for name, dtype in shots.dtypes.items()}}
    manifest = output / 'manifest.json.tmp'
    manifest.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    manifest.replace(output / 'manifest.json')
    return report
