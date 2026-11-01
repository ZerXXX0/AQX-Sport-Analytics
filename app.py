import json
import joblib
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from core import ROOT, FEATURES, metrics, zones, clutch
from charts import render_shot_explorer

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='ClutchIQ',
    page_icon='🏀',
    layout='wide',
    initial_sidebar_state='expanded'
)

# ── Design-system CSS (Stitch tokens) — use st.html() to avoid text leak ─────
st.html("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet">
<style>
  :root {
    --bg:           #0c1322;
    --surf-lowest:  #070e1d;
    --surf-low:     #141b2b;
    --surf:         #191f2f;
    --surf-high:    #232a3a;
    --surf-highest: #2e3545;
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
  /* Streamlit layout & chrome */
  [data-testid="stDecoration"], footer { display: none !important; }
  [data-testid="stToolbarActions"], [data-testid="stMainMenu"] { display: none !important; }

  /* Keep stHeader transparent so expand sidebar button is accessible */
  [data-testid="stHeader"] {
    background: transparent !important;
    color: var(--on-surf) !important;
    pointer-events: none !important;
    z-index: 99999 !important;
  }
  [data-testid="stHeader"] [data-testid="stToolbar"] {
    background: transparent !important;
    pointer-events: none !important;
  }
  /* Expand sidebar button when sidebar is collapsed */
  [data-testid="stExpandSidebarButton"],
  [data-testid="stSidebarCollapsedControl"],
  button[aria-label="Expand sidebar"] {
    pointer-events: auto !important;
    visibility: visible !important;
    display: inline-flex !important;
    color: var(--on-surf) !important;
    background: var(--surf-low) !important;
    border: 1px solid var(--surf-high) !important;
    border-radius: 6px !important;
    margin: 8px 0 0 8px !important;
    padding: 6px 10px !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
  }
  [data-testid="stExpandSidebarButton"]:hover,
  [data-testid="stSidebarCollapsedControl"]:hover,
  button[aria-label="Expand sidebar"]:hover {
    color: var(--primary) !important;
    border-color: var(--primary) !important;
    background: var(--surf) !important;
    transform: translateX(2px) !important;
  }
  [data-testid="stExpandSidebarButton"] svg,
  [data-testid="stSidebarCollapsedControl"] svg,
  button[aria-label="Expand sidebar"] svg {
    fill: currentColor !important;
  }
  [data-testid="stSidebarCollapseButton"] button {
    color: var(--on-surf) !important;
    background: transparent !important;
    border-radius: 6px !important;
    transition: all 0.15s ease !important;
  }
  [data-testid="stSidebarCollapseButton"] button:hover {
    color: var(--primary) !important;
    background: var(--surf-high) !important;
  }

  [data-testid="stMainBlockContainer"] { padding-top: 1rem !important; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: var(--surf-lowest)!important;
    border-right: 1px solid var(--surf-high)!important;
  }
  [data-testid="stSidebar"] label {
    font-family: var(--mono)!important;
    font-size: 10px!important;
    letter-spacing: .05em;
    text-transform: uppercase;
    color: var(--on-var)!important;
  }
  [data-testid="stSidebar"] select,
  [data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: var(--surf-high)!important;
    color: var(--on-surf)!important;
    border: 1px solid var(--surf-highest)!important;
    border-radius: 4px!important;
    font-size: 13px!important;
  }

  /* Tabs — single row, no wrap */
  [data-testid="stTabs"] [role="tablist"] {
    display: flex!important;
    flex-wrap: nowrap!important;
    white-space: nowrap!important;
    overflow: visible!important;
    gap: 0!important;
    border-bottom: 1px solid var(--surf-high)!important;
    background: transparent!important;
    margin-bottom: 8px!important;
  }
  [data-testid="stTabs"] [role="tab"] {
    font-family: var(--font)!important;
    font-size: 13px!important;
    font-weight: 500!important;
    color: #6B7280!important;
    padding: 10px 16px!important;
    white-space: nowrap!important;
    border: none!important;
    background: transparent!important;
    transition: color .15s!important;
  }
  [data-testid="stTabs"] [role="tab"]:hover { color: var(--on-surf)!important; }
  [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #fff!important;
    font-weight: 700!important;
    border-bottom: 3px solid var(--primary)!important;
  }
  [data-testid="stTabs"] [data-baseweb="tab-highlight"] { display: none!important; }

  /* Metrics */
  [data-testid="stMetric"] {
    background: var(--surf-low)!important;
    border-radius: 6px!important;
    padding: 16px!important;
    border-left: 3px solid var(--primary)!important;
    transition: box-shadow .2s, background .2s!important;
  }
  [data-testid="stMetric"]:hover {
    background: var(--surf)!important;
    box-shadow: 0 0 24px -4px rgba(255,107,53,.18)!important;
  }
  [data-testid="stMetricLabel"] p {
    font-family: var(--mono)!important;
    font-size: 10px!important;
    letter-spacing: .05em!important;
    text-transform: uppercase!important;
    color: var(--on-var)!important;
  }
  [data-testid="stMetricValue"] {
    font-family: var(--mono)!important;
    font-size: 26px!important;
    font-weight: 700!important;
    letter-spacing: -0.02em!important;
    color: var(--on-surf)!important;
  }

  /* Dataframes */
  [data-testid="stDataFrame"] {
    border-radius: 6px!important;
    overflow: hidden!important;
    border: 1px solid var(--surf-high)!important;
  }

  /* Sliders */
  [data-testid="stSlider"] {
    --slider-focused: 1 !important;
    padding-bottom: 14px !important;
  }
  [data-testid="stSlider"] label {
    margin-bottom: 6px !important;
  }
  [data-testid="stSlider"] label p {
    font-family: var(--font) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: var(--on-surf) !important;
    letter-spacing: -0.01em !important;
  }
  /* Slider thumb */
  [data-testid="stSlider"] [role="slider"] {
    background: var(--primary) !important;
    border: 2.5px solid #ffffff !important;
    box-shadow: 0 0 10px rgba(255, 107, 53, 0.7) !important;
    width: 18px !important;
    height: 18px !important;
    cursor: grab !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
  }
  [data-testid="stSlider"] [role="slider"]:hover,
  [data-testid="stSlider"] [role="slider"]:active {
    transform: scale(1.18) !important;
    box-shadow: 0 0 16px rgba(255, 107, 53, 0.95) !important;
    cursor: grabbing !important;
  }
  /* Current value hovering above thumb */
  [data-testid="stSliderThumbValue"] {
    font-family: var(--mono) !important;
    font-weight: 700 !important;
    font-size: 12px !important;
    color: var(--primary) !important;
    background: var(--surf-high) !important;
    padding: 2px 8px !important;
    border-radius: 4px !important;
    border: 1px solid rgba(255, 107, 53, 0.4) !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5) !important;
  }
  /* Bottom tick labels (min/max numbers) - ALWAYS VISIBLE without hover */
  [data-testid="stSliderTickBar"],
  div[data-testid="stSliderTickBar"] {
    opacity: 1 !important;
    visibility: visible !important;
    display: flex !important;
    justify-content: space-between !important;
    margin-top: 6px !important;
    transition: none !important;
  }
  [data-testid="stSliderTickBar"] > div,
  [data-testid="stSliderTickBar"] span,
  [data-testid="stSliderTickBar"] p,
  [data-testid="stSliderTickBar"] * {
    opacity: 1 !important;
    visibility: visible !important;
    color: #cbd5e1 !important;
    font-family: var(--mono) !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em !important;
  }

  /* Buttons */
  [data-testid="stFormSubmitButton"] button,
  [data-testid="baseButton-secondary"] {
    background: var(--primary)!important;
    color: #070e1d!important;
    font-family: var(--font)!important;
    font-weight: 600!important;
    border: none!important;
    border-radius: 4px!important;
    transition: filter .15s, box-shadow .15s!important;
  }
  [data-testid="stFormSubmitButton"] button:hover,
  [data-testid="baseButton-secondary"]:hover {
    filter: brightness(1.1)!important;
    box-shadow: 0 0 12px rgba(255,107,53,.4)!important;
  }

  /* Caption */
  [data-testid="stCaptionContainer"] p {
    font-family: var(--font)!important;
    font-size: 12px!important;
    color: var(--on-var)!important;
    font-style: italic!important;
  }

  /* Multiselect tag */
  [data-testid="stMultiSelect"] [data-baseweb="tag"] {
    background: var(--primary)!important;
    color: var(--bg)!important;
    font-family: var(--mono)!important;
    font-size: 11px!important;
    border-radius: 999px!important;
  }

  /* ── Card helper classes ── */
  .iq-card {
    background: var(--surf-low);
    border-radius: 8px;
    padding: 20px;
    border: 1px solid var(--surf-high);
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
  }
  .iq-card::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: var(--primary);
    border-radius: 8px 0 0 8px;
  }
  .iq-card-header {
    font-family: var(--font);
    font-size: 18px;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--on-surf);
    margin: 0 0 4px;
  }
  .iq-card-sub {
    font-size: 12px;
    color: var(--on-var);
    margin: 0 0 16px;
  }
  .iq-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    background: var(--surf-highest);
    color: var(--secondary);
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: .05em;
    text-transform: uppercase;
    vertical-align: middle;
    margin-left: 8px;
  }
  .iq-module-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    background: var(--primary);
    color: #070e1d;
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .05em;
    text-transform: uppercase;
    vertical-align: middle;
  }
  .iq-insight {
    background: rgba(255,107,53,.08);
    border-left: 3px solid var(--primary);
    border-radius: 4px;
    padding: 12px 16px;
    font-size: 13px;
    color: var(--on-surf);
    margin-top: 12px;
  }
  .iq-stat-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid var(--surf-high);
  }
  .iq-stat-row:last-child { border-bottom: none; }
  .iq-stat-label { font-size: 12px; color: var(--on-var); }
  .iq-stat-val {
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 600;
    color: var(--on-surf);
  }
  .iq-def-term {
    font-family: var(--mono);
    font-weight: 700;
    color: var(--primary);
    font-size: 13px;
  }
  .iq-code-block {
    background: var(--surf-lowest);
    border-radius: 6px;
    padding: 16px;
    font-family: var(--mono);
    font-size: 12px;
    color: #4ade80;
    white-space: pre;
    overflow-x: auto;
    border: 1px solid var(--surf-high);
  }
  .iq-partition-card {
    background: var(--surf-high);
    border-radius: 6px;
    padding: 16px;
    text-align: center;
  }
  .iq-partition-num {
    font-family: var(--mono);
    font-size: 28px;
    font-weight: 700;
    color: var(--on-surf);
    letter-spacing: -0.02em;
  }
  .iq-partition-sub { font-size: 12px; color: var(--on-var); margin-top: 2px; }

  /* Section header */
  .iq-section-label {
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: var(--on-var);
  }
  .iq-section-title {
    font-family: var(--font);
    font-size: 32px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--on-surf);
    margin: 0;
    line-height: 1.15;
  }
  .iq-section-sub {
    font-size: 14px;
    color: var(--on-var);
    margin: 4px 0 0;
  }

  /* Leverage / parameter panel */
  .iq-param-panel {
    background: var(--surf-low);
    border-radius: 8px;
    padding: 20px 24px;
    border: 1px solid var(--surf-high);
    margin-bottom: 16px;
  }
  .iq-slider-wrap {
    background: var(--surf);
    border-radius: 6px;
    padding: 14px 16px;
  }
  .iq-slider-value {
    font-family: var(--mono);
    font-size: 15px;
    font-weight: 700;
    color: var(--primary);
    background: var(--surf-highest);
    padding: 2px 10px;
    border-radius: 4px;
  }

  /* Clutch comparison cards */
  .iq-clutch-card {
    background: var(--surf);
    border-radius: 8px;
    padding: 20px;
    border: 1px solid var(--surf-high);
    position: relative;
    overflow: hidden;
  }
  .iq-clutch-card-hot::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
    background: var(--primary);
  }
  .iq-clutch-card-cool::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
    background: var(--secondary);
  }
  .iq-clutch-label-hot {
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .05em;
    color: var(--primary);
    text-transform: uppercase;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .iq-clutch-label-cool {
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .05em;
    color: var(--secondary);
    text-transform: uppercase;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  /* Context strip */
  .iq-context-strip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
    background: var(--surf-low);
    border-radius: 6px;
    padding: 10px 16px;
    margin-bottom: 16px;
    border: 1px solid var(--surf-high);
  }
  .iq-context-strip-label {
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: .05em;
    text-transform: uppercase;
    color: var(--primary);
    font-weight: 700;
  }
  .iq-context-strip-val {
    font-size: 13px;
    color: var(--on-var);
  }
  .iq-live-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    background: var(--secondary);
    border-radius: 50%;
    animation: pulse 2s ease-in-out infinite;
    margin-right: 6px;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  /* Simulator result panel */
  .iq-result-idle {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 260px;
    gap: 12px;
    color: var(--on-var);
    text-align: center;
  }
  .iq-result-idle p {
    font-size: 13px;
    margin: 0;
    line-height: 1.6;
  }

  /* Methodology def block */
  .iq-def-block {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 8px;
  }
  .iq-def-row {
    display: flex;
    align-items: baseline;
    gap: 8px;
  }
</style>
""")

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
    if k == 'Attempts':
        return f'{int(v):,}'
    try:
        return f'{float(v):.2f}'
    except (TypeError, ValueError):
        return str(v)


def _metric_rows_html(m: dict) -> str:
    rows = []
    for k, v in m.items():
        rows.append(
            f'<div class="iq-stat-row">'
            f'<span class="iq-stat-label">{k}</span>'
            f'<span class="iq-stat-val">{_fmt_metric(k, v)}</span>'
            f'</div>'
        )
    return ''.join(rows)


# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.html("""
<div style="padding:4px 0 14px;display:flex;align-items:center;gap:10px;">
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#FF6B35"
       stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <path d="M5 5a10 10 0 0 0 14 14"/>
    <path d="M19 5a10 10 0 0 0-14 14"/>
    <line x1="12" y1="2" x2="12" y2="22"/>
    <line x1="2" y1="12" x2="22" y2="12"/>
  </svg>
  <span style="font-family:'Inter',sans-serif;font-size:20px;font-weight:700;color:#fff;letter-spacing:-0.02em;">Clutch<span style="color:#ff6b35;">IQ</span></span>
</div>
<p style="font-size:11px;color:#a98a80;font-style:italic;line-height:1.5;margin:0 0 16px;">
  Smarter shot selection through NBA analytics · 2023/24 regular season
</p>
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
  <span style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.05em;
               text-transform:uppercase;color:#a98a80;font-weight:600;">⬡ Filters</span>
  <span style="font-size:16px;color:#a98a80;">⊞</span>
</div>
""")

# ── Guard: pipeline not built ────────────────────────────────────────────────
if not (ROOT / 'data/shots.parquet').exists():
    st.html("""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                min-height:60vh;gap:16px;text-align:center;">
      <h2 style="font-size:24px;font-weight:700;color:#dce2f7;">Dataset not ready</h2>
      <p style="color:#a98a80;font-size:14px;">
        Run <code style="background:#232a3a;padding:2px 6px;border-radius:4px;color:#ff6b35;">
        python build.py</code> first.
      </p>
    </div>""")
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

st.sidebar.html("""
<div style="margin-top:24px;padding-top:16px;border-top:1px solid #232a3a;">
  <p style="font-size:11px;color:#a98a80;font-style:italic;line-height:1.5;margin:0 0 12px;">
    League benchmark follows quarter and shot type across all teams.
  </p>
  <div style="display:flex;justify-content:space-between;align-items:center;
              font-family:'JetBrains Mono',monospace;font-size:10px;
              text-transform:uppercase;letter-spacing:.05em;">
    <span style="color:#a98a80;">Telemetry v2.4</span>
    <span style="color:#41eec2;font-weight:700;">
      <span style="display:inline-block;width:7px;height:7px;background:#41eec2;
                   border-radius:50%;margin-right:4px;vertical-align:middle;"></span>READY
    </span>
  </div>
</div>
""")

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
    st.html('<div class="iq-insight">⚠️ No attempts match the current filters.</div>')
    st.stop()

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_labels = ['Overview', 'Shot Explorer', 'Clutch Analysis',
              'Player Comparison', 'Shot Prediction', 'Methodology']
tabs = st.tabs(tab_labels)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 0 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.html("""
    <div style="margin-bottom:20px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span style="width:8px;height:8px;border-radius:50%;background:#ff6b35;
                     box-shadow:0 0 8px rgba(255,107,53,.8);display:inline-block;"></span>
        <span class="iq-section-label">Macro Analytics · Cohort 2023-24</span>
      </div>
      <h2 class="iq-section-title">Shooting Profile</h2>
      <p class="iq-section-sub">Overview of all tracked field goal events for the 2023/24 NBA regular season.</p>
    </div>
    """)

    # Active filter chips
    filter_chip_team   = team if team != 'All' else 'All Teams'
    filter_chip_player = player if player != 'All' else 'All Players'
    filter_chip_period = f'Q{period}' if period != 'All' else 'All Quarters'
    filter_chip_kind   = kind if kind != 'All' else 'All Shot Types'

    st.html(f"""
    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;">
      <div style="padding:4px 10px;background:#232a3a;border-radius:4px;font-size:11px;
                  color:#a98a80;font-family:'JetBrains Mono',monospace;">
        Team: <span style="color:#dce2f7;font-weight:600;">{filter_chip_team}</span>
      </div>
      <div style="padding:4px 10px;background:#232a3a;border-radius:4px;font-size:11px;
                  color:#a98a80;font-family:'JetBrains Mono',monospace;">
        Player: <span style="color:#dce2f7;font-weight:600;">{filter_chip_player}</span>
      </div>
      <div style="padding:4px 10px;background:#232a3a;border-radius:4px;font-size:11px;
                  color:#a98a80;font-family:'JetBrains Mono',monospace;">
        Period: <span style="color:#41eec2;font-weight:600;">{filter_chip_period}</span>
      </div>
      <div style="padding:4px 10px;background:#232a3a;border-radius:4px;font-size:11px;
                  color:#a98a80;font-family:'JetBrains Mono',monospace;">
        Shot Type: <span style="color:#dce2f7;font-weight:600;">{filter_chip_kind}</span>
      </div>
    </div>
    """)

    # Metric cards
    m = metrics(df)
    game_count = df.GAME_ID.nunique()
    col_keys = ['Games', 'Attempts', 'FG%', 'eFG%', 'Points / attempt']
    all_vals  = {'Games': game_count, **m}
    cols = st.columns(len(col_keys))
    for i, k in enumerate(col_keys):
        v = all_vals.get(k, 0)
        if k in ('Games', 'Attempts'):
            display = f'{int(v):,}'
        else:
            display = f'{float(v):.2f}'
        cols[i].metric(k, display)

    # Points per attempt over time
    st.html("""
    <div class="iq-card" style="margin-top:8px;">
      <p class="iq-card-header">Points per Attempt Over Time
        <span class="iq-badge">NBA Aggregated</span>
      </p>
      <p class="iq-card-sub">Scoring yield per field goal attempt across calendar windows</p>
    """)

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
    st.plotly_chart(fig_trend, width='stretch')
    st.caption('Daily aggregate · changes reflect different opponents and samples.')

    # Legend row
    st.html("""
      <div style="display:flex;align-items:center;gap:20px;margin-top:-8px;margin-bottom:4px;
                  font-size:12px;color:#a98a80;font-family:'JetBrains Mono',monospace;">
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="display:inline-block;width:14px;height:2px;background:#ff6b35;"></span>
          Rolling Efficiency
        </div>
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="display:inline-block;width:14px;height:2px;background:#41eec2;opacity:.6;
                       border-top:1px dashed #41eec2;"></span>
          League Benchmark
        </div>
      </div>
    </div>
    """)

    # Player table
    st.html("""
    <div class="iq-card">
      <p class="iq-card-header">Top Volume Scorers &amp; Efficiency Breakdown</p>
      <p class="iq-card-sub">Player-level offensive load versus conversion rate · sorted by attempts</p>
    """)
    player_tbl = (df.groupby('PLAYER_NAME')
                    .agg(attempts=('points', 'size'),
                         makes=('SHOT_MADE_FLAG', 'sum'),
                         points=('points', 'sum'))
                    .assign(**{'FG%': lambda x: (100 * x.makes / x.attempts).round(1)})
                    .sort_values('attempts', ascending=False))
    st.dataframe(player_tbl, width='stretch')
    st.html("</div>")

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — SHOT EXPLORER
# ═══════════════════════════════════════════════════════════════════════════
with tabs[1]:
    render_shot_explorer(df, league=league)
with tabs[2]:
    st.html("""
    <div style="margin-bottom:20px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span class="iq-module-badge">Module 03</span>
        <span class="iq-section-label">High Leverage Index</span>
      </div>
      <h2 class="iq-section-title">Close Games, Event by Event</h2>
      <p class="iq-section-sub">
        Evaluating late-clock and high-leverage shot execution under clutch constraints
        across 2023/24 regular season telemetries.
      </p>
    </div>
    """)

    # Parameter controller panel
    st.html("""
    <div class="iq-param-panel">
      <div style="display:flex;align-items:center;justify-content:space-between;
                  flex-wrap:wrap;gap:8px;margin-bottom:14px;">
        <div style="display:flex;align-items:center;gap:8px;">
          <span style="font-size:18px;color:#ff6b35;">⊞</span>
          <span style="font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;
                       letter-spacing:.05em;text-transform:uppercase;color:#dce2f7;">
            Clutch Boundary Parameters
          </span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;font-family:'JetBrains Mono',monospace;
                    font-size:10px;color:#a98a80;letter-spacing:.05em;text-transform:uppercase;">
          <span class="iq-live-dot"></span> Real-time Telemetry Engine
        </div>
      </div>
    """)

    c1, c2 = st.columns(2)
    with c1:
        minutes = st.slider('Maximum minutes remaining', 1, 5, 5, key='clutch_min')
    with c2:
        margin  = st.slider('Maximum absolute score margin', 1, 15, 5, key='clutch_gap')

    st.html(f"""
      <div style="margin-top:10px;display:flex;align-items:center;gap:6px;
                  font-size:12px;color:#a98a80;font-style:italic;">
        <span style="font-size:14px;">ⓘ</span>
        Quarter ≥ 4 · time ≤ {minutes}:00 · |margin| ≤ {margin}. Unknown score context excluded.
      </div>
    </div>
    """)

    known = df[df.score_margin_before.notna()].copy()
    known['Clutch'] = clutch(
        known.PERIOD, known.seconds_remaining,
        known.score_margin_before, minutes * 60, margin
    )
    excluded = len(df) - len(known)

    clutch_df    = known[known.Clutch]
    nonclutch_df = known[~known.Clutch]
    clutch_m     = metrics(clutch_df)
    nonclutch_m  = metrics(nonclutch_df)

    # Leverage state pill
    st.html(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap;">
      <div style="display:flex;align-items:center;gap:8px;background:#232a3a;
                  padding:8px 14px;border-radius:6px;">
        <span style="color:#41eec2;font-size:16px;">⏱</span>
        <div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:10px;
                      color:#a98a80;text-transform:uppercase;letter-spacing:.05em;">
            Leverage State
          </div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
                      color:#dce2f7;font-weight:600;">
            Q4/OT ≤ {minutes}:00 · ±{margin} PTS
          </div>
        </div>
      </div>
      <div style="font-size:12px;color:#a98a80;font-style:italic;">
        {excluded} attempts excluded (unknown score context)
      </div>
    </div>
    """)

    # Comparison cards
    c_col1, c_col2 = st.columns(2)
    with c_col1:
        html_rows = _metric_rows_html(clutch_m)
        st.html(f"""
        <div class="iq-clutch-card iq-clutch-card-hot">
          <div class="iq-clutch-label-hot">
            🔥 CLUTCH
            <span style="color:#a98a80;font-weight:400;">({len(clutch_df):,} attempts)</span>
          </div>
          {html_rows}
        </div>
        """)

    with c_col2:
        html_rows2 = _metric_rows_html(nonclutch_m)
        st.html(f"""
        <div class="iq-clutch-card iq-clutch-card-cool">
          <div class="iq-clutch-label-cool">
            NON-CLUTCH
            <span style="color:#a98a80;font-weight:400;">({len(nonclutch_df):,} attempts)</span>
          </div>
          {html_rows2}
        </div>
        """)

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

    st.html('<div class="iq-card"><p class="iq-card-header">FG% — Clutch vs Non-Clutch</p>')
    st.plotly_chart(fig_c, width='stretch')
    st.html('</div>')

    st.html('<div class="iq-card"><p class="iq-card-header">Clutch Zone Breakdown</p>')
    if len(clutch_df):
        st.dataframe(zones(clutch_df), width='stretch')
    else:
        st.info('No clutch attempts for the current filter selection.')
    st.html('</div>')

# ═══════════════════════════════════════════════════════════════════════════
# TAB 3 — PLAYER COMPARISON
# ═══════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.html("""
    <div style="margin-bottom:20px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span class="iq-module-badge">Module 04</span>
        <span class="iq-section-label">Descriptive Comparison</span>
      </div>
      <h2 class="iq-section-title">Player Comparison</h2>
      <p class="iq-section-sub">
        Descriptive comparisons — not adjusted for defenders, roles, or shot difficulty.
      </p>
    </div>
    """)

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

        st.html('<div class="iq-card"><p class="iq-card-header">Metrics Table</p>')
        st.dataframe(comparison, width='stretch')
        st.html('</div>')

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
            fig_comp.update_layout(
                barmode='group',
                legend=dict(orientation='h', y=1.08)
            )
            apply_theme(fig_comp, height=280)
            st.html('<div class="iq-card"><p class="iq-card-header">Efficiency Comparison</p>')
            st.plotly_chart(fig_comp, width='stretch')
            st.html('</div>')
    else:
        st.html('<div class="iq-insight">Select at least one player above.</div>')

# ═══════════════════════════════════════════════════════════════════════════
# TAB 4 — SHOT PREDICTION
# ═══════════════════════════════════════════════════════════════════════════
with tabs[4]:
    evaluation = load_evaluation()

    st.html("""
    <div style="margin-bottom:20px;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span class="iq-context-strip-label">Inference Engine</span>
        <span style="color:#a98a80;font-size:11px;font-family:'JetBrains Mono',monospace;">/</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#a98a80;">
          Logit Calibration Model v2.8
        </span>
      </div>
      <h2 class="iq-section-title">Shot Success Prediction</h2>
      <p class="iq-section-sub">
        What-if analysis powered by regularized logistic regression.
        Sidebar filters do not retrain the model.
      </p>
    </div>
    """)

    sim_col, res_col = st.columns([1, 1.2])

    with sim_col:
        st.html("""
        <div class="iq-card" style="margin-bottom:0;">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
            <span style="color:#ff6b35;font-size:16px;">⊞</span>
            <span class="iq-context-strip-label">Interactive Sandbox</span>
          </div>
          <p class="iq-card-header">Shot Simulator</p>
          <p class="iq-card-sub">Adjust parameters and run inference against the trained model</p>
        </div>
        """)
        with st.form('predict_form'):
            x_val  = st.slider('Width from basket — X coordinate (ft)', -25.0, 25.0, 0.0, 0.5)
            y_val  = st.slider('Length from basket — Y coordinate (ft)', -5.0, 42.0, 15.0, 0.5)
            value  = st.selectbox('Shot value', [2, 3])
            period_pred = st.selectbox('Period', [1, 2, 3, 4, 5, 6])
            max_sec = 300 if period_pred >= 5 else 720
            sec    = st.slider('Seconds remaining in period', 0, max_sec, min(120, max_sec))
            gap    = st.slider('Home minus away score before shot', -40, 40, 0)
            submit = st.form_submit_button('⚡ Estimate Probability', width='stretch')

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
            st.plotly_chart(fig_gauge, width='stretch')

            mc1, mc2 = st.columns(2)
            mc1.metric('Make Probability', f'{p:.1%}')
            mc2.metric('Expected Pts/Att', f'{p * value:.3f}')
            st.caption('Estimate excludes free throws and subsequent possessions.')

            # Insight
            zone_label = 'Restricted Area' if dist < 8 else ('Mid-Range' if dist < 22 else '3PT Zone')
            st.html(f"""
            <div class="iq-insight">
              📍 <b>Dist:</b> {dist:.1f} ft · <b>Zone:</b> {zone_label} ·
              <b>Make prob:</b> {p:.1%} · <b>xPts:</b> {p*value:.3f}/att
            </div>
            """)
        else:
            st.html("""
            <div class="iq-result-idle">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#ff6b35"
                   stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <path d="M5 5a10 10 0 0 0 14 14"/>
                <path d="M19 5a10 10 0 0 0-14 14"/>
                <line x1="12" y1="2" x2="12" y2="22"/>
                <line x1="2" y1="12" x2="22" y2="12"/>
              </svg>
              <p>Configure shot parameters and click<br>
                 <b style="color:#ff6b35;">⚡ Estimate Probability</b>
              </p>
            </div>
            """)

    # Model performance section
    st.html("""
    <div class="iq-card" style="margin-top:16px;">
      <p class="iq-card-header">Model Performance</p>
      <p class="iq-card-sub">Chronological train/val/test split · no data leakage</p>
    """)
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

    st.html('<p class="iq-card-header" style="margin-top:20px;">Calibration Curve</p>')
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
        st.plotly_chart(fig_cal, width='stretch')

    st.html('<p class="iq-card-header" style="margin-top:20px;">Standardized Logistic Coefficients</p>')
    st.caption('Associations only — not causal effects.')
    coefs = evaluation.get('coefficients', {})
    if coefs:
        coef_df = pd.Series(coefs, name='Coefficient').to_frame()
        st.dataframe(
            coef_df.style.bar(color=['#ff6b35', '#41eec2'], align='zero'),
            width='stretch'
        )
    st.html('</div>')

# ═══════════════════════════════════════════════════════════════════════════
# TAB 5 — METHODOLOGY
# ═══════════════════════════════════════════════════════════════════════════
with tabs[5]:
    manifest   = load_manifest()
    evaluation = load_evaluation()

    st.html("""
    <div style="margin-bottom:24px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span class="iq-module-badge">Module 06</span>
        <span class="iq-section-label">Documentation</span>
      </div>
      <h2 class="iq-section-title">Methodology</h2>
      <p class="iq-section-sub">Data sources, metric definitions, model details, and limitations.</p>
    </div>
    """)

    # Data source
    st.html("""
    <div class="iq-card">
      <p class="iq-card-header">📁 Data Source</p>
      <p style="font-size:13px;color:#a98a80;margin:0 0 12px;">
        Source:
        <a href="https://github.com/shufinskiy/nba_data"
           style="color:#ff6b35;">github.com/shufinskiy/nba_data</a>
        — compiled from NBA sources. Credit the repository maintainer and NBA.
        Repository software license does not establish all third-party data rights.
      </p>
    </div>
    """)

    if manifest:
        st.html(f'<div class="iq-code-block">{json.dumps(manifest, indent=2)}</div>')

    # Metric definitions
    st.html("""
    <div class="iq-card" style="margin-top:16px;">
      <p class="iq-card-header">📊 Metric Definitions</p>
      <div class="iq-def-block">
        <div class="iq-def-row">
          <span class="iq-def-term">FG%</span>
          <span style="font-size:13px;color:#dce2f7;">— Makes ÷ Attempts</span>
        </div>
        <div class="iq-def-row">
          <span class="iq-def-term">eFG%</span>
          <span style="font-size:13px;color:#dce2f7;">— (Makes + 0.5 × Three-Point Makes) ÷ Attempts</span>
        </div>
        <div class="iq-def-row">
          <span class="iq-def-term">Points / Attempt</span>
          <span style="font-size:13px;color:#dce2f7;">— Observed FG points only; excludes free throws</span>
        </div>
        <div class="iq-def-row">
          <span class="iq-def-term">Clutch</span>
          <span style="font-size:13px;color:#dce2f7;">— Q4/OT · time ≤5:00 · |margin| ≤5 before the shot</span>
        </div>
        <div class="iq-def-row">
          <span class="iq-def-term">Wilson CI</span>
          <span style="font-size:13px;color:#dce2f7;">— 95% binomial CI for FG%; 30 attempts is a display threshold</span>
        </div>
      </div>
    </div>
    """)

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

        st.html(f"""
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
        """)

    # Limitations
    st.html("""
    <div class="iq-card" style="margin-top:16px;">
      <p class="iq-card-header">⚠️ Limitations</p>
      <ul style="font-size:13px;color:#a98a80;font-style:italic;line-height:1.9;
                 margin:8px 0 0;padding-left:20px;">
        <li>No defender distance or shot-clock data in the inspected schemas</li>
        <li>Estimates are observational associations, not causal recommendations</li>
        <li>Data is historical — app does not provide live NBA results</li>
        <li>One season (2023/24 regular season) only</li>
        <li>Model uncertainty and changing player roles limit actionability</li>
        <li>Score context reconstructed from play-by-play; ordering edge cases remain</li>
        <li>Standardized coefficients reflect associations, not causal effects</li>
      </ul>
    </div>
    """)

    # Footer
    st.html("""
    <div style="text-align:center;margin-top:24px;padding-top:16px;border-top:1px solid #232a3a;">
      <p style="font-size:11px;color:#4b5563;font-style:italic;margin:0;">
        Historical observational analysis only. No tactical guarantees.
        ClutchIQ · 2023/24 NBA Regular Season
      </p>
    </div>
    """)
