import json
import numpy as np
import pandas as pd
from core import clutch, metrics, zones, ROOT, FEATURES

def test_clutch_boundaries():
    result=clutch(pd.Series([3,4,4,5,4,4]),pd.Series([10,300,301,60,1,1]),pd.Series([0,5,0,-5,6,np.nan]))
    assert result.tolist()==[False,True,False,True,False,False]

def test_metrics_known_fixture():
    d=pd.DataFrame({'SHOT_MADE_FLAG':[1,0,1,0],'shot_value':[2,2,3,3],'points':[2,0,3,0],'SHOT_ZONE_BASIC':['A']*4})
    m=metrics(d)
    assert m['FG%']==50 and m['3P%']==50
    assert m['Points / attempt']==1.25 and m['eFG%']==62.5
    z=zones(d).iloc[0]
    assert z['FG% lower']<50<z['FG% upper']
    assert metrics(d.iloc[:0])['Attempts']==0

def test_real_data_and_inference():
    import joblib
    d=pd.read_parquet(ROOT/'data/shots.parquet')
    assert not d.duplicated(['GAME_ID','GAME_EVENT_ID']).any()
    assert (d.is_clutch == clutch(d.PERIOD,d.seconds_remaining,d.score_margin_before)).all()
    assert d.points.sum()==(d.shot_value*d.SHOT_MADE_FLAG).sum()
    m=joblib.load(ROOT/'artifacts/model.joblib')
    p=m.predict_proba(d[FEATURES].iloc[:50])[:,1]
    assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
    e=json.loads((ROOT/'artifacts/evaluation.json').read_text())
    a,b=map(pd.Timestamp,e['split_dates'])
    sets=[set(d.loc[d.GAME_DATE<a,'GAME_ID']),set(d.loc[(d.GAME_DATE>=a)&(d.GAME_DATE<b),'GAME_ID']),set(d.loc[d.GAME_DATE>=b,'GAME_ID'])]
    assert not sets[0]&sets[1] and not sets[0]&sets[2] and not sets[1]&sets[2]

def test_streamlit_flows():
    from streamlit.testing.v1 import AppTest
    at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=90).run()
    assert not at.exception
    at.sidebar.selectbox[0].select('Atlanta Hawks').run()
    assert not at.exception
    at.sidebar.selectbox[1].select('Trae Young').run()
    assert not at.exception
    at.button[0].click().run()
    assert not at.exception
