"""Priority Queue & Interventions View - Unified Municipal Command & Action Workflow."""

import time
import textwrap
import streamlit as st
from datetime import datetime
from app.ui.pune_data import PRIORITY_QUEUE
from app.db.session import SessionLocal
from app.db.models import Violation, AuditLog

def render_priority_queue(embedded: bool = False):
    """Render 3 Priority Queue actionable incidents for municipal officers."""

    if not embedded:
        st.markdown(textwrap.dedent("""
        <div class="flood-header">
            <div class="flood-title-block">
                <h1>Priority Queue & Escalation Action</h1>
                <p>High-severity flood choke points and dumping violations requiring officer verification</p>
            </div>
            <div class="header-actions">
                <div class="bell-badge">
                    <span>⚠️</span>
                    <span class="bell-count">3</span>
                </div>
                <div class="date-badge">🔒 DPDP Compliant Human Verification Protocol</div>
            </div>
        </div>
        """).strip(), unsafe_allow_html=True)

    st.info("🛡️ **Municipal Protocol:** All automated VLM violator detections and flood interventions require human municipal verification prior to fine dispatch or heavy machinery mobilization.")

    for i, item in enumerate(PRIORITY_QUEUE):
        card_html = textwrap.dedent(f"""
<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:18px; margin-bottom:14px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
<div style="display:flex; align-items:center; gap:10px;">
<span style="background:#FEE2E2; color:#DC2626; font-weight:800; font-size:11px; padding:3px 8px; border-radius:6px;">
SEVERITY {item['severity']}
</span>
<b style="font-size:15px; color:#0F172A;">{item['location']}</b>
<span style="font-size:12px; color:#64748B;">({item['zone']} Zone)</span>
</div>
<div style="font-size:12px; color:#94A3B8;">Reported {item['reported_at']}</div>
</div>
<div style="font-size:13px; color:#334155; margin-bottom:12px;">{item['description']}</div>
</div>
""").strip()
        st.markdown(card_html, unsafe_allow_html=True)

        col_meta, col_action = st.columns([2, 1])
        with col_meta:
            st.markdown(f"**Issue Category:** `{item['category']}` | **Risk Score:** `{item['risk_score']}/100`")
            if "plate_text" in item:
                st.markdown(f"**Identified Vehicle Plate:** `{item['plate_text']}` (Legibility: High)")
            st.markdown(f"**Suggested Protocol:** `{item['suggested_action']}`")
            st.markdown(f"**Assigned Unit:** `{item['assigned_crew']}`")

        with col_action:
            st.markdown("#### Officer Decision")
            btn1, btn2 = st.columns(2)
            with btn1:
                if st.button("✅ Authorize", key=f"auth_{item['id']}", type="primary", use_container_width=True):
                    db = SessionLocal()
                    db.add(AuditLog(user="Chief Municipal Officer", action=f"authorized_intervention_{item['id']}", entity="incident", entity_id=item['id']))
                    db.commit()
                    db.close()

                    # Trigger dynamic 3s toast in interventions state
                    if "operations_list" in st.session_state:
                        new_op = {
                            "id": f"OP-AUTH-{item['id'][-2:]}",
                            "type": item.get('suggested_action', 'Intervention Crew'),
                            "location": item['location'],
                            "status": "Deployed & En Route",
                            "crew_head": item.get('assigned_crew', 'Disaster Cell Engr.'),
                            "units": 1,
                            "water_discharged_m3": 0,
                            "eta_cleared": "25 mins"
                        }
                        st.session_state["operations_list"].insert(0, new_op)

                    st.session_state["deploy_success_data"] = {
                        "id": f"OP-AUTH-{item['id'][-2:]}",
                        "eq_type": item.get('suggested_action', 'Intervention Crew'),
                        "target_loc": item['location'],
                        "crew_head": item.get('assigned_crew', 'Disaster Cell Engr.'),
                        "priority": "Emergency Priority 1",
                        "timestamp": time.time()
                    }
                    st.success(f"Incident {item['id']} Authorized! {item['suggested_action']} dispatched to {item['location']}.")
                    st.rerun()

            with btn2:
                if st.button("❌ Dismiss", key=f"dism_{item['id']}", use_container_width=True):
                    db = SessionLocal()
                    db.add(AuditLog(user="Chief Municipal Officer", action=f"dismissed_{item['id']}", entity="incident", entity_id=item['id']))
                    db.commit()
                    db.close()
                    st.warning(f"Incident {item['id']} dismissed.")
        st.markdown("<hr style='border:none; border-top:1px dashed #E2E8F0; margin:14px 0;'>", unsafe_allow_html=True)


def render_priority_queue_and_interventions():
    """Render unified Priority Queue & Field Interventions Executive Command Center."""
    from app.ui.views.interventions import render_interventions

    st.markdown(textwrap.dedent("""
    <div class="flood-header">
        <div class="flood-title-block">
            <h1>Priority Queue & Field Interventions</h1>
            <p>Unified Municipal Operations: VLM violation escalations, human authorization, and machinery dispatch</p>
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

    tab_queue, tab_dispatch = st.tabs([
        "⚠️ Actionable Priority Queue (3)",
        "🚜 Real-Time Field Deployments & Dispatch"
    ])

    with tab_queue:
        render_priority_queue(embedded=True)

    with tab_dispatch:
        render_interventions(embedded=True)
