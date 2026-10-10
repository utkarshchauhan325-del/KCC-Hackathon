"""Analytics view and printable flood risk audit report."""

import io
import json
import textwrap
import streamlit as st
import pandas as pd
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from app.ui.pune_data import PUNE_LOCATIONS, KPIS
from app.ui.components.styles import page_header, section_title, status_pill
from app.ui.components.charts import (
    render_7day_rainfall_water_correlation,
    render_ward_vulnerability_bars,
    render_blockage_vs_flood_scatter
)

_CHART_CONFIG = {"displayModeBar": False}


def generate_printable_pdf_report() -> bytes:
    """Generate official, print-ready PDF municipal flood risk audit report."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    printable_width = 595.27 - 72

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0B1220'),
    )
    sub_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
    )
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor('#0B1220'),
        spaceBefore=10,
        spaceAfter=5,
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1E293B'),
    )
    callout_style = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1E3A8A'),
    )
    meta_val_style = ParagraphStyle(
        'MetaV',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#0B1220'),
    )
    th_style = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1E293B'),
    )
    td_style = ParagraphStyle(
        'TD',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#1E293B'),
    )
    td_crit_style = ParagraphStyle(
        'TDCrit',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#DC2626'),
    )

    timestamp_str = datetime.now().strftime("%B %d, %Y - %I:%M %p")

    story = []
    story.append(Paragraph('PUNE MUNICIPAL CORPORATION', title_style))
    story.append(Paragraph('Disaster Management Cell &middot; Flood Risk and Drainage Audit', sub_style))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width='100%', thickness=2, color=colors.HexColor('#0B1220'), spaceAfter=8))

    # Metadata table
    meta_data = [
        [
            Paragraph('<b>Report Ref:</b> PMC/DRM/2026/FL-0924', meta_val_style),
            Paragraph(f'<b>Assessment Date:</b> {timestamp_str}', meta_val_style),
        ],
        [
            Paragraph('<b>Surveillance Jurisdiction:</b> Pune Central & Greater Urban Corridors', meta_val_style),
            Paragraph('<b>Classification:</b> <font color="#DC2626"><b>PRIORITY LEVEL 1 (ACTIONABLE)</b></font>', meta_val_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[printable_width * 0.5, printable_width * 0.5])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Section 1: Executive Summary
    story.append(Paragraph('1. Executive Summary &amp; Overall Risk Posture', h2_style))
    story.append(Paragraph(
        'An audit of hydrological and camera data across <b>53 municipal monitoring stations</b> reveals elevated surcharge and backflow vulnerability across low-lying arterial corridors. '
        'A cumulative <b>5 locations</b> are currently operating under <b>Critical Flood Hazard Thresholds (Water capacity &gt; 80%)</b>, primarily exacerbated by solid-waste culvert choking and the Mula-Mutha river stage rising (+1.4m above baseline).',
        body_style,
    ))
    story.append(Spacer(1, 6))

    # Emergency Directives Callout
    callout_data = [[Paragraph(
        '<b>Emergency Directives:</b> Immediate deployment of high-capacity mobile dewatering pumps (500-1000 GPM) to MG Road and FC Road junctions. '
        'Mechanical desilting crawlers to be mobilized to Deccan Gymkhana sluice gates within 45 minutes.',
        callout_style,
    )]]
    callout_table = Table(callout_data, colWidths=[printable_width])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EFF6FF')),
        ('LINELEFT', (0, 0), (0, -1), 3, colors.HexColor('#2563EB')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#BFDBFE')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 8))

    # Section 2: Critical Hotspots Table
    story.append(Paragraph('2. Critical Hotspots &amp; Telemetry Breakdown', h2_style))
    crit_locs = [l for l in PUNE_LOCATIONS if l['risk_level'] == 'Critical']
    th_row = [
        Paragraph('Location', th_style),
        Paragraph('Zone', th_style),
        Paragraph('Risk Score', th_style),
        Paragraph('3h Rain', th_style),
        Paragraph('Water Cap.', th_style),
        Paragraph('Trash Blk.', th_style),
        Paragraph('Conduit Specification', th_style),
    ]
    col_w = [110, 65, 55, 50, 60, 55, 128]
    table_rows = [th_row]
    for l in crit_locs:
        table_rows.append([
            Paragraph(str(l['name']), td_style),
            Paragraph(str(l['zone']), td_style),
            Paragraph(f"{l['risk_score']}/100", td_crit_style),
            Paragraph(f"{l['rainfall_3h']} mm", td_style),
            Paragraph(f"{l['water_level_pct']}%", td_crit_style),
            Paragraph(f"{l['blockage_pct']}%", td_style),
            Paragraph(str(l['drain_type']), td_style),
        ])

    crit_table = Table(table_rows, colWidths=col_w)
    crit_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(crit_table)
    story.append(Spacer(1, 8))

    # Section 3: Root Cause Diagnostics
    story.append(Paragraph('3. Root Cause &amp; Computer Vision Diagnostics', h2_style))
    bullets = [
        '<b>Debris Choking (78% Correlation):</b> Vision inspection shows plastic and corrugated packaging accumulation over intake gratings, impeding gravity discharge.',
        '<b>River Stage Backflow:</b> Mula-Mutha river levels have exceeded the discharge sill level at Deccan Gymkhana, preventing unassisted gravity outfall.',
        '<b>Underpass Sump Saturation:</b> Pune Station underpass automated pump sump operating at 60% capacity; backup generator units cleared for continuous duty.',
    ]
    for b in bullets:
        story.append(Paragraph(f'&bull; {b}', body_style))
        story.append(Spacer(1, 2))

    # Section 4: Actionable Interventions
    story.append(Spacer(1, 4))
    story.append(Paragraph('4. Actionable 24-Hour Engineering Interventions', h2_style))
    interventions = [
        '<b>Hour 0 - 2:</b> Deploy Mobile Dewatering Units OP-701 &amp; OP-702 to clear MG Road and FC Road intersections.',
        '<b>Hour 2 - 6:</b> Sluice gate mechanical debris removal at Bund Garden and Deccan Gymkhana outfalls.',
        '<b>Hour 6 - 24:</b> Solid Waste Department enforcement of strict commercial dumping fines under Section 376 of Maharashtra Municipal Corporations Act.',
    ]
    for i, item in enumerate(interventions, 1):
        story.append(Paragraph(f'{i}. {item}', body_style))
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceAfter=4))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor('#64748B'),
    )
    story.append(Table([[
        Paragraph('Generated by FloodGuard &middot; Disaster Management Cell', footer_style),
        Paragraph('For review by the Chief Disaster Management Officer, Pune Municipal Corporation', ParagraphStyle('FR', parent=footer_style, alignment=2)),
    ]], colWidths=[printable_width * 0.5, printable_width * 0.5], style=[
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    doc.build(story)
    return buf.getvalue()


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
                st.markdown(section_title("Blockage against standing water", "Standing water depth (mm) by drainage blockage severity tier"), unsafe_allow_html=True)
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
<div style="{h3}">Overview</div>
<p style="{body}">Camera and sensor data from 53 arterial junctions indicate immediate waterlogging risk at 5 critical locations: MG Road Junction, FC Road Junction, Deccan Gymkhana, Dapodi Confluence, and Sangamwadi.</p>
<p style="{body}">Current risk is driven by high antecedent rainfall (average 34 mm in 3 hours), debris blocking stormwater box culverts (average 71%), and a raised Mula-Mutha river stage, which is restricting drainage.</p>
<div style="{h3}">Sewer Overflow Risk Formula</div>
<p style="{body}">Risk scores are computed in code using:</p>
<code style="display:block; background:#F8FAFC; border:1px solid #E3E8EF; border-radius:8px; padding:10px 12px; font-size:12px; color:#0B1220; white-space:pre-wrap;">Risk = 0.35 &times; Water_State + 0.25 &times; Trash_Inside + 0.15 &times; Trash_Near + 0.10 &times; Inlet_Blocked + 0.10 &times; Hazard_Weight + 0.05 &times; Wet_Condition</code>
<p style="{body} margin-top:8px;">A minimum risk score of 70 points is applied whenever standing sewage or bubbling water is identified.</p>
</div>
"""
        st.markdown(" ".join(l.strip() for l in report_summary_html.splitlines() if l.strip()), unsafe_allow_html=True)

    with tab_export:
        e1, e2, e3 = st.columns(3, gap="medium")

        with e1:
            with st.container(border=True):
                st.markdown(section_title("Audit report", "Official municipal flood risk and drainage audit report in PDF format."), unsafe_allow_html=True)
                pdf_report_bytes = generate_printable_pdf_report()
                st.download_button(
                    label="Download report (PDF)",
                    data=pdf_report_bytes,
                    file_name=f"PMC_Flood_Risk_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )

        with e2:
            with st.container(border=True):
                st.markdown(section_title("Location data (CSV)", "All 53 locations with rainfall, capacity and risk scores."), unsafe_allow_html=True)
                df_export = pd.DataFrame(PUNE_LOCATIONS)
                try:
                    csv_data = df_export.to_csv(index=False).encode('utf-8')
                except Exception:
                    import csv
                    import io
                    buf = io.StringIO()
                    if PUNE_LOCATIONS:
                        writer = csv.DictWriter(buf, fieldnames=list(PUNE_LOCATIONS[0].keys()))
                        writer.writeheader()
                        writer.writerows(PUNE_LOCATIONS)
                    csv_data = buf.getvalue().encode('utf-8')
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
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
