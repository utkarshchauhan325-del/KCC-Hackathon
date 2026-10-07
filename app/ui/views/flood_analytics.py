"""Analytics view and printable flood risk audit report."""

import io
import json
import textwrap
import streamlit as st
import pandas as pd
from datetime import datetime

from app.ui.pune_data import PUNE_LOCATIONS, KPIS
from app.ui.components.styles import page_header, section_title, status_pill
from app.ui.components.charts import (
    render_7day_rainfall_water_correlation,
    render_ward_vulnerability_bars,
    render_blockage_vs_flood_scatter
)

_CHART_CONFIG = {"displayModeBar": False}


def generate_printable_html_report() -> str:
    """Generate official, print-ready HTML municipal flood risk audit report."""
    timestamp_str = datetime.now().strftime("%B %d, %Y - %I:%M %p")

    crit_locs = [l for l in PUNE_LOCATIONS if l["risk_level"] == "Critical"]
    crit_table_rows = "".join([
        f"""
        <tr>
            <td style="padding:8px; border:1px solid #CBD5E1; font-weight:600;">{l['name']}</td>
            <td style="padding:8px; border:1px solid #CBD5E1;">{l['zone']}</td>
            <td style="padding:8px; border:1px solid #CBD5E1; color:#DC2626; font-weight:700;">{l['risk_score']}/100</td>
            <td style="padding:8px; border:1px solid #CBD5E1;">{l['rainfall_3h']} mm</td>
            <td style="padding:8px; border:1px solid #CBD5E1; font-weight:700; color:#DC2626;">{l['water_level_pct']}%</td>
            <td style="padding:8px; border:1px solid #CBD5E1;">{l['blockage_pct']}%</td>
            <td style="padding:8px; border:1px solid #CBD5E1;">{l['drain_type']}</td>
        </tr>
        """ for l in crit_locs
    ])

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Pune Municipal Corporation - Flood Risk & Drainage Audit Report</title>
        <style>
            body {{
                font-family: Inter, 'Helvetica Neue', Arial, sans-serif;
                color: #0F172A;
                line-height: 1.5;
                margin: 40px;
                background: #FFFFFF;
            }}
            .header {{
                border-bottom: 3px solid #0B1220;
                padding-bottom: 16px;
                margin-bottom: 24px;
            }}
            .title {{
                font-size: 24px;
                font-weight: 800;
                color: #0B1220;
                margin: 0;
                text-transform: uppercase;
                letter-spacing: -0.01em;
            }}
            .subtitle {{
                font-size: 14px;
                color: #475569;
                margin: 4px 0 0 0;
            }}
            .meta-box {{
                display: flex;
                justify-content: space-between;
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                padding: 12px 16px;
                border-radius: 6px;
                margin-bottom: 24px;
                font-size: 13px;
            }}
            h2 {{
                font-size: 16px;
                font-weight: 700;
                color: #0B1220;
                border-bottom: 1px solid #E2E8F0;
                padding-bottom: 6px;
                margin-top: 24px;
                text-transform: uppercase;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 16px 0;
                font-size: 12px;
            }}
            th {{
                background: #F1F5F9;
                color: #1E293B;
                padding: 8px;
                border: 1px solid #CBD5E1;
                text-align: left;
            }}
            .badge-crit {{
                color: #DC2626;
                font-weight: bold;
            }}
            .recommendation-box {{
                background: #EFF6FF;
                border-left: 4px solid #2563EB;
                padding: 12px 16px;
                margin: 16px 0;
                font-size: 13px;
            }}
            .footer {{
                margin-top: 50px;
                border-top: 1px solid #CBD5E1;
                padding-top: 16px;
                display: flex;
                justify-content: space-between;
                font-size: 11px;
                color: #64748B;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1 class="title">Pune Municipal Corporation</h1>
            <div class="subtitle">Disaster Management Cell &middot; Flood Risk and Drainage Audit</div>
        </div>

        <div class="meta-box">
            <div><b>Report Ref:</b> PMC/DRM/2026/FL-0924</div>
            <div><b>Assessment Date:</b> {timestamp_str}</div>
            <div><b>Surveillance Jurisdiction:</b> Pune Central & Greater Urban Corridors</div>
            <div><b>Classification:</b> PRIORITY LEVEL 1 (ACTIONABLE)</div>
        </div>

        <h2>1. Executive Summary & Overall Risk Posture</h2>
        <p>
            An audit of hydrological and camera data across <b>53 municipal monitoring stations</b> reveals elevated surcharge and backflow vulnerability across low-lying arterial corridors.
            A cumulative <b>5 locations</b> are currently operating under <b>Critical Flood Hazard Thresholds (Water capacity &gt; 80%)</b>, primarily exacerbated by solid-waste culvert choking and the Mula-Mutha river stage rising (+1.4m above baseline).
        </p>

        <div class="recommendation-box">
            <b>Emergency Directives:</b> Immediate deployment of high-capacity mobile dewatering pumps (500-1000 GPM) to MG Road and FC Road junctions. Mechanical desilting crawlers to be mobilized to Deccan Gymkhana sluice gates within 45 minutes.
        </div>

        <h2>2. Critical Hotspots & Telemetry Breakdown</h2>
        <table>
            <thead>
                <tr>
                    <th>Location</th>
                    <th>Zone</th>
                    <th>Risk Score</th>
                    <th>3h Rainfall</th>
                    <th>Water Capacity</th>
                    <th>Trash Blockage</th>
                    <th>Conduit Specification</th>
                </tr>
            </thead>
            <tbody>
                {crit_table_rows}
            </tbody>
        </table>

        <h2>3. Root Cause & Computer Vision Diagnostics</h2>
        <ul>
            <li><b>Debris Choking (78% Correlation):</b> Vision inspection shows plastic and corrugated packaging accumulation over intake gratings, impeding gravity discharge.</li>
            <li><b>River Stage Backflow:</b> Mula-Mutha river levels have exceeded the discharge sill level at Deccan Gymkhana, preventing unassisted gravity outfall.</li>
            <li><b>Underpass Sump Saturation:</b> Pune Station underpass automated pump sump operating at 60% capacity; backup generator units cleared for continuous duty.</li>
        </ul>

        <h2>4. Actionable 24-Hour Engineering Interventions</h2>
        <ol>
            <li><b>Hour 0 - 2:</b> Deploy Mobile Dewatering Units OP-701 &amp; OP-702 to clear MG Road and FC Road intersections.</li>
            <li><b>Hour 2 - 6:</b> Sluice gate mechanical debris removal at Bund Garden and Deccan Gymkhana outfalls.</li>
            <li><b>Hour 6 - 24:</b> Solid Waste Department enforcement of strict commercial dumping fines under Section 376 of Maharashtra Municipal Corporations Act.</li>
        </ol>

        <div class="footer">
            <div>Generated by FloodGuard</div>
            <div>For review by the Chief Disaster Management Officer, Pune Municipal Corporation</div>
        </div>
    </body>
    </html>
    """

def render_flood_analytics():
    """Render analytics charts, the audit report summary and data exports."""

    st.markdown(page_header(
        "Analytics and reports",
        "Rainfall against risk, ward comparison and blockage against standing water. Export the audit report and datasets.",
        eyebrow="Analytics",
        meta=["Report ref <b>PMC/DRM/2026/FL-0924</b>"],
    ), unsafe_allow_html=True)

    tab_graphs, tab_report, tab_export = st.tabs(["Charts", "Audit report", "Export"])

    with tab_graphs:
        with st.container(border=True):
            st.markdown(section_title(
                "Rainfall and city risk index, last 7 days",
                "Cumulative rainfall (bars) against the deterministic sewer overflow risk index (line)",
            ), unsafe_allow_html=True)
            st.plotly_chart(render_7day_rainfall_water_correlation(), use_container_width=True, config=_CHART_CONFIG)

        c1, c2 = st.columns([1, 1], gap="medium")
        with c1:
            with st.container(border=True):
                st.markdown(section_title("Locations by zone and severity", "Critical, high and medium points per municipal zone"), unsafe_allow_html=True)
                st.plotly_chart(render_ward_vulnerability_bars(), use_container_width=True, config=_CHART_CONFIG)
        with c2:
            with st.container(border=True):
                st.markdown(section_title("Blockage against standing water", "Each point is a monitored location"), unsafe_allow_html=True)
                st.plotly_chart(render_blockage_vs_flood_scatter(), use_container_width=True, config=_CHART_CONFIG)

    with tab_report:
        st.caption("PMC/DRM/2026/FL-0924 · Pune Municipal Corporation, Disaster Management Cell")
        h3 = "font-family:var(--fg-font-head); color:#0B1220; font-size:15px; font-weight:600; margin:22px 0 6px 0;"
        body = "font-size:13.5px; color:#334155; line-height:1.65;"
        report_summary_html = f"""
<div class="fg-card" style="padding:26px 30px;">
<div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap; padding-bottom:14px; border-bottom:1px solid #E3E8EF; margin-bottom:16px;">
<div>
<div class="fg-eyebrow">Pune Municipal Corporation</div>
<div style="font-family:var(--fg-font-head); font-size:20px; font-weight:600; color:#0B1220;">Flood risk and drainage audit</div>
<div style="color:#64708A; font-size:12.5px;">Disaster Management Cell</div>
</div>
{status_pill('High', 'Active monsoon surcharge')}
</div>
<div class="fg-kv" style="border-top:none; padding-top:0;">
<div><span class="fg-k">Date</span><span class="fg-v mono">24 Sep 2026</span></div>
<div><span class="fg-k">City risk index</span><span class="fg-v mono" style="color:#C8281C;">78.4 / 100</span></div>
<div><span class="fg-k">Monsoon stage</span><span class="fg-v">Active, low pressure</span></div>
<div><span class="fg-k">Monitored</span><span class="fg-v">53 locations, 6 cameras</span></div>
</div>
<div style="{h3}">1. Summary</div>
<p style="{body}">Camera and sensor data from 53 arterial junctions show immediate waterlogging risk at <b>5 critical locations</b>: MG Road Junction, FC Road Junction, Deccan Gymkhana, Dapodi Confluence and Sangamwadi. Runoff is held back by high antecedent rainfall (average 34 mm in 3 h), debris in stormwater box culverts (average 71% blocked) and a raised Mula-Mutha river stage.</p>
<div style="{h3}">2. Bottlenecks</div>
<ul style="{body}">
<li><b>MG Road Junction (Ward 14):</b> 90% conduit capacity, 28 cm standing water. Plastic and debris on road gratings. Mobile dewatering pump deployed.</li>
<li><b>FC Road Junction (Ward 09):</b> 80% capacity. Commercial cardboard and plastic blocking the inlet. Solid waste enforcement notified.</li>
<li><b>Deccan Gymkhana sluice gate:</b> River backflow prevents gravity drainage to the Mula outfall. Flap gate needs clearing by crane.</li>
</ul>
<div style="{h3}">3. Sewer overflow scoring (pass C)</div>
<p style="{body}">Scores are computed in code, not by the model:</p>
<code style="display:block; background:#F8FAFC; border:1px solid #E3E8EF; border-radius:8px; padding:10px 12px; font-size:12px; color:#0B1220; white-space:pre-wrap;">Risk = 0.35 x Water_State + 0.25 x Trash_Inside + 0.15 x Trash_Near + 0.10 x Inlet_Blocked + 0.10 x Hazard_Weight + 0.05 x Wet_Condition</code>
<p style="{body} margin-top:8px;">A floor of 70 points applies whenever standing sewage or bubbling water is identified.</p>
<div style="{h3}">4. Orders</div>
<ol style="{body}">
<li>Move 500 GPM mobile pumps to MG Road and FC Road junctions.</li>
<li>Activate the Traffic Ward 3 underpass barricade protocol if rainfall exceeds 40 mm in the next 2 hours.</li>
<li>Send a jetting machine to the Deccan Gymkhana river discharge culvert.</li>
</ol>
</div>
"""
        st.markdown(" ".join(l.strip() for l in report_summary_html.splitlines() if l.strip()), unsafe_allow_html=True)

    with tab_export:
        e1, e2, e3 = st.columns(3, gap="medium")

        with e1:
            with st.container(border=True):
                st.markdown(section_title("Audit report", "Printable HTML. Use the browser's print dialog to save as PDF."), unsafe_allow_html=True)
                st.download_button(
                    label="Download report (HTML)",
                    data=generate_printable_html_report(),
                    file_name=f"PMC_Flood_Risk_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                    mime="text/html",
                    type="primary",
                    use_container_width=True
                )

        with e2:
            with st.container(border=True):
                st.markdown(section_title("Location data (CSV)", "All 53 locations with rainfall, capacity and risk scores."), unsafe_allow_html=True)
                df_export = pd.DataFrame(PUNE_LOCATIONS)
                st.download_button(
                    label="Download CSV",
                    data=df_export.to_csv(index=False).encode('utf-8'),
                    file_name=f"pune_flood_telemetry_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        with e3:
            with st.container(border=True):
                st.markdown(section_title("Locations (GeoJSON)", "Point layer for QGIS, ArcGIS or other GIS tools."), unsafe_allow_html=True)
                geojson_data = {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": [l["lng"], l["lat"]]},
                            "properties": l
                        } for l in PUNE_LOCATIONS
                    ]
                }
                st.download_button(
                    label="Download GeoJSON",
                    data=json.dumps(geojson_data, indent=2),
                    file_name=f"pune_flood_hotspots_{datetime.now().strftime('%Y%m%d')}.geojson",
                    mime="application/json",
                    use_container_width=True
                )
