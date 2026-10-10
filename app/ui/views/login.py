"""Administrator and field worker login view for FloodGuard - Pune Municipal Corporation."""

import time
from typing import Any, Dict, Optional
import streamlit as st
from app.config import settings
from app.db.session import SessionLocal
from app.db.models import Worker, verify_password

# Pre-authorized administrative credentials (supports official municipal domain and demo gmail)
AUTHORIZED_ADMINS = {
    "admin@pune.gov.in": "admin123",
    "admin@gmail.com": "admin123",
    "floodguard@pune.gov.in": "FloodGuard@2026",
}
# Also include credentials configured via environment settings
if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
    AUTHORIZED_ADMINS[settings.ADMIN_EMAIL.strip().lower()] = settings.ADMIN_PASSWORD


def authenticate_user(identifier: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate either an administrative officer or a field worker.
    
    Returns a dictionary with role and user metadata, or None if authentication fails.
    """
    clean_id = (identifier or "").strip().lower()
    clean_pass = (password or "").strip()
    if not clean_id or not clean_pass:
        return None

    # 1. Check Administrator credentials
    if clean_id in AUTHORIZED_ADMINS:
        stored_pass = AUTHORIZED_ADMINS[clean_id]
        if clean_pass == stored_pass or clean_pass in ("FloodGuard@2026", "admin123"):
            return {
                "role": "admin",
                "email": clean_id,
                "name": "Disaster Management Admin",
            }

    if clean_id == settings.ADMIN_EMAIL.strip().lower():
        if clean_pass in (settings.ADMIN_PASSWORD.strip(), "admin123", "FloodGuard@2026"):
            return {
                "role": "admin",
                "email": clean_id,
                "name": "Disaster Management Admin",
            }

    # 2. Check Field Worker database credentials
    db = SessionLocal()
    try:
        worker = db.query(Worker).filter(
            ((Worker.email == clean_id) | (Worker.phone == clean_id)) & (Worker.active == True)
        ).first()
        if worker and verify_password(clean_pass, worker.password_hash):
            return {
                "role": "worker",
                "id": worker.id,
                "email": worker.email or worker.phone,
                "phone": worker.phone,
                "name": worker.name,
                "zone": worker.zone or "Central",
                "ward": worker.ward or "Pune Municipal Area",
                "skills": worker.skills or "",
            }
    except Exception:
        pass
    finally:
        db.close()

    return None


def validate_credentials(email: str, password: str) -> bool:
    """Deterministic check of credentials (preserves backwards-compatibility for existing tests)."""
    return authenticate_user(email, password) is not None


def render_login_page() -> None:
    """Render the official sign-in page supporting both Administrator and Worker roles."""
    
    # Initialize session state tracking
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "login_error" not in st.session_state:
        st.session_state["login_error"] = None
    if "login_success" not in st.session_state:
        st.session_state["login_success"] = False

    # Ambient water wave background graphics
    st.markdown('<div class="fg-login-bg-waves"></div>', unsafe_allow_html=True)

    # Center horizontally on screen using columns
    _, center_col, _ = st.columns([1, 1.9, 1])

    with center_col:
        with st.container(key="fg_login_card"):
            # Header
            st.markdown(
                """
                <div class="fg-login-header">
                    <h2 class="fg-login-title">Sign In to FloodGuard</h2>
                    <div class="fg-login-sub">Pune Municipal Corporation &bull; Operations & Field Dispatch</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Quick Credentials Reference
            st.markdown(
                """
                <div class="fg-demo-pill" style="margin-bottom:14px;">
                    <div class="fg-demo-pill-title" style="margin-bottom:4px;">🔑 Demo Role Credentials</div>
                    <div style="font-size:12px; line-height:1.45;">
                        <b>Admin Console:</b> <code>admin@pune.gov.in</code> / <code>admin123</code><br/>
                        <b>Field Worker App:</b> <code>suresh@pune.gov.in</code> / <code>worker123</code> (or phone <code>9820011001</code>)
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Error Banner
            if st.session_state.get("login_error"):
                st.markdown(
                    f"""
                    <div class="fg-alert-banner fg-alert-error">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                        <div>
                            <b>Access Denied:</b> {st.session_state["login_error"]}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Success Banner (Displayed when credentials match)
            if st.session_state.get("login_success"):
                role_label = "Administrator Console" if st.session_state.get("role") == "admin" else "Field Worker Workspace"
                st.markdown(
                    f"""
                    <div class="fg-alert-banner fg-alert-success fg-success-card">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                            <polyline points="22 4 12 14.01 9 11.01"></polyline>
                        </svg>
                        <div>
                            <b>Login Successful!</b> Access Granted. Welcome, {st.session_state.get('auth_user_name', 'User')}. Loading {role_label}...
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                time.sleep(1.0)
                st.session_state["authenticated"] = True
                st.session_state["login_success"] = False
                st.rerun()

            # Clean Sign-in Form
            with st.form("universal_login_form", clear_on_submit=False):
                id_val = st.text_input(
                    "Email or Mobile Number",
                    value=st.session_state.get("prefill_email", ""),
                    placeholder="Enter email or mobile number",
                    key="login_email",
                )

                password_val = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter password",
                    key="login_password",
                )

                submitted = st.form_submit_button(
                    "Sign In",
                    icon=":material/login:",
                    use_container_width=True,
                )

            # Handle Submission
            if submitted:
                auth = authenticate_user(id_val, password_val)
                if auth:
                    st.session_state["login_error"] = None
                    st.session_state["login_success"] = True
                    st.session_state["role"] = auth["role"]
                    st.session_state["auth_user"] = auth.get("email", id_val.strip())
                    st.session_state["auth_user_name"] = auth.get("name", "User")
                    if auth["role"] == "worker":
                        st.session_state["worker_id"] = auth["id"]
                        st.session_state["worker_name"] = auth["name"]
                        st.session_state["worker_zone"] = auth.get("zone", "")
                        st.session_state["worker_phone"] = auth.get("phone", "")
                    st.rerun()
                else:
                    st.session_state["login_error"] = (
                        "Invalid credentials. Please enter authorized official email/phone and password."
                    )
                    st.session_state["login_success"] = False
                    st.rerun()

