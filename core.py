import json
import numpy as np
import pandas as pd

# Compatibility exports for the existing app and model.
from etl import ROOT, clutch, prepare, read_archive

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
