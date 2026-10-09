"""FloodGuard theme: design tokens, global CSS, inline SVG icons and clean HTML helpers.

Professional municipal command-center visual language:
- Clean high-contrast canvas with subtle micro-grid
- Crisp dark sidebar command panel
- Zero emojis across all views and components
- Hairline borders, precise typography (Space Grotesk + Inter + JetBrains Mono)
- Intentional severity status colors
"""

from html import escape
from typing import Iterable, Optional

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
ACCENT = "#0A7C8F"
ACCENT_BRIGHT = "#12B5CB"
ACCENT_SOFT = "#E4F4F6"
INK = "#0B1220"
INK_2 = "#334155"
MUTED = "#64748B"
LINE = "#E2E8F0"
GRID = "#EEF1F5"

STATUS = {
    "Critical": {"fg": "#DC2626", "bg": "#FEF2F2", "line": "#FECACA"},
    "High": {"fg": "#EA580C", "bg": "#FFF7ED", "line": "#FFEDD5"},
    "Medium": {"fg": "#D97706", "bg": "#FFFBEB", "line": "#FEF3C7"},
    "Low": {"fg": "#059669", "bg": "#ECFDF5", "line": "#A7F3D0"},
}

FONT_HEAD = "'Space Grotesk', 'Inter', system-ui, sans-serif"
FONT_BODY = "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif"
FONT_MONO = "'JetBrains Mono', ui-monospace, 'SFMono-Regular', Consolas, monospace"


def status_color(level: str) -> str:
    return STATUS.get(level, {"fg": ACCENT})["fg"]


# ---------------------------------------------------------------------------
# Inline SVG line icons (24px grid, stroke, currentColor)
# ---------------------------------------------------------------------------
_ICON_PATHS = {
    "grid": '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/>',
    "map": '<path d="M9 4 3.5 6v14L9 18l6 2 5.5-2V4L15 6 9 4Z"/><path d="M9 4v14M15 6v14"/>',
    "camera": '<rect x="3" y="6.5" width="13" height="11" rx="2"/><path d="m16 10.5 5-3v9l-5-3"/>',
    "queue": '<path d="M4 6h16M4 12h10M4 18h7"/><circle cx="18.5" cy="16.5" r="2.5"/>',
    "chart": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h10"/>',
    "pin": '<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11Z"/><circle cx="12" cy="10" r="2.3"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "alert": '<path d="M12 4 2.8 19.5h18.4L12 4Z"/><path d="M12 10v4.5M12 17.2v.1"/>',
    "drop": '<path d="M12 3.5s6 6.6 6 11a6 6 0 0 1-12 0c0-4.4 6-11 6-11Z"/>',
    "rain": '<path d="M7 15a4.5 4.5 0 1 1 1.2-8.8A5.5 5.5 0 0 1 18.6 8 3.6 3.6 0 0 1 18 15H7Z"/><path d="M8 18.5 7 21M12 18.5 11 21M16 18.5 15 21"/>',
    "gauge": '<path d="M4.5 17a8.5 8.5 0 1 1 15 0"/><path d="m12 13 3.5-4"/>',
    "layers": '<path d="m12 3.5 9 5-9 5-9-5 9-5Z"/><path d="m3 13.5 9 5 9-5"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "truck": '<path d="M3 6.5h11v9H3zM14 10h4l3 3v2.5h-7"/><circle cx="7" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>',
    "user": '<circle cx="12" cy="8.5" r="3.5"/><path d="M5 20a7 7 0 0 1 14 0"/>',
    "file": '<path d="M6 3.5h8l4 4V20.5H6z"/><path d="M14 3.5v4h4M9 12h6M9 16h6"/>',
    "download": '<path d="M12 4v11M7 10.5l5 5 5-5M5 20h14"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "close": '<path d="M6 6l12 12M18 6 6 18"/>',
    "shield": '<path d="M12 3.5 5 6v5.5c0 4.3 3 7.7 7 9 4-1.3 7-4.7 7-9V6l-7-2.5Z"/>',
    "wave": '<path d="M3 9c2.2 0 2.2-2 4.5-2s2.2 2 4.5 2 2.2-2 4.5-2S18.8 9 21 9M3 15c2.2 0 2.2-2 4.5-2s2.2 2 4.5 2 2.2-2 4.5-2 2.3 2 4.5 2"/>',
    "traffic": '<rect x="8" y="3" width="8" height="18" rx="3"/><circle cx="12" cy="7.5" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="12" cy="16.5" r="1.3"/>',
}


def icon(name: str, size: int = 16, color: str = "currentColor", stroke: float = 1.6) -> str:
    """Return an inline SVG line icon."""
    body = _ICON_PATHS.get(name, "")
    return (
        f'<svg class="fg-ico" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{body}</svg>'
    )


BRAND_MARK = (
    '<svg width="28" height="28" viewBox="0 0 32 32" fill="none" aria-hidden="true">'
    '<rect x="1" y="1" width="30" height="30" rx="9" fill="#0A7C8F"/>'
    '<path d="M16 6.5s6 6.4 6 10.6a6 6 0 0 1-12 0c0-4.2 6-10.6 6-10.6Z" stroke="#FFFFFF" stroke-width="2"/>'
    '<path d="M12.6 18.2c1.1 1.4 2.2 1.9 3.4 1.9" stroke="#E4F4F6" stroke-width="1.6" stroke-linecap="round"/>'
    "</svg>"
)


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------
def _flat(html: str) -> str:
    """Collapse markup to one line so st.markdown never treats indentation as code."""
    return " ".join(line.strip() for line in html.splitlines() if line.strip())


def page_header(title: str, subtitle: str = "", eyebrow: str = "", meta: Optional[Iterable[str]] = None) -> str:
    chips = "".join(f'<span class="fg-chip">{m}</span>' for m in (meta or []))
    return _flat(f"""
    <div class="fg-page-head">
      <div>
        {f'<div class="fg-eyebrow">{escape(eyebrow)}</div>' if eyebrow else ''}
        <h1 class="fg-h1">{escape(title)}</h1>
        {f'<p class="fg-sub">{escape(subtitle)}</p>' if subtitle else ''}
      </div>
      {f'<div class="fg-meta">{chips}</div>' if chips else ''}
    </div>
    """)


def section_title(title: str, sub: str = "", right: str = "") -> str:
    return _flat(f"""
    <div class="fg-section">
      <div>
        <h3 class="fg-h3">{escape(title)}</h3>
        {f'<p class="fg-section-sub">{sub}</p>' if sub else ''}
      </div>
      {f'<div>{right}</div>' if right else ''}
    </div>
    """)


def status_pill(level: str, text: Optional[str] = None) -> str:
    key = level.capitalize() if level else ""
    cls = {"Critical": "crit", "High": "high", "Medium": "watch", "Low": "ok"}.get(key, "neutral")
    return f'<span class="fg-pill fg-pill-{cls}"><i></i>{escape(text or level)}</span>'


def chip(text: str, tone: str = "neutral") -> str:
    return f'<span class="fg-chip fg-chip-{tone}">{text}</span>'


def get_floodguard_css() -> str:
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block');

:root {
  --fg-bg: #F8FAFC;
  --fg-surface: #FFFFFF;
  --fg-surface-2: #F1F5F9;
  --fg-line: #E2E8F0;
  --fg-line-strong: #CBD5E1;
  --fg-ink: #0F172A;
  --fg-ink-2: #334155;
  --fg-muted: #64748B;
  --fg-faint: #94A3B8;
  --fg-accent: #0A7C8F;
  --fg-accent-bright: #0284C7;
  --fg-accent-soft: #E0F2FE;
  --fg-crit: #DC2626;  --fg-crit-bg: #FEF2F2;  --fg-crit-line: #FECACA;
  --fg-high: #EA580C;  --fg-high-bg: #FFF7ED;  --fg-high-line: #FFEDD5;
  --fg-watch: #D97706; --fg-watch-bg: #FFFBEB; --fg-watch-line: #FEF3C7;
  --fg-ok: #059669;    --fg-ok-bg: #ECFDF5;    --fg-ok-line: #A7F3D0;
  --fg-radius: 12px;
  --fg-radius-sm: 8px;
  --fg-shadow: 0 1px 3px rgba(15, 23, 42, 0.05), 0 1px 2px rgba(15, 23, 42, 0.03);
  --fg-shadow-md: 0 4px 12px -2px rgba(15, 23, 42, 0.08);
  --fg-font-head: 'Space Grotesk', 'Inter', system-ui, sans-serif;
  --fg-font-body: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --fg-font-mono: 'JetBrains Mono', ui-monospace, Consolas, monospace;
}

/* ---------- Canvas ---------- */
html, body, .stApp, [data-testid="stAppViewContainer"] {
  font-family: var(--fg-font-body);
  color: var(--fg-ink);
}
.stApp {
  background-color: var(--fg-bg) !important;
  background-image:
    linear-gradient(rgba(10, 124, 143, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(10, 124, 143, 0.025) 1px, transparent 1px);
  background-size: 28px 28px;
  background-attachment: fixed;
}
[data-testid="stMainBlockContainer"], .block-container {
  padding-top: 18px !important;
  padding-bottom: 54px !important;
  padding-left: 28px !important;
  padding-right: 28px !important;
  max-width: 1400px;
}
h1, h2, h3, h4, h5 { font-family: var(--fg-font-head) !important; color: var(--fg-ink) !important; letter-spacing: -0.015em; }
code, kbd, pre { font-family: var(--fg-font-mono) !important; }
p, li { color: var(--fg-ink-2); }
.fg-ico { display: inline-block; vertical-align: -3px; flex-shrink: 0; }
.fg-mono { font-family: var(--fg-font-mono); font-variant-numeric: tabular-nums; }

/* ---------- Hide Generic Streamlit Chrome Only (Keep Sidebar Visible!) ---------- */
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stAppDeployButton"], #MainMenu, footer {
  display: none !important;
}
iframe[height="0"] { position: absolute !important; width: 0 !important; height: 0 !important; border: 0 !important; }

/* ---------- Proper Professional Sidebar ---------- */
section[data-testid="stSidebar"] {
  display: flex !important;
  background-color: #0B132B !important;
  border-right: 1px solid #1E293B !important;
  box-shadow: 4px 0 20px rgba(0, 0, 0, 0.25) !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
  background-color: #0B132B !important;
  padding: 18px 14px 24px 14px !important;
}

/* Sidebar Brand */
.fg-sb-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 6px 12px 6px;
}
.fg-sb-logo {
  flex-shrink: 0;
}
.fg-sb-title {
  font-family: var(--fg-font-head);
  font-weight: 700;
  font-size: 18px;
  color: #FFFFFF;
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.fg-sb-org {
  font-size: 11.5px;
  color: #94A3B8;
  line-height: 1.25;
  margin-top: 2px;
}
.fg-sb-status {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.25);
  border-radius: 6px;
  padding: 4px 8px;
  margin: 0 4px 10px 4px;
}
.fg-sb-pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10B981;
  box-shadow: 0 0 8px #10B981;
  display: inline-block;
}
.fg-sb-stat-text {
  font-family: var(--fg-font-mono);
  font-size: 9.5px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: #34D399;
}
.fg-sb-divider {
  height: 1px;
  background: #1E293B;
  margin: 12px 4px;
}
.fg-sb-nav-label {
  font-family: var(--fg-font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: #64748B;
  margin: 8px 6px 6px 6px;
}

/* Sidebar Navigation Link Styling */
section[data-testid="stSidebar"] [data-testid="stPageLink"] a,
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
  border-radius: 8px !important;
  padding: 9px 12px !important;
  margin: 3px 0 !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  transition: all 0.15s ease !important;
}
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p {
  font-family: var(--fg-font-head) !important;
  font-size: 13.5px !important;
  font-weight: 500 !important;
  color: #94A3B8 !important;
  margin: 0 !important;
}
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] [data-testid="stIconMaterial"],
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] .material-symbols-rounded,
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] .material-symbols-outlined {
  font-family: "Material Symbols Rounded", "Material Symbols Outlined", sans-serif !important;
  font-size: 19px !important;
  color: #38BDF8 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {
  background: #1C2541 !important;
  border-color: #2D3748 !important;
}
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover p {
  color: #FFFFFF !important;
}
section[data-testid="stSidebar"] [aria-current="page"] [data-testid="stPageLink-NavLink"],
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-selected="true"] {
  background: rgba(14, 165, 233, 0.16) !important;
  border-color: rgba(56, 189, 248, 0.35) !important;
}
section[data-testid="stSidebar"] [aria-current="page"] [data-testid="stPageLink-NavLink"] p,
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-selected="true"] p {
  color: #38BDF8 !important;
  font-weight: 600 !important;
}

/* Sidebar Info Card */
.fg-sb-card {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid #1E293B;
  border-radius: 10px;
  padding: 10px 12px;
  margin: 6px 4px;
}
.fg-sb-card-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 11.5px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.fg-sb-card-row:last-child {
  border-bottom: none;
}
.fg-sb-card-k {
  color: #94A3B8;
}
.fg-sb-card-v {
  color: #E2E8F0;
  font-weight: 500;
}
.fg-sb-card-v.font-mono {
  font-family: var(--fg-font-mono);
}
.fg-sb-alert {
  color: #FBBF24 !important;
  font-family: var(--fg-font-mono);
  font-size: 10px;
  font-weight: 600;
}

/* Sidebar Footer Desk */
.fg-sb-footer {
  margin-top: 18px;
  padding: 10px 8px;
  border-top: 1px solid #1E293B;
  font-size: 11px;
}
.fg-sb-desk {
  font-family: var(--fg-font-mono);
  font-size: 9.5px;
  letter-spacing: 0.08em;
  color: #64748B;
  font-weight: 600;
  margin-bottom: 4px;
}
.fg-sb-phone {
  color: #94A3B8;
  line-height: 1.4;
}
.fg-sb-tollfree {
  color: #38BDF8;
  font-family: var(--fg-font-mono);
  font-weight: 600;
  margin-top: 2px;
}

/* ---------- Top Operational Status Strip ---------- */
.fg-top-strip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  background: #FFFFFF;
  border: 1px solid var(--fg-line);
  border-radius: 10px;
  padding: 8px 16px;
  margin-bottom: 16px;
  box-shadow: var(--fg-shadow);
}
.fg-top-strip-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.fg-top-tag {
  font-family: var(--fg-font-mono);
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--fg-accent);
}
.fg-top-sep {
  color: var(--fg-line-strong);
}
.fg-top-zone {
  font-weight: 500;
  color: var(--fg-ink-2);
}
.fg-top-strip-right {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11.5px;
}
.fg-top-clock {
  font-family: var(--fg-font-mono);
  color: var(--fg-muted);
}
.fg-top-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10B981;
}
.fg-top-active {
  font-family: var(--fg-font-mono);
  font-size: 10.5px;
  font-weight: 600;
  color: #059669;
}

/* ---------- Page Header ---------- */
.fg-page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
  padding: 4px 0 16px 0;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--fg-line);
}
.fg-eyebrow {
  font-family: var(--fg-font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-accent);
  margin-bottom: 4px;
  font-weight: 600;
}
.fg-h1 {
  font-family: var(--fg-font-head) !important;
  font-size: 26px !important;
  font-weight: 700 !important;
  line-height: 1.2 !important;
  letter-spacing: -0.02em !important;
  margin: 0 !important;
  color: var(--fg-ink) !important;
}
.fg-sub {
  margin: 5px 0 0 0 !important;
  font-size: 13.5px !important;
  color: var(--fg-muted) !important;
  max-width: 800px;
}
.fg-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.fg-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  font-weight: 500;
  color: var(--fg-ink-2);
  background: #FFFFFF;
  border: 1px solid var(--fg-line);
  padding: 4px 10px;
  border-radius: 8px;
  white-space: nowrap;
}
.fg-chip b {
  font-family: var(--fg-font-mono);
  font-weight: 600;
  color: var(--fg-ink);
}
.fg-chip-accent { color: var(--fg-accent); background: var(--fg-accent-soft); border-color: #B9E6EC; }
.fg-chip-ok { color: var(--fg-ok); background: var(--fg-ok-bg); border-color: var(--fg-ok-line); }
.fg-chip-warn { color: var(--fg-high); background: var(--fg-high-bg); border-color: var(--fg-high-line); }
.fg-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; display: inline-block; }

.fg-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
  margin: 8px 0 8px 0;
}
.fg-h3 {
  font-family: var(--fg-font-head) !important;
  font-size: 16.5px !important;
  font-weight: 600 !important;
  margin: 0 !important;
  color: var(--fg-ink) !important;
}
.fg-section-sub {
  margin: 2px 0 0 0 !important;
  font-size: 12.5px !important;
  color: var(--fg-muted) !important;
}

/* ---------- Surfaces & Cards ---------- */
.fg-card {
  background: var(--fg-surface);
  border: 1px solid var(--fg-line);
  border-radius: var(--fg-radius);
  padding: 16px 18px;
  box-shadow: var(--fg-shadow);
  margin-bottom: 12px;
}
.fg-card-title {
  font-family: var(--fg-font-head);
  font-size: 15px;
  font-weight: 600;
  color: var(--fg-ink);
  margin: 0;
}
.fg-card-sub {
  font-size: 12px;
  color: var(--fg-muted) !important;
  margin: 2px 0 8px 0 !important;
}

/* KPI Tiles */
.fg-kpi {
  background: #FFFFFF;
  border: 1px solid var(--fg-line);
  border-radius: var(--fg-radius);
  padding: 14px 16px;
  box-shadow: var(--fg-shadow);
  position: relative;
  overflow: hidden;
  margin-bottom: 6px;
}
.fg-kpi::before {
  content: "";
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 3.5px;
  border-radius: 0 3px 3px 0;
  background: var(--kpi-c, var(--fg-accent));
}
.fg-kpi-label {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: var(--fg-muted);
  font-weight: 500;
}
.fg-kpi-label .fg-ico {
  color: var(--kpi-c, var(--fg-accent));
}
.fg-kpi-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
}
.fg-kpi-value {
  font-family: var(--fg-font-mono);
  font-size: 28px;
  font-weight: 600;
  color: var(--fg-ink);
  line-height: 1;
}
.fg-kpi-delta {
  font-family: var(--fg-font-mono);
  font-size: 11px;
  color: var(--fg-muted);
}
.fg-kpi-delta b {
  color: var(--kpi-c, var(--fg-ink));
  font-weight: 600;
}

/* Status Pills */
.fg-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2.5px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  border: 1px solid;
  white-space: nowrap;
}
.fg-pill i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  display: inline-block;
}
.fg-pill-crit { color: var(--fg-crit); background: var(--fg-crit-bg); border-color: var(--fg-crit-line); }
.fg-pill-high { color: var(--fg-high); background: var(--fg-high-bg); border-color: var(--fg-high-line); }
.fg-pill-watch { color: var(--fg-watch); background: var(--fg-watch-bg); border-color: var(--fg-watch-line); }
.fg-pill-ok { color: var(--fg-ok); background: var(--fg-ok-bg); border-color: var(--fg-ok-line); }
.fg-pill-neutral { color: var(--fg-ink-2); background: var(--fg-surface-2); border-color: var(--fg-line); }

/* Progress Bars */
.progress-track { background: #E2E8F0; border-radius: 4px; overflow: hidden; display: inline-block; vertical-align: middle; }
.progress-fill { height: 100%; border-radius: 4px; }
.fill-critical { background: var(--fg-crit); }
.fill-high { background: var(--fg-high); }
.fill-medium { background: var(--fg-watch); }
.fill-low { background: var(--fg-ok); }

/* Alerts List */
.alert-item { display: flex; align-items: flex-start; gap: 12px; padding: 9px 0; border-bottom: 1px solid #F1F5F9; }
.alert-item:last-child { border-bottom: none; }
.alert-bar { width: 3.5px; align-self: stretch; border-radius: 3px; flex-shrink: 0; }
.alert-content { flex: 1; min-width: 0; }
.alert-title { font-size: 13px !important; line-height: 1.35 !important; font-weight: 600; color: var(--fg-ink) !important; margin: 0 !important; }
.alert-subtitle { font-size: 12px !important; line-height: 1.35 !important; color: var(--fg-muted) !important; margin: 2px 0 0 0 !important; }
.alert-time { font-family: var(--fg-font-mono); font-size: 11px; color: var(--fg-faint); white-space: nowrap; }

/* Data Grid in Cards */
.fg-kv { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px 18px; padding-top: 10px; border-top: 1px solid #F1F5F9; }
.fg-kv > div { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.fg-k { font-size: 11px; color: var(--fg-muted); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
.fg-v { font-size: 13px; color: var(--fg-ink); font-weight: 500; }
.fg-v.mono { font-family: var(--fg-font-mono); font-weight: 500; }

/* Form Controls */
div[data-baseweb="select"] > div, div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input, textarea {
  background-color: #FFFFFF !important; border-color: var(--fg-line-strong) !important; border-radius: var(--fg-radius-sm) !important; color: var(--fg-ink) !important;
}
div[data-baseweb="select"] > div:focus-within, div[data-testid="stTextInput"] input:focus { border-color: var(--fg-accent) !important; box-shadow: 0 0 0 3px rgba(10,124,143,.14) !important; }

/* Buttons */
div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button {
  border-radius: var(--fg-radius-sm) !important; font-weight: 600 !important; font-size: 13px !important;
  border: 1px solid var(--fg-line-strong) !important; background: #FFFFFF !important; color: var(--fg-ink) !important;
  box-shadow: var(--fg-shadow) !important; transition: all 0.15s ease !important;
}
div[data-testid="stButton"] button:hover, div[data-testid="stDownloadButton"] button:hover { border-color: var(--fg-accent) !important; color: var(--fg-accent) !important; }
div[data-testid="stButton"] button[kind="primary"], div[data-testid="stDownloadButton"] button[kind="primary"] {
  background: var(--fg-ink) !important; color: #FFFFFF !important; border-color: var(--fg-ink) !important;
}
div[data-testid="stButton"] button[kind="primary"] p, div[data-testid="stDownloadButton"] button[kind="primary"] p { color: #FFFFFF !important; }
div[data-testid="stButton"] button[kind="primary"]:hover, div[data-testid="stDownloadButton"] button[kind="primary"]:hover { background: var(--fg-accent) !important; border-color: var(--fg-accent) !important; color: #FFFFFF !important; }

/* Metric Cards */
div[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid var(--fg-line); border-radius: var(--fg-radius); padding: 12px 16px; box-shadow: var(--fg-shadow); }
div[data-testid="stMetricLabel"] p { font-size: 12px !important; color: var(--fg-muted) !important; font-weight: 500 !important; }
div[data-testid="stMetricValue"] { font-family: var(--fg-font-mono) !important; font-weight: 600 !important; font-size: 24px !important; color: var(--fg-ink) !important; }

/* Ranking Table Box */
.st-key-ranking_table_box { background: #FFFFFF; border: 1px solid var(--fg-line); border-radius: var(--fg-radius); padding: 8px 12px 10px 12px; box-shadow: var(--fg-shadow); }
.st-key-ranking_table_box div[data-testid="stHorizontalBlock"] { gap: 6px !important; align-items: center !important; margin: 0 !important; padding: 2px 0 !important; border-bottom: 1px solid #F1F5F9; }
.st-key-ranking_table_box div[data-testid="stButton"] button {
  min-height: 28px !important; height: 28px !important; padding: 0 6px !important; border: none !important; background: transparent !important; box-shadow: none !important;
  justify-content: flex-start !important; text-align: left !important;
}
.st-key-ranking_table_box div[data-testid="stButton"] button > div { justify-content: flex-start !important; width: 100%; }
.st-key-ranking_table_box div[data-testid="stButton"] button p { text-align: left !important; font-size: 12.5px !important; font-weight: 500 !important; color: var(--fg-ink) !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.st-key-ranking_table_box div[data-testid="stButton"] button:hover { background: var(--fg-surface-2) !important; }
.st-key-ranking_table_box div[data-testid="stButton"] button[kind="primary"] { background: var(--fg-accent-soft) !important; box-shadow: inset 2px 0 0 var(--fg-accent) !important; border-radius: 0 6px 6px 0 !important; }
.st-key-ranking_table_box div[data-testid="stButton"] button[kind="primary"] p { color: var(--fg-accent) !important; font-weight: 600 !important; }
.fg-th { white-space: nowrap; font-size: 11px; font-weight: 600; color: var(--fg-muted); text-transform: uppercase; letter-spacing: 0.06em; }
.fg-num { font-family: var(--fg-font-mono); font-size: 12px; color: var(--fg-ink); font-variant-numeric: tabular-nums; }
.fg-rule { border: none; border-top: 1px solid var(--fg-line); margin: 20px 0; }
</style>
"""
