"""Plotly charts for the FloodGuard console, styled with clear visual explanations and thresholds."""

import plotly.graph_objects as go
import numpy as np
from app.ui.components.styles import ACCENT, ACCENT_BRIGHT, GRID, INK, LINE, MUTED, STATUS

FONT = "Inter, system-ui, -apple-system, sans-serif"
MONO = "JetBrains Mono, ui-monospace, monospace"
C_CRIT = "#DC2626"
C_HIGH = "#EA580C"
C_WATCH = "#D97706"
C_OK = "#059669"
C_RAIN = "#0284C7"


def _style(fig: go.Figure, height: int, margin: dict, legend: dict = None) -> go.Figure:
    """Apply the console chart style: clean canvas, crisp hairline grid, mono tick labels."""
    fig.update_layout(
        height=height,
        margin=margin,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=MUTED),
        hoverlabel=dict(
            bgcolor="#0B132B",
            bordercolor="#1E293B",
            font=dict(family=FONT, size=12, color="#FFFFFF")
        ),
        legend=legend or dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11, color=MUTED),
            bgcolor="rgba(0,0,0,0)"
        ),
        bargap=0.35,
    )
    fig.update_xaxes(
        showgrid=False,
        linecolor=LINE,
        ticks="",
        tickfont=dict(family=MONO, size=11, color=MUTED),
        title_font=dict(size=12, color=MUTED),
        zeroline=False
    )
    fig.update_yaxes(
        gridcolor="#E2E8F0",
        gridwidth=1,
        linecolor="rgba(0,0,0,0)",
        ticks="",
        zeroline=False,
        tickfont=dict(family=MONO, size=11, color=MUTED),
        title_font=dict(size=12, color=MUTED)
    )
    return fig


def render_risk_distribution_donut() -> go.Figure:
    """Donut chart showing risk distribution with direct count & percentage labels."""
    labels = ["Critical (>80)", "High (60-80)", "Watch (40-60)", "Normal (<40)"]
    values = [5, 17, 23, 8]
    colors = [C_CRIT, C_HIGH, C_WATCH, C_OK]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.68,
        sort=False,
        direction="clockwise",
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2.5)),
        textinfo="percent+value",
        texttemplate="<b>%{value}</b><br><span style='font-size:10px'>%{percent}</span>",
        textposition="inside",
        textfont=dict(family=FONT, size=11, color="#FFFFFF"),
        hovertemplate="<b>%{label}</b><br>Locations: %{value}<br>Share: %{percent}<extra></extra>"
    )])
    _style(fig, 240, dict(t=10, b=10, l=10, r=130), legend=dict(
        orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02,
        font=dict(size=11.5, color=MUTED), itemsizing="constant", bgcolor="rgba(0,0,0,0)"))
    fig.update_layout(annotations=[dict(
        text=f"<span style='font-family:{MONO};font-size:26px;font-weight:700;color:{INK}'>53</span><br>"
             f"<span style='font-size:11px;color:{MUTED};font-weight:500'>MONITORED SITES</span>",
        x=0.5, y=0.5, showarrow=False)])
    return fig


def render_rainfall_forecast_bars() -> go.Figure:
    """24h rainfall forecast bar chart with critical flood threshold guidelines."""
    hours = ["Current", "+3 Hours", "+6 Hours", "+12 Hours", "+24 Hours"]
    rainfall = [12, 34, 52, 74, 32]
    # Color-coded by rainfall threat
    bar_colors = [
        ACCENT if r < 30 else (C_WATCH if r < 60 else C_CRIT)
        for r in rainfall
    ]

    fig = go.Figure()

    # Bar trace with value labels
    fig.add_trace(go.Bar(
        x=hours,
        y=rainfall,
        marker=dict(color=bar_colors, line=dict(width=0), cornerradius=6),
        text=[f"<b>{r} mm</b>" for r in rainfall],
        textposition="outside",
        textfont=dict(family=MONO, size=11, color=INK),
        hovertemplate="<b>%{x}</b><br>Precipitation: %{y} mm<br>Threat: %{marker.color}<extra></extra>",
        name="Precipitation"
    ))

    # Reference threshold lines for clear explanation
    fig.add_hline(
        y=70, line_dash="dash", line_color=C_CRIT, line_width=1.5,
        annotation_text="Red Alert (70 mm) - Flash Flood Risk",
        annotation_position="top left",
        annotation_font=dict(size=10.5, color=C_CRIT, family=FONT)
    )
    fig.add_hline(
        y=45, line_dash="dot", line_color=C_WATCH, line_width=1.5,
        annotation_text="Orange Advisory (45 mm) - Inflow Surcharge",
        annotation_position="top left",
        annotation_font=dict(size=10.5, color=C_WATCH, family=FONT)
    )

    _style(fig, 240, dict(t=25, b=25, l=45, r=15))
    fig.update_yaxes(range=[0, 92], tickvals=[0, 30, 60, 90], ticktext=["0 mm", "30 mm", "60 mm", "90 mm"])
    return fig


def render_water_level_trend() -> go.Figure:
    """Water level & conduit saturation trend with danger mark lines and projections."""
    times = ["Now", "+3h", "+6h", "+12h", "+24h"]
    mg_road = [38, 52, 54, 78, 90]
    fc_road = [28, 36, 40, 60, 58]

    fig = go.Figure()

    # Danger overflow reference line
    fig.add_hline(
        y=80, line_dash="dash", line_color=C_CRIT, line_width=1.5,
        annotation_text="Danger Mark: 80% Capacity (Spill Warning)",
        annotation_position="top left",
        annotation_font=dict(size=10.5, color=C_CRIT, family=FONT)
    )
    fig.add_hline(
        y=50, line_dash="dot", line_color=C_WATCH, line_width=1.2,
        annotation_text="Advisory Mark: 50% (Dewatering Trigger)",
        annotation_position="top left",
        annotation_font=dict(size=10.5, color=C_WATCH, family=FONT)
    )

    # Shaded MG Road area
    fig.add_trace(go.Scatter(
        x=times, y=mg_road, mode="lines+markers", name="MG Road Culvert",
        line=dict(color=C_CRIT, width=2.5, shape="spline"),
        marker=dict(size=7, color=C_CRIT, symbol="circle"),
        fill="tozeroy",
        fillcolor="rgba(220, 38, 38, 0.08)",
        hovertemplate="MG Road: <b>%{y}%</b> conduit saturation<extra></extra>"
    ))

    # FC Road
    fig.add_trace(go.Scatter(
        x=times, y=fc_road, mode="lines+markers", name="FC Road Drain",
        line=dict(color=ACCENT, width=2.5, shape="spline"),
        marker=dict(size=7, color=ACCENT, symbol="diamond"),
        fill="tozeroy",
        fillcolor="rgba(10, 124, 143, 0.06)",
        hovertemplate="FC Road: <b>%{y}%</b> conduit saturation<extra></extra>"
    ))

    # Projected Trend Trace
    fig.add_trace(go.Scatter(
        x=["+6h", "+12h", "+24h"], y=[54, 78, 90], mode="lines", name="Projected",
        line=dict(color=C_CRIT, width=2, dash="dot"),
        hovertemplate="Projected Trajectory: <b>%{y}%</b><extra></extra>"
    ))

    # Callout on projected peak
    fig.add_annotation(
        x="+24h", y=90,
        text="<b>Projected Peak: 90%</b><br>Emergency Spill",
        showarrow=True, arrowhead=2, arrowsize=1, arrowcolor=C_CRIT,
        ax=-60, ay=-35,
        bgcolor="#FFF5F5", bordercolor=C_CRIT, borderwidth=1,
        font=dict(size=10, color=C_CRIT, family=FONT)
    )

    _style(fig, 240, dict(t=25, b=25, l=45, r=15), legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        font=dict(size=11, color=MUTED), bgcolor="rgba(0,0,0,0)"))
    fig.update_yaxes(range=[0, 105], tickvals=[0, 25, 50, 75, 100], ticktext=["0%", "25%", "50%", "75%", "100%"])
    return fig


def render_7day_rainfall_water_correlation() -> go.Figure:
    """7-day cumulative rainfall vs city flood risk index explaining hydrological lag."""
    days = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"]
    rain = [5.2, 12.0, 48.5, 62.4, 88.0, 110.5, 134.2]
    flood_index = [12, 18, 42, 58, 74, 86, 92]

    fig = go.Figure()

    # Left Y axis: Cumulative rainfall
    fig.add_trace(go.Bar(
        x=days, y=rain, name="Cumulative Rainfall (mm)",
        marker=dict(color=C_RAIN, cornerradius=4), yaxis="y",
        hovertemplate="%{x}: <b>%{y} mm</b> cumulative rain<extra></extra>"
    ))

    # Right Y axis: City risk index
    fig.add_trace(go.Scatter(
        x=days, y=flood_index, name="City Flood Index (0-100)", mode="lines+markers",
        line=dict(color=C_CRIT, width=3, shape="spline"),
        marker=dict(size=8, color=C_CRIT, symbol="circle"),
        yaxis="y2",
        hovertemplate="%{x}: Flood Risk Index <b>%{y}/100</b><extra></extra>"
    ))

    # Statistical correlation callout banner
    fig.add_annotation(
        xref="paper", yref="paper", x=0.03, y=0.92,
        text="<b>Correlation: r = +0.94</b> | Hydrological Lag: ~3.5 Hours from Peak Rainfall to Surcharge",
        showarrow=False,
        bgcolor="rgba(241, 245, 249, 0.95)", bordercolor="#CBD5E1", borderwidth=1,
        font=dict(size=11, color=INK, family=FONT)
    )

    _style(fig, 330, dict(t=35, b=30, l=55, r=55))
    fig.update_layout(
        yaxis=dict(title=dict(text="Rainfall (mm)", font=dict(color=C_RAIN))),
        yaxis2=dict(
            title=dict(text="City Flood Risk Index", font=dict(color=C_CRIT)),
            overlaying="y", side="right", range=[0, 105],
            tickvals=[0, 25, 50, 75, 100], showgrid=False,
            tickfont=dict(family=MONO, size=11, color=C_CRIT)
        ),
    )
    return fig


def render_ward_vulnerability_bars() -> go.Figure:
    """Ward vulnerability comparison stacked by severity with total indicators."""
    zones = ["Central (Ward 9-14)", "East (Ward 25-28)", "North (Ward 1-5)", "West (Ward 20-24)", "South (Ward 30-35)"]
    critical = [3, 1, 1, 0, 0]
    high = [7, 4, 2, 2, 2]
    medium = [9, 5, 4, 3, 2]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Critical (>80)", x=zones, y=critical, marker_color=C_CRIT,
        text=critical, textposition="inside", insidetextanchor="middle",
        textfont=dict(color="#FFF", family=MONO, size=11)
    ))
    fig.add_trace(go.Bar(
        name="High (60-80)", x=zones, y=high, marker_color=C_HIGH,
        text=high, textposition="inside", insidetextanchor="middle",
        textfont=dict(color="#FFF", family=MONO, size=11)
    ))
    fig.add_trace(go.Bar(
        name="Medium (40-60)", x=zones, y=medium, marker_color=C_WATCH,
        text=medium, textposition="inside", insidetextanchor="middle",
        textfont=dict(color="#FFF", family=MONO, size=11)
    ))

    # Add total location markers
    totals = [c + h + m for c, h, m in zip(critical, high, medium)]
    for z, total in zip(zones, totals):
        fig.add_annotation(
            x=z, y=total + 0.6,
            text=f"<b>{total} sites</b>",
            showarrow=False,
            font=dict(family=MONO, size=10.5, color=INK)
        )

    _style(fig, 320, dict(t=35, b=45, l=45, r=15))
    fig.update_layout(barmode="stack", bargap=0.45)
    fig.update_xaxes(tickfont=dict(family=FONT, size=11.5, color=INK))
    fig.update_yaxes(title="Monitored Drainage Sites", range=[0, 22])
    return fig


def render_blockage_vs_flood_scatter() -> go.Figure:
    """Scatter: Debris blockage % vs standing water depth (cm) with trendline and risk quadrant."""
    blockages = [78, 65, 52, 34, 28, 72, 30, 15, 40, 18, 58, 12, 55, 32, 80, 68]
    water_depths = [28, 22, 15, 11, 8, 26, 9, 4, 12, 5, 17, 3, 16, 8, 29, 24]
    labels = [
        "MG Road", "FC Road", "Swargate", "Pune Stn", "Kothrud", "Deccan",
        "Khadki", "Aundh", "Yerwada", "Karve", "Hadapsar", "Bibwewadi",
        "Kondhwa", "PCMC", "Dapodi", "Sangamwadi"
    ]

    fig = go.Figure()

    # Highlight High-Risk Quadrant (Blockage > 50% & Depth > 15 cm)
    fig.add_shape(
        type="rect",
        x0=50, x1=85, y0=15, y1=32,
        fillcolor="rgba(220, 38, 38, 0.08)",
        line=dict(color=C_CRIT, width=1, dash="dot"),
        layer="below"
    )
    fig.add_annotation(
        x=67, y=30.5,
        text="<b>CRITICAL INTERVENTION ZONE</b><br>Blockage > 50% & Depth > 15 cm",
        showarrow=False,
        font=dict(size=10, color=C_CRIT, family=FONT)
    )

    # Linear trendline rendered as shape to preserve single scatter trace
    slope, intercept = np.polyfit(blockages, water_depths, 1)
    x0_trend, x1_trend = 10, 85
    y0_trend, y1_trend = float(slope * x0_trend + intercept), float(slope * x1_trend + intercept)
    fig.add_shape(
        type="line",
        x0=x0_trend, y0=y0_trend, x1=x1_trend, y1=y1_trend,
        line=dict(color="#0A7C8F", width=2, dash="dash"),
        layer="below"
    )
    fig.add_annotation(
        x=28, y=13,
        text=f"<b>Trend: +{slope:.2f} cm / % blockage</b>",
        showarrow=False,
        font=dict(size=10.5, color="#0A7C8F", family=FONT)
    )

    # Scatter points
    point_colors = [
        C_CRIT if (b > 50 and d > 15) else (C_HIGH if (b > 50 or d > 15) else ACCENT)
        for b, d in zip(blockages, water_depths)
    ]
    fig.add_trace(go.Scatter(
        x=blockages,
        y=water_depths,
        mode="markers+text",
        text=[l if (b > 60 and d > 20) else "" for l, b, d in zip(labels, blockages, water_depths)],
        customdata=labels,
        textposition="top right",
        textfont=dict(family=FONT, size=11, color=INK),
        marker=dict(
            size=11,
            color=point_colors,
            line=dict(color="#FFFFFF", width=1.5),
            symbol="circle"
        ),
        hovertemplate="<b>%{customdata}</b><br>Blockage: %{x}%<br>Water Depth: %{y} cm<extra></extra>",
        name="Drainage Sites"
    ))

    _style(fig, 320, dict(t=25, b=45, l=55, r=15))
    fig.update_xaxes(title="Drainage Debris & Silt Obstruction (%)", showgrid=True, gridcolor="#F1F5F9", range=[8, 88])
    fig.update_yaxes(title="Standing Water Depth (cm)", showgrid=True, gridcolor="#F1F5F9", range=[0, 33])
    return fig
