import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent

def read_archive(path):
    """Read a .tar.xz archive or a plain .csv file."""
    path = Path(path)
    if path.suffix == '.csv' and path.exists():
        return pd.read_csv(path, dtype={'GAME_ID': str})
    with tarfile.open(path, 'r:xz') as archive:
        member = next(m for m in archive if m.name.endswith('.csv'))
        return pd.read_csv(archive.extractfile(member), dtype={'GAME_ID': str})

def clutch(period, seconds, margin, limit=300, gap=5):
    return (period >= 4) & (seconds <= limit) & (margin.abs() <= gap) & margin.notna()

def _resolve(source, name, season):
    """Return path to .tar.xz if it exists, else fall back to plain .csv."""
    tar = Path(source) / f'{name}_{season}.tar.xz'
    if tar.exists():
        return tar
    csv = Path(source) / f'{name}_{season}.csv'
    if csv.exists():
        return csv
    raise FileNotFoundError(
        f"Dataset not found. Tried:\n  {tar}\n  {csv}\n"
        f"Place shotdetail_{season}.tar.xz / .csv and nbastats_{season}.tar.xz / .csv in: {source}"
    )

def prepare(source, season=2023):
    shots = read_archive(_resolve(source, 'shotdetail', season))
    pbp   = read_archive(_resolve(source, 'nbastats',   season))
    raw_count = len(shots)
    shots = shots.drop_duplicates(['GAME_ID', 'GAME_EVENT_ID'])
    shots = shots[shots.SHOT_MADE_FLAG.isin([0, 1]) & shots.SHOT_TYPE.isin(['2PT Field Goal', '3PT Field Goal']) & (shots.SHOT_ATTEMPTED_FLAG == 1)].copy()
    # Remove exact duplicates; ambiguous event IDs cannot safely supply context.
    pbp = pbp.drop_duplicates()
    ambiguous = pbp.duplicated(['GAME_ID', 'EVENTNUM'], keep=False)
    bad_keys = pbp.loc[ambiguous, ['GAME_ID', 'EVENTNUM']].drop_duplicates()
    pbp = pbp.sort_values(['GAME_ID', 'EVENTNUM'], kind='stable')
    parsed = pbp.SCORE.astype('string').str.extract(r'^(\d+)\s*-\s*(\d+)$').astype(float)
    # SCORE is away-home. Forward-fill within each game; shift to obtain pre-event score.
    for col, idx in [('away', 0), ('home', 1)]:
        after = parsed[idx].groupby(pbp.GAME_ID).ffill().fillna(0)
        pbp[col + '_before'] = after.groupby(pbp.GAME_ID).shift().fillna(0)
    pbp['score_margin_before'] = pbp.home_before - pbp.away_before
    context = pbp.loc[~pbp.duplicated(['GAME_ID', 'EVENTNUM'], keep=False), ['GAME_ID', 'EVENTNUM', 'score_margin_before']]
    shots = shots.merge(context, left_on=['GAME_ID', 'GAME_EVENT_ID'], right_on=['GAME_ID', 'EVENTNUM'], how='left', validate='one_to_one')
    shots['seconds_remaining'] = shots.MINUTES_REMAINING * 60 + shots.SECONDS_REMAINING
    shots['is_clutch'] = clutch(shots.PERIOD, shots.seconds_remaining, shots.score_margin_before)
    shots['shot_value'] = np.where(shots.SHOT_TYPE.str.startswith('3'), 3, 2)
    shots['points'] = shots.shot_value * shots.SHOT_MADE_FLAG
    shots['GAME_DATE'] = pd.to_datetime(shots.GAME_DATE.astype(str), format='%Y%m%d')
    shots['x_ft'] = shots.LOC_X / 10
    shots['y_ft'] = shots.LOC_Y / 10
    shots['season'] = f'{season}/{str(season+1)[-2:]}'
    report = {'source': 'https://github.com/shufinskiy/nba_data', 'season': f'{season}/{season+1}', 'raw_shots': raw_count, 'eligible_shots': len(shots), 'games': shots.GAME_ID.nunique(), 'missing_score_context': int(shots.score_margin_before.isna().sum()), 'ambiguous_pbp_keys': len(bad_keys), 'date_min': str(shots.GAME_DATE.min()), 'date_max': str(shots.GAME_DATE.max()), 'clutch_attempts': int(shots.is_clutch.sum())}
    return shots, report

def metrics(df):
    n = len(df)
    threes = df[df.shot_value == 3]
    return {'Attempts': n, 'FG%': 100 * df.SHOT_MADE_FLAG.mean() if n else 0, '3P%': 100 * threes.SHOT_MADE_FLAG.mean() if len(threes) else 0, 'Points / attempt': df.points.mean() if n else 0, 'eFG%': 100 * (df.SHOT_MADE_FLAG.sum() + .5 * threes.SHOT_MADE_FLAG.sum()) / n if n else 0}

def zones(df):
    z = df.groupby('SHOT_ZONE_BASIC').agg(attempts=('points', 'size'), makes=('SHOT_MADE_FLAG', 'sum'), points=('points', 'sum'))
    z['FG%'] = 100 * z.makes / z.attempts
    z['Points / attempt'] = z.points / z.attempts
    # Wilson 95% interval for binomial make rate.
    p = z.makes / z.attempts; n = z.attempts; q = 1.96
    center = (p + q*q/(2*n)) / (1+q*q/n)
    half = q*np.sqrt(p*(1-p)/n+q*q/(4*n*n))/(1+q*q/n)
    z['FG% lower'] = 100*(center-half); z['FG% upper'] = 100*(center+half)
    return z.reset_index()

FEATURES = ['SHOT_DISTANCE', 'x_ft', 'y_ft', 'shot_value', 'PERIOD', 'seconds_remaining', 'score_margin_before']

def train(df):
    from sklearn.pipeline import make_pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss
    from sklearn.calibration import calibration_curve
    import joblib
    games = df.groupby('GAME_ID').GAME_DATE.min().sort_values(kind='stable')
    dates = sorted(games.unique()); a = dates[int(len(dates)*.70)]; b = dates[int(len(dates)*.85)]
    groups = [df[df.GAME_DATE < a], df[(df.GAME_DATE >= a)&(df.GAME_DATE < b)], df[df.GAME_DATE >= b]]
    model = make_pipeline(SimpleImputer(add_indicator=True), StandardScaler(), LogisticRegression(max_iter=1500, random_state=42))
    model.fit(groups[0][FEATURES], groups[0].SHOT_MADE_FLAG)
    results = {'features': FEATURES, 'split_dates': [str(a), str(b)], 'partitions': {k: {'shots': len(v), 'games': v.GAME_ID.nunique()} for k,v in zip(['train','validation','test'],groups)}, 'scores': {}}
    for label, subset in zip(['validation','test'], groups[1:]):
        y = subset.SHOT_MADE_FLAG
        pred = model.predict_proba(subset[FEATURES])[:,1]
        reference = np.full(len(y), groups[0].SHOT_MADE_FLAG.mean())
        results['scores'][label] = {}
        for name,p in [('logistic',pred),('constant',reference)]:
            results['scores'][label][name] = {'ROC-AUC': roc_auc_score(y,p), 'Brier': brier_score_loss(y,p), 'Log loss': log_loss(y,p)}
        if label == 'test':
            actual, estimated = calibration_curve(y,pred,n_bins=10)
            results['calibration'] = {'predicted': estimated.tolist(), 'observed': actual.tolist()}
    names = model[:-1].get_feature_names_out(FEATURES)
    results['coefficients'] = dict(zip(names, model[-1].coef_[0].tolist()))
    (ROOT/'artifacts').mkdir(exist_ok=True)
    joblib.dump(model, ROOT/'artifacts/model.joblib')
    (ROOT/'artifacts/evaluation.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    return results
