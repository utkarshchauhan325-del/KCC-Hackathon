"""Plotly charts for the FloodGuard console, styled to the shared light theme."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Dict, Any

from app.ui.components.styles import ACCENT, ACCENT_BRIGHT, GRID, INK, LINE, MUTED, STATUS

FONT = "Inter, system-ui, sans-serif"
MONO = "JetBrains Mono, ui-monospace, monospace"
C_CRIT = STATUS["Critical"]["fg"]
C_HIGH = STATUS["High"]["fg"]
C_WATCH = "#D4A106"
C_OK = STATUS["Low"]["fg"]
C_RAIN = "#7CC7D4"


def _style(fig: go.Figure, height: int, margin: dict, legend: dict = None) -> go.Figure:
    """Apply the console chart style: no backgrounds, hairline grid, mono tick labels."""
    fig.update_layout(
        height=height,
        margin=margin,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=MUTED),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=LINE, font=dict(family=FONT, size=12, color=INK)),
        legend=legend or dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                              font=dict(size=11, color=MUTED), bgcolor="rgba(0,0,0,0)"),
        bargap=0.45,
    )
    fig.update_xaxes(showgrid=False, linecolor=LINE, ticks="", tickfont=dict(family=MONO, size=10.5, color=MUTED),
                     title_font=dict(size=11.5, color=MUTED), zeroline=False)
    fig.update_yaxes(gridcolor=GRID, gridwidth=1, linecolor="rgba(0,0,0,0)", ticks="", zeroline=False,
                     tickfont=dict(family=MONO, size=10.5, color=MUTED), title_font=dict(size=11.5, color=MUTED))
    return fig

def render_risk_distribution_donut() -> go.Figure:
    """Donut chart of risk distribution across the 53 monitored locations."""
    labels = ["Critical", "High", "Medium", "Low"]
    values = [5, 17, 23, 8]
    colors = [C_CRIT, C_HIGH, C_WATCH, C_OK]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.74,
        sort=False,
        direction="clockwise",
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=3)),
        textinfo="none",
        hovertemplate="%{label}: %{value} locations (%{percent})<extra></extra>"
    )])
    _style(fig, 220, dict(t=10, b=10, l=10, r=110), legend=dict(
        orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02,
        font=dict(size=12, color=MUTED), itemsizing="constant", bgcolor="rgba(0,0,0,0)"))
    fig.update_layout(annotations=[dict(
        text=f"<span style='font-family:JetBrains Mono;font-size:24px;color:{INK}'>53</span><br>"
             f"<span style='font-size:11px;color:{MUTED}'>locations</span>",
        x=0.5, y=0.5, showarrow=False)])
    return fig


def render_rainfall_forecast_bars() -> go.Figure:
    """24h rainfall forecast bar chart."""
    hours = ["Now", "3h", "6h", "12h", "24h"]
    rainfall = [12, 34, 52, 74, 32]

    fig = go.Figure(data=[go.Bar(
        x=hours,
        y=rainfall,
        marker=dict(color=ACCENT, line=dict(width=0), cornerradius=4),
        hovertemplate="%{x}: %{y} mm<extra></extra>"
    )])
    _style(fig, 220, dict(t=10, b=25, l=45, r=10))
    fig.update_yaxes(range=[0, 85], tickvals=[0, 40, 80], ticktext=["0 mm", "40 mm", "80 mm"])
    return fig


def render_water_level_trend() -> go.Figure:
    """Water level trend for MG Road vs FC Road with projected tail."""
    times = ["Now", "3h", "6h", "12h", "24h"]
    mg_road = [38, 52, 54, 78, 90]
    fc_road = [28, 36, 40, 60, 58]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=mg_road, mode="lines+markers", name="MG Road",
        line=dict(color=C_CRIT, width=2), marker=dict(size=5, color=C_CRIT),
        hovertemplate="MG Road: %{y}%<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=times, y=fc_road, mode="lines+markers", name="FC Road",
        line=dict(color=ACCENT, width=2), marker=dict(size=5, color=ACCENT),
        hovertemplate="FC Road: %{y}%<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=["12h", "24h"], y=[78, 90], mode="lines", name="Projected",
        line=dict(color=C_CRIT, width=1.5, dash="dot"), showlegend=False, hoverinfo="skip"
    ))
    _style(fig, 220, dict(t=20, b=25, l=45, r=10), legend=dict(
        orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1,
        font=dict(size=11, color=MUTED), bgcolor="rgba(0,0,0,0)"))
    fig.update_yaxes(range=[0, 105], tickvals=[0, 50, 100], ticktext=["0%", "50%", "100%"])
    return fig


def render_7day_rainfall_water_correlation() -> go.Figure:
    """7-day rainfall vs city risk index."""
    days = ["Sep 18", "Sep 19", "Sep 20", "Sep 21", "Sep 22", "Sep 23", "Sep 24"]
    rain = [5.2, 12.0, 48.5, 62.4, 88.0, 110.5, 134.2]
    flood_index = [12, 18, 42, 58, 74, 86, 92]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=days, y=rain, name="Cumulative rainfall (mm)",
        marker=dict(color=C_RAIN, cornerradius=3), yaxis="y",
        hovertemplate="%{x}: %{y} mm<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=days, y=flood_index, name="City risk index (0-100)", mode="lines+markers",
        line=dict(color=C_CRIT, width=2), marker=dict(size=6, color=C_CRIT), yaxis="y2",
        hovertemplate="%{x}: index %{y}<extra></extra>"
    ))
    _style(fig, 320, dict(t=30, b=30, l=50, r=50))
    fig.update_layout(
        yaxis=dict(title="Rainfall (mm)"),
        yaxis2=dict(title="Risk index", overlaying="y", side="right", range=[0, 100], tickvals=[0, 50, 100], showgrid=False,
                    tickfont=dict(family=MONO, size=10.5, color=MUTED), title_font=dict(size=11.5, color=MUTED)),
    )
    return fig


def render_ward_vulnerability_bars() -> go.Figure:
    """Ward comparison across Central, West, East, North, South."""
    zones = ["Central (Ward 9-14)", "East (Ward 25-28)", "North (Ward 1-5)", "West (Ward 20-24)", "South (Ward 30-35)"]
    critical = [3, 1, 1, 0, 0]
    high = [7, 4, 2, 2, 2]
    medium = [9, 5, 4, 3, 2]

    fig = go.Figure(data=[
        go.Bar(name="Critical", x=zones, y=critical, marker_color=C_CRIT),
        go.Bar(name="High", x=zones, y=high, marker_color=C_HIGH),
        go.Bar(name="Medium", x=zones, y=medium, marker_color=C_WATCH),
    ])
    _style(fig, 300, dict(t=30, b=40, l=45, r=10))
    fig.update_layout(barmode="stack", bargap=0.5)
    fig.update_xaxes(tickfont=dict(family=FONT, size=11, color=MUTED))
    fig.update_yaxes(title="Locations")
    return fig


def render_blockage_vs_flood_scatter() -> go.Figure:
    """Scatter: debris blockage % vs standing water depth (cm)."""
    blockages = [78, 65, 52, 34, 28, 72, 30, 15, 40, 18, 58, 12, 55, 32, 80, 68]
    water_depths = [28, 22, 15, 11, 8, 26, 9, 4, 12, 5, 17, 3, 16, 8, 29, 24]
    labels = ["MG Road", "FC Road", "Swargate", "Pune Stn", "Kothrud", "Deccan", "Khadki", "Aundh", "Yerwada", "Karve", "Hadapsar", "Bibwewadi", "Kondhwa", "PCMC", "Dapodi", "Sangamwadi"]

    fig = go.Figure(data=go.Scatter(
        x=blockages,
        y=water_depths,
        text=labels,
        mode="markers",
        marker=dict(
            size=10,
            color=water_depths,
            colorscale=[[0, "#CDEBF0"], [0.5, ACCENT_BRIGHT], [1, "#0B3F4A"]],
            line=dict(color="#FFFFFF", width=1),
            showscale=True,
            colorbar=dict(title=dict(text="Depth (cm)", font=dict(size=11, color=MUTED)), len=0.8, thickness=8,
                          outlinewidth=0, tickfont=dict(family=MONO, size=10, color=MUTED)),
        ),
        hovertemplate="%{text}<br>Blockage %{x}%<br>Depth %{y} cm<extra></extra>"
    ))
    _style(fig, 300, dict(t=20, b=40, l=50, r=10))
    fig.update_xaxes(title="Debris / silt blockage (%)", showgrid=True, gridcolor=GRID)
    fig.update_yaxes(title="Standing water depth (cm)")
    return fig
