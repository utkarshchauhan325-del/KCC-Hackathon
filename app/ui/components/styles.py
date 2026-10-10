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

/* ---------- Top navigation bar (no sidebar) ---------- */
section[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"] { display: none !important; }

.st-key-fg_topnav {
  background: linear-gradient(110deg, #0B132B 0%, #111D3A 100%);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 22px;
  box-shadow: 0 10px 28px rgba(11, 19, 43, 0.2);
  /* Keep a visible gutter around the taller, rounded navigation bar. */
  --fg-bleed: max(0px, calc((100vw - 1412px) / 2));
  width: calc(100% + 20px + 2 * var(--fg-bleed)) !important;
  max-width: none !important;
  margin-left: calc(-10px - var(--fg-bleed)) !important;
  padding: 16px calc(28px + var(--fg-bleed));
}
/* Pin the bar: Streamlit wraps it in a box of its own height, so the wrapper is what sticks */
[data-testid="stLayoutWrapper"]:has(> .st-key-fg_topnav) { position: sticky; top: 10px; z-index: 999; margin-top: -8px; margin-bottom: 28px; }
.st-key-fg_topnav [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; row-gap: 4px !important; align-items: center !important; }
.st-key-fg_topnav [data-testid="stColumn"] { width: auto !important; flex: 0 0 auto !important; min-width: 0 !important; }
.st-key-fg_topnav [data-testid="stColumn"]:first-child { flex: 1 1 auto !important; }
.st-key-fg_topnav [data-testid="stColumn"]:last-child { flex: 0 0 auto !important; margin-left: auto; }

.fg-nav-brand { display: flex; align-items: center; gap: 10px; white-space: nowrap; padding-right: 12px; }
.fg-sb-logo { flex-shrink: 0; }
.fg-nav-title { font-family: var(--fg-font-head); font-weight: 700; font-size: 17px; color: #FFFFFF; letter-spacing: -0.02em; line-height: 1.1; }
.fg-nav-org { font-size: 11px; color: #94A3B8; line-height: 1.2; }
.fg-nav-status { display: flex; align-items: center; justify-content: flex-end; gap: 8px; white-space: nowrap; padding-left: 12px; }
.fg-nav-clock { font-family: var(--fg-font-mono); font-size: 11.5px; color: #CBD5E1; }
.fg-top-dot { width: 7px; height: 7px; border-radius: 50%; background: #10B981; box-shadow: 0 0 8px #10B981; display: inline-block; }

[class*="st-key-fgnav_"] [data-testid="stPageLink"] a,
[class*="st-key-fgnav_"] [data-testid="stPageLink-NavLink"] {
  border-radius: 8px !important; padding: 6px 12px !important; margin: 0 !important;
  background: transparent !important; border: 1px solid transparent !important; transition: all 0.15s ease !important;
  white-space: nowrap !important;
}
[class*="st-key-fgnav_"] [data-testid="stPageLink-NavLink"] p {
  font-family: var(--fg-font-head) !important; font-size: 13.5px !important; font-weight: 500 !important;
  color: #CBD5E1 !important; margin: 0 !important; white-space: nowrap !important;
}
[class*="st-key-fgnav_"] [data-testid="stIconMaterial"], [class*="st-key-fgnav_"] .material-symbols-rounded {
  font-size: 18px !important; color: #38BDF8 !important;
}
[class*="st-key-fgnav_"] [data-testid="stPageLink-NavLink"]:hover { background: #1C2541 !important; border-color: #2D3748 !important; }
[class*="st-key-fgnav_"] [data-testid="stPageLink-NavLink"]:hover p { color: #FFFFFF !important; }
[class*="st-key-fgnav_active"] [data-testid="stPageLink-NavLink"] { background: rgba(14, 165, 233, 0.16) !important; border-color: rgba(56, 189, 248, 0.35) !important; }
[class*="st-key-fgnav_active"] [data-testid="stPageLink-NavLink"] p { color: #FFFFFF !important; font-weight: 600 !important; }
@media (max-width: 1100px) {
  .st-key-fg_topnav [data-testid="stColumn"]:last-child { display: none !important; }
}
@media (max-width: 760px) {
  .fg-nav-org { display: none; }
  .st-key-fg_topnav { border-radius: 18px; padding: 12px 18px; }
  [data-testid="stLayoutWrapper"]:has(> .st-key-fg_topnav) { position: relative; }
  .st-key-fg_topnav [data-testid="stHorizontalBlock"] { column-gap: 2px !important; row-gap: 6px !important; }
  .st-key-fg_topnav [data-testid="stColumn"]:first-child { flex: 1 1 100% !important; margin-bottom: 2px; }
  [class*="st-key-fgnav_"] [data-testid="stIconMaterial"] { font-size: 16px !important; }
  [class*="st-key-fgnav_"] [data-testid="stPageLink-NavLink"] { padding: 5px 8px !important; }
  [class*="st-key-fgnav_"] [data-testid="stPageLink-NavLink"] p { font-size: 12.5px !important; }
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
/* Dashboard map + ranking: side by side on wide screens, stacked below 1200px */
@media (max-width: 1200px) {
  .st-key-fg_maprank > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
  .st-key-fg_maprank > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important;
  }
}

/* Ranking table stays a table at any width: rows never stack, and it drops the
   rain and saturation columns when it gets narrow instead of squashing them. */
.st-key-ranking_table_box { container-type: inline-size; }
.st-key-ranking_table_box [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; }
.st-key-ranking_table_box [data-testid="stColumn"] { min-width: 0 !important; }
.st-key-ranking_table_box .fg-pill { padding: 2px 7px; font-size: 10.5px; }
@container (max-width: 600px) {
  .st-key-ranking_table_box [data-testid="stColumn"]:nth-child(4),
  .st-key-ranking_table_box [data-testid="stColumn"]:nth-child(5) { display: none !important; }
}
@container (max-width: 380px) {
  .st-key-ranking_table_box [data-testid="stColumn"]:nth-child(6) { display: none !important; }
  .st-key-ranking_table_box .fg-pill { font-size: 0; gap: 0; padding: 4px; }
}
.fg-th { white-space: nowrap; font-size: 11px; font-weight: 600; color: var(--fg-muted); text-transform: uppercase; letter-spacing: 0.06em; }
.fg-num { font-family: var(--fg-font-mono); font-size: 12px; color: var(--fg-ink); font-variant-numeric: tabular-nums; }
.fg-rule { border: none; border-top: 1px solid var(--fg-line); margin: 20px 0; }

/* Video panels (CCTV page) */
.fg-video-bar { background: #0F172A; color: #CBD5E1; border-radius: 12px 12px 0 0; padding: 9px 14px; display: flex; justify-content: space-between; align-items: center; gap: 10px; font-family: var(--fg-font-mono); font-size: 11.5px; }
.fg-video-bar b { color: #F8FAFC; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fg-video-bar .fg-rec { display: inline-flex; align-items: center; gap: 7px; min-width: 0; }
.fg-video-bar .fg-rec i { width: 7px; height: 7px; border-radius: 50%; background: #10B981; flex-shrink: 0; display: inline-block; }
[class*="st-key-fgvideo"] video { max-height: 68vh; width: 100%; background: #0B1220; border-radius: 0 0 12px 12px; display: block; }
.fg-dropzone-empty { height: 300px; border-radius: 12px; background: linear-gradient(180deg, #F8FAFC, #EEF2F6); border: 1.5px dashed #CBD5E1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; color: var(--fg-muted); text-align: center; padding: 16px; }
[data-testid="stFileUploaderDropzone"] { border: 1.5px dashed var(--fg-line-strong) !important; background: #FFFFFF !important; border-radius: var(--fg-radius) !important; }
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--fg-accent) !important; background: #F5FBFC !important; }

/* Score tiles */
.fg-grid { display: grid; gap: 10px; margin-bottom: 10px; }
.fg-grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.fg-grid-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.fg-grid-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
@media (max-width: 900px) { .fg-grid-3, .fg-grid-4 { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 560px) { .fg-grid-2, .fg-grid-3, .fg-grid-4 { grid-template-columns: 1fr; } }
.fg-score { background: #FFFFFF; border: 1px solid var(--fg-line); border-radius: var(--fg-radius); padding: 12px 14px; box-shadow: var(--fg-shadow); min-width: 0; }
.fg-score-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.fg-score-label { font-size: 12px; color: var(--fg-muted); font-weight: 500; }
.fg-score-val { font-family: var(--fg-font-mono); font-size: 24px; font-weight: 600; color: var(--fg-ink); line-height: 1.1; margin: 6px 0 8px 0; }
.fg-score-val small { font-size: 12px; color: var(--fg-faint); font-weight: 500; }
.fg-score-note { font-size: 11.5px; color: var(--fg-muted); margin-top: 6px; }
.fg-bar { height: 6px; background: #EEF2F6; border-radius: 4px; overflow: hidden; }
.fg-bar > span { display: block; height: 100%; border-radius: 4px; }

/* Evidence frames */
[class*="st-key-fgframe"] img { aspect-ratio: 16 / 10; object-fit: cover; border-radius: 10px; border: 1px solid var(--fg-line); background: #0B1220; }
[class*="st-key-fgframe"] [data-testid="stImageCaption"], [class*="st-key-fgframe"] [data-testid="caption"] { font-size: 11.5px !important; color: var(--fg-muted) !important; text-align: left !important; }
.fg-noframe { aspect-ratio: 16 / 10; border-radius: 10px; border: 1px dashed var(--fg-line-strong); background: repeating-linear-gradient(135deg, #F8FAFC, #F8FAFC 8px, #F1F5F9 8px, #F1F5F9 16px); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; color: var(--fg-faint); font-size: 12px; text-align: center; padding: 10px; }

/* ==========================================================================
   Priority Queue Redesign Styles (Master-Detail, KPIs, Filmstrip & Badges)
   Tokens: Teal #0E7C86, Navy #0B132B, Space Grotesk / Inter, JetBrains Mono
   ========================================================================== */
.fg-pq-header { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.fg-pq-title-group .fg-eyebrow { color: #0E7C86; font-weight: 700; font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 2px; }
.fg-pq-title-group h1 { font-family: var(--fg-font-head); font-size: 26px; font-weight: 700; color: #0B132B; margin: 0; line-height: 1.15; }
.fg-pq-title-group p { font-size: 13.5px; color: #64748B; margin: 4px 0 0 0; }
.fg-pq-header-actions { display: flex; align-items: center; gap: 10px; }

/* 4 KPI Cards Strip with Colored Left Accent */
.fg-pq-kpi {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  padding: 14px 16px 14px 18px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
}
.fg-pq-kpi-1 { border-left: 3.5px solid #DC2626 !important; }
.fg-pq-kpi-2 { border-left: 3.5px solid #0E7C86 !important; }
.fg-pq-kpi-3 { border-left: 3.5px solid #D97706 !important; }
.fg-pq-kpi-4 { border-left: 3.5px solid #0B132B !important; }

.fg-pq-kpi-label { font-size: 12px; font-weight: 500; color: #64748B; margin-bottom: 4px; }
.fg-pq-kpi-val { font-family: var(--fg-font-mono); font-size: 28px; font-weight: 700; color: #0B132B; line-height: 1.1; }
.fg-pq-kpi-note { font-size: 11.5px; color: #94A3B8; margin-top: 4px; }

/* Filter Strip and Pill Controls */
.st-key-pq_tab_pills [data-testid="stPills"] button {
  border-radius: 20px !important;
  font-size: 12.5px !important;
  font-weight: 500 !important;
  padding: 3px 12px !important;
  border: 1px solid #CBD5E1 !important;
  background: #FFFFFF !important;
  color: #334155 !important;
}
.st-key-pq_tab_pills [data-testid="stPills"] button[aria-selected="true"] {
  background: #0B132B !important;
  color: #FFFFFF !important;
  border-color: #0B132B !important;
}

.st-key-pq_f_sev div[data-baseweb="select"] > div,
.st-key-pq_f_src div[data-baseweb="select"] > div,
.st-key-pq_f_zone div[data-baseweb="select"] > div,
.st-key-pq_f_sort div[data-baseweb="select"] > div {
  border-radius: 20px !important;
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  font-size: 12.5px !important;
}
.st-key-pq_f_search input {
  border-radius: 20px !important;
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  font-size: 12.5px !important;
}

/* Master List: Incident Card Containers */
[class*="st-key-pq_card_"] {
  position: relative !important;
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  border-radius: 10px !important;
  padding: 14px 16px !important;
  margin-bottom: 12px !important;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03) !important;
  transition: all 0.18s ease !important;
  cursor: pointer !important;
}
[class*="st-key-pq_card_"]:hover {
  background: #F1F5F9 !important;
  border-color: #CBD5E1 !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06) !important;
}
[class*="st-key-pq_card_sel_"] {
  position: relative !important;
  background: #FFFFFF !important;
  border: 1.5px solid #0E7C86 !important;
  border-radius: 10px !important;
  padding: 14px 16px !important;
  margin-bottom: 12px !important;
  box-shadow: 0 0 0 1px rgba(14, 124, 134, 0.15), 0 4px 12px rgba(14, 124, 134, 0.06) !important;
  cursor: pointer !important;
}
[class*="st-key-pq_card_sel_"]:hover {
  background: #F8FAFC !important;
  border-color: #0E7C86 !important;
}

/* Invisible overlay button allowing full-card click anywhere on the div */
[class*="st-key-sel_card_"] {
  position: absolute !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100% !important;
  height: 100% !important;
  z-index: 5 !important;
  margin: 0 !important;
  padding: 0 !important;
}
[class*="st-key-sel_card_"] button {
  width: 100% !important;
  height: 100% !important;
  min-height: 100% !important;
  background: transparent !important;
  border: none !important;
  color: transparent !important;
  opacity: 0 !important;
  cursor: pointer !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

/* Thumbnail with Bounding Box and Timestamp Overlays */
.fg-pq-thumb {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  border-radius: 6px;
  overflow: hidden;
  background: #0B1220;
}
.fg-pq-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.fg-pq-bbox {
  position: absolute;
  border: 1.5px solid #DC2626;
  pointer-events: none;
  box-sizing: border-box;
}
.fg-pq-bbox-label {
  position: absolute;
  top: 0;
  left: 0;
  background: #DC2626;
  color: #FFFFFF;
  font-family: var(--fg-font-mono);
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  white-space: nowrap;
  letter-spacing: 0.01em;
}
.fg-pq-thumb-ts {
  position: absolute;
  bottom: 6px;
  right: 6px;
  background: rgba(11, 19, 43, 0.88);
  color: #FFFFFF;
  font-family: var(--fg-font-mono);
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
}
.fg-pq-hatched {
  width: 100%;
  aspect-ratio: 16 / 10;
  border-radius: 6px;
  border: 1px dashed #CBD5E1;
  background: repeating-linear-gradient(45deg, #F8FAFC, #F8FAFC 8px, #EEF2F6 8px, #EEF2F6 16px);
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 10px;
  color: #64748B;
  font-size: 11.5px;
  font-weight: 500;
  line-height: 1.35;
}

/* Incident Metadata & Badges */
.fg-pq-meta-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.fg-pq-badges { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.fg-pq-sev-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 5px;
}
.fg-pq-sev-5 { background: #FEE2E2; color: #DC2626; border: 1px solid #FECACA; }
.fg-pq-sev-4 { background: #FFEDD5; color: #EA580C; border: 1px solid #FED7AA; }
.fg-pq-sev-3 { background: #FEF3C7; color: #D97706; border: 1px solid #FDE68A; }
.fg-pq-src-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 5px;
  background: #CCFBF1;
  color: #0F766E;
  border: 1px solid #99F6E4;
}
.fg-pq-src-sensor {
  background: #F1F5F9;
  color: #475569;
  border: 1px solid #E2E8F0;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 5px;
}
.fg-pq-meta-id { font-family: var(--fg-font-mono); font-size: 11.5px; color: #94A3B8; }

/* Interactive Title Link */
[class*="st-key-sel_title_"] button {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  margin: 2px 0 3px 0 !important;
  text-align: left !important;
  font-family: var(--fg-font-head) !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  color: #0B132B !important;
  box-shadow: none !important;
  min-height: unset !important;
  height: auto !important;
  cursor: pointer !important;
}
[class*="st-key-sel_title_"] button:hover {
  color: #0E7C86 !important;
}

.fg-pq-title {
  font-family: var(--fg-font-head);
  font-size: 15px;
  font-weight: 700;
  color: #0B132B;
  margin: 2px 0 3px 0;
  line-height: 1.3;
}
.fg-pq-title span { font-weight: 400; color: #64748B; font-size: 14.5px; }
.fg-pq-desc { font-size: 13px; color: #475569; line-height: 1.4; margin-bottom: 8px; }

/* Circular Risk Score Rings */
.fg-pq-ring {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--fg-font-mono);
  font-size: 13px;
  font-weight: 700;
  color: #0B132B;
  flex-shrink: 0;
  background: #FFFFFF;
}
.fg-pq-ring-red { border: 2px solid #DC2626; }
.fg-pq-ring-orange { border: 2px solid #EA580C; }
.fg-pq-ring-amber { border: 2px solid #D97706; }
.fg-pq-ring-teal { border: 2px solid #0E7C86; }

.fg-pq-col-meta { display: flex; flex-direction: column; gap: 1px; }
.fg-pq-col-lbl { font-size: 10.5px; text-transform: uppercase; color: #64748B; font-weight: 600; }
.fg-pq-col-val { font-size: 12.5px; font-weight: 600; color: #0B132B; }

/* Sticky Detail Panel */
.st-key-fg_pq_detail_container {
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  border-radius: 12px !important;
  padding: 18px 20px !important;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.04) !important;
  position: sticky !important;
  top: 75px !important;
}
.fg-pq-detail-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.fg-pq-detail-meta { font-family: var(--fg-font-mono); font-size: 11.5px; color: #64748B; margin-bottom: 2px; }
.fg-pq-detail-title { font-family: var(--fg-font-head); font-size: 20px; font-weight: 700; color: #0B132B; margin: 0; }

.fg-pq-detail-img-box {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  border-radius: 8px;
  overflow: hidden;
  background: #0B1220;
  margin-bottom: 10px;
}
.fg-pq-detail-img-box img { width: 100%; height: 100%; object-fit: cover; display: block; }
.fg-pq-detail-corner-pill {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: rgba(11, 19, 43, 0.88);
  color: #FFFFFF;
  font-family: var(--fg-font-mono);
  font-size: 10.5px;
  font-weight: 600;
  padding: 2.5px 8px;
  border-radius: 4px;
}

/* Filmstrip Thumbnails Row */
.fg-pq-filmstrip-thumb {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  border-radius: 5px;
  overflow: hidden;
  background: #0B1220;
  border: 1px solid #CBD5E1;
  transition: all 0.15s ease;
}
.fg-pq-filmstrip-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.fg-pq-filmstrip-active {
  border: 2px solid #0E7C86 !important;
  box-shadow: 0 0 0 1px #0E7C86;
}
.fg-pq-filmstrip-ts {
  position: absolute;
  bottom: 2px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.85);
  color: #FFFFFF;
  font-family: var(--fg-font-mono);
  font-size: 9.5px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
}

/* Micro-button for Filmstrip interaction */
[class*="st-key-fstrip_"] button {
  height: 22px !important;
  min-height: 22px !important;
  padding: 0 2px !important;
  font-size: 10px !important;
  font-family: var(--fg-font-mono) !important;
  margin-top: 2px !important;
  border-radius: 3px !important;
  background: #F8FAFC !important;
  border: 1px solid #E2E8F0 !important;
  color: #475569 !important;
}
[class*="st-key-fstrip_"] button:hover {
  background: #0E7C86 !important;
  color: #FFFFFF !important;
  border-color: #0E7C86 !important;
}

.fg-pq-ai-lbl { font-size: 11.5px; color: #64748B; margin-top: 14px; margin-bottom: 3px; }
.fg-pq-ai-text { font-size: 13.5px; color: #1E293B; line-height: 1.45; }

.fg-pq-triplet-row {
  display: flex;
  gap: 24px;
  margin: 14px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid #F1F5F9;
}
.fg-pq-triplet-lbl { font-size: 11px; color: #64748B; margin-bottom: 2px; }
.fg-pq-triplet-val { font-family: var(--fg-font-mono); font-size: 13.5px; font-weight: 700; color: #0B132B; }

.fg-pq-sec-lbl { font-size: 11px; color: #64748B; margin-bottom: 4px; }
.fg-pq-sec-val { font-size: 13.5px; color: #0B132B; font-weight: 700; line-height: 1.35; margin-bottom: 14px; }
.fg-pq-crew-box {
  background: #FFFFFF;
  border: 1px solid #CBD5E1;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 13px;
  color: #0B132B;
  font-weight: 600;
  margin-bottom: 16px;
}

/* ==========================================================================
   Administrator Sign-in Page Styling & Centering
   ========================================================================== */
.stApp:has(.st-key-fg_login_card) [data-testid="stMainBlockContainer"],
.stApp:has(.st-key-fg_login_card) .block-container {
  max-width: 900px !important;
  margin: 0 auto !important;
  padding-top: 10vh !important;
  padding-bottom: 5vh !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
}

.fg-login-bg-waves {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 260px;
  pointer-events: none;
  z-index: 0;
  opacity: 0.6;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 320' preserveAspectRatio='none'><path fill='%23BAE6FD' fill-opacity='0.45' d='M0,192L48,197.3C96,203,192,213,288,197.3C384,181,480,139,576,133.3C672,128,768,160,864,176C960,192,1056,192,1152,176C1248,160,1344,128,1392,112L1440,96L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z'></path><path fill='%23E0F2FE' fill-opacity='0.6' d='M0,224L48,229.3C96,235,192,245,288,229.3C384,213,480,171,576,165.3C672,160,768,192,864,208C960,224,1056,224,1152,208C1248,192,1344,160,1392,144L1440,128L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z'></path></svg>");
  background-size: cover;
  background-position: bottom;
  background-repeat: no-repeat;
}

.st-key-fg_login_card {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 480px;
  margin: 0 auto !important;
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  border-radius: 20px !important;
  box-shadow: 0 20px 45px -10px rgba(15, 23, 42, 0.12), 0 2px 8px rgba(15, 23, 42, 0.05) !important;
  padding: 34px 32px 28px !important;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.fg-login-header {
  text-align: center;
  margin-bottom: 22px;
}
.fg-login-title {
  font-family: var(--fg-font-head);
  font-size: 24px;
  font-weight: 700;
  color: #0B132B;
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin: 0;
}
.fg-login-sub {
  font-size: 13px;
  color: #64748B;
  margin-top: 5px;
  line-height: 1.35;
}

.fg-demo-pill {
  background: #F0F9FF;
  border: 1px solid #BAE6FD;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 20px;
  font-size: 12.5px;
  color: #0369A1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  line-height: 1.5;
}
.fg-demo-pill-title {
  font-weight: 700;
  color: #0284C7;
  font-size: 11.5px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 2px;
}
.fg-demo-pill code {
  background: #E0F2FE;
  color: #0C4A6E;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  font-family: var(--fg-font-mono);
}

.st-key-fg_login_card [data-testid="stForm"] {
  border: none !important;
  padding: 0 !important;
  background: transparent !important;
}

.st-key-fg_login_card label p {
  font-size: 13.5px !important;
  font-weight: 600 !important;
  color: #1E293B !important;
  margin-bottom: 5px !important;
}
.st-key-fg_login_card [data-testid="stTextInputRootElement"] {
  border-radius: 10px !important;
  border: 1.5px solid #CBD5E1 !important;
  background: #F8FAFC !important;
  transition: all 0.2s ease !important;
}
.st-key-fg_login_card [data-testid="stTextInputRootElement"]:focus-within {
  border-color: #0284C7 !important;
  box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.15) !important;
  background: #FFFFFF !important;
}
.st-key-fg_login_card [data-testid="stTextInputRootElement"] input {
  font-size: 14px !important;
  color: #0F172A !important;
  padding: 10px 14px !important;
}

.st-key-fg_login_card [data-testid="stFormSubmitButton"] button {
  width: 100% !important;
  background: #0B132B !important;
  color: #FFFFFF !important;
  border: none !important;
  border-radius: 10px !important;
  padding: 12px 20px !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  letter-spacing: -0.01em !important;
  box-shadow: 0 4px 14px rgba(11, 19, 43, 0.25) !important;
  transition: all 0.2s ease !important;
  margin-top: 10px !important;
}
.st-key-fg_login_card [data-testid="stFormSubmitButton"] button:hover {
  background: #1C2541 !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 18px rgba(11, 19, 43, 0.3) !important;
}
.st-key-fg_login_card [data-testid="stFormSubmitButton"] button:active {
  transform: translateY(0px) !important;
}

/* Shake Animation for failure */
@keyframes fg-shake {
  0%, 100% { transform: translateX(0); }
  15%, 45%, 75% { transform: translateX(-9px); }
  30%, 60%, 90% { transform: translateX(9px); }
}
.fg-shake-card {
  animation: fg-shake 0.5s cubic-bezier(0.36, 0.07, 0.19, 0.97) both;
}

/* Success Animation */
@keyframes fg-pop-success {
  0% { transform: scale(0.96); opacity: 0.4; }
  50% { transform: scale(1.02); }
  100% { transform: scale(1); opacity: 1; }
}
.fg-success-card {
  animation: fg-pop-success 0.45s ease-out forwards;
}

/* Animated alert banners */
@keyframes fg-slide-down {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
.fg-alert-banner {
  border-radius: 12px;
  padding: 11px 14px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  animation: fg-slide-down 0.3s ease-out;
  line-height: 1.4;
}
.fg-alert-error {
  background: #FEF2F2;
  border: 1.5px solid #FCA5A5;
  color: #991B1B;
}
.fg-alert-success {
  background: #ECFDF5;
  border: 1.5px solid #6EE7B7;
  color: #065F46;
}

/* Authenticated Topnav additions */
.fg-nav-user-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 4px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: #E2E8F0;
  font-size: 11.5px;
  font-family: var(--fg-font-mono);
  white-space: nowrap;
}
.st-key-fg_logout_btn div[data-testid="stButton"] button {
  background: rgba(239, 68, 68, 0.18) !important;
  border: 1px solid rgba(239, 68, 68, 0.35) !important;
  color: #FECACA !important;
  border-radius: 8px !important;
  padding: 4px 10px !important;
  min-height: 28px !important;
  height: 28px !important;
  font-size: 11.5px !important;
  font-weight: 500 !important;
  transition: all 0.15s ease !important;
}
.st-key-fg_logout_btn div[data-testid="stButton"] button:hover {
  background: rgba(239, 68, 68, 0.35) !important;
  color: #FFFFFF !important;
}
</style>
"""
