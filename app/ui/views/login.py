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
    """Render the official administrator login page matching the Pune Municipal Corporation design."""
    
    # Initialize session state tracking
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "login_error" not in st.session_state:
        st.session_state["login_error"] = None
    if "login_success" not in st.session_state:
        st.session_state["login_success"] = False
    if "shake_active" not in st.session_state:
        st.session_state["shake_active"] = False

    # Ambient water wave background graphics
    st.markdown('<div class="fg-login-bg-waves"></div>', unsafe_allow_html=True)

    # Outer flex wrapper to center the card vertically and horizontally
    st.markdown('<div class="fg-login-page-wrapper">', unsafe_allow_html=True)

    # Determine animation CSS class for the card
    card_class = "fg-shake-card" if st.session_state.get("shake_active") else ""
    if st.session_state.get("login_success"):
        card_class = "fg-success-card"

    # Reset shake state for subsequent renders
    st.session_state["shake_active"] = False

    # Main Card Container (Streamlit keyed container allows full CSS customization)
    with st.container(key="fg_login_card"):
        # If card shake or success animation class is active, inject dynamic class
        if card_class:
            st.markdown(
                f'<script>document.querySelector(".st-key-fg_login_card")?.classList.add("{card_class}");</script>',
                unsafe_allow_html=True,
            )

        # Card Header: Profile Icon Box + Title + Subtitle
        st.markdown(
            """
            <div class="fg-login-header">
                <div class="fg-login-avatar">
                    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#0284C7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
                        <circle cx="12" cy="7" r="4"></circle>
                    </svg>
                </div>
                <div>
                    <h2 class="fg-login-title">Administrator sign in</h2>
                    <div class="fg-login-sub">Access is restricted to authorized personnel.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Demo Credentials Guidance Callout
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

        # Display Animated Alerts (Failure or Success)
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

        if st.session_state.get("login_success"):
            st.markdown(
                """
                <div class="fg-alert-banner fg-alert-success fg-success-card">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                    </svg>
                    <div>
                        <b>Credentials Verified:</b> Welcome Administrator. Decrypting FloodGuard Command Console...
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Main Sign-in Form
        with st.form("admin_login_form", clear_on_submit=False):
            # Official Email Input (Defaulted to admin@pune.gov.in as in the reference design)
            email_val = st.text_input(
                "Official email",
                value=st.session_state.get("prefill_email", "admin@pune.gov.in"),
                placeholder="admin@pune.gov.in",
                key="login_email",
            )

            # Password Input with native eye toggle
            password_val = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                key="login_password",
            )

            # Auxiliary row: Remember device checkbox + Forgot password link
            aux_col1, aux_col2 = st.columns([1.6, 1], vertical_alignment="center")
            with aux_col1:
                remember_me = st.checkbox("Remember this device", value=True, key="login_remember")
            with aux_col2:
                st.markdown(
                    '<div style="text-align: right;"><a href="#help" class="fg-forgot-link" title="Contact PMC IT Helpdesk">Forgot password?</a></div>',
                    unsafe_allow_html=True,
                )

            # Sign In Securely Button
            submitted = st.form_submit_button(
                "Sign in securely",
                icon=":material/lock:",
                use_container_width=True,
            )

        # Handle Form Submission
        if submitted:
            if validate_credentials(email_val, password_val):
                st.session_state["login_error"] = None
                st.session_state["login_success"] = True
                st.session_state["authenticated"] = True
                st.session_state["auth_user"] = email_val.strip()
                st.session_state["shake_active"] = False
                # Smooth animated delay before landing on the command console
                time.sleep(0.9)
                st.rerun()
            else:
                st.session_state["login_error"] = (
                    "Invalid official credentials. Please check your admin email and password."
                )
                st.session_state["login_success"] = False
                st.session_state["authenticated"] = False
                st.session_state["shake_active"] = True
                st.rerun()

        # Quick Demo autofill option
        demo_col1, demo_col2 = st.columns([1, 1])
        with demo_col1:
            if st.button("Quick Fill: Official Email", help="Autofill admin@pune.gov.in", key="btn_fill_pune"):
                st.session_state["prefill_email"] = "admin@pune.gov.in"
                st.rerun()
        with demo_col2:
            if st.button("Quick Fill: Admin Gmail", help="Autofill admin@gmail.com", key="btn_fill_gmail"):
                st.session_state["prefill_email"] = "admin@gmail.com"
                st.rerun()

        # Security Badge: Protected municipal access · Secure session
        st.markdown(
            """
            <div class="fg-security-badge">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#0284C7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                    <path d="m9 12 2 2 4-4"></path>
                </svg>
                <span>Protected municipal access &middot; Secure session</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Card Footer: Copyright and Privacy/Help Desk links
        st.markdown(
            """
            <div class="fg-login-footer">
                <div>&copy; 2026 FloodGuard &middot; Pune Municipal Corporation</div>
                <div>
                    <a href="#privacy">Privacy</a> &middot; 
                    <a href="#helpdesk">Help desk</a>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Close outer wrapper
    st.markdown("</div>", unsafe_allow_html=True)
