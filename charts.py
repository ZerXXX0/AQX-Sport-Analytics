import numpy as np
import plotly.graph_objects as go

COURT_BG     = '#070d18'   # ultra-deep navy (Stitch spec)
COURT_LINE   = '#d2d8e2'   # court lines at 28% opacity
MADE_COLOR   = '#41eec2'   # neon teal for made shots
MISSED_COLOR = '#4B5563'   # slate for missed shots

def court(df):
    """Half-court shot chart using Stitch design tokens."""
    fig = go.Figure()

    # Missed shots — muted slate 'x' markers
    d_miss = df[df.SHOT_MADE_FLAG == 0]
    fig.add_trace(go.Scattergl(
        x=d_miss.x_ft, y=d_miss.y_ft,
        mode='markers', name='Missed',
        marker=dict(color=MISSED_COLOR, size=5, opacity=0.5, symbol='x'),
        text=d_miss.PLAYER_NAME + ' · ' + d_miss.SHOT_ZONE_BASIC,
        hovertemplate='%{text}<br>x %{x:.1f} ft · y %{y:.1f} ft<extra>Missed</extra>'
    ))

    # Made shots — neon teal circles with orange glow
    d_made = df[df.SHOT_MADE_FLAG == 1]
    fig.add_trace(go.Scattergl(
        x=d_made.x_ft, y=d_made.y_ft,
        mode='markers', name='Made',
        marker=dict(
            color=MADE_COLOR, size=6, opacity=0.7, symbol='circle',
            line=dict(color=COURT_BG, width=1)
        ),
        text=d_made.PLAYER_NAME + ' · ' + d_made.SHOT_ZONE_BASIC,
        hovertemplate='%{text}<br>x %{x:.1f} ft · y %{y:.1f} ft<extra>Made</extra>'
    ))

    # Restricted area radial glow overlay
    t_ra = np.linspace(0, np.pi, 80)
    fig.add_trace(go.Scatter(
        x=4*np.cos(t_ra), y=4*np.sin(t_ra),
        mode='lines',
        line=dict(color='rgba(255,107,53,0.35)', width=1.5),
        hoverinfo='skip', showlegend=False
    ))

    def line(x, y, color=None, width=1.2):
        fig.add_trace(go.Scatter(
            x=x, y=y, mode='lines',
            line=dict(color=color or f'rgba(210,216,226,0.28)', width=width),
            hoverinfo='skip', showlegend=False
        ))

    # Perimeter / baseline
    line([-25, 25, 25, -25, -25], [-5.25, -5.25, 41.75, 41.75, -5.25])
    # Lane (paint)
    line([-8, -8, 8, 8, -8], [-5.25, 13.75, 13.75, -5.25, -5.25])
    # Backboard
    line([-3, 3], [-0.75, -0.75])
    # Basket circle
    t = np.linspace(0, 2*np.pi, 100)
    line(0.75*np.cos(t), 0.75*np.sin(t))
    # Free-throw circle (top half)
    t_ft = np.linspace(0, np.pi, 100)
    line(6*np.cos(t_ft), 13.75 + 6*np.sin(t_ft))
    # Free-throw circle (bottom half, dashed)
    fig.add_trace(go.Scatter(
        x=list(6*np.cos(-t_ft)), y=list(13.75 + 6*np.sin(-t_ft)),
        mode='lines',
        line=dict(color='rgba(210,216,226,0.28)', width=1.2, dash='dot'),
        hoverinfo='skip', showlegend=False
    ))
    # 3-point arc
    t3 = np.linspace(np.arccos(22/23.75), np.pi - np.arccos(22/23.75), 150)
    line(23.75*np.cos(t3), 23.75*np.sin(t3))
    # 3-point corner lines
    y3 = np.sqrt(23.75**2 - 22**2)
    line([-22, -22], [-5.25, y3])
    line([22,  22],  [-5.25, y3])

    fig.update_layout(
        template='plotly_dark',
        height=520,
        paper_bgcolor=COURT_BG,
        plot_bgcolor=COURT_BG,
        margin=dict(l=4, r=4, t=4, b=4),
        xaxis=dict(range=[-26, 26], visible=False, fixedrange=True),
        yaxis=dict(range=[-6, 43], visible=False, scaleanchor='x',
                   scaleratio=1, fixedrange=True),
        legend=dict(orientation='h', y=-0.02,
                    font=dict(family='JetBrains Mono', size=11, color='#a98a80'),
                    bgcolor='rgba(0,0,0,0)'),
    )
    return fig
