"""Mutha river watch: Khadakwasla dam releases, read from the web by a TinyFish agent.

Riverside Pune floods when Khadakwasla dam releases water into the Mutha, even with no
local rain, and the release figures have no public API. A TinyFish Web Agent reads the
latest reported release from news search; the result is cached in
data/intel/river_watch.json and refreshed in the background, because a run takes ~1 min.

Only a release reported within RELEASE_CURRENT_DAYS counts as current. Older reports are
shown as "last reported" and never affect the flood forecast.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from app.config import settings
from app.core.prompts import KHADAKWASLA_RELEASE_GOAL
from app.core.tinyfish_client import run_web_agent

logger = logging.getLogger("civiceye.river_watch")

NEWS_SEARCH_URL = "https://www.bing.com/news/search?q=Khadakwasla+dam+discharge+cusecs&qft=sortbydate%3d%221%22"
CACHE_PATH = settings.DATA_DIR / "intel" / "river_watch.json"
CACHE_MAX_AGE_HOURS = 6
RELEASE_CURRENT_DAYS = 2

# Monitored locations on the Mutha (downstream of Khadakwasla). Aundh and Dapodi are on
# the Mula / Pavana and are not affected by this dam.
MUTHA_RIVERSIDE_IDS = {"LOC-06", "LOC-16", "LOC-09"}  # Deccan Gymkhana, Sangamwadi Bridge, Yerwada Bridge

# Approximate release bands (cusecs). Low causeways such as Baba Bhide bridge go under at
# around 10,000 cusecs; the 2019 floods followed releases of over 40,000.
RELEASE_BANDS = [
    (15000, "Flood release", "Critical"),
    (5000, "Riverbank alert", "High"),
    (1, "Release on", "Medium"),
]

RELEVANT_TERMS = re.compile(r"khadakwasla|mutha", re.I)

_refresh_lock = threading.Lock()
_refresh_thread: Optional[threading.Thread] = None


def release_band(cusecs: Optional[float]) -> Dict[str, str]:
    """Label and severity level for a release in cusecs (None or 0 means no release)."""
    for floor, label, level in RELEASE_BANDS:
        if cusecs and cusecs >= floor:
            return {"label": label, "level": level}
    return {"label": "No release", "level": "Low"}


def river_inflow_pct_per_hour(cusecs: Optional[float]) -> float:
    """Extra conduit saturation (% per hour) a release pushes into Mutha riverside outfalls.

    Backflow from a high river stops outfalls draining; 2,500 cusecs adds 1 %/h, capped at 8 %/h.
    """
    if not cusecs or cusecs <= 0:
        return 0.0
    return round(min(8.0, cusecs / 2500.0), 2)


def _parse_date(value: Any) -> Optional[date]:
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def summarise_reports(raw_reports: List[Dict[str, Any]], today: date) -> Dict[str, Any]:
    """Turn the agent's report list into the latest figure and whether it is current."""
    reports = []
    for r in raw_reports or []:
        # Search results include other dams (e.g. on the Cauvery); keep only this river system
        if not RELEVANT_TERMS.search(f"{r.get('headline') or ''} {r.get('url') or ''}"):
            continue
        d = _parse_date(r.get("date"))
        if d is None or d > today + timedelta(days=1):
            continue
        cusecs = r.get("discharge_cusecs")
        try:
            cusecs = float(cusecs) if cusecs not in (None, "") else None
        except (TypeError, ValueError):
            cusecs = None
        reports.append({
            "date": d.isoformat(),
            "discharge_cusecs": cusecs,
            "headline": str(r.get("headline") or "").strip(),
            "source": str(r.get("source") or "").strip(),
            "url": str(r.get("url") or "").strip(),
        })
    reports.sort(key=lambda r: r["date"], reverse=True)

    with_figure = [r for r in reports if r["discharge_cusecs"]]
    latest = with_figure[0] if with_figure else None
    current = bool(latest and (today - _parse_date(latest["date"])).days <= RELEASE_CURRENT_DAYS)
    current_cusecs = latest["discharge_cusecs"] if current else 0.0
    return {
        "reports": reports,
        "latest": latest,
        "current": current,
        "current_cusecs": current_cusecs,
        "band": release_band(current_cusecs),
        "inflow_pct_per_hour": river_inflow_pct_per_hour(current_cusecs),
    }


def _read_cache() -> Optional[Dict[str, Any]]:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def refresh_river_watch() -> Dict[str, Any]:
    """Run the TinyFish agent now (about a minute) and update the cache.

    A failed run keeps the previous good reports and records the error.
    """
    today = date.today()
    run = run_web_agent(NEWS_SEARCH_URL, KHADAKWASLA_RELEASE_GOAL.format(today=today.isoformat()))
    previous = _read_cache() or {}
    entry: Dict[str, Any] = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "status": run["status"],
        "error": run.get("error"),
        "steps": run.get("steps", []),
        "run_id": run.get("run_id"),
        "raw_reports": previous.get("raw_reports", []),
    }
    if run["status"] == "ok":
        result = run.get("result") or {}
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except ValueError:
                result = {}
        entry["raw_reports"] = result.get("reports", []) if isinstance(result, dict) else []
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    return get_river_watch()


def _is_stale(entry: Optional[Dict[str, Any]]) -> bool:
    if not entry or not entry.get("checked_at"):
        return True
    try:
        age = datetime.now() - datetime.fromisoformat(entry["checked_at"])
    except ValueError:
        return True
    return age > timedelta(hours=CACHE_MAX_AGE_HOURS)


def refresh_in_background() -> bool:
    """Start a background refresh unless one is already running. Returns True if started."""
    global _refresh_thread
    with _refresh_lock:
        if _refresh_thread is not None and _refresh_thread.is_alive():
            return False

        def _run() -> None:
            try:
                refresh_river_watch()
            except Exception:  # never let a background refresh crash the app
                logger.exception("River watch refresh failed")

        _refresh_thread = threading.Thread(target=_run, name="river-watch-refresh", daemon=True)
        _refresh_thread.start()
        return True


def is_refreshing() -> bool:
    return _refresh_thread is not None and _refresh_thread.is_alive()


def get_river_watch(auto_refresh: bool = False) -> Dict[str, Any]:
    """Cached river watch, summarised for display and scoring. Never blocks on the agent.

    With auto_refresh, a stale or missing cache starts a background agent run.
    """
    entry = _read_cache()
    if auto_refresh and _is_stale(entry) and get_tinyfish_key_present():
        refresh_in_background()
    summary = summarise_reports((entry or {}).get("raw_reports", []), date.today())
    summary.update({
        "checked_at": (entry or {}).get("checked_at"),
        "status": (entry or {}).get("status", "never_run"),
        "error": (entry or {}).get("error"),
        "steps": (entry or {}).get("steps", []),
        "refreshing": is_refreshing(),
        "source_url": NEWS_SEARCH_URL,
    })
    return summary


def get_tinyfish_key_present() -> bool:
    from app.core.tinyfish_client import get_tinyfish_api_key

    return bool(get_tinyfish_api_key())
