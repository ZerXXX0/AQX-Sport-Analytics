import json
import joblib
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from core import ROOT, FEATURES, metrics, zones, clutch

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='ClutchIQ',
    page_icon='🏀',
    layout='wide',
    initial_sidebar_state='expanded'
)

# ── Design-system CSS (Stitch tokens) ────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet">
<style>
  :root {
    --bg:           #0c1322;
    --surf-low:     #141b2b;
    --surf:         #191f2f;
    --surf-high:    #232a3a;
    --surf-highest: #2e3545;
    --surf-lowest:  #070e1d;
    --on-surf:      #dce2f7;
    --on-var:       #a98a80;
    --primary:      #ff6b35;
    --primary-dim:  #ffb59d;
    --secondary:    #41eec2;
    --font:         'Inter', sans-serif;
    --mono:         'JetBrains Mono', monospace;
  }
  html, body, [data-testid="stApp"] {
    background: var(--bg) !important;
    color: var(--on-surf) !important;
    font-family: var(--font) !important;
  }
  [data-testid="stHeader"], [data-testid="stDecoration"], footer { display:none!important; }

  /* Sidebar */
  [data-testid="stSidebar"] { background: var(--surf-lowest)!important; border-right:1px solid var(--surf-high)!important; }
  [data-testid="stSidebar"] label { font-family:var(--mono)!important; font-size:10px!important; letter-spacing:.05em; text-transform:uppercase; color:var(--on-var)!important; }
  [data-testid="stSidebar"] select { background:var(--surf-high)!important; color:var(--on-surf)!important; border:1px solid var(--surf-highest)!important; border-radius:4px!important; font-size:13px!important; }

  /* Tabs — single row, no wrap */
  [data-testid="stTabs"] [role="tablist"] { display:flex!important; flex-wrap:nowrap!important; white-space:nowrap!important; overflow:visible!important; gap:0!important; border-bottom:1px solid var(--surf-high)!important; background:transparent!important; }
  [data-testid="stTabs"] [role="tab"] { font-family:var(--font)!important; font-size:13px!important; font-weight:500!important; color:#6B7280!important; padding:10px 16px!important; white-space:nowrap!important; border:none!important; background:transparent!important; transition:color .15s!important; }
  [data-testid="stTabs"] [role="tab"]:hover { color:var(--on-surf)!important; }
  [data-testid="stTabs"] [role="tab"][aria-selected="true"] { color:#fff!important; font-weight:700!important; border-bottom:3px solid var(--primary)!important; }
  [data-testid="stTabs"] [data-baseweb="tab-highlight"] { display:none!important; }

  /* Metrics */
  [data-testid="stMetric"] { background:var(--surf-low)!important; border-radius:6px!important; padding:16px!important; border-left:3px solid var(--primary)!important; transition:box-shadow .2s,background .2s!important; }
  [data-testid="stMetric"]:hover { background:var(--surf)!important; box-shadow:0 0 24px -4px rgba(255,107,53,.18)!important; }
  [data-testid="stMetricLabel"] p { font-family:var(--mono)!important; font-size:10px!important; letter-spacing:.05em!important; text-transform:uppercase!important; color:var(--on-var)!important; }
  [data-testid="stMetricValue"] { font-family:var(--mono)!important; font-size:26px!important; font-weight:700!important; letter-spacing:-0.02em!important; color:var(--on-surf)!important; }

  /* Dataframes */
  [data-testid="stDataFrame"] { border-radius:6px!important; overflow:hidden!important; border:1px solid var(--surf-high)!important; }

  /* Sliders */
  [data-testid="stSlider"] [role="slider"] { background:var(--primary)!important; border:2px solid var(--bg)!important; box-shadow:0 0 8px rgba(255,107,53,.4)!important; }

  /* Buttons */
  [data-testid="stFormSubmitButton"] button, [data-testid="baseButton-secondary"] {
    background:var(--primary)!important; color:var(--bg)!important;
    font-family:var(--font)!important; font-weight:600!important;
    border:none!important; border-radius:4px!important;
    transition:filter .15s,box-shadow .15s!important;
  }
  [data-testid="stFormSubmitButton"] button:hover, [data-testid="baseButton-secondary"]:hover {
    filter:brightness(1.1)!important; box-shadow:0 0 12px rgba(255,107,53,.4)!important;
  }

  /* Caption */
  [data-testid="stCaptionContainer"] p { font-family:var(--font)!important; font-size:12px!important; color:var(--on-var)!important; font-style:italic!important; }

  /* Multiselect tag */
  [data-testid="stMultiSelect"] [data-baseweb="tag"] { background:var(--primary)!important; color:var(--bg)!important; font-family:var(--mono)!important; font-size:11px!important; border-radius:999px!important; }

  /* Card helper classes */
  .iq-card { background:var(--surf-low); border-radius:8px; padding:20px; border:1px solid var(--surf-high); margin-bottom:16px; }
  .iq-card-header { font-family:var(--font); font-size:18px; font-weight:600; letter-spacing:-0.01em; color:var(--on-surf); margin:0 0 4px; }
  .iq-card-sub { font-size:12px; color:var(--on-var); margin:0 0 16px; }
  .iq-badge { display:inline-block; padding:2px 8px; border-radius:4px; background:var(--surf-highest); color:var(--secondary); font-family:var(--mono); font-size:10px; font-weight:600; letter-spacing:.05em; text-transform:uppercase; vertical-align:middle; margin-left:8px; }
  .iq-insight { background:rgba(255,107,53,.08); border-left:3px solid var(--primary); border-radius:4px; padding:12px 16px; font-size:13px; color:var(--on-surf); margin-top:12px; }
  .iq-stat-row { display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid var(--surf-high); }
  .iq-stat-label { font-size:12px; color:var(--on-var); }
  .iq-stat-val { font-family:var(--mono); font-size:13px; font-weight:600; color:var(--on-surf); }
  .iq-def-term { font-family:var(--mono); font-weight:700; color:var(--primary); font-size:13px; }
  .iq-code-block { background:var(--surf-lowest); border-radius:6px; padding:16px; font-family:var(--mono); font-size:12px; color:#4ade80; white-space:pre; overflow-x:auto; border:1px solid var(--surf-high); }
  .iq-partition-card { background:var(--surf-high); border-radius:6px; padding:16px; text-align:center; }
  .iq-partition-num { font-family:var(--mono); font-size:28px; font-weight:700; color:var(--on-surf); letter-spacing:-0.02em; }
  .iq-partition-sub { font-size:12px; color:var(--on-var); margin-top:2px; }
</style>
""", unsafe_allow_html=True)

# ── Plotly theme helper ──────────────────────────────────────────────────────
_THEME = dict(
    template='plotly_dark',
    paper_bgcolor='#141b2b',
    plot_bgcolor='#141b2b',
    font=dict(family='Inter, sans-serif', color='#dce2f7', size=12),
    margin=dict(l=16, r=16, t=32, b=16),
    colorway=['#ff6b35', '#41eec2', '#ffb59d', '#7b899e'],
    xaxis=dict(gridcolor='#232a3a', linecolor='#232a3a', zerolinecolor='#232a3a'),
    yaxis=dict(gridcolor='#232a3a', linecolor='#232a3a', zerolinecolor='#232a3a'),
)

def apply_theme(fig, height=360):
    fig.update_layout(height=height, **_THEME)
    return fig


def _fmt_metric(k, v):
    """Format a metric value for display in HTML."""
    if k == 'Attempts':
        return f'{int(v):,}'
    try:
        return f'{float(v):.2f}'
    except (TypeError, ValueError):
        return str(v)


def _metric_rows_html(m: dict) -> str:
    """Build HTML rows for a metric dict."""
    rows = []
    for k, v in m.items():
        rows.append(
            f'<div class="iq-stat-row">'
            f'<span class="iq-stat-label">{k}</span>'
            f'<span class="iq-stat-val">{_fmt_metric(k, v)}</span>'
            f'</div>'
        )
    return ''.join(rows)


# ── Sidebar logo ─────────────────────────────────────────────────────────────
st.sidebar.markdown("""
<div style="padding:4px 0 12px;display:flex;align-items:center;gap:10px;">
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#FF6B35"
       stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <path d="M5 5a10 10 0 0 0 14 14"/>
    <path d="M19 5a10 10 0 0 0-14 14"/>
    <line x1="12" y1="2" x2="12" y2="22"/>
    <line x1="2" y1="12" x2="22" y2="12"/>
  </svg>
  <span style="font-family:'Inter',sans-serif;font-size:20px;font-weight:700;color:#fff;letter-spacing:-0.02em;">ClutchIQ</span>
</div>
<p style="font-size:11px;color:#a98a80;font-style:italic;line-height:1.4;margin:0 0 16px;">
  Smarter shot selection through NBA analytics · 2023/24 regular season
</p>
<div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.05em;
            text-transform:uppercase;color:#a98a80;margin-bottom:6px;">⬡ Filters</div>
""", unsafe_allow_html=True)

# ── Guard: pipeline not built ────────────────────────────────────────────────
if not (ROOT / 'data/shots.parquet').exists():
    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                min-height:60vh;gap:16px;text-align:center;">
      <h2 style="font-size:24px;font-weight:700;color:#dce2f7;">Dataset not ready</h2>
      <p style="color:#a98a80;font-size:14px;">
        Run <code style="background:#232a3a;padding:2px 6px;border-radius:4px;color:#ff6b35;">
        python build.py</code> first.
      </p>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── Load data ────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    return pd.read_parquet(ROOT / 'data/shots.parquet')

@st.cache_resource
def load_model():
    return joblib.load(ROOT / 'artifacts/model.joblib')

@st.cache_data
def load_evaluation():
    return json.loads((ROOT / 'artifacts/evaluation.json').read_text())

@st.cache_data
def load_manifest():
    p = ROOT / 'data/manifest.json'
    return json.loads(p.read_text()) if p.exists() else {}

data = load_data()

# ── Sidebar filters ──────────────────────────────────────────────────────────
team   = st.sidebar.selectbox('Team',      ['All'] + sorted(data.TEAM_NAME.unique()))
base   = data if team == 'All' else data[data.TEAM_NAME == team]
player = st.sidebar.selectbox('Player',    ['All'] + sorted(base.PLAYER_NAME.unique()))
period = st.sidebar.selectbox('Quarter',   ['All'] + sorted(data.PERIOD.unique().tolist()))
kind   = st.sidebar.selectbox('Shot type', ['All', '2PT Field Goal', '3PT Field Goal'])

st.sidebar.markdown("""
<div style="margin-top:24px;padding-top:16px;border-top:1px solid #232a3a;">
  <p style="font-size:11px;color:#a98a80;font-style:italic;line-height:1.5;margin:0 0 12px;">
    League benchmark follows quarter and shot type across all teams.
  </p>
  <div style="display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;
              font-size:10px;text-transform:uppercase;letter-spacing:.05em;">
    <span style="color:#a98a80;">Telemetry v2.4</span>
    <span style="color:#41eec2;font-weight:700;">READY</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Apply filters ────────────────────────────────────────────────────────────
df     = base if player == 'All' else base[base.PLAYER_NAME == player]
league = data.copy()

if period != 'All':
    df     = df[df.PERIOD == period]
    league = league[league.PERIOD == period]
if kind != 'All':
    df     = df[df.SHOT_TYPE == kind]
    league = league[league.SHOT_TYPE == kind]

if df.empty:
    st.markdown('<div class="iq-insight">⚠️ No attempts match the current filters.</div>',
                unsafe_allow_html=True)
    st.stop()

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_labels = ['Overview', 'Shot Explorer', 'Clutch Analysis',
              'Player Comparison', 'Shot Prediction', 'Methodology']
tabs = st.tabs(tab_labels)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 0 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown("""
    <div style="margin-bottom:20px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
        <span style="width:8px;height:8px;border-radius:50%;background:#ff6b35;
                     box-shadow:0 0 8px rgba(255,107,53,.8);display:inline-block;"></span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:10px;
                     letter-spacing:.1em;text-transform:uppercase;color:#a98a80;">
          Macro Analytics · Cohort 2023-24</span>
      </div>
      <h2 style="font-family:'Inter',sans-serif;font-size:32px;font-weight:700;
                 letter-spacing:-0.02em;color:#dce2f7;margin:0;">Shooting Profile</h2>
    </div>
    """, unsafe_allow_html=True)

    # Metric cards
    m = metrics(df)
    game_count = df.GAME_ID.nunique()
    col_keys = ['Games', 'Attempts', 'FG%', 'eFG%', 'Points / attempt']
    all_vals  = {'Games': game_count, **m}
    cols = st.columns(len(col_keys))
    for i, k in enumerate(col_keys):
        v = all_vals.get(k, 0)
        if k == 'Games':
            display = f'{int(v):,}'
        elif k == 'Attempts':
            display = f'{int(v):,}'
        else:
            display = f'{float(v):.2f}'
        cols[i].metric(k, display)

    # Points per attempt over time
    st.markdown('<div class="iq-card">', unsafe_allow_html=True)
    st.markdown("""
    <p class="iq-card-header">Points per Attempt Over Time
      <span class="iq-badge">NBA Aggregated</span>
    </p>
    <p class="iq-card-sub">Scoring yield per field goal attempt across calendar windows</p>
    """, unsafe_allow_html=True)

    daily = (df.groupby('GAME_DATE')
               .agg(points=('points', 'sum'), attempts=('points', 'size'))
               .reset_index())
    daily['ppa'] = daily.points / daily.attempts.replace(0, float('nan'))
    league_avg = float(league.points.sum() / max(len(league), 1))

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=daily.GAME_DATE, y=daily['ppa'],
        mode='lines+markers',
        line=dict(color='#ff6b35', width=2.5),
        marker=dict(color='#070e1d', size=6, line=dict(color='#ff6b35', width=2)),
        fill='tozeroy', fillcolor='rgba(255,107,53,0.08)',
        name='Rolling Efficiency',
        hovertemplate='%{x|%b %d, %Y}<br><b>%{y:.3f}</b> Pts/Att<extra></extra>'
    ))
    fig_trend.add_hline(
        y=league_avg, line=dict(color='#41eec2', width=1, dash='dot'),
        annotation_text=f'Lg Benchmark: {league_avg:.2f}',
        annotation=dict(font=dict(color='#41eec2', size=10))
    )
    apply_theme(fig_trend, height=300)
    st.plotly_chart(fig_trend, use_container_width=True)
    st.caption('Daily aggregate · changes reflect different opponents and samples.')
    st.markdown('</div>', unsafe_allow_html=True)

    # Player table
    st.markdown('<div class="iq-card">', unsafe_allow_html=True)
    st.markdown("""
    <p class="iq-card-header">Top Volume Scorers & Efficiency Breakdown</p>
    <p class="iq-card-sub">Player-level offensive load versus conversion rate</p>
    """, unsafe_allow_html=True)
    player_tbl = (df.groupby('PLAYER_NAME')
                    .agg(attempts=('points', 'size'),
                         makes=('SHOT_MADE_FLAG', 'sum'),
                         points=('points', 'sum'))
                    .assign(**{'FG%': lambda x: (100 * x.makes / x.attempts).round(1)})
                    .sort_values('attempts', ascending=False))
    st.dataframe(player_tbl, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — SHOT EXPLORER
# ═══════════════════════════════════════════════════════════════════════════
with tabs[1]:
    from charts import court

    st.markdown("""
    <div style="margin-bottom:20px;">
      <h2 style="font-family:'Inter',sans-serif;font-size:32px;font-weight:700;
                 letter-spacing:-0.02em;color:#dce2f7;margin:0;">Spatial Shot Distribution</h2>
      <p style="font-size:13px;color:#a98a80;margin:4px 0 0;">
        Court coordinates in feet · basket at origin (0,0) ·
        <span style="color:#41eec2;">{:,}</span> field goal events
      </p>
    </div>
    """.format(len(df)), unsafe_allow_html=True)

    left_col, right_col = st.columns([1.2, 1])

    with left_col:
        st.markdown('<div class="iq-card">', unsafe_allow_html=True)
        st.markdown('<p class="iq-card-header">Half-Court Shot Chart</p>', unsafe_allow_html=True)
        fig_court = court(df)
        apply_theme(fig_court, height=520)
        st.plotly_chart(fig_court, use_container_width=True)
        st.caption('Made shots = teal circles · Missed shots = slate × markers. '
                   'Beyond-half-court attempts may lie outside the visible area.')
        st.markdown('</div>', unsafe_allow_html=True)

    with right_col:
        z     = zones(df)
        bench = zones(league)[['SHOT_ZONE_BASIC', 'FG%']].rename(columns={'FG%': 'League FG%'})
        comp  = z.merge(bench, on='SHOT_ZONE_BASIC')

        st.markdown('<div class="iq-card">', unsafe_allow_html=True)
        st.markdown('<p class="iq-card-header">FG% by Zone vs League</p>', unsafe_allow_html=True)
        fig_zone = go.Figure()
        fig_zone.add_bar(x=comp.SHOT_ZONE_BASIC, y=comp['FG%'],
                         name='Selected', marker_color='#ff6b35')
        fig_zone.add_bar(x=comp.SHOT_ZONE_BASIC, y=comp['League FG%'],
                         name='League', marker_color='#41eec2')
        fig_zone.update_layout(barmode='group', xaxis_tickangle=-30,
                                legend=dict(orientation='h', y=1.12))
        apply_theme(fig_zone, height=240)
        st.plotly_chart(fig_zone, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="iq-card">', unsafe_allow_html=True)
        st.markdown('<p class="iq-card-header">Attempts by Zone</p>', unsafe_allow_html=True)
        fig_att = px.bar(z.sort_values('attempts', ascending=False),
                         x='SHOT_ZONE_BASIC', y='attempts',
                         color_discrete_sequence=['#ff6b35'])
        fig_att.update_traces(marker_line_width=0)
        apply_theme(fig_att, height=200)
        st.plotly_chart(fig_att, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="iq-card">', unsafe_allow_html=True)
    st.markdown('<p class="iq-card-header">Zone Breakdown Table</p>', unsafe_allow_html=True)
    st.dataframe(z, use_container_width=True)
    reliable = z[z.attempts >= 30].sort_values('Points / attempt', ascending=False)
    if len(reliable):
        best = reliable.iloc[0]
        st.markdown(
            f'<div class="iq-insight">🏆 <b>Best Zone:</b> {best.SHOT_ZONE_BASIC} · '
            f'<b>{float(best["Points / attempt"]):.2f}</b> pts/attempt · '
            f'n={int(best.attempts)} attempts. '
            f'<span style="color:#a98a80;font-size:11px;">'
            f'Historical association only.</span></div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — CLUTCH ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("""
    <div style="margin-bottom:20px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
        <span style="background:#ff6b35;color:#070e1d;padding:2px 8px;border-radius:4px;
                     font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;
                     letter-spacing:.05em;text-transform:uppercase;">Module 03</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:10px;
                     letter-spacing:.1em;text-transform:uppercase;color:#a98a80;">
          High Leverage Index</span>
      </div>
      <h2 style="font-family:'Inter',sans-serif;font-size:32px;font-weight:700;
                 letter-spacing:-0.02em;color:#dce2f7;margin:0;">Close Games, Event by Event</h2>
      <p style="font-size:14px;color:#a98a80;margin:4px 0 0;">
        Evaluating late-clock and high-leverage shot execution under clutch constraints.</p>
    </div>
    """, unsafe_allow_html=True)

    # Sliders
    st.markdown('<div class="iq-card">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        minutes = st.slider('Maximum minutes remaining', 1, 5, 5, key='clutch_min')
    with c2:
        margin  = st.slider('Maximum absolute score margin', 1, 15, 5, key='clutch_gap')
    st.markdown('</div>', unsafe_allow_html=True)

    known = df[df.score_margin_before.notna()].copy()
    known['Clutch'] = clutch(
        known.PERIOD, known.seconds_remaining,
        known.score_margin_before, minutes * 60, margin
    )
    excluded = len(df) - len(known)
    st.caption(
        f'Q4/OT · time ≤{minutes}:00 · |margin| ≤{margin} · '
        f'{excluded} attempts excluded (unknown score context)'
    )

    clutch_df    = known[known.Clutch]
    nonclutch_df = known[~known.Clutch]
    clutch_m     = metrics(clutch_df)
    nonclutch_m  = metrics(nonclutch_df)

    # Comparison cards — built with helper to avoid f-string format bugs
    c_col1, c_col2 = st.columns(2)
    with c_col1:
        html_rows = _metric_rows_html(clutch_m)
        st.markdown(f"""
        <div class="iq-card" style="border-left:3px solid #ff6b35;">
          <div style="font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;
                      letter-spacing:.05em;color:#ff6b35;text-transform:uppercase;margin-bottom:12px;">
            🔥 CLUTCH <span style="color:#a98a80;font-weight:400;">({len(clutch_df):,} attempts)</span>
          </div>
          {html_rows}
        </div>
        """, unsafe_allow_html=True)

    with c_col2:
        html_rows2 = _metric_rows_html(nonclutch_m)
        st.markdown(f"""
        <div class="iq-card" style="border-left:3px solid #41eec2;">
          <div style="font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;
                      letter-spacing:.05em;color:#41eec2;text-transform:uppercase;margin-bottom:12px;">
            NON-CLUTCH <span style="color:#a98a80;font-weight:400;">({len(nonclutch_df):,} attempts)</span>
          </div>
          {html_rows2}
        </div>
        """, unsafe_allow_html=True)

    # Bar chart comparison
    rows  = [{'Situation': name, **metrics(known[known.Clutch == flag])}
             for flag, name in [(True, 'Clutch'), (False, 'Non-Clutch')]]
    tbl   = pd.DataFrame(rows)
    fig_c = px.bar(tbl, x='Situation', y='FG%', color='Situation',
                   color_discrete_map={'Clutch': '#ff6b35', 'Non-Clutch': '#41eec2'},
                   text='FG%')
    fig_c.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig_c.update_layout(showlegend=False)
    apply_theme(fig_c, height=280)

    st.markdown('<div class="iq-card">', unsafe_allow_html=True)
    st.markdown('<p class="iq-card-header">FG% — Clutch vs Non-Clutch</p>', unsafe_allow_html=True)
    st.plotly_chart(fig_c, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="iq-card">', unsafe_allow_html=True)
    st.markdown('<p class="iq-card-header">Clutch Zone Breakdown</p>', unsafe_allow_html=True)
    if len(clutch_df):
        st.dataframe(zones(clutch_df), use_container_width=True)
    else:
        st.info('No clutch attempts for the current filter selection.')
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 3 — PLAYER COMPARISON
# ═══════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown("""
    <div style="margin-bottom:20px;">
      <h2 style="font-family:'Inter',sans-serif;font-size:32px;font-weight:700;
                 letter-spacing:-0.02em;color:#dce2f7;margin:0;">Player Comparison</h2>
      <p style="font-size:13px;color:#a98a80;margin:4px 0 0;">
        Descriptive comparisons — not adjusted for defenders, roles, or shot difficulty.</p>
    </div>
    """, unsafe_allow_html=True)

    pool = base.copy()
    if period != 'All': pool = pool[pool.PERIOD == period]
    if kind   != 'All': pool = pool[pool.SHOT_TYPE == kind]

    all_players = sorted(base.PLAYER_NAME.unique())
    names = st.multiselect(
        'Select players to compare',
        all_players,
        default=all_players[:min(3, len(all_players))]
    )

    if names:
        comparison = pd.DataFrame(
            [{'Player': n, **metrics(pool[pool.PLAYER_NAME == n])} for n in names]
        ).set_index('Player')

        st.markdown('<div class="iq-card">', unsafe_allow_html=True)
        st.markdown('<p class="iq-card-header">Metrics Table</p>', unsafe_allow_html=True)
        st.dataframe(comparison, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if len(names) >= 2:
            metric_cols = ['FG%', 'eFG%', 'Points / attempt']
            colors = ['#ff6b35', '#41eec2', '#ffb59d', '#7b899e']
            fig_comp = go.Figure()
            for i, n in enumerate(names):
                row = metrics(pool[pool.PLAYER_NAME == n])
                fig_comp.add_bar(
                    name=n,
                    x=metric_cols,
                    y=[float(row.get(c, 0)) for c in metric_cols],
                    marker_color=colors[i % len(colors)]
                )
            fig_comp.update_layout(barmode='group')
            apply_theme(fig_comp, height=280)
            st.markdown('<div class="iq-card">', unsafe_allow_html=True)
            st.markdown('<p class="iq-card-header">Efficiency Comparison</p>', unsafe_allow_html=True)
            st.plotly_chart(fig_comp, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="iq-insight">Select at least one player above.</div>',
                    unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 4 — SHOT PREDICTION
# ═══════════════════════════════════════════════════════════════════════════
with tabs[4]:
    evaluation = load_evaluation()

    st.markdown("""
    <div style="margin-bottom:20px;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
        <span style="font-family:'JetBrains Mono',monospace;font-size:10px;
                     letter-spacing:.1em;text-transform:uppercase;color:#ff6b35;">
          Inference Engine</span>
        <span style="color:#a98a80;font-size:10px;">/</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#a98a80;">
          Logit Calibration Model v2.8</span>
      </div>
      <h2 style="font-family:'Inter',sans-serif;font-size:32px;font-weight:700;
                 letter-spacing:-0.02em;color:#dce2f7;margin:0;">Shot Success Prediction</h2>
      <p style="font-size:13px;color:#a98a80;margin:4px 0 0;">
        What-if analysis powered by regularized logistic regression.
        Sidebar filters do not retrain the model.</p>
    </div>
    """, unsafe_allow_html=True)

    sim_col, res_col = st.columns([1, 1.2])

    with sim_col:
        st.markdown('<div class="iq-card">', unsafe_allow_html=True)
        st.markdown("""
        <p class="iq-card-header">Shot Simulator</p>
        <p class="iq-card-sub">Adjust parameters and run inference</p>
        """, unsafe_allow_html=True)
        with st.form('predict_form'):
            x_val  = st.slider('Width from basket — X coordinate (ft)', -25.0, 25.0, 0.0, 0.5)
            y_val  = st.slider('Length from basket — Y coordinate (ft)', -5.0, 42.0, 15.0, 0.5)
            value  = st.selectbox('Shot value', [2, 3])
            period_pred = st.selectbox('Period', [1, 2, 3, 4, 5, 6])
            max_sec = 300 if period_pred >= 5 else 720
            sec    = st.slider('Seconds remaining in period', 0, max_sec, min(120, max_sec))
            gap    = st.slider('Home minus away score before shot', -40, 40, 0)
            submit = st.form_submit_button('⚡ Estimate Probability', use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with res_col:
        if submit:
            import numpy as np
            dist = float(np.sqrt(x_val**2 + y_val**2))
            inp  = pd.DataFrame(
                [[dist, float(x_val), float(y_val), int(value),
                  int(period_pred), int(sec), float(gap)]],
                columns=FEATURES
            )
            model = load_model()
            p = float(model.predict_proba(inp)[0, 1])

            # Gauge chart
            fig_gauge = go.Figure(go.Indicator(
                mode='gauge+number',
                value=p * 100,
                number=dict(suffix='%', font=dict(family='JetBrains Mono', size=36,
                                                   color='#dce2f7')),
                gauge=dict(
                    axis=dict(range=[0, 100],
                              tickfont=dict(color='#a98a80', size=10)),
                    bar=dict(color='#ff6b35'),
                    bgcolor='#141b2b',
                    borderwidth=0,
                    steps=[dict(range=[0, 100], color='#0c1322')],
                    threshold=dict(line=dict(color='#41eec2', width=2),
                                   thickness=0.75, value=50)
                )
            ))
            apply_theme(fig_gauge, height=240)
            st.plotly_chart(fig_gauge, use_container_width=True)

            mc1, mc2 = st.columns(2)
            mc1.metric('Make Probability', f'{p:.1%}')
            mc2.metric('Expected Pts/Att', f'{p * value:.3f}')
            st.caption('Estimate excludes free throws and subsequent possessions.')
        else:
            st.markdown("""
            <div style="height:260px;display:flex;flex-direction:column;align-items:center;
                        justify-content:center;gap:12px;color:#a98a80;text-align:center;">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#ff6b35"
                   stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <path d="M5 5a10 10 0 0 0 14 14"/>
                <path d="M19 5a10 10 0 0 0-14 14"/>
                <line x1="12" y1="2" x2="12" y2="22"/>
                <line x1="2" y1="12" x2="22" y2="12"/>
              </svg>
              <p style="font-size:13px;margin:0;">
                Configure shot parameters and click<br>
                <b style="color:#ff6b35;">⚡ Estimate Probability</b>
              </p>
            </div>
            """, unsafe_allow_html=True)

    # Model performance section
    st.markdown('<div class="iq-card" style="margin-top:16px;">', unsafe_allow_html=True)
    st.markdown('<p class="iq-card-header">Model Performance</p>', unsafe_allow_html=True)
    scores = evaluation.get('scores', {})
    p1, p2, p3 = st.columns(3)
    try:
        p1.metric('Validation ROC-AUC',
                  f"{scores['validation']['logistic']['ROC-AUC']:.4f}")
        p2.metric('Test ROC-AUC',
                  f"{scores['test']['logistic']['ROC-AUC']:.4f}")
        p3.metric('Test Brier Score',
                  f"{scores['test']['logistic']['Brier']:.4f}")
    except KeyError:
        st.warning('Score data incomplete — re-run build.py.')

    st.markdown('<p class="iq-card-header" style="margin-top:20px;">Calibration Curve</p>',
                unsafe_allow_html=True)
    cal = evaluation.get('calibration', {})
    if cal:
        fig_cal = go.Figure()
        fig_cal.add_trace(go.Scatter(
            x=cal['predicted'], y=cal['observed'],
            mode='lines+markers',
            line=dict(color='#ff6b35', width=2),
            marker=dict(color='#ff6b35', size=7,
                        line=dict(color='#070e1d', width=1.5)),
            name='Model'
        ))
        fig_cal.add_trace(go.Scatter(
            x=[0, 1], y=[0, 1],
            mode='lines',
            line=dict(color='#41eec2', width=1, dash='dot'),
            name='Ideal'
        ))
        fig_cal.update_layout(
            xaxis_title='Predicted Probability',
            yaxis_title='Observed Make Rate',
            legend=dict(orientation='h', y=1.08)
        )
        apply_theme(fig_cal, height=280)
        st.plotly_chart(fig_cal, use_container_width=True)

    st.markdown('<p class="iq-card-header" style="margin-top:20px;">'
                'Standardized Logistic Coefficients</p>', unsafe_allow_html=True)
    st.caption('Associations only — not causal effects.')
    coefs = evaluation.get('coefficients', {})
    if coefs:
        coef_df = pd.Series(coefs, name='Coefficient').to_frame()
        st.dataframe(
            coef_df.style.bar(color=['#ff6b35', '#41eec2'], align='zero'),
            use_container_width=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 5 — METHODOLOGY
# ═══════════════════════════════════════════════════════════════════════════
with tabs[5]:
    manifest   = load_manifest()
    evaluation = load_evaluation()

    st.markdown("""
    <div style="margin-bottom:24px;">
      <h2 style="font-family:'Inter',sans-serif;font-size:32px;font-weight:700;
                 letter-spacing:-0.02em;color:#dce2f7;margin:0;">Methodology</h2>
      <p style="font-size:13px;color:#a98a80;margin:4px 0 0;">
        Data sources, metric definitions, model details, and limitations.</p>
    </div>
    """, unsafe_allow_html=True)

    # Data source
    st.markdown("""
    <div class="iq-card">
      <p class="iq-card-header">📁 Data Source</p>
      <p style="font-size:13px;color:#a98a80;margin:0 0 12px;">
        Source: <a href="https://github.com/shufinskiy/nba_data"
        style="color:#ff6b35;">github.com/shufinskiy/nba_data</a> — compiled from NBA sources.
        Credit the repository maintainer and NBA.
        Repository software license does not establish all third-party data rights.
      </p>
    </div>
    """, unsafe_allow_html=True)

    if manifest:
        st.markdown(
            f'<div class="iq-code-block">{json.dumps(manifest, indent=2)}</div>',
            unsafe_allow_html=True
        )

    # Metric definitions
    st.markdown("""
    <div class="iq-card" style="margin-top:16px;">
      <p class="iq-card-header">📊 Metric Definitions</p>
      <div style="display:flex;flex-direction:column;gap:10px;margin-top:8px;">
        <div><span class="iq-def-term">FG%</span>
             <span style="font-size:13px;color:#dce2f7;margin-left:8px;">— Makes ÷ Attempts</span></div>
        <div><span class="iq-def-term">eFG%</span>
             <span style="font-size:13px;color:#dce2f7;margin-left:8px;">— (Makes + 0.5 × Three-Point Makes) ÷ Attempts</span></div>
        <div><span class="iq-def-term">Points / Attempt</span>
             <span style="font-size:13px;color:#dce2f7;margin-left:8px;">— Observed FG points only; excludes free throws</span></div>
        <div><span class="iq-def-term">Clutch</span>
             <span style="font-size:13px;color:#dce2f7;margin-left:8px;">— Q4/OT · time ≤5:00 · |margin| ≤5 before the shot</span></div>
        <div><span class="iq-def-term">Wilson CI</span>
             <span style="font-size:13px;color:#dce2f7;margin-left:8px;">— 95% binomial confidence interval for FG%; 30 attempts is a display threshold</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Model details
    parts = evaluation.get('partitions', {})
    split = evaluation.get('split_dates', ['—', '—'])
    if parts:
        t_shots = parts.get('train', {}).get('shots', 0)
        t_games = parts.get('train', {}).get('games', 0)
        v_shots = parts.get('validation', {}).get('shots', 0)
        v_games = parts.get('validation', {}).get('games', 0)
        x_shots = parts.get('test', {}).get('shots', 0)
        x_games = parts.get('test', {}).get('games', 0)
        split0  = str(split[0])[:10] if len(split) > 0 else '—'
        split1  = str(split[1])[:10] if len(split) > 1 else '—'

        st.markdown(f"""
        <div class="iq-card" style="margin-top:16px;">
          <p class="iq-card-header">🤖 Model Details</p>
          <p style="font-size:13px;color:#a98a80;margin:0 0 16px;">
            Chronological 70 / 15 / 15 split by game date — games stay together.
            Imputation and scaling fit on training data only.
            No outcome, final score, or post-shot information used as a feature.
          </p>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:12px;">
            <div class="iq-partition-card">
              <div class="iq-partition-num">{t_shots:,}</div>
              <div class="iq-partition-sub">{t_games} games</div>
              <div style="margin-top:8px;font-family:'JetBrains Mono',monospace;font-size:10px;
                          letter-spacing:.05em;color:#a98a80;text-transform:uppercase;">Train</div>
            </div>
            <div class="iq-partition-card">
              <div class="iq-partition-num" style="color:#41eec2;">{v_shots:,}</div>
              <div class="iq-partition-sub">{v_games} games</div>
              <div style="margin-top:8px;font-family:'JetBrains Mono',monospace;font-size:10px;
                          letter-spacing:.05em;color:#41eec2;text-transform:uppercase;">Validation</div>
            </div>
            <div class="iq-partition-card">
              <div class="iq-partition-num" style="color:#ff6b35;">{x_shots:,}</div>
              <div class="iq-partition-sub">{x_games} games</div>
              <div style="margin-top:8px;font-family:'JetBrains Mono',monospace;font-size:10px;
                          letter-spacing:.05em;color:#ff6b35;text-transform:uppercase;">Test</div>
            </div>
          </div>
          <p style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#a98a80;margin:0;">
            Train/Val split: {split0} · Val/Test split: {split1}
          </p>
        </div>
        """, unsafe_allow_html=True)

    # Limitations
    st.markdown("""
    <div class="iq-card" style="margin-top:16px;">
      <p class="iq-card-header">⚠️ Limitations</p>
      <ul style="font-size:13px;color:#a98a80;font-style:italic;line-height:1.8;margin:0;padding-left:20px;">
        <li>No defender distance or shot-clock data in the inspected schemas</li>
        <li>Estimates are observational associations, not causal recommendations</li>
        <li>Data is historical — app does not provide live NBA results</li>
        <li>One season (2023/24 regular season) only</li>
        <li>Model uncertainty and changing player roles limit actionability</li>
        <li>Score context reconstructed from play-by-play; ordering edge cases remain</li>
        <li>Standardized coefficients reflect associations, not causal effects</li>
      </ul>
    </div>
    """, unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div style="text-align:center;margin-top:24px;padding-top:16px;border-top:1px solid #232a3a;">
      <p style="font-size:11px;color:#4b5563;font-style:italic;margin:0;">
        Historical observational analysis only. No tactical guarantees.
        ClutchIQ · 2023/24 NBA Regular Season
      </p>
    </div>
    """, unsafe_allow_html=True)
