"""Flood Analytics View & Detailed Municipal Analysis Audit Report Generator."""

import io
import json
import streamlit as st
import pandas as pd
from datetime import datetime

from app.ui.pune_data import PUNE_LOCATIONS, KPIS
from app.ui.components.charts import (
    render_7day_rainfall_water_correlation,
    render_ward_vulnerability_bars,
    render_blockage_vs_flood_scatter
)

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
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                color: #0F172A;
                line-height: 1.5;
                margin: 40px;
                background: #FFFFFF;
            }}
            .header {{
                border-bottom: 3px solid #1E3A8A;
                padding-bottom: 16px;
                margin-bottom: 24px;
            }}
            .title {{
                font-size: 24px;
                font-weight: 800;
                color: #1E3A8A;
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
                color: #1E3A8A;
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
            <h1 class="title">🏛️ Pune Municipal Corporation</h1>
            <div class="subtitle">Disaster Management Cell • FloodGuard Municipal Intelligence Audit Report</div>
        </div>

        <div class="meta-box">
            <div><b>Report Ref:</b> PMC/DRM/2026/FL-0924</div>
            <div><b>Assessment Date:</b> {timestamp_str}</div>
            <div><b>Surveillance Jurisdiction:</b> Pune Central & Greater Urban Corridors</div>
            <div><b>Classification:</b> PRIORITY LEVEL 1 (ACTIONABLE)</div>
        </div>

        <h2>1. Executive Summary & Overall Risk Posture</h2>
        <p>
            An intensive hydrological and vision-intelligence audit conducted across <b>53 municipal monitoring stations</b> reveals elevated surcharge and backflow vulnerability across low-lying arterial corridors.
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
            <div>Generated by FloodGuard Municipal Intelligence Core</div>
            <div>Certified by Chief Disaster Management Officer, Pune Municipal Corp.</div>
        </div>
    </body>
    </html>
    """

def render_flood_analytics():
    """Render comprehensive flood analytics graphs and municipal audit report."""

    st.markdown("""
    <div class="flood-header">
        <div class="flood-title-block">
            <h1>Flood Analytics & Municipal Audit Report</h1>
            <p>Hydrological correlations, infrastructure capacity analysis, and certified executive reporting</p>
        </div>
        <div class="header-actions">
            <div class="date-badge">📈 Automated AI Analysis Engine</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_graphs, tab_report, tab_export = st.tabs([
        "📊 Advanced Analytical Graphs",
        "📑 Comprehensive Municipal Audit Report",
        "📥 Data & Report Export"
    ])

    with tab_graphs:
        st.markdown("### 📈 Hydrological Correlation & Surcharge Analytics")

        # Row 1: 7-Day Monsoon Correlation
        st.markdown("""
        <div class="fg-card">
            <h4 class="fg-card-title">Precipitation Accumulation vs City-Wide Risk Index</h4>
            <p class="fg-card-sub">Dual-axis correlation of cumulative rainfall against the deterministic sewer overflow risk index</p>
        """, unsafe_allow_html=True)
        corr_fig = render_7day_rainfall_water_correlation()
        st.plotly_chart(corr_fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Row 2: Ward Comparison and Scatter Correlation
        c1, c2 = st.columns([1, 1], gap="medium")
        with c1:
            st.markdown("""
            <div class="fg-card">
                <h4 class="fg-card-title">Ward Vulnerability Matrix</h4>
                <p class="fg-card-sub">Distribution of Critical, High, and Medium risk points per municipal zone</p>
            """, unsafe_allow_html=True)
            ward_fig = render_ward_vulnerability_bars()
            st.plotly_chart(ward_fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("""
            <div class="fg-card">
                <h4 class="fg-card-title">Culvert Blockage vs Standing Water Depth</h4>
                <p class="fg-card-sub">Empirical validation: Solid debris blockage directly drives road waterlogging depth</p>
            """, unsafe_allow_html=True)
            scatter_fig = render_blockage_vs_flood_scatter()
            st.plotly_chart(scatter_fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with tab_report:
        st.markdown("### 🏛️ Executive Flood Risk & Drainage Audit Report")
        st.caption("Official Document: PMC/DRM/2026/FL-0924 • Pune Municipal Corporation Disaster Management Cell")

        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:10px; padding:24px 30px; box-shadow:0 1px 4px rgba(0,0,0,0.05); font-family:'Plus Jakarta Sans',sans-serif;">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #1E3A8A; padding-bottom:12px; margin-bottom:20px;">
                <div>
                    <h2 style="color:#1E3A8A; margin:0; font-size:22px; font-weight:800;">PUNE MUNICIPAL CORPORATION</h2>
                    <div style="color:#64748B; font-size:13px; font-weight:600;">Disaster Management Cell • Municipal Intelligence Flood Risk Audit</div>
                </div>
                <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:6px; padding:6px 12px; font-size:12px; color:#1E40AF; font-weight:700;">
                    STATUS: ACTIVE MONSOON SURCHARGE
                </div>
            </div>

            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:12px; background:#F8FAFC; border:1px solid #E2E8F0; padding:12px; border-radius:8px; margin-bottom:20px; font-size:12px;">
                <div><b>Date:</b> Sep 24, 2026</div>
                <div><b>City Risk Index:</b> <span style="color:#DC2626; font-weight:800;">78.4 / 100 (HIGH)</span></div>
                <div><b>Monsoon Stage:</b> Active Monsoon Low Pressure</div>
                <div><b>Monitored Nodes:</b> 53 Locations (6 CCTV Feeds)</div>
            </div>

            <h3 style="color:#1E3A8A; font-size:16px; font-weight:700; border-bottom:1px solid #E2E8F0; padding-bottom:4px; margin-top:16px;">1. EXECUTIVE SUMMARY</h3>
            <p style="font-size:13px; color:#334155; line-height:1.6;">
                A city-wide automated surveillance audit utilizing computer vision telemetry across 53 arterial junctions indicates immediate waterlogging vulnerability in <b>5 critical locations</b>: MG Road Junction, FC Road Junction, Deccan Gymkhana, Dapodi Confluence, and Sangamwadi. Surface runoff is hindered by a composite effect of <b>high antecedent rainfall (avg 34mm / 3h)</b>, <b>debris blockage in stormwater box culverts (average 71% choke)</b>, and <b>elevated stage levels along the Mula-Mutha river corridor</b>.
            </p>

            <h3 style="color:#1E3A8A; font-size:16px; font-weight:700; border-bottom:1px solid #E2E8F0; padding-bottom:4px; margin-top:20px;">2. CRITICAL BOTTLENECK ANALYSIS</h3>
            <div style="font-size:13px; color:#334155; line-height:1.6;">
                <ul>
                    <li><b>MG Road Junction (Ward 14):</b> 90% water capacity reached with 28cm standing depth. Vision models indicate heavy plastic bag and debris entrapment on road gratings. Mobile dewatering pump unit deployed.</li>
                    <li><b>FC Road Junction (Ward 09):</b> 80% capacity reached. Commercial cardboard and plastic dumping directly suffocating intake throat. Solid waste enforcement crew notified.</li>
                    <li><b>Deccan Gymkhana Sluice Gate:</b> River backflow prevents gravity drainage into Mula river outfall. Requires flap gate clearance crane.</li>
                </ul>
            </div>

            <h3 style="color:#1E3A8A; font-size:16px; font-weight:700; border-bottom:1px solid #E2E8F0; padding-bottom:4px; margin-top:20px;">3. DETERMINISTIC SEWER OVERFLOW SCORING (PASS C)</h3>
            <p style="font-size:13px; color:#334155; line-height:1.6;">
                Risk scores are calculated using the deterministic formula:
                <br>
                <code>Risk = (0.35 × Water_State) + (0.25 × Trash_Inside) + (0.15 × Trash_Near) + (0.10 × Inlet_Blocked) + (0.10 × Hazard_Weight) + (0.05 × Wet_Condition)</code>
                <br>
                Where sewer overflow surcharge floor of 70 points is applied deterministically whenever standing sewage or bubbling water is identified by the Vision Language Model.
            </p>

            <h3 style="color:#1E3A8A; font-size:16px; font-weight:700; border-bottom:1px solid #E2E8F0; padding-bottom:4px; margin-top:20px;">4. ACTIONABLE DIRECTIVES & REMEDIATION PLAN</h3>
            <div style="background:#EFF6FF; border-left:4px solid #2563EB; padding:12px 16px; border-radius:4px; font-size:13px; color:#1E3A8A; line-height:1.6;">
                <b>Immediate Orders:</b>
                <br>1. Mobilize Mobile 500 GPM pump units to MG Road and FC Road junctions immediately.
                <br>2. Activate Traffic Ward 3 underpass barricade protocol if rainfall exceeds 40mm in the next 2 hours.
                <br>3. Engage desilting jetting machine for Deccan Gymkhana river discharge culvert.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tab_export:
        st.markdown("### 📥 Export Official Reports & Telemetry Datasets")

        e1, e2, e3 = st.columns(3)

        with e1:
            st.markdown("#### 📄 Printable Audit Report")
            st.write("Full certified municipal intelligence report ready for executive briefings and print/PDF.")
            html_report = generate_printable_html_report()
            st.download_button(
                label="⬇️ Download HTML / PDF Report",
                data=html_report,
                file_name=f"PMC_Flood_Risk_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                mime="text/html",
                type="primary",
                use_container_width=True
            )

        with e2:
            st.markdown("#### 📊 Sensor Telemetry (CSV)")
            st.write("Complete tabular dataset of all 53 monitoring locations with rainfall, capacity, and risk scores.")
            df_export = pd.DataFrame(PUNE_LOCATIONS)
            csv_data = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Download Telemetry CSV",
                data=csv_data,
                file_name=f"pune_flood_telemetry_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with e3:
            st.markdown("#### 🗺️ Geospatial GeoJSON")
            st.write("Spatial GIS vector dataset for loading directly into QGIS, ArcGIS, or municipal command map.")
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
                label="⬇️ Download GeoJSON Layer",
                data=json.dumps(geojson_data, indent=2),
                file_name=f"pune_flood_hotspots_{datetime.now().strftime('%Y%m%d')}.geojson",
                mime="application/json",
                use_container_width=True
            )
