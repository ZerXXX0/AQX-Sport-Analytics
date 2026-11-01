import numpy as np
import plotly.graph_objects as go

def court(df):
    fig = go.Figure()
    for flag,label,color,symbol in [(0,'Missed','#7b899e','x'),(1,'Made','#ff9b42','circle')]:
        d=df[df.SHOT_MADE_FLAG==flag]
        fig.add_trace(go.Scattergl(x=d.x_ft,y=d.y_ft,mode='markers',name=label,marker=dict(color=color,size=5,opacity=.5,symbol=symbol),text=d.PLAYER_NAME+' · '+d.SHOT_ZONE_BASIC,hovertemplate='%{text}<br>x %{x:.1f} ft · y %{y:.1f} ft<extra>%{fullData.name}</extra>'))
    def line(x,y): fig.add_trace(go.Scatter(x=x,y=y,mode='lines',line=dict(color='#d2d8e2',width=1),hoverinfo='skip',showlegend=False))
    line([-25,25,25,-25,-25],[-5.25,-5.25,41.75,41.75,-5.25])
    line([-8,-8,8,8],[-5.25,13.75,13.75,-5.25])
    line([-3,3],[-.75,-.75])
    t=np.linspace(0,2*np.pi,100); line(.75*np.cos(t),.75*np.sin(t))
    t=np.linspace(0,np.pi,100); line(6*np.cos(t),13.75+6*np.sin(t))
    t=np.linspace(np.arccos(22/23.75),np.pi-np.arccos(22/23.75),150); line(23.75*np.cos(t),23.75*np.sin(t))
    y=np.sqrt(23.75**2-22**2)
    line([-22,-22],[-5.25,y]); line([22,22],[-5.25,y])
    fig.update_layout(template='plotly_dark',height=560,margin=dict(l=5,r=5,t=5,b=5),xaxis=dict(range=[-26,26],visible=False),yaxis=dict(range=[-6,43],visible=False,scaleanchor='x',scaleratio=1),legend=dict(orientation='h'),paper_bgcolor='#111827',plot_bgcolor='#111827')
    return fig
