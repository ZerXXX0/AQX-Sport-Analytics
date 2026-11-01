"""Shot Explorer adapter; coordinates follow docs/data-contract.md.

The local SVG/canvas component uses Streamlit's existing component protocol.
It requires no frontend build, remote asset, or additional runtime dependency.
"""
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

COURT = {
    'left': -25, 'right': 25, 'baseline': -5.25, 'half': 41.75,
    'threeRadius': 23.75, 'cornerX': 22, 'keyX': 8, 'freeThrowY': 13.75,
    'freeThrowRadius': 6, 'restrictedRadius': 4, 'backboardY': -1.25,
    'rimRadius': .75, 'hexRadius': 2,
    'view': {'left': -27, 'top': 43.75, 'width': 54, 'height': 51},
}

# Bare names explicitly mean fractions; percent columns must say so, or callers
# must supply probability_scale=100. Never guess the scale from max().
PROBABILITY_COLUMNS = {
    'predicted_probability': 1, 'make_probability': 1,
    'shot_probability': 1, 'predicted_make_probability': 1,
    'predicted_probability_pct': 100, 'make_probability_pct': 100,
}


def prepare_chart_data(df, probability_column=None, probability_scale=None, *, league=None):
    """Preserve eligible attempts, flag unplottable coordinates, never clamp.

    Packet row order is documented in ``fields``. String dictionaries avoid
    repeating labels for the entire season. Predictions are never synthesized.
    """
    if 'SHOT_MADE_FLAG' not in df:
        raise ValueError('Shot results (SHOT_MADE_FLAG) are unavailable.')
    result = pd.to_numeric(df.SHOT_MADE_FLAG, errors='coerce')
    valid_result = result.isin([0, 1])
    shots = df.loc[valid_result].reset_index(drop=True)

    def number(name):
        return pd.to_numeric(shots.get(name, pd.Series(np.nan, index=shots.index)),
                             errors='coerce').replace([np.inf, -np.inf], np.nan)

    if {'LOC_X', 'LOC_Y'}.issubset(shots.columns):
        x, y = number('LOC_X') / 10, number('LOC_Y') / 10
        coordinate_source = 'LOC_X / 10, LOC_Y / 10'
    elif {'x_ft', 'y_ft'}.issubset(shots.columns):
        x, y = number('x_ft'), number('y_ft')
        coordinate_source = 'x_ft, y_ft (project data contract)'
    else:
        raise ValueError('Shot coordinates are unavailable (LOC_X/LOC_Y or x_ft/y_ft).')
    mismatch = pd.Series(False, index=shots.index)
    if {'LOC_X', 'LOC_Y', 'x_ft', 'y_ft'}.issubset(shots.columns):
        mismatch = ((x - number('x_ft')).abs() > 1e-6) | ((y - number('y_ft')).abs() > 1e-6)

    column = probability_column
    if column is None:
        column = next((c for c in PROBABILITY_COLUMNS if c in shots), None)
    scale = probability_scale if probability_scale is not None else PROBABILITY_COLUMNS.get(column)
    probability = pd.Series(np.nan, index=shots.index)
    invalid_predictions = 0
    prediction_status = 'No per-shot predicted probability is available in this dataset.'
    if column is not None and column in shots:
        if scale not in (1, 100):
            prediction_status = f'Probability scale for {column} is unspecified; provide 1 or 100.'
        else:
            raw = number(column)
            allowed = raw.between(0, scale)
            probability = (raw / scale).where(allowed)
            invalid_predictions = int((shots[column].notna() & ~allowed).sum())
            prediction_status = f'{column}: source scale 0–{scale}; displayed as percent.'

    shot_value = number('shot_value').where(number('shot_value').isin([2, 3]))
    if 'SHOT_TYPE' in shots:
        shot_value = shot_value.fillna(shots.SHOT_TYPE.map({'2PT Field Goal': 2, '3PT Field Goal': 3}))
    clock = number('seconds_remaining').fillna(number('MINUTES_REMAINING') * 60 + number('SECONDS_REMAINING'))
    period = number('PERIOD').where(number('PERIOD').ge(1) & number('PERIOD').mod(1).eq(0))
    clock = clock.where(clock.ge(0) & clock.le(np.where(period.gt(4), 300, 720)))

    dictionaries, codes = {}, {}
    for field, source in [('players', 'PLAYER_NAME'), ('zones', 'SHOT_ZONE_BASIC'), ('types', 'SHOT_TYPE')]:
        labels = shots.get(source, pd.Series('Unknown', index=shots.index)).fillna('Unknown').astype(str).str.strip()
        labels = labels.mask(labels.eq(''), 'Unknown')
        dictionaries[field] = sorted(labels.unique().tolist())
        codes[field] = labels.map({label: i for i, label in enumerate(dictionaries[field])})

    frame = pd.DataFrame({
        'x': x, 'y': y, 'made': pd.to_numeric(shots.SHOT_MADE_FLAG),
        'player': codes['players'], 'zone': codes['zones'], 'type': codes['types'],
        'distance': number('SHOT_DISTANCE').where(number('SHOT_DISTANCE').ge(0)),
        'period': period, 'seconds': clock, 'value': shot_value, 'probability': probability,
        'game': shots.get('GAME_ID', pd.Series('', index=shots.index)).fillna('').astype(str),
        'event': shots.get('GAME_EVENT_ID', pd.Series('', index=shots.index)).fillna('').astype(str),
    })
    valid_xy = x.notna() & y.notna()
    visible = valid_xy & x.between(COURT['left'], COURT['right']) & y.between(COURT['baseline'], COURT['half'])
    benchmarks = {}
    if league is not None and {'SHOT_ZONE_BASIC', 'SHOT_MADE_FLAG'}.issubset(league.columns):
        league_results = pd.to_numeric(league.SHOT_MADE_FLAG, errors='coerce')
        comparison = league.loc[league_results.isin([0, 1]), ['SHOT_ZONE_BASIC']].copy()
        comparison['made'] = league_results[league_results.isin([0, 1])].to_numpy()
        for label, group in comparison.groupby('SHOT_ZONE_BASIC'):
            benchmarks[str(label)] = {'attempts': len(group), 'fg': float(group.made.mean() * 100)}
    return {
        'revision': hashlib.sha256(pd.util.hash_pandas_object(frame, index=False).values.tobytes()).hexdigest(),
        'fields': list(frame.columns),
        'rows': frame.astype(object).where(frame.notna(), None).values.tolist(),
        **dictionaries, 'court': COURT, 'benchmarks': benchmarks,
        'meta': {
            'attempts': len(shots), 'invalidResults': int((~valid_result).sum()),
            'invalidCoordinates': int((~valid_xy).sum()), 'outsideCourt': int((valid_xy & ~visible).sum()),
            'coordinateMismatches': int(mismatch.sum()), 'coordinateSource': coordinate_source,
            'predictions': int(probability.notna().sum()),
            'expectedPoints': int((probability.notna() & shot_value.notna()).sum()),
            'invalidPredictions': invalid_predictions, 'predictionStatus': prediction_status,
        },
    }


def render_shot_explorer(df, *, league=None, probability_column=None, probability_scale=None):
    """Render only Shot Explorer; sidebar filters have already been applied."""
    import streamlit as st
    from streamlit.components.v1 import declare_component

    try:
        with st.spinner('Preparing shot visualization…'):
            packet = prepare_chart_data(df, probability_column, probability_scale, league=league)
    except (ValueError, TypeError, KeyError) as exc:
        st.error(f'Shot visualization unavailable: {exc}')
        return
    component = declare_component('clutchiq_shot_explorer', path=str(Path(__file__).parent / 'visualization'))
    component(packet=packet, key='shot_explorer', default=None)
