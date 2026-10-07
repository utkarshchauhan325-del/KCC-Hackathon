"""FloodGuard theme: design tokens, global CSS, inline SVG icons and small HTML helpers.

Every view builds its markup from the helpers here so the console keeps one visual
language: light cool-grey canvas, white surfaces, hairline borders, a single teal accent
and status colours used only where they carry meaning.
"""

from html import escape
from typing import Iterable, Optional

# ---------------------------------------------------------------------------
# Design tokens (mirrored as CSS custom properties in get_floodguard_css)
# ---------------------------------------------------------------------------
ACCENT = "#0A7C8F"
ACCENT_BRIGHT = "#12B5CB"
ACCENT_SOFT = "#E4F4F6"
INK = "#0B1220"
INK_2 = "#334155"
MUTED = "#64708A"
LINE = "#E3E8EF"
GRID = "#EEF1F5"

STATUS = {
    "Critical": {"fg": "#C8281C", "bg": "#FDF0EE", "line": "#F6CFCA"},
    "High": {"fg": "#C25A06", "bg": "#FEF4E8", "line": "#F7D9B5"},
    "Medium": {"fg": "#9A7200", "bg": "#FBF6E2", "line": "#EEDF9E"},
    "Low": {"fg": "#14784F", "bg": "#EAF6EF", "line": "#BFE3CF"},
}

FONT_HEAD = "'Space Grotesk', 'Inter', system-ui, sans-serif"
FONT_BODY = "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif"
FONT_MONO = "'JetBrains Mono', ui-monospace, 'SFMono-Regular', Consolas, monospace"


def status_color(level: str) -> str:
    return STATUS.get(level, {"fg": ACCENT})["fg"]


# ---------------------------------------------------------------------------
# Inline SVG line icons (24px grid, 1.6 stroke, currentColor)
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
    '<svg width="26" height="26" viewBox="0 0 32 32" fill="none" aria-hidden="true">'
    '<rect x="1" y="1" width="30" height="30" rx="9" fill="#0B1220"/>'
    '<path d="M16 7.5s6 6.4 6 10.6a6 6 0 0 1-12 0c0-4.2 6-10.6 6-10.6Z" stroke="#12B5CB" stroke-width="1.8"/>'
    '<path d="M12.6 19.2c1.1 1.4 2.2 1.9 3.4 1.9" stroke="#12B5CB" stroke-width="1.6" stroke-linecap="round"/>'
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

:root {
  --fg-bg: #F3F5F8;
  --fg-surface: #FFFFFF;
  --fg-surface-2: #F8FAFC;
  --fg-line: #E3E8EF;
  --fg-line-strong: #CFD6E0;
  --fg-ink: #0B1220;
  --fg-ink-2: #334155;
  --fg-muted: #64708A;
  --fg-faint: #94A0B4;
  --fg-accent: #0A7C8F;
  --fg-accent-bright: #12B5CB;
  --fg-accent-soft: #E4F4F6;
  --fg-crit: #C8281C;  --fg-crit-bg: #FDF0EE;  --fg-crit-line: #F6CFCA;
  --fg-high: #C25A06;  --fg-high-bg: #FEF4E8;  --fg-high-line: #F7D9B5;
  --fg-watch: #9A7200; --fg-watch-bg: #FBF6E2; --fg-watch-line: #EEDF9E;
  --fg-ok: #14784F;    --fg-ok-bg: #EAF6EF;    --fg-ok-line: #BFE3CF;
  --fg-radius: 12px;
  --fg-radius-sm: 8px;
  --fg-shadow: 0 1px 2px rgba(11, 18, 32, 0.04), 0 1px 1px rgba(11, 18, 32, 0.02);
  --fg-shadow-lg: 0 18px 48px -12px rgba(11, 18, 32, 0.18), 0 4px 12px rgba(11, 18, 32, 0.06);
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
    linear-gradient(rgba(10, 124, 143, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(10, 124, 143, 0.035) 1px, transparent 1px);
  background-size: 32px 32px;
  background-attachment: fixed;
}
[data-testid="stMainBlockContainer"], .block-container {
  padding-top: 96px !important;
  padding-bottom: 64px !important;
  max-width: 1320px;
}
h1, h2, h3, h4, h5 { font-family: var(--fg-font-head) !important; color: var(--fg-ink) !important; letter-spacing: -0.01em; }
code, kbd, pre { font-family: var(--fg-font-mono) !important; }
p, li { color: var(--fg-ink-2); }
.fg-ico { display: inline-block; vertical-align: -3px; flex-shrink: 0; }
.fg-mono { font-family: var(--fg-font-mono); font-variant-numeric: tabular-nums; }

/* ---------- Hide Streamlit chrome ---------- */
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stAppDeployButton"], #MainMenu, footer,
section[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"], [data-testid="stExpandSidebarButton"] {
  display: none !important;
}
iframe[height="0"] { position: absolute !important; width: 0 !important; height: 0 !important; border: 0 !important; }

/* ---------- Top bar ---------- */
.st-key-fg_topbar {
  position: fixed !important;
  top: 12px; left: 50%; transform: translateX(-50%);
  width: min(1296px, calc(100% - 24px)) !important;
  z-index: 999900;
  padding: 7px 8px 7px 14px !important;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: saturate(160%) blur(16px);
  -webkit-backdrop-filter: saturate(160%) blur(16px);
  border: 1px solid rgba(207, 214, 224, 0.85);
  border-radius: 16px;
  box-shadow: 0 8px 28px -14px rgba(11, 18, 32, 0.22), inset 0 1px 0 rgba(255,255,255,0.9);
  flex-wrap: nowrap !important;
  gap: 10px !important;
}
.st-key-fg_topbar::after {
  content: ""; position: absolute; left: 18px; right: 18px; bottom: -1px; height: 1px;
  background: linear-gradient(90deg, transparent, var(--fg-accent-bright), transparent);
  opacity: 0.55; pointer-events: none;
}
.st-key-fg_topbar > div { width: auto !important; flex: 0 0 auto; }
.st-key-fg_topbar > div:has(.st-key-fg_links), .st-key-fg_topbar > .st-key-fg_links, .st-key-fg_topbar > div:has(.fg-clock) { margin-left: auto !important; }
.st-key-fg_topbar [data-testid="stMarkdownContainer"] p { margin: 0; }
.st-key-fg_topbar .st-key-fg_brand { flex: 0 0 auto; }
.st-key-fg_topbar .st-key-fg_links { flex: 1 1 auto !important; justify-content: center; }
.fg-brand { display: flex; align-items: center; gap: 10px; white-space: nowrap; }
.fg-brand-name { font-family: var(--fg-font-head); font-weight: 600; font-size: 16px; color: var(--fg-ink); letter-spacing: -0.01em; line-height: 1.1; }
.fg-brand-org { font-size: 11px; color: var(--fg-muted); line-height: 1.2; }
.fg-clock { font-family: var(--fg-font-mono); font-size: 11.5px; color: var(--fg-muted); white-space: nowrap; padding: 0 6px; }

/* Inline links */
.st-key-fg_links { gap: 2px !important; background: var(--fg-surface-2); border: 1px solid var(--fg-line); border-radius: 11px; padding: 3px !important; width: auto !important; flex-grow: 0 !important; margin: 0 auto; }
.st-key-fg_links [data-testid="stPageLink"] a,
.st-key-fg_links [data-testid="stPageLink-NavLink"] {
  padding: 5px 12px !important; border-radius: 8px !important; margin: 0 !important;
  background: transparent; transition: background .15s ease, color .15s ease;
}
.st-key-fg_links [data-testid="stPageLink-NavLink"] p,
.st-key-fg_links [data-testid="stPageLink-NavLink"] span { font-size: 13px !important; font-weight: 500 !important; color: var(--fg-ink-2) !important; }
.st-key-fg_links [data-testid="stPageLink-NavLink"]:hover { background: #FFFFFF !important; }
.st-key-fg_links [data-testid="stPageLink-NavLink"]:hover p { color: var(--fg-ink) !important; }
.st-key-fg_links [class*="st-key-navon_"] [data-testid="stPageLink-NavLink"] {
  background: #FFFFFF !important; box-shadow: 0 1px 2px rgba(11,18,32,.08), 0 0 0 1px var(--fg-line);
}
.st-key-fg_links [class*="st-key-navon_"] [data-testid="stPageLink-NavLink"] p { color: var(--fg-ink) !important; font-weight: 600 !important; }
.st-key-fg_links [class*="st-key-navon_"] [data-testid="stPageLink-NavLink"] p::before {
  content: ""; display: inline-block; width: 6px; height: 6px; border-radius: 50%;
  background: var(--fg-accent-bright); margin-right: 7px; vertical-align: 1px;
  box-shadow: 0 0 0 3px rgba(18,181,203,.18);
}

/* Menu button */
.st-key-fg_topbar [data-testid="stPopover"] button {
  background: var(--fg-ink) !important; color: #FFFFFF !important; border: 1px solid var(--fg-ink) !important;
  border-radius: 10px !important; min-height: 34px !important; padding: 4px 12px !important; box-shadow: none !important;
}
.st-key-fg_topbar [data-testid="stPopover"] button p { color: #FFFFFF !important; font-size: 13px !important; font-weight: 500 !important; }
.st-key-fg_topbar [data-testid="stPopover"] button svg, .st-key-fg_topbar [data-testid="stPopover"] button span { color: #FFFFFF !important; fill: #FFFFFF !important; }
.st-key-fg_topbar [data-testid="stPopover"] button:hover { background: #1B2537 !important; }

/* Popover panel = command palette */
[data-testid="stPopoverBody"] {
  min-width: 380px; max-width: 92vw; padding: 10px !important;
  border-radius: 14px !important; border: 1px solid var(--fg-line) !important;
  box-shadow: var(--fg-shadow-lg) !important;
  background: rgba(255,255,255,0.97) !important;
  animation: fgPop .16s cubic-bezier(.2,.8,.2,1);
}
@keyframes fgPop { from { opacity: 0; transform: translateY(-6px) scale(.985); } to { opacity: 1; transform: none; } }
.fg-pal-head { display:flex; justify-content:space-between; align-items:center; padding: 4px 6px 8px 6px; border-bottom: 1px solid var(--fg-line); margin-bottom: 4px; }
.fg-pal-title { font-family: var(--fg-font-mono); font-size: 10.5px; letter-spacing: .08em; text-transform: uppercase; color: var(--fg-muted); }
.fg-pal-foot { display:flex; justify-content:space-between; gap: 8px; padding: 8px 6px 2px 6px; border-top: 1px solid var(--fg-line); margin-top: 4px; font-size: 11px; color: var(--fg-muted); }
[class*="st-key-pal_"] { position: relative; border-radius: 10px; padding: 8px 10px 8px 44px !important; gap: 0 !important; transition: background .12s ease; }
[class*="st-key-pal_"] *:not(.fg-pal-ico):not(.fg-pal-count):not(svg):not(path):not(rect):not(circle) { position: static !important; }
[class*="st-key-pal_"] [data-testid="stMarkdownContainer"], .st-key-fg_topbar [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
[class*="st-key-pal_"] { padding-top: 9px !important; padding-bottom: 9px !important; }
[class*="st-key-pal_"]:hover { background: var(--fg-surface-2); }
[class*="st-key-pal_on_"] { background: var(--fg-accent-soft) !important; }
[class*="st-key-pal_"] [data-testid="stPageLink-NavLink"] { padding: 0 !important; margin: 0 !important; background: transparent !important; position: static !important; }
[class*="st-key-pal_"] [data-testid="stPageLink-NavLink"]::after { content: ""; position: absolute; inset: 0; border-radius: 10px; }
[class*="st-key-pal_"] [data-testid="stPageLink-NavLink"] p { font-family: var(--fg-font-head); font-size: 14px !important; font-weight: 600 !important; color: var(--fg-ink) !important; }
[class*="st-key-pal_"] [data-testid="stPageLink"] { margin: 0 !important; }
.fg-pal-ico { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); width: 26px; height: 26px; border-radius: 8px; border: 1px solid var(--fg-line); background: #FFFFFF; display: flex; align-items: center; justify-content: center; color: var(--fg-accent); }
.fg-pal-desc { font-size: 12px !important; color: var(--fg-muted); line-height: 1.35; margin-top: 1px; }
.fg-pal-count { position: absolute; right: 10px; top: 10px; font-family: var(--fg-font-mono); font-size: 10.5px; color: var(--fg-crit); background: var(--fg-crit-bg); border: 1px solid var(--fg-crit-line); padding: 1px 6px; border-radius: 6px; }
[data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] { gap: 2px; }

/* ---------- Page header ---------- */
.fg-page-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; padding: 4px 0 18px 0; margin-bottom: 18px; border-bottom: 1px solid var(--fg-line); }
.fg-eyebrow { font-family: var(--fg-font-mono); font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--fg-accent); margin-bottom: 6px; }
.fg-h1 { font-family: var(--fg-font-head) !important; font-size: 28px !important; font-weight: 600 !important; line-height: 1.15 !important; letter-spacing: -0.02em !important; margin: 0 !important; padding: 0 !important; color: var(--fg-ink) !important; }
.fg-sub { margin: 6px 0 0 0 !important; font-size: 14px !important; color: var(--fg-muted) !important; max-width: 720px; }
.fg-meta { display: flex; gap: 6px; flex-wrap: wrap; }
.fg-chip { display: inline-flex; align-items: center; gap: 6px; font-size: 11.5px; font-weight: 500; color: var(--fg-ink-2); background: var(--fg-surface); border: 1px solid var(--fg-line); padding: 4px 9px; border-radius: 8px; white-space: nowrap; }
.fg-chip b { font-family: var(--fg-font-mono); font-weight: 500; color: var(--fg-ink); }
.fg-chip-accent { color: var(--fg-accent); background: var(--fg-accent-soft); border-color: #C3E6EB; }
.fg-chip-ok { color: var(--fg-ok); background: var(--fg-ok-bg); border-color: var(--fg-ok-line); }
.fg-chip-warn { color: var(--fg-high); background: var(--fg-high-bg); border-color: var(--fg-high-line); }
.fg-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; display: inline-block; }

.fg-section { display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; margin: 10px 0 10px 0; }
.fg-h3 { font-family: var(--fg-font-head) !important; font-size: 17px !important; font-weight: 600 !important; margin: 0 !important; padding: 0 !important; color: var(--fg-ink) !important; }
.fg-section-sub { margin: 3px 0 0 0 !important; font-size: 12.5px !important; line-height: 1.45 !important; color: var(--fg-muted) !important; }

/* ---------- Surfaces ---------- */
.fg-card { background: var(--fg-surface); border: 1px solid var(--fg-line); border-radius: var(--fg-radius); padding: 16px 18px; box-shadow: var(--fg-shadow); margin-bottom: 14px; }
.fg-card-title { font-family: var(--fg-font-head); font-size: 15px; font-weight: 600; color: var(--fg-ink); margin: 0; }
.fg-card-sub { font-size: 12px; color: var(--fg-muted) !important; margin: 3px 0 10px 0 !important; }
div[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stVerticalBlock"][class*="st-key-"]:not([class*="st-key-fg_"]):not([class*="st-key-pal_"]):not([class*="st-key-nav"]) { border-radius: var(--fg-radius); }
[data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"][style*="border"],
div[data-testid="stVerticalBlockBorderWrapper"] { background: var(--fg-surface); border-color: var(--fg-line) !important; box-shadow: var(--fg-shadow); }

/* KPI tiles */
.fg-kpi { background: var(--fg-surface); border: 1px solid var(--fg-line); border-radius: var(--fg-radius); padding: 14px 16px 14px 16px; box-shadow: var(--fg-shadow); position: relative; overflow: hidden; margin-bottom: 8px; }
.fg-kpi::before { content: ""; position: absolute; left: 0; top: 14px; bottom: 14px; width: 3px; border-radius: 0 3px 3px 0; background: var(--kpi-c, var(--fg-accent)); }
.fg-kpi-label { display: flex; align-items: center; gap: 7px; font-size: 12.5px; color: var(--fg-muted); font-weight: 500; }
.fg-kpi-label .fg-ico { color: var(--kpi-c, var(--fg-accent)); }
.fg-kpi-row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-top: 8px; }
.fg-kpi-value { font-family: var(--fg-font-mono); font-size: 30px; font-weight: 500; color: var(--fg-ink); line-height: 1; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
.fg-kpi-delta { font-family: var(--fg-font-mono); font-size: 11px; color: var(--fg-muted); white-space: nowrap; }
.fg-kpi-delta b { color: var(--kpi-c, var(--fg-ink)); font-weight: 500; }

/* Status pills */
.fg-pill { display: inline-flex; align-items: center; gap: 6px; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; letter-spacing: .01em; border: 1px solid; white-space: nowrap; }
.fg-pill i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; display: inline-block; }
.fg-pill-crit { color: var(--fg-crit); background: var(--fg-crit-bg); border-color: var(--fg-crit-line); }
.fg-pill-high { color: var(--fg-high); background: var(--fg-high-bg); border-color: var(--fg-high-line); }
.fg-pill-watch { color: var(--fg-watch); background: var(--fg-watch-bg); border-color: var(--fg-watch-line); }
.fg-pill-ok { color: var(--fg-ok); background: var(--fg-ok-bg); border-color: var(--fg-ok-line); }
.fg-pill-neutral { color: var(--fg-ink-2); background: var(--fg-surface-2); border-color: var(--fg-line); }

/* Progress bars */
.progress-track { background: #EDF0F4; border-radius: 4px; overflow: hidden; display: inline-block; vertical-align: middle; }
.progress-fill { height: 100%; border-radius: 4px; }
.fill-critical { background: var(--fg-crit); } .fill-high { background: var(--fg-high); }
.fill-medium { background: #D4A106; } .fill-low { background: var(--fg-ok); }

/* Alerts list */
.alert-item { display: flex; align-items: flex-start; gap: 12px; padding: 10px 0; border-bottom: 1px solid #F0F2F6; }
.alert-item:last-child { border-bottom: none; }
.alert-bar { width: 3px; align-self: stretch; border-radius: 3px; flex-shrink: 0; }
.alert-content { flex: 1; min-width: 0; }
.alert-title { font-size: 13px !important; line-height: 1.35 !important; font-weight: 600; color: var(--fg-ink) !important; margin: 0 !important; }
.alert-subtitle { font-size: 12px !important; line-height: 1.35 !important; color: var(--fg-muted) !important; margin: 2px 0 0 0 !important; }
.alert-time { font-family: var(--fg-font-mono); font-size: 11px; color: var(--fg-faint); white-space: nowrap; }

/* Data grid used in cards */
.fg-kv { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px 18px; padding-top: 10px; border-top: 1px solid #F0F2F6; }
.fg-kv > div { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.fg-k { font-size: 11px; color: var(--fg-muted); text-transform: uppercase; letter-spacing: .05em; font-weight: 500; }
.fg-v { font-size: 13px; color: var(--fg-ink); font-weight: 500; }
.fg-v.mono { font-family: var(--fg-font-mono); font-weight: 500; }

/* ---------- Widgets ---------- */
label[data-testid="stWidgetLabel"] p, div[data-testid="stWidgetLabel"] p { color: var(--fg-ink-2) !important; font-weight: 500 !important; font-size: 12.5px !important; }
div[data-baseweb="select"] > div, div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input, textarea {
  background-color: #FFFFFF !important; border-color: var(--fg-line-strong) !important; border-radius: var(--fg-radius-sm) !important; color: var(--fg-ink) !important;
}
div[data-baseweb="select"] > div:focus-within, div[data-testid="stTextInput"] input:focus { border-color: var(--fg-accent) !important; box-shadow: 0 0 0 3px rgba(10,124,143,.14) !important; }
div[data-baseweb="popover"] ul[role="listbox"] { background: #FFFFFF !important; }
li[role="option"] { font-size: 13px !important; }
li[role="option"]:hover, li[role="option"][aria-selected="true"] { background-color: var(--fg-accent-soft) !important; color: var(--fg-ink) !important; }

div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button {
  border-radius: var(--fg-radius-sm) !important; font-weight: 500 !important; font-size: 13px !important;
  border: 1px solid var(--fg-line-strong) !important; background: #FFFFFF !important; color: var(--fg-ink) !important;
  box-shadow: var(--fg-shadow) !important; transition: border-color .15s ease, background .15s ease, color .15s ease !important;
}
div[data-testid="stButton"] button:hover, div[data-testid="stDownloadButton"] button:hover { border-color: var(--fg-accent) !important; color: var(--fg-accent) !important; }
div[data-testid="stButton"] button[kind="primary"], div[data-testid="stDownloadButton"] button[kind="primary"] {
  background: var(--fg-ink) !important; color: #FFFFFF !important; border-color: var(--fg-ink) !important;
}
div[data-testid="stButton"] button[kind="primary"] p, div[data-testid="stDownloadButton"] button[kind="primary"] p { color: #FFFFFF !important; }
div[data-testid="stButton"] button[kind="primary"]:hover, div[data-testid="stDownloadButton"] button[kind="primary"]:hover { background: var(--fg-accent) !important; border-color: var(--fg-accent) !important; color: #FFFFFF !important; }
div[data-testid="stButton"] button:disabled { opacity: .45 !important; }

/* Tabs */
div[data-testid="stTabs"] div[role="tablist"] { gap: 4px !important; border-bottom: 1px solid var(--fg-line) !important; }
div[data-testid="stTabs"] [role="tab"] { padding: 8px 2px !important; margin-right: 22px !important; background: transparent !important; }
div[data-testid="stTabs"] [role="tab"] p { font-family: var(--fg-font-body); font-size: 13.5px !important; font-weight: 500 !important; color: var(--fg-muted) !important; }
div[data-testid="stTabs"] [role="tab"][aria-selected="true"] p { color: var(--fg-ink) !important; font-weight: 600 !important; }
div[data-testid="stTabs"] [data-baseweb="tab-highlight"], div[data-testid="stTabs"] .react-aria-SelectionIndicator { background-color: var(--fg-accent) !important; height: 2px !important; }
div[data-testid="stTabs"] [role="tab"] { position: relative; }
div[data-testid="stTabs"] .react-aria-SelectionIndicator { position: absolute !important; left: 0; right: 0; bottom: -1px; }
div[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none; }

/* Expander */
div[data-testid="stExpander"] details { background: #FFFFFF !important; border: 1px solid var(--fg-line) !important; border-radius: var(--fg-radius) !important; box-shadow: var(--fg-shadow); }
div[data-testid="stExpander"] summary p { font-weight: 500 !important; font-size: 14px !important; color: var(--fg-ink) !important; }
div[data-testid="stExpander"] summary:hover p { color: var(--fg-accent) !important; }

/* Metrics */
div[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid var(--fg-line); border-radius: var(--fg-radius); padding: 12px 14px; box-shadow: var(--fg-shadow); }
div[data-testid="stMetricLabel"] p { font-size: 12.5px !important; color: var(--fg-muted) !important; font-weight: 500 !important; }
div[data-testid="stMetricValue"] { font-family: var(--fg-font-mono) !important; font-weight: 500 !important; font-size: 26px !important; color: var(--fg-ink) !important; }
div[data-testid="stMetricDelta"] { font-family: var(--fg-font-mono); font-size: 11.5px !important; }

/* Alerts / captions / dataframes */
div[data-testid="stAlert"] { border-radius: var(--fg-radius) !important; border: 1px solid var(--fg-line); }
div[data-testid="stCaptionContainer"] p, .stCaption p { color: var(--fg-muted) !important; font-size: 12px !important; }
div[data-testid="stDataFrame"] { border: 1px solid var(--fg-line); border-radius: var(--fg-radius); overflow: hidden; }
div[data-testid="stFileUploader"] section { background: #FFFFFF; border: 1px dashed var(--fg-line-strong); border-radius: var(--fg-radius); }
hr { border-color: var(--fg-line) !important; }
.fg-rule { border: none; border-top: 1px solid var(--fg-line); margin: 22px 0; }

/* Evidence media: the whole frame must always fit on screen */
.st-key-fg_evidence_video [data-testid="stVideo"], .st-key-fg_evidence_video video {
  display: block; max-height: 70vh !important; width: auto !important; max-width: 100% !important;
  margin: 0 auto; object-fit: contain; background: #0B1220; border-radius: 10px;
}
[data-testid="stImage"] img, [data-testid="stImageContainer"] img { max-height: 70vh; object-fit: contain; }

/* Ranking table buttons (corridor names) */
.st-key-ranking_table_box { background: #FFFFFF; border: 1px solid var(--fg-line); border-radius: var(--fg-radius); padding: 8px 12px 10px 12px; box-shadow: var(--fg-shadow); }
.st-key-ranking_table_box div[data-testid="stHorizontalBlock"] { gap: 6px !important; align-items: center !important; margin: 0 !important; padding: 1px 0 !important; border-bottom: 1px solid #F2F4F7; }
.st-key-ranking_table_box div[data-testid="stButton"] button {
  min-height: 28px !important; height: 28px !important; padding: 0 6px !important; border: none !important; background: transparent !important; box-shadow: none !important;
  justify-content: flex-start !important; text-align: left !important; overflow: hidden;
}
.st-key-ranking_table_box div[data-testid="stButton"] button > div { justify-content: flex-start !important; width: 100%; }
.st-key-ranking_table_box div[data-testid="stButton"] button p { text-align: left !important; font-size: 12.5px !important; font-weight: 500 !important; color: var(--fg-ink) !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.st-key-ranking_table_box div[data-testid="stButton"] button:hover { background: var(--fg-surface-2) !important; }
.st-key-ranking_table_box div[data-testid="stButton"] button[kind="primary"] { background: var(--fg-accent-soft) !important; box-shadow: inset 2px 0 0 var(--fg-accent) !important; border-radius: 0 6px 6px 0 !important; }
.st-key-ranking_table_box div[data-testid="stButton"] button[kind="primary"] p { color: var(--fg-accent) !important; font-weight: 600 !important; }
.fg-th { white-space: nowrap; font-size: 10.5px; font-weight: 500; color: var(--fg-muted); text-transform: uppercase; letter-spacing: .06em; }
.fg-num { font-family: var(--fg-font-mono); font-size: 12px; color: var(--fg-ink); font-variant-numeric: tabular-nums; }

/* ---------- Narrow screens ---------- */
@media (max-width: 900px) {
  .st-key-fg_links, .fg-clock, .st-key-fg_topbar > div:has(.st-key-fg_links), .st-key-fg_topbar > div:has(.fg-clock) { display: none !important; }
  .st-key-fg_topbar > div:has([data-testid="stPopover"]) { margin-left: auto !important; }
  .st-key-fg_topbar { justify-content: space-between !important; }
}
@media (max-width: 640px) {
  .st-key-ranking_table_box { overflow-x: auto; padding-bottom: 16px !important; }
  .st-key-ranking_table_box [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; min-width: 620px; }
  .st-key-ranking_table_box [data-testid="stColumn"] { min-width: 0 !important; width: auto !important; }
  .st-key-ranking_table_box [data-testid="stColumn"]:nth-child(1) { flex: 3.2 1 0 !important; }
  .st-key-ranking_table_box [data-testid="stColumn"]:nth-child(2) { flex: 1.2 1 0 !important; }
  .st-key-ranking_table_box [data-testid="stColumn"]:nth-child(3) { flex: 0.8 1 0 !important; }
  .st-key-ranking_table_box [data-testid="stColumn"]:nth-child(4) { flex: 1.1 1 0 !important; }
  .st-key-ranking_table_box [data-testid="stColumn"]:nth-child(5) { flex: 1.8 1 0 !important; }
  .st-key-ranking_table_box [data-testid="stColumn"]:nth-child(6) { flex: 0.9 1 0 !important; }
  [data-testid="stMainBlockContainer"], .block-container { padding-left: 16px !important; padding-right: 16px !important; padding-top: 84px !important; }
  .st-key-fg_topbar { top: 8px; width: calc(100% - 16px) !important; border-radius: 14px; }
  .fg-brand-org { display: none; }
  .fg-h1 { font-size: 22px !important; }
  [data-testid="stPopoverBody"] { min-width: calc(100vw - 32px); }
  .fg-kpi-value { font-size: 26px; }
}
</style>
"""
