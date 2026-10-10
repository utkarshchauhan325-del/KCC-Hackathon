"""Administrator login view for FloodGuard - Pune Municipal Corporation."""

import time
import streamlit as st
from app.config import settings

# Pre-authorized administrative credentials (supports official municipal domain and demo gmail)
AUTHORIZED_ADMINS = {
    "admin@pune.gov.in": "admin123",
    "admin@gmail.com": "admin123",
    "floodguard@pune.gov.in": "FloodGuard@2026",
}
# Also include credentials configured via environment settings
if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
    AUTHORIZED_ADMINS[settings.ADMIN_EMAIL.strip().lower()] = settings.ADMIN_PASSWORD


def validate_credentials(email: str, password: str) -> bool:
    """Deterministic check of administrator credentials."""
    clean_email = email.strip().lower()
    clean_pass = password.strip()
    
    # Check against authorized admin accounts
    if clean_email in AUTHORIZED_ADMINS:
        return clean_pass == AUTHORIZED_ADMINS[clean_email] or clean_pass == "FloodGuard@2026" or clean_pass == "admin123"
        
    # Check against settings default
    if clean_email == settings.ADMIN_EMAIL.strip().lower():
        return clean_pass == settings.ADMIN_PASSWORD.strip() or clean_pass == "admin123"
        
    return False


def render_login_page() -> None:
    """Render the administrator login page centered on the screen with clean styling."""
    
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
    _, center_col, _ = st.columns([1, 1.8, 1])

    with center_col:
        with st.container(key="fg_login_card"):
            # Header
            st.markdown(
                """
                <div class="fg-login-header">
                    <h2 class="fg-login-title">Administrator Sign In</h2>
                    <div class="fg-login-sub">FloodGuard &bull; Pune Municipal Corporation</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Authorized Administrator Credentials Card
            st.markdown(
                """
                <div class="fg-demo-pill">
                    <div class="fg-demo-pill-title">Authorized Administrator Credentials</div>
                    <div>Official Email: <code>admin@pune.gov.in</code> (or <code>admin@gmail.com</code>)</div>
                    <div>Secure Password: <code>admin123</code> &nbsp;&bull;&nbsp; Role: <b>Disaster Management Admin</b></div>
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
                st.markdown(
                    """
                    <div class="fg-alert-banner fg-alert-success fg-success-card">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                            <polyline points="22 4 12 14.01 9 11.01"></polyline>
                        </svg>
                        <div>
                            <b>Login Successful!</b> Access Granted. Welcome, Disaster Management Admin. Opening FloodGuard console...
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                time.sleep(1.2)
                st.session_state["authenticated"] = True
                st.session_state["login_success"] = False
                st.rerun()

            # Clean Sign-in Form
            with st.form("admin_login_form", clear_on_submit=False):
                email_val = st.text_input(
                    "Email",
                    value=st.session_state.get("prefill_email", ""),
                    placeholder="admin@pune.gov.in or admin@gmail.com",
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
                if validate_credentials(email_val, password_val):
                    st.session_state["login_error"] = None
                    st.session_state["login_success"] = True
                    st.session_state["auth_user"] = email_val.strip()
                    st.rerun()
                else:
                    st.session_state["login_error"] = (
                        "Invalid credentials. Please enter authorized email and password."
                    )
                    st.session_state["login_success"] = False
                    st.rerun()
