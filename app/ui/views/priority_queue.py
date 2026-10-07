"""Priority Queue & Field Interventions View - Unified Municipal Action & Crew Dispatch Center."""

import time
import textwrap
import streamlit as st
from datetime import datetime
from app.ui.pune_data import PRIORITY_QUEUE, PUNE_LOCATIONS, OPERATIONS_INTERVENTIONS
from app.db.session import SessionLocal
from app.db.models import Violation, AuditLog

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

def render_priority_queue_and_interventions():
    """Render unified Priority Queue & Field Interventions Command Center.
    
    Directly attaches the 4 dispatch dropdowns under each hotspot requiring attention.
    When a crew is dispatched, displays the deployed machinery and the leader's name under that section.
    """

    # Initialize session state for persistent operations
    if "operations_list" not in st.session_state:
        st.session_state["operations_list"] = [dict(op) for op in OPERATIONS_INTERVENTIONS]

    operations = st.session_state["operations_list"]

    # Calculate active deployed locations and leads for dynamic filtering
    deployed_locations_raw = [op["location"].strip().lower() for op in operations]
    deployed_leads_raw = [op["crew_head"].strip().lower() for op in operations]

    # Filter locations: ONLY show places which are NOT yet under command
    available_locations = []
    for loc in PUNE_LOCATIONS:
        loc_name = loc["name"].strip()
        loc_lower = loc_name.lower()
        is_deployed = any(
            loc_lower == dep or loc_lower in dep or dep in loc_lower
            for dep in deployed_locations_raw
        )
        if not is_deployed:
            available_locations.append(loc_name)

    # Filter crew leads: ONLY show officers who are currently open / available
    available_leads = [
        lead for lead in PUNE_MUNICIPAL_CREW_ROSTER
        if lead.strip().lower() not in deployed_leads_raw
    ]

    # Dynamic metrics
    pump_count = sum(op.get("units", 1) for op in operations if "Pump" in op.get("type", ""))
    total_water = sum(op.get("water_discharged_m3", 0) for op in operations)
    en_route_count = sum(1 for op in operations if "En Route" in op.get("status", ""))

    # Inject targeted light-theme styling (crisp white boxes, no dark/black boxes)
    st.markdown("""
    <style>
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

        div[data-testid="stExpander"] {
            background-color: #FFFFFF !important;
            border: 1.5px solid #E2E8F0 !important;
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
        div[data-testid="stExpander"] div[data-testid="stExpanderDetails"] {
            background-color: #FFFFFF !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Top Executive Header
    st.markdown(textwrap.dedent("""
    <div class="flood-header">
        <div class="flood-title-block">
            <h1>Priority Queue & Field Interventions</h1>
            <p>Unified Municipal Operations: High-severity flood choke points, rapid crew deployment, and machinery tracking</p>
        </div>
        <div class="header-actions">
            <div class="bell-badge">
                <span>⚠️</span>
                <span class="bell-count">3</span>
            </div>
            <div class="date-badge">🚜 Rapid Response Command Active</div>
        </div>
    </div>
    """).strip(), unsafe_allow_html=True)

    # Auto-dismissing Deployment Toast Notification Overlay (Floats over the screen)
    if "deploy_success_data" in st.session_state and st.session_state["deploy_success_data"]:
        toast_data = st.session_state["deploy_success_data"]
        elapsed = time.time() - toast_data.get("timestamp", 0)
        if elapsed < 5.0:
            st.toast(f"🚀 Dispatched {toast_data['eq_type']} to {toast_data['target_loc']} (Lead: {toast_data['crew_head']})", icon="✅")
            st.html(f"""
            <div id="deploy-notification-overlay" style="
                position: fixed;
                top: 24px;
                right: 28px;
                z-index: 99999999;
                background: linear-gradient(135deg, #065F46 0%, #047857 100%);
                border: 1.5px solid #34D399;
                border-radius: 14px;
                padding: 18px 24px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
                font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
                min-width: 360px;
                max-width: 520px;
                pointer-events: auto;
                animation: toastSlideDown 0.4s cubic-bezier(0.16, 1, 0.3, 1), toastFadeOut 0.5s ease-in 4.0s forwards;
            ">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:16px;">
                    <div style="display:flex; align-items:flex-start; gap:14px;">
                        <span style="font-size:24px; background:#10B98133; border:1px solid #34D39960; width:44px; height:44px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;">
                            🚀
                        </span>
                        <div>
                            <div style="font-size:15px; font-weight:800; color:#ECFDF5; letter-spacing:0.01em;">
                                Deployment Order Dispatched Successfully!
                            </div>
                            <div style="font-size:13px; color:#A7F3D0; margin-top:4px; line-height:1.4;">
                                <b>{toast_data['eq_type']}</b> mobilized to <b>{toast_data['target_loc']}</b>
                            </div>
                            <div style="font-size:12px; color:#D1FAE5; margin-top:4px;">
                                👷 Lead: <b>{toast_data['crew_head']}</b> &bull; 🎯 {toast_data['priority']}
                            </div>
                        </div>
                    </div>
                    <button onclick="document.getElementById('deploy-notification-overlay').remove();" style="
                        background: rgba(255, 255, 255, 0.15);
                        border: none;
                        color: #FFFFFF;
                        font-size: 16px;
                        font-weight: 700;
                        width: 26px;
                        height: 26px;
                        border-radius: 50%;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        padding: 0;
                    ">✕</button>
                </div>
                <div style="margin-top:12px; display:flex; justify-content:space-between; align-items:center; font-size:11px; color:#A7F3D0;">
                    <span>⏱️ Auto-dismissing</span>
                    <span style="background:#065F46; padding:3px 8px; border-radius:10px; border:1px solid #34D39944;">Alerted via SMS & Radio</span>
                </div>
                <div style="position:absolute; bottom:0; left:0; height:4px; background:#34D399; width:100%; animation: toastTimer 4.0s linear forwards; border-radius: 0 0 14px 14px;"></div>
            </div>

            <style>
            @keyframes toastSlideDown {{
                0% {{ opacity: 0; transform: translateY(-20px) scale(0.96); }}
                100% {{ opacity: 1; transform: translateY(0) scale(1); }}
            }}
            @keyframes toastTimer {{
                from {{ width: 100%; }}
                to {{ width: 0%; }}
            }}
            @keyframes toastFadeOut {{
                0% {{ opacity: 1; transform: translateY(0); }}
                100% {{ opacity: 1; transform: translateY(-15px); pointer-events: none; }}
            }}
            </style>
            <script>
            setTimeout(function() {{
                var el = document.getElementById('deploy-notification-overlay');
                if (el) {{
                    el.remove();
                }}
            }}, 4600);
            </script>
            """)
        else:
            st.session_state["deploy_success_data"] = None

    st.markdown("### 🚨 Hotspots Requiring Immediate Attention")
    st.info("🛡️ **Municipal Rapid Response Protocol:** Each critical incident below provides real-time diagnostic telemetry. Configure machinery and assign an open engineer directly to mobilize crews.")

    # Iterate through Priority Queue locations requiring attention
    for i, item in enumerate(PRIORITY_QUEUE):
        loc_name = item["location"]
        loc_lower = loc_name.strip().lower()

        # Check if a crew is currently deployed for this specific place
        deployed_op = None
        for op in operations:
            dep_loc_lower = op.get("location", "").strip().lower()
            if loc_lower == dep_loc_lower:
                deployed_op = op
                break

        # Incident Card Container
        detected_plate_html = f"<div>🚗 <b>Detected Plate:</b> <code style='background:#F1F5F9; padding:2px 6px; border-radius:4px;'>{item['plate_text']}</code></div>" if "plate_text" in item else ""
        st.html(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:18px 20px; margin-bottom:8px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="background:#FEE2E2; color:#DC2626; font-weight:800; font-size:11px; padding:3px 8px; border-radius:6px;">
                        SEVERITY {item['severity']}
                    </span>
                    <b style="font-size:16px; color:#0F172A;">{item['location']}</b>
                    <span style="font-size:12px; color:#64748B;">({item['zone']} Zone)</span>
                </div>
                <div style="font-size:12px; color:#94A3B8;">Reported {item['reported_at']}</div>
            </div>
            <div style="font-size:13.5px; color:#334155; line-height:1.5; margin-bottom:12px;">{item['description']}</div>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:10px; font-size:12.5px; color:#475569; padding-top:10px; border-top:1px solid #F1F5F9;">
                <div>📂 <b>Issue Category:</b> <span style="color:#0284C7; font-weight:600;">{item['category']}</span></div>
                <div>📊 <b>Risk Score:</b> <span style="color:#DC2626; font-weight:700;">{item['risk_score']}/100</span></div>
                <div>📋 <b>Suggested Protocol:</b> {item['suggested_action']}</div>
                {detected_plate_html}
            </div>
        </div>
        """)

        # UNDER EACH PLACE: Show deployed crew details OR the 4 dropdown boxes to deploy
        if deployed_op:
            # Active Crew Deployed for this Place
            status_color = "#16A34A" if "Operating" in deployed_op["status"] or "Deployed" in deployed_op["status"] else "#EA580C"
            st.html(f"""
            <div style="background:#F0FDF4; border:1.5px solid #86EFAC; border-radius:12px; padding:16px 20px; margin-bottom:12px; box-shadow:0 2px 6px rgba(22, 163, 74, 0.08);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:8px;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="background:#DCFCE7; color:#15803D; font-weight:800; font-size:11px; padding:4px 10px; border-radius:8px; border:1px solid #BBF7D0;">
                            ● ACTIVE CREW DEPLOYED
                        </span>
                        <b style="font-size:15px; color:#0F172A;">{deployed_op['type']}</b>
                        <span style="font-size:12px; color:#64748B;">({deployed_op['id']})</span>
                    </div>
                    <span style="background:{status_color}15; color:{status_color}; font-weight:700; font-size:11px; padding:3px 10px; border-radius:12px; border:1px solid {status_color}40;">
                        {deployed_op['status']}
                    </span>
                </div>
                <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:12px; font-size:13px; color:#1E293B; padding-top:10px; border-top:1px solid #DCFCE7;">
                    <div>👷 <b>Unit Lead:</b> <span style="color:#0284C7; font-weight:800; font-size:14px;">{deployed_op['crew_head']}</span></div>
                    <div>💧 <b>Water Pumped:</b> <b>{deployed_op.get('water_discharged_m3', 0)} m³</b></div>
                    <div>⏱️ <b>ETA Resolution:</b> <b>{deployed_op.get('eta_cleared', '30 mins')}</b></div>
                </div>
            </div>
            """)

            # Demobilize action button
            demob_c1, demob_c2 = st.columns([5, 1])
            with demob_c2:
                if st.button("🔄 Demobilize Crew", key=f"demob_{item['id']}_{deployed_op['id']}", help=f"Recall crew from {item['location']} and return officer to available pool", use_container_width=True):
                    operations.remove(deployed_op)
                    st.session_state["operations_list"] = operations
                    try:
                        db = SessionLocal()
                        db.add(AuditLog(user="Chief Municipal Officer", action=f"demobilized_{deployed_op['id']}_from_{item['location']}", entity="operation", entity_id=deployed_op['id']))
                        db.commit()
                        db.close()
                    except Exception:
                        pass
                    st.rerun()

        else:
            # NO CREW DEPLOYED YET: Show the 4 Dropdown Boxes directly under this place
            with st.container(border=True):
                st.markdown("<div style='font-size:13.5px; font-weight:800; color:#0F172A; margin-bottom:12px;'>🚜 Dispatch Intervention Machinery & Emergency Crew to this Site:</div>", unsafe_allow_html=True)

                d1, d2 = st.columns(2)
                with d1:
                    mach_type = st.selectbox(
                        "Machinery Type",
                        [
                            "High Pressure Silt Jetting & Suction Tanker",
                            "Mobile 500 GPM Dewatering Pump",
                            "Mobile 1000 GPM Heavy Surcharge Pump",
                            "Robotic Drain Cleaning Crawler",
                            "Traffic Diversion Barricade Unit"
                        ],
                        key=f"mach_{item['id']}"
                    )

                    # Target location dropdown (defaults to this place's name, plus any other unassigned spots)
                    loc_options = [item['location']] + [l for l in available_locations if l.lower() != loc_lower]
                    target_loc = st.selectbox(
                        "Target Location",
                        loc_options,
                        index=0,
                        key=f"loc_{item['id']}",
                        help="Target location where the machinery and crew will be mobilized"
                    )

                with d2:
                    if available_leads:
                        assigned_lead = st.selectbox(
                            "Assigned Junior Engineer / Lead (Available Officers Only)",
                            available_leads,
                            key=f"lead_{item['id']}",
                            help="Only crew leads who are open and not currently deployed are shown"
                        )
                    else:
                        st.warning("⚠️ All municipal officers are currently deployed.")
                        assigned_lead = None

                    prio = st.selectbox(
                        "Deployment Priority",
                        [
                            "Emergency Priority 1 (Within 10m)",
                            "Priority 2 (Within 30m)",
                            "Routine Preventive"
                        ],
                        key=f"prio_{item['id']}"
                    )

                can_deploy = bool(target_loc and assigned_lead)
                if st.button(f"🚀 Confirm Deployment Order to {item['location']}", key=f"deploy_btn_{item['id']}", type="primary", disabled=not can_deploy, use_container_width=False):
                    new_id = f"OP-{700 + len(operations) + 1}"
                    eta = "20 mins" if "10m" in prio else ("45 mins" if "30m" in prio else "1h 30m")
                    new_op = {
                        "id": new_id,
                        "type": mach_type,
                        "location": target_loc,
                        "status": "Deployed & En Route",
                        "crew_head": assigned_lead,
                        "units": 1,
                        "water_discharged_m3": 0,
                        "eta_cleared": eta
                    }

                    # Prepend to active operations list
                    st.session_state["operations_list"].insert(0, new_op)

                    # Set toast data for floating screen overlay
                    st.session_state["deploy_success_data"] = {
                        "id": new_id,
                        "eq_type": mach_type,
                        "target_loc": target_loc,
                        "crew_head": assigned_lead,
                        "priority": prio,
                        "timestamp": time.time()
                    }

                    # Audit log
                    try:
                        db = SessionLocal()
                        db.add(AuditLog(user="Chief Municipal Officer", action=f"dispatched_{new_id}_{mach_type}_to_{target_loc}", entity="operation", entity_id=new_id))
                        db.commit()
                        db.close()
                    except Exception:
                        pass

                    st.rerun()

        st.markdown("<hr style='border:none; border-top:1px dashed #E2E8F0; margin:16px 0 20px 0;'>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # OTHER ACTIVE MUNICIPAL OPERATIONS ACROSS PUNE
    # -------------------------------------------------------------
    other_ops = [
        op for op in operations
        if not any(op.get("location", "").strip().lower() == item["location"].strip().lower() for item in PRIORITY_QUEUE)
    ]

    if other_ops:
        st.markdown("### 🚜 Other Active Municipal Field Deployments")
        for idx, op in enumerate(other_ops):
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
                    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:12px; font-size:12.5px; color:#475569; padding-top:8px; border-top:1px solid #F1F5F9;">
                        <div>📍 <b>Target Location:</b> {op['location']}</div>
                        <div>👷 <b>Unit Lead:</b> <span style="color:#0284C7; font-weight:700;">{op['crew_head']}</span></div>
                        <div>💧 <b>Water Pumped:</b> {op.get('water_discharged_m3', 0)} m³</div>
                        <div>⏱️ <b>ETA Resolution:</b> {op.get('eta_cleared', '-')}</div>
                    </div>
                </div>
                """).strip()
                st.markdown(op_html, unsafe_allow_html=True)
            with btn_col:
                st.write("")
                if st.button("Demobilize", key=f"demob_other_{op['id']}_{idx}", help=f"Recall crew from {op['location']} and return officer to pool", use_container_width=True):
                    operations.remove(op)
                    st.session_state["operations_list"] = operations
                    st.rerun()

    # Expander to dispatch additional machinery to any other hotspot in Pune
    with st.expander("➕ Dispatch Additional Intervention to Any Other Municipal Hotspot"):
        f1, f2 = st.columns(2)
        with f1:
            gen_eq_type = st.selectbox(
                "Machinery Type (General)",
                [
                    "High Pressure Silt Jetting & Suction Tanker",
                    "Mobile 500 GPM Dewatering Pump",
                    "Mobile 1000 GPM Heavy Surcharge Pump",
                    "Robotic Drain Cleaning Crawler",
                    "Traffic Diversion Barricade Unit"
                ],
                key="gen_eq_type"
            )

            if available_locations:
                gen_target_loc = st.selectbox(
                    "Target Location (Unassigned Hotspots Only)",
                    available_locations,
                    key="gen_target_loc"
                )
            else:
                st.warning("⚠️ All municipal hotspots currently have deployed crews assigned.")
                gen_target_loc = None

        with f2:
            if available_leads:
                gen_crew_head = st.selectbox(
                    "Assigned Junior Engineer / Lead (Available Officers Only)",
                    available_leads,
                    key="gen_crew_head"
                )
            else:
                st.warning("⚠️ All municipal officers are currently deployed.")
                gen_crew_head = None

            gen_priority = st.selectbox(
                "Deployment Priority (General)",
                [
                    "Emergency Priority 1 (Within 10m)",
                    "Priority 2 (Within 30m)",
                    "Routine Preventive"
                ],
                key="gen_priority"
            )

        gen_can_deploy = bool(gen_target_loc and gen_crew_head)
        if st.button("🚀 Confirm Deployment Order", key="gen_deploy_btn", type="primary", disabled=not gen_can_deploy):
            new_id = f"OP-{700 + len(operations) + 1}"
            eta = "20 mins" if "10m" in gen_priority else ("45 mins" if "30m" in gen_priority else "1h 30m")
            new_op = {
                "id": new_id,
                "type": gen_eq_type,
                "location": gen_target_loc,
                "status": "Deployed & En Route",
                "crew_head": gen_crew_head,
                "units": 1,
                "water_discharged_m3": 0,
                "eta_cleared": eta
            }
            st.session_state["operations_list"].insert(0, new_op)
            st.session_state["deploy_success_data"] = {
                "id": new_id,
                "eq_type": gen_eq_type,
                "target_loc": gen_target_loc,
                "crew_head": gen_crew_head,
                "priority": gen_priority,
                "timestamp": time.time()
            }
            st.rerun()

def render_priority_queue():
    """Alias for unified view."""
    render_priority_queue_and_interventions()
