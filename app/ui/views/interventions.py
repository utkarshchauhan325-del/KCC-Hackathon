"""Operations & Interventions View - Municipal Machinery & Crew Dispatch Tracker."""

import time
import textwrap
import streamlit as st
from app.ui.pune_data import OPERATIONS_INTERVENTIONS, PUNE_LOCATIONS

# Municipal roster of Junior Engineers and Rapid Response Unit Leads across Pune
PUNE_MUNICIPAL_CREW_ROSTER = [
    "S. Patil (Junior Engineer)",
    "V. Kadam (Roads & Drainage)",
    "Traffic Ward 3",
    "Disaster Cell Engr. 2",
    "R. Deshmukh (Drainage Specialist - Shivajinagar)",
    "A. Shinde (Junior Engineer - Aundh)",
    "M. Joshi (Quick Response - Swargate)",
    "P. More (Mechanical Division - Hadapsar)",
    "K. Gaikwad (Disaster Mgmt - Kothrud)",
    "N. Kulkarni (River & Sluice Gate Engr)",
    "T. Pawar (Stormwater Ops - Bibwewadi)",
    "H. Salunke (Rapid Dewatering Crew)",
    "B. Jagtap (Suction Jetting Lead - Yerwada)",
    "C. Kamble (Culvert Maintenance - PCMC)",
    "D. Wagh (Hydraulic Emergency - Dapodi)",
]

def render_interventions():
    """Render municipal interventions and machinery dispatch tracker with dynamic assignment."""

    # Initialize session state for persistent operations
    if "operations_list" not in st.session_state:
        st.session_state["operations_list"] = [dict(op) for op in OPERATIONS_INTERVENTIONS]

    operations = st.session_state["operations_list"]

    # Calculate active deployed locations (normalize for strict matching)
    deployed_locations_raw = [op["location"].strip().lower() for op in operations]
    deployed_leads_raw = [op["crew_head"].strip().lower() for op in operations]

    # Filter locations: ONLY show places which are NOT yet under command (no crew deployed)
    available_locations = []
    for loc in PUNE_LOCATIONS:
        loc_name = loc["name"].strip()
        loc_lower = loc_name.lower()
        # Exclude if exact match or substring match with active deployments
        is_deployed = any(
            loc_lower == dep or loc_lower in dep or dep in loc_lower
            for dep in deployed_locations_raw
        )
        if not is_deployed:
            available_locations.append(loc_name)

    # Filter crew leads: ONLY show officers/leads who are open / not currently assigned
    available_leads = [
        lead for lead in PUNE_MUNICIPAL_CREW_ROSTER
        if lead.strip().lower() not in deployed_leads_raw
    ]

    # Calculate dynamic metrics
    pump_count = sum(op.get("units", 1) for op in operations if "Pump" in op.get("type", ""))
    total_water = sum(op.get("water_discharged_m3", 0) for op in operations)
    en_route_count = sum(1 for op in operations if "En Route" in op.get("status", ""))

    # Inject targeted light-theme styling to ensure all selectboxes, expanders, and demobilize buttons are crisp white
    st.markdown("""
    <style>
        /* Force white backgrounds and clean borders on all selectboxes */
        div[data-baseweb="select"],
        div[data-baseweb="select"] > div,
        div[data-baseweb="select"] input {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border-color: #CBD5E1 !important;
        }
        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div {
            color: #0F172A !important;
        }
        div[data-baseweb="select"] svg {
            fill: #475569 !important;
        }
        div[data-baseweb="select"] > div:hover {
            border-color: #94A3B8 !important;
        }
        div[data-baseweb="select"] > div:focus-within {
            border-color: #0284C7 !important;
            box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.15) !important;
        }

        /* Dropdown popover list items */
        div[data-baseweb="popover"],
        div[data-baseweb="popover"] > div,
        ul[role="listbox"],
        li[role="option"] {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
        }
        li[role="option"]:hover,
        li[role="option"][aria-selected="true"] {
            background-color: #F1F5F9 !important;
            color: #0284C7 !important;
            font-weight: 600 !important;
        }

        /* Secondary buttons (Demobilize) - Crisp white with subtle border and red hover */
        div[data-testid="stButton"] > button:not([kind="primary"]):not([data-testid="baseButton-primary"]) {
            background-color: #FFFFFF !important;
            color: #475569 !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
            transition: all 0.15s ease !important;
        }
        div[data-testid="stButton"] > button:not([kind="primary"]):not([data-testid="baseButton-primary"]):hover {
            background-color: #FEF2F2 !important;
            color: #DC2626 !important;
            border-color: #FECACA !important;
            box-shadow: 0 2px 6px rgba(220, 38, 38, 0.12) !important;
        }

        /* Expander container and header */
        div[data-testid="stExpander"] {
            background-color: #FFFFFF !important;
            border: 1.5px solid #E2E8F0 !important;
            border-radius: 12px !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
        }
        div[data-testid="stExpander"] details {
            background-color: #FFFFFF !important;
            border-radius: 12px !important;
        }
        div[data-testid="stExpander"] summary {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
            font-weight: 700 !important;
            font-size: 14px !important;
            border-bottom: 1px solid #E2E8F0 !important;
        }
        div[data-testid="stExpander"] summary:hover {
            background-color: #F1F5F9 !important;
            color: #0284C7 !important;
        }
        div[data-testid="stExpander"] summary svg {
            fill: #475569 !important;
        }
        div[data-testid="stExpander"] div[data-testid="stExpanderDetails"] {
            background-color: #FFFFFF !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(textwrap.dedent(f"""
    <div class="flood-header">
        <div class="flood-title-block">
            <h1>Municipal Operations & Interventions</h1>
            <p>Dewatering pumps, suction tankers, robotic rovers, and rapid response units</p>
        </div>
        <div class="header-actions">
            <div class="date-badge">🚜 {len(operations)} Active Machinery Operations</div>
        </div>
    </div>
    """).strip(), unsafe_allow_html=True)

    # Top summary metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active Dewatering Pumps", f"{pump_count} Units", "+2 Deployed")
    m2.metric("Water Discharged", f"{total_water:,} m³", "↑ 180 m³/h")
    m3.metric("Units En Route", f"{en_route_count} Units", "ETA < 15m")
    m4.metric("Avg Clearance Time", "42 mins", "↓ 12 mins")

    st.write("")

    # Auto-dismissing Deployment Toast / Notification Box (disappears after 3 seconds)
    if "deploy_success_data" in st.session_state and st.session_state["deploy_success_data"]:
        toast_data = st.session_state["deploy_success_data"]
        elapsed = time.time() - toast_data.get("timestamp", 0)
        if elapsed < 4.5:
            st.markdown(textwrap.dedent(f"""
            <div id="deploy-notification-box" style="
                background: linear-gradient(135deg, #059669 0%, #047857 100%);
                border: 1.5px solid #34D399;
                border-radius: 12px;
                padding: 16px 20px;
                margin-bottom: 20px;
                box-shadow: 0 8px 24px rgba(5, 150, 105, 0.28);
                color: #FFFFFF;
                font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
                position: relative;
                overflow: hidden;
                animation: toastFadeOut 0.6s ease-in 3.0s forwards;
            ">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
                    <div style="display:flex; align-items:center; gap:14px;">
                        <span style="font-size:24px; background:#10B98133; border:1px solid #34D39960; width:44px; height:44px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center;">
                            🚀
                        </span>
                        <div>
                            <div style="font-size:15px; font-weight:800; color:#ECFDF5; letter-spacing:0.01em;">
                                Deployment Order Dispatched Successfully!
                            </div>
                            <div style="font-size:13px; color:#A7F3D0; margin-top:3px;">
                                <b>{toast_data['eq_type']}</b> deployed to <b>{toast_data['target_loc']}</b> &bull; Lead: <b>{toast_data['crew_head']}</b> &bull; Priority: <b>{toast_data['priority']}</b>
                            </div>
                        </div>
                    </div>
                    <div style="background:#065F46; border:1px solid #34D39955; color:#D1FAE5; font-size:11px; font-weight:700; padding:5px 12px; border-radius:14px; white-space:nowrap;">
                        ⏱️ Auto-dismissing in 3s &bull; Alerted via SMS & Radio
                    </div>
                </div>
                <!-- 3-Second Countdown Progress Bar -->
                <div style="position:absolute; bottom:0; left:0; height:4px; background:#34D399; width:100%; animation: toastTimer 3.0s linear forwards;"></div>
            </div>

            <style>
            @keyframes toastTimer {{
                from {{ width: 100%; }}
                to {{ width: 0%; }}
            }}
            @keyframes toastFadeOut {{
                0% {{ opacity: 1; transform: translateY(0); max-height: 120px; margin-bottom: 20px; }}
                80% {{ opacity: 0; transform: translateY(-6px); max-height: 120px; margin-bottom: 20px; }}
                100% {{ opacity: 0; transform: translateY(-16px); max-height: 0; padding: 0; margin-bottom: 0; border: none; overflow: hidden; display: none; }}
            }}
            </style>
            <script>
            setTimeout(function() {{
                var el = document.getElementById('deploy-notification-box');
                if (el) {{
                    el.style.display = 'none';
                    el.remove();
                }}
            }}, 3500);
            </script>
            """).strip(), unsafe_allow_html=True)

    # Active Operations Grid
    st.markdown("### 🚜 Real-Time Field Deployments")

    for idx, op in enumerate(operations):
        status_color = "#16A34A" if "Operating" in op["status"] or "Deployed" in op["status"] else "#EA580C"

        card_col, btn_col = st.columns([5.2, 1], gap="small")
        with card_col:
            op_html = textwrap.dedent(f"""
<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:16px 20px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
<div style="display:flex; align-items:center; gap:10px;">
<b style="font-size:15px; color:#0F172A;">{op['type']}</b>
<span style="font-size:12px; color:#64748B;">({op['id']})</span>
</div>
<span style="background:{status_color}15; color:{status_color}; font-weight:700; font-size:11px; padding:3px 10px; border-radius:12px; border:1px solid {status_color}40;">
{op['status']}
</span>
</div>
<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:12px; font-size:12px; color:#475569; padding-top:8px; border-top:1px solid #F1F5F9;">
<div>📍 <b>Target Location:</b> {op['location']}</div>
<div>👷 <b>Unit Lead:</b> {op['crew_head']}</div>
<div>💧 <b>Water Pumped:</b> {op['water_discharged_m3']} m³</div>
<div>⏱️ <b>ETA Resolution:</b> {op['eta_cleared']}</div>
</div>
</div>
""").strip()
            st.markdown(op_html, unsafe_allow_html=True)
        with btn_col:
            st.write("")
            if st.button("Demobilize", key=f"recall_op_{op['id']}_{idx}", help=f"Recall crew from {op['location']} and return to pool", use_container_width=True):
                operations.pop(idx)
                st.session_state["operations_list"] = operations
                st.rerun()

    # Dispatch New Unit Form with Dynamic Dropdowns
    with st.expander("➕ Dispatch Additional Intervention Machinery / Emergency Crew", expanded=True):
        f1, f2 = st.columns(2)
        with f1:
            eq_type = st.selectbox("Machinery Type", [
                "High Pressure Silt Jetting & Suction Tanker",
                "Mobile 500 GPM Dewatering Pump",
                "Mobile 1000 GPM Heavy Surcharge Pump",
                "Robotic Drain Cleaning Crawler",
                "Traffic Diversion Barricade Unit"
            ])

            if available_locations:
                target_loc = st.selectbox(
                    "Target Location (Unassigned Hotspots Only)",
                    available_locations,
                    help="Only places which are not yet under command are displayed here."
                )
            else:
                st.warning("⚠️ All municipal hotspots currently have deployed crews assigned.")
                target_loc = None

        with f2:
            if available_leads:
                crew_head = st.selectbox(
                    "Assigned Junior Engineer / Lead (Available Officers Only)",
                    available_leads,
                    help="Only crew leads who are currently open/unassigned are displayed here."
                )
            else:
                st.warning("⚠️ All municipal officers are currently deployed.")
                crew_head = None

            priority = st.selectbox("Deployment Priority", [
                "Emergency Priority 1 (Within 10m)",
                "Priority 2 (Within 30m)",
                "Routine Preventive"
            ])

        can_deploy = bool(target_loc and crew_head)
        if st.button("🚀 Confirm Deployment Order", type="primary", disabled=not can_deploy, use_container_width=False):
            new_id = f"OP-{700 + len(operations) + 1}"
            eta = "20 mins" if "10m" in priority else ("45 mins" if "30m" in priority else "1h 30m")
            new_op = {
                "id": new_id,
                "type": eq_type,
                "location": target_loc,
                "status": "Deployed & En Route",
                "crew_head": crew_head,
                "units": 1,
                "water_discharged_m3": 0,
                "eta_cleared": eta
            }

            # Add to persistent operations at the top
            st.session_state["operations_list"].insert(0, new_op)

            # Record toast data for the 3-second auto-dismiss message
            st.session_state["deploy_success_data"] = {
                "id": new_id,
                "eq_type": eq_type,
                "target_loc": target_loc,
                "crew_head": crew_head,
                "priority": priority,
                "timestamp": time.time()
            }

            # Log to DB audit log if available
            try:
                from app.db.session import SessionLocal
                from app.db.models import AuditLog
                db = SessionLocal()
                db.add(AuditLog(
                    user="Chief Municipal Officer",
                    action=f"deployed_{new_id}_{eq_type}_to_{target_loc}",
                    entity="operation",
                    entity_id=new_id
                ))
                db.commit()
                db.close()
            except Exception:
                pass

            st.rerun()

