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

    /* ============================================================= */
    /* PREMIUM WIDGET THEMING (WHITE CARDS, NO BLACK BOXES)         */
    /* ============================================================= */

    /* Widget Labels */
    label[data-testid="stWidgetLabel"] p,
    label[data-testid="stWidgetLabel"] span,
    div[data-testid="stWidgetLabel"] {
        color: #334155 !important;
        font-weight: 600 !important;
        font-size: 13px !important;
    }

    /* Dropdown / Selectbox Containers */
    div[data-testid="stSelectbox"] > div {
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
    }

    div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
    }

    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1.5px solid #CBD5E1 !important;
        border-radius: 8px !important;
        color: #0F172A !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
    }

    div[data-baseweb="select"] > div:hover {
        border-color: #94A3B8 !important;
    }

    div[data-baseweb="select"] > div:focus-within {
        border-color: #0284C7 !important;
        box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.15) !important;
    }

    /* Selectbox selected value text & icon */
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div[aria-selected="true"],
    div[data-baseweb="select"] * {
        color: #0F172A !important;
    }

    div[data-baseweb="select"] svg {
        fill: #475569 !important;
    }

    /* Selectbox Dropdown Menu / Popover */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.12), 0 8px 10px -6px rgba(15, 23, 42, 0.08) !important;
    }

    ul[role="listbox"] {
        background-color: #FFFFFF !important;
        padding: 4px !important;
    }

    li[role="option"] {
        background-color: #FFFFFF !important;
        color: #1E293B !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        border-radius: 6px !important;
        padding: 8px 12px !important;
        transition: background-color 0.12s ease !important;
    }

    li[role="option"]:hover,
    li[role="option"][aria-selected="true"] {
        background-color: #F1F5F9 !important;
        color: #0284C7 !important;
        font-weight: 600 !important;
    }

    /* Text Inputs */
    div[data-testid="stTextInput"] input {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1.5px solid #CBD5E1 !important;
        border-radius: 8px !important;
        font-size: 13px !important;
        padding: 8px 12px !important;
    }

    div[data-testid="stTextInput"] input:focus {
        border-color: #0284C7 !important;
        box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.15) !important;
    }

    /* Buttons (Secondary / Demobilize Buttons) */
    div[data-testid="stButton"] > button {
        background-color: #FFFFFF !important;
        color: #334155 !important;
        border: 1.5px solid #CBD5E1 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        padding: 6px 14px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
        transition: all 0.15s ease !important;
    }

    div[data-testid="stButton"] > button:hover {
        background-color: #F8FAFC !important;
        border-color: #DC2626 !important;
        color: #DC2626 !important;
        box-shadow: 0 2px 6px rgba(220, 38, 38, 0.1) !important;
    }

    /* Primary Buttons (Confirm Deployment Order) */
    div[data-testid="stButton"] > button[kind="primary"],
    div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.28) !important;
    }

    div[data-testid="stButton"] > button[kind="primary"]:hover,
    div[data-testid="stButton"] > button[data-testid="baseButton-primary"]:hover {
        background: linear-gradient(135deg, #0369A1 0%, #075985 100%) !important;
        color: #FFFFFF !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(2, 132, 199, 0.35) !important;
    }

    /* Expanders (+ Dispatch Additional Machinery) */
    div[data-testid="stExpander"] {
        background-color: #FFFFFF !important;
        border: 1.5px solid #E2E8F0 !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
        overflow: hidden;
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
        padding: 12px 18px !important;
        border-bottom: 1px solid #E2E8F0 !important;
        transition: background-color 0.15s ease !important;
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
        padding: 18px 20px !important;
    }

    /* Executive Command Tabs */
    div[data-testid="stTabs"] {
        margin-bottom: 24px !important;
    }

    div[data-testid="stTabs"] div[role="tablist"] {
        gap: 8px !important;
        border-bottom: 2px solid #E2E8F0 !important;
    }

    div[data-testid="stTabs"] button[role="tab"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #64748B !important;
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        border-bottom: none !important;
        padding: 10px 22px !important;
        border-radius: 8px 8px 0 0 !important;
        transition: all 0.15s ease !important;
    }

    div[data-testid="stTabs"] button[role="tab"]:hover {
        color: #0284C7 !important;
        background-color: #F1F5F9 !important;
    }

    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: #0284C7 !important;
        background-color: #FFFFFF !important;
        border-color: #CBD5E1 #CBD5E1 #FFFFFF #CBD5E1 !important;
        box-shadow: 0 -2px 6px rgba(2, 132, 199, 0.08) !important;
    }

    /* Hide standard Streamlit header clutter */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Completely remove the << sidebar collapse option so it never goes inside */
    [data-testid="stSidebarCollapseButton"],
    button[data-testid="stSidebarCollapseButton"],
    div[data-testid="stSidebarCollapseButton"],
    header[data-testid="stSidebarHeader"],
    div[data-testid="stSidebarHeader"] {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: hidden !important;
    }

    /* Hide any collapsed control / expand toggle */
    [data-testid="collapsedControl"],
    [data-testid="stExpandSidebarButton"],
    button[data-testid="stExpandSidebarButton"] {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }

    /* Keep sidebar permanently visible with clean fixed width */
    section[data-testid="stSidebar"] {
        display: flex !important;
        visibility: visible !important;
        transform: none !important;
        min-width: 290px !important;
        max-width: 320px !important;
        width: 300px !important;
    }

    /* Prevent iframe script containers from taking visual space */
    iframe[height="0"] {
        position: absolute !important;
        width: 0 !important;
        height: 0 !important;
        border: none !important;
        pointer-events: none !important;
    }

    /* Clean, compact corridor buttons in Emergency Ranking table */
    div[data-testid="stColumn"] div.stButton > button {
        border-radius: 6px !important;
        font-size: 11px !important;
        padding: 3px 8px !important;
        min-height: 28px !important;
        height: 28px !important;
        line-height: 1.15 !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
    }
    div[data-testid="stColumn"] div.stButton > button[kind="secondary"] {
        background-color: transparent !important;
        border: 1px solid transparent !important;
        color: #1E293B !important;
        font-weight: 700 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        box-shadow: none !important;
    }
    div[data-testid="stColumn"] div.stButton > button[kind="secondary"]:hover {
        background-color: #F1F5F9 !important;
        border-color: #E2E8F0 !important;
        color: #0284C7 !important;
    }
    div[data-testid="stColumn"] div.stButton > button[kind="primary"] {
        background-color: #E0F2FE !important;
        border: 1px solid #BAE6FD !important;
        color: #0284C7 !important;
        font-weight: 800 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        box-shadow: none !important;
    }
</style>
"""
