import json
import joblib
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from core import ROOT, FEATURES, metrics, zones, clutch
from charts import render_shot_explorer

st.set_page_config(page_title='ClutchIQ',page_icon='🏀',layout='wide')
st.title('ClutchIQ 🏀')
st.caption('Smarter shot selection through NBA analytics · 2023/24 regular season')
if not (ROOT/'data/shots.parquet').exists():
    st.info('Prepare the real dataset first: python build.py'); st.stop()
@st.cache_data
def load(): return pd.read_parquet(ROOT/'data/shots.parquet')
@st.cache_resource
def model(): return joblib.load(ROOT/'artifacts/model.joblib')
data=load()
team=st.sidebar.selectbox('Team',['All']+sorted(data.TEAM_NAME.unique()))
base=data if team=='All' else data[data.TEAM_NAME==team]
player=st.sidebar.selectbox('Player',['All']+sorted(base.PLAYER_NAME.unique()))
period=st.sidebar.selectbox('Quarter',['All']+sorted(data.PERIOD.unique().tolist()))
kind=st.sidebar.selectbox('Shot type',['All','2PT Field Goal','3PT Field Goal'])
df=base if player=='All' else base[base.PLAYER_NAME==player]
league=data
if period!='All': df=df[df.PERIOD==period]; league=league[league.PERIOD==period]
if kind!='All': df=df[df.SHOT_TYPE==kind]; league=league[league.SHOT_TYPE==kind]
st.sidebar.caption('League benchmark follows quarter and shot type, across all teams and players.')
if df.empty: st.info('No attempts match these filters.'); st.stop()
tabs=st.tabs(['Overview','Shot Explorer','Clutch Analysis','Player Comparison','Shot Prediction','Methodology'])
with tabs[0]:
    st.subheader('Your shooting profile')
    vals={'Games':df.GAME_ID.nunique(),**metrics(df)}
    cols=st.columns(4)
    for i,(k,v) in enumerate(vals.items()): cols[i%4].metric(k,f'{v:,.0f}' if k in ['Games','Attempts'] else f'{v:.2f}')
    daily=df.groupby('GAME_DATE').agg(points=('points','sum'),attempts=('points','size')).reset_index()
    daily['Points / attempt']=daily.points/daily.attempts
    st.plotly_chart(px.line(daily,x='GAME_DATE',y='Points / attempt',markers=True,template='plotly_dark'),width='stretch')
    st.caption('Daily aggregate; changes can reflect different players and opponents.')
    st.dataframe(df.groupby('PLAYER_NAME').agg(attempts=('points','size'),makes=('SHOT_MADE_FLAG','sum'),points=('points','sum')).sort_values('attempts',ascending=False),width='stretch')
with tabs[1]:
    render_shot_explorer(df, league=league)
with tabs[2]:
    st.subheader('Close games, event by event')
    minutes=st.slider('Maximum minutes remaining',1,5,5)
    margin=st.slider('Maximum absolute pre-shot score margin',1,15,5)
    known=df[df.score_margin_before.notna()].copy()
    known['Clutch']=clutch(known.PERIOD,known.seconds_remaining,known.score_margin_before,minutes*60,margin)
    st.caption(f'Quarter ≥4, time ≤{minutes}:00, absolute score margin before shot ≤{margin}. Unknown score context excluded: {len(df)-len(known)} attempts.')
    rows=[{'Situation':name,**metrics(known[known.Clutch==flag])} for flag,name in [(True,'Clutch'),(False,'Non-clutch')]]
    table=pd.DataFrame(rows); st.dataframe(table,width='stretch')
    st.plotly_chart(px.bar(table,x='Situation',y='FG%',color='Situation',template='plotly_dark'),width='stretch')
    st.dataframe(zones(known[known.Clutch]),width='stretch')
with tabs[3]:
    names=st.multiselect('Compare players across the selected team / quarter / shot type',sorted(base.PLAYER_NAME.unique()),default=sorted(base.PLAYER_NAME.unique())[:2])
    pool=base
    if period!='All': pool=pool[pool.PERIOD==period]
    if kind!='All': pool=pool[pool.SHOT_TYPE==kind]
    comparison=pd.DataFrame([{'Player':n,**metrics(pool[pool.PLAYER_NAME==n])} for n in names])
    st.dataframe(comparison,width='stretch')
    st.caption('Descriptive comparisons are not adjusted for defenders, roles, or shot difficulty.')
with tabs[4]:
    evaluation=json.loads((ROOT/'artifacts/evaluation.json').read_text())
    st.subheader('Shot-success model')
    st.caption('Independent what-if inputs; sidebar filters do not retrain this model. Shot clock and defender tracking are unavailable.')
    with st.form('predict'):
        x=st.slider('Width from basket (feet)',-25.,25.,0.)
        y=st.slider('Length from basket (feet)',-5.,42.,15.)
        value=st.selectbox('Shot value',[2,3]); q=st.selectbox('Period',[1,2,3,4,5,6])
        sec=st.slider('Seconds remaining in period',0,300 if q>=5 else 720,120)
        gap=st.slider('Home minus away score before shot',-40,40,0)
        submit=st.form_submit_button('Estimate probability')
    if submit:
        inp=pd.DataFrame([[round((x*x+y*y)**.5),x,y,value,q,sec,gap]],columns=FEATURES)
        p=model().predict_proba(inp)[0,1]
        st.metric('Estimated make probability',f'{p:.1%}'); st.metric('Model-estimated points / attempt',f'{p*value:.2f}')
        st.caption('User-specified shot value; verify it matches court geometry. Estimate excludes free throws and subsequent possessions.')
    st.write('Held-out test results'); st.dataframe(pd.DataFrame(evaluation['scores']['test']).T)
    cal=evaluation['calibration']; fig=go.Figure(go.Scatter(x=cal['predicted'],y=cal['observed'],mode='lines+markers',name='Model'))
    fig.add_trace(go.Scatter(x=[0,1],y=[0,1],mode='lines',name='Ideal'))
    fig.update_layout(xaxis_title='Predicted probability',yaxis_title='Observed make rate',template='plotly_dark')
    st.plotly_chart(fig,width='stretch')
    st.write('Standardized logistic coefficients (associations, not causal effects)')
    st.dataframe(pd.Series(evaluation['coefficients'],name='Coefficient'))
with tabs[5]:
    st.write('Source: https://github.com/shufinskiy/nba_data — compiled from NBA sources. Credit the repository maintainer and NBA; repository software license does not establish all third-party data rights.')
    st.json(json.loads((ROOT/'data/manifest.json').read_text()))
    st.write('FG% = makes / attempts. eFG% = (makes + 0.5 × three-point makes) / attempts. Observed points/attempt excludes free throws. Zone intervals are 95% Wilson intervals; 30 attempts is a display threshold, not proof of reliability.')
    st.write('Clutch uses the pre-event score reconstructed from sorted play-by-play. Unmatched/ambiguous events retain unknown context. Scores assume the initial score is 0–0; source corrections and event ordering remain limitations.')
    st.write('Chronological 70/15/15 split by date; games stay together. Imputation and scaling fit training data only. No outcome, final score, shot-result description, or post-shot score is used as a feature.')
    st.json(evaluation['partitions'])
    st.caption('Historical observational analysis. No defender distance, shot clock, fatigue, or full tactical context. Model uncertainty and changing player roles limit recommendations.')
