"""Custom CSS Styling to match FloodGuard Municipal Intelligence Executive UI."""

def get_floodguard_css() -> str:
    return """
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Overall Streamlit background */
    .stApp {
        background-color: #F8FAFC !important;
        color: #1E293B !important;
    }

    /* Top navigation/header container */
    .flood-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 0 20px 0;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 20px;
    }

    .flood-title-block h1 {
        font-size: 26px;
        font-weight: 800;
        color: #0F172A;
        margin: 0;
        letter-spacing: -0.02em;
    }

    .flood-title-block p {
        font-size: 14px;
        color: #64748B;
        margin: 3px 0 0 0;
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 16px;
    }

    .search-mock {
        display: flex;
        align-items: center;
        gap: 8px;
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 13px;
        color: #64748B;
        min-width: 230px;
    }

    .bell-badge {
        position: relative;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 50%;
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        cursor: pointer;
    }

    .bell-count {
        position: absolute;
        top: -3px;
        right: -3px;
        background: #EF4444;
        color: white;
        font-size: 10px;
        font-weight: 700;
        border-radius: 50%;
        width: 16px;
        height: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .avatar-badge {
        background: #3B82F6;
        color: white;
        font-weight: 700;
        border-radius: 50%;
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
    }

    .date-badge {
        font-size: 12px;
        font-weight: 600;
        color: #64748B;
        background: #F1F5F9;
        padding: 6px 12px;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
    }

    /* KPI Cards */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 24px;
    }

    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        position: relative;
    }

    .kpi-left {
        display: flex;
        flex-direction: column;
    }

    .kpi-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
    }

    .kpi-icon {
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        font-size: 14px;
    }

    .kpi-title {
        font-size: 13px;
        font-weight: 600;
        color: #475569;
    }

    .kpi-num-row {
        display: flex;
        align-items: baseline;
        gap: 8px;
    }

    .kpi-value {
        font-size: 30px;
        font-weight: 800;
        color: #0F172A;
        line-height: 1;
    }

    .kpi-diff {
        font-size: 12px;
        font-weight: 700;
        display: flex;
        align-items: center;
    }

    .kpi-diff.red { color: #EF4444; }
    .kpi-diff.orange { color: #F97316; }
    .kpi-diff.blue { color: #2563EB; }
    .kpi-diff.amber { color: #D97706; }

    .kpi-sparkline {
        width: 80px;
        height: 36px;
    }

    /* Content Card Container */
    .fg-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
        margin-bottom: 20px;
    }

    .fg-card-title {
        font-size: 16px;
        font-weight: 700;
        color: #0F172A;
        margin: 0 0 4px 0;
    }

    .fg-card-sub {
        font-size: 12px;
        color: #64748B;
        margin: 0 0 14px 0;
    }

    /* Status & Risk Badges */
    .pill-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    .pill-critical {
        background-color: #FEE2E2;
        color: #DC2626;
        border: 1px solid #FECACA;
    }

    .pill-high {
        background-color: #FFEDD5;
        color: #EA580C;
        border: 1px solid #FED7AA;
    }

    .pill-medium {
        background-color: #FEF3C7;
        color: #D97706;
        border: 1px solid #FDE68A;
    }

    .pill-low {
        background-color: #DCFCE7;
        color: #16A34A;
        border: 1px solid #BBF7D0;
    }

    /* Status text colors */
    .st-waterlogging { color: #DC2626; font-weight: 700; }
    .st-rising { color: #EA580C; font-weight: 700; }
    .st-normal { color: #16A34A; font-weight: 600; }
    .st-stable { color: #64748B; font-weight: 500; }

    /* Progress bar */
    .progress-track {
        background: #F1F5F9;
        border-radius: 6px;
        height: 8px;
        width: 100%;
        overflow: hidden;
        display: inline-block;
        vertical-align: middle;
    }

    .progress-fill {
        height: 100%;
        border-radius: 6px;
    }

    .fill-critical { background: #EF4444; }
    .fill-high { background: #F97316; }
    .fill-medium { background: #FBBF24; }
    .fill-low { background: #10B981; }

    /* Recent alerts item */
    .alert-item {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 10px 0;
        border-bottom: 1px solid #F1F5F9;
    }

    .alert-item:last-child {
        border-bottom: none;
    }

    .alert-dot {
        font-size: 14px;
        margin-top: 2px;
    }

    .alert-content {
        flex: 1;
    }

    .alert-title {
        font-size: 13px;
        font-weight: 600;
        color: #1E293B;
        margin: 0;
    }

    .alert-subtitle {
        font-size: 12px;
        color: #64748B;
        margin: 2px 0 0 0;
    }

    .alert-time {
        font-size: 11px;
        color: #94A3B8;
        white-space: nowrap;
    }

    /* Sidebar aesthetics */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }

    .brand-container {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 0 18px 0;
        border-bottom: 1px solid #F1F5F9;
        margin-bottom: 16px;
    }

    .brand-title {
        font-size: 18px;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.1;
    }

    .brand-sub {
        font-size: 11px;
        color: #64748B;
        font-weight: 600;
    }

    .nav-section-title {
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 0.08em;
        color: #94A3B8;
        text-transform: uppercase;
        margin: 18px 0 6px 4px;
    }

    .municipal-footer {
        display: flex;
        align-items: center;
        gap: 10px;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 10px 14px;
        margin-top: 40px;
    }

    .footer-title {
        font-size: 12px;
        font-weight: 700;
        color: #1E293B;
        margin: 0;
    }

    .footer-sub {
        font-size: 11px;
        color: #64748B;
        margin: 0;
    }

    /* Streamlit widgets adjustment */
    .stRadio > div {
        gap: 4px;
    }

    /* Hide standard Streamlit header clutter */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
"""
