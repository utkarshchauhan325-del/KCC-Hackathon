"""Interactive Plotly charts for FloodGuard Municipal Intelligence."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Dict, Any

def render_risk_distribution_donut() -> go.Figure:
    """Render the exact donut chart showing Risk Distribution across 53 locations."""
    labels = ["Critical", "High", "Medium", "Low"]
    values = [5, 17, 23, 8]
    colors = ["#EF4444", "#F97316", "#F59E0B", "#10B981"]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.68,
        sort=False,
        direction="clockwise",
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
        textinfo="none",
        hoverinfo="label+value+percent",
        hovertemplate="<b>%{label} Risk</b><br>Locations: %{value}<br>Share: %{percent}<extra></extra>"
    )])

    # Center label annotation "53 Total Locations"
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(size=12, color="#475569", family="Plus Jakarta Sans"),
            itemsizing="constant"
        ),
        margin=dict(t=10, b=10, l=10, r=100),
        height=220,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        annotations=[
            dict(
                text="<b>53</b><br><span style='font-size:11px;color:#64748B;font-weight:500;'>Total<br>Locations</span>",
                x=0.5, y=0.5,
                font=dict(size=20, color="#0F172A", family="Plus Jakarta Sans"),
                showarrow=False
            )
        ]
    )
    return fig

def render_rainfall_forecast_bars() -> go.Figure:
    """Render the 24h rainfall forecast bar chart."""
    hours = ["Now", "3h", "6h", "12h", "24h"]
    rainfall = [12, 34, 52, 74, 32]

    fig = go.Figure(data=[go.Bar(
        x=hours,
        y=rainfall,
        marker=dict(
            color="#3B82F6",
            line=dict(color="#2563EB", width=1)
        ),
        width=0.45,
        hovertemplate="<b>%{x}</b><br>Rainfall: %{y} mm<extra></extra>"
    )])

    fig.update_layout(
        margin=dict(t=15, b=25, l=35, r=15),
        height=220,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(
            title="",
            range=[0, 85],
            tickmode="array",
            tickvals=[0, 40, 80],
            ticktext=["0 mm", "40 mm", "80 mm"],
            gridcolor="#F1F5F9",
            zerolinecolor="#E2E8F0",
            tickfont=dict(size=11, color="#64748B")
        ),
        xaxis=dict(
            title="",
            tickfont=dict(size=11, color="#64748B"),
            showgrid=False
        )
    )
    return fig

def render_water_level_trend() -> go.Figure:
    """Render the multi-line chart for Water Level Trend (MG Road vs FC Road)."""
    times = ["Now", "3h", "6h", "12h", "24h"]
    mg_road = [38, 52, 54, 78, 90]
    fc_road = [28, 36, 40, 60, 58]

    fig = go.Figure()

    # MG Road (Critical - Red)
    fig.add_trace(go.Scatter(
        x=times,
        y=mg_road,
        mode="lines+markers",
        name="MG Road",
        line=dict(color="#EF4444", width=2.5),
        marker=dict(size=6, color="#EF4444"),
        hovertemplate="MG Road: %{y}%<extra></extra>"
    ))

    # FC Road (High - Orange)
    fig.add_trace(go.Scatter(
        x=times,
        y=fc_road,
        mode="lines+markers",
        name="FC Road",
        line=dict(color="#F97316", width=2.5),
        marker=dict(size=6, color="#F97316"),
        hovertemplate="FC Road: %{y}%<extra></extra>"
    ))

    # Projected dotted tail
    fig.add_trace(go.Scatter(
        x=["12h", "24h"],
        y=[78, 90],
        mode="lines",
        name="Projected",
        line=dict(color="#EF4444", width=2, dash="dot"),
        showlegend=False,
        hoverinfo="skip"
    ))

    fig.update_layout(
        margin=dict(t=15, b=25, l=45, r=15),
        height=220,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color="#64748B")
        ),
        yaxis=dict(
            title="",
            range=[0, 105],
            tickmode="array",
            tickvals=[0, 50, 100],
            ticktext=["0%", "50%", "100%"],
            gridcolor="#F1F5F9",
            zerolinecolor="#E2E8F0",
            tickfont=dict(size=11, color="#64748B")
        ),
        xaxis=dict(
            title="",
            tickfont=dict(size=11, color="#64748B"),
            showgrid=False
        )
    )
    return fig

def render_7day_rainfall_water_correlation() -> go.Figure:
    """Historical 7-Day rainfall vs water level correlation for analytics."""
    days = ["Sep 18", "Sep 19", "Sep 20", "Sep 21", "Sep 22", "Sep 23", "Sep 24"]
    rain = [5.2, 12.0, 48.5, 62.4, 88.0, 110.5, 134.2]
    flood_index = [12, 18, 42, 58, 74, 86, 92]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=days, y=rain,
        name="Daily Cumulative Rain (mm)",
        marker_color="#93C5FD",
        opacity=0.7,
        yaxis="y"
    ))
    fig.add_trace(go.Scatter(
        x=days, y=flood_index,
        name="City Surcharge Risk Index (0-100)",
        mode="lines+markers",
        line=dict(color="#DC2626", width=3),
        marker=dict(size=8, color="#DC2626"),
        yaxis="y2"
    ))

    fig.update_layout(
        title="7-Day Historical Monsoon Accumulation vs Surcharge Surge",
        height=320,
        margin=dict(t=40, b=30, l=40, r=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.1, x=0.2),
        yaxis=dict(title="Precipitation (mm)", gridcolor="#F1F5F9"),
        yaxis2=dict(title="Risk Index", overlaying="y", side="right", range=[0, 100], gridcolor="rgba(0,0,0,0)")
    )
    return fig

def render_ward_vulnerability_bars() -> go.Figure:
    """Ward vulnerability comparison across Central, West, East, North, South."""
    zones = ["Central (Ward 9-14)", "East (Ward 25-28)", "North (Ward 1-5)", "West (Ward 20-24)", "South (Ward 30-35)"]
    critical = [3, 1, 1, 0, 0]
    high = [7, 4, 2, 2, 2]
    medium = [9, 5, 4, 3, 2]

    fig = go.Figure(data=[
        go.Bar(name="Critical", x=zones, y=critical, marker_color="#EF4444"),
        go.Bar(name="High", x=zones, y=high, marker_color="#F97316"),
        go.Bar(name="Medium", x=zones, y=medium, marker_color="#F59E0B")
    ])

    fig.update_layout(
        barmode="stack",
        height=300,
        margin=dict(t=30, b=40, l=30, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.1, x=0.3),
        yaxis=dict(gridcolor="#F1F5F9", title="Location Count")
    )
    return fig

def render_blockage_vs_flood_scatter() -> go.Figure:
    """Scatter analysis: Debris Blockage % vs Waterlogging Depth (cm)."""
    blockages = [78, 65, 52, 34, 28, 72, 30, 15, 40, 18, 58, 12, 55, 32, 80, 68]
    water_depths = [28, 22, 15, 11, 8, 26, 9, 4, 12, 5, 17, 3, 16, 8, 29, 24]
    labels = ["MG Road", "FC Road", "Swargate", "Pune Stn", "Kothrud", "Deccan", "Khadki", "Aundh", "Yerwada", "Karve", "Hadapsar", "Bibwewadi", "Kondhwa", "PCMC", "Dapodi", "Sangamwadi"]

    fig = go.Figure(data=go.Scatter(
        x=blockages,
        y=water_depths,
        text=labels,
        mode="markers+text",
        textposition="top center",
        marker=dict(
            size=12,
            color=water_depths,
            colorscale="Reds",
            showscale=True,
            colorbar=dict(title="Depth (cm)", len=0.8)
        ),
        hovertemplate="<b>%{text}</b><br>Blockage: %{x}%<br>Water Depth: %{y} cm<extra></extra>"
    ))

    fig.update_layout(
        title="Culvert Trash Blockage vs Water Depth Correlation",
        height=300,
        margin=dict(t=40, b=30, l=40, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Debris / Silt Blockage (%)", gridcolor="#F1F5F9"),
        yaxis=dict(title="Standing Water Depth (cm)", gridcolor="#F1F5F9")
    )
    return fig
