"""TinyFish API client for real-time civic intelligence and citizen web complaints.

Interacts with the official TinyFish Web Search API (https://api.search.tinyfish.ai)
to discover current Pune-specific municipal flood alerts, rainfall advisories,
drainage complaints, and road closures.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional
import requests
from app.config import settings

logger = logging.getLogger("civiceye.tinyfish")

TINYFISH_SEARCH_ENDPOINT = "https://api.search.tinyfish.ai"
REQUEST_TIMEOUT_SECONDS = 12

# Common Pune locations and municipal landmarks to detect in report text
PUNE_KNOWN_LOCATIONS = [
    "MG Road", "FC Road", "Fergusson College Road", "Deccan Gymkhana", "Deccan",
    "Sinhagad Road", "Sinhgad Road", "Ekta Nagar", "Vitthal Nagar", "Nimbhan Nagar",
    "Dapodi", "Sangamwadi", "Kothrud", "Hadapsar", "Viman Nagar", "Katraj",
    "Baner", "Balewadi", "Hinjawadi", "Hinjewadi", "Yerwada", "Yerawada",
    "Bavdhan", "Swargate", "Shivajinagar", "Shivaji Nagar", "Karve Nagar",
    "Aundh", "Pashan", "Camp", "Koregaon Park", "Kalyani Nagar", "Khadki",
    "Bibvewadi", "Dhankawadi", "Warje", "Wakad", "Pimpri", "Chinchwad",
    "Bhosari", "Nigdi", "Kasba Peth", "Budhwar Peth", "Bund Garden",
    "Mula-Mutha", "Mutha River", "Mula River", "Khadakwasla", "Pashan Lake",
    "Dighi", "Dighigaon", "Chakan", "Alandi", "Wagholi", "Manjri",
    "Kondhwa", "Undri", "Vadgaon Sheri", "Lohegaon", "Dhanori", "Vishrantwadi"
]

# Fallback list is strictly empty - no fake or hardcoded mock reports are permitted
FALLBACK_CIVIC_REPORTS: List[Dict[str, Any]] = []



def get_tinyfish_api_key() -> str:
    """Retrieve TinyFish API key from environment variable or settings."""
    key = (
        os.getenv("TINYFISH_API_KEY")
        or os.getenv("tinyfishapikey")
        or getattr(settings, "TINYFISH_API_KEY", "")
    )
    return key.strip() if key else ""


def mask_api_key(key: str) -> str:
    """Safely mask key for display without exposing secrets."""
    if not key:
        return "Not Configured"
    if len(key) <= 12:
        return "sk-tinyfish-••••"
    return f"{key[:11]}••••••••{key[-4:]}"


def extract_pune_locations(text: str, query_keyword: str = "") -> List[str]:
    """Scan text against known Pune zones, wards, and arterial roads."""
    found: List[str] = []
    text_lower = text.lower()

    if query_keyword and query_keyword.strip():
        qk = query_keyword.strip().lower()
        if qk in text_lower:
            found.append(query_keyword.strip().title())

    for loc in PUNE_KNOWN_LOCATIONS:
        pattern = r"\b" + re.escape(loc.lower()) + r"\b"
        if re.search(pattern, text_lower) and loc not in found and loc.title() not in found:
            found.append(loc)
    return found[:4]


def categorize_report(title: str, snippet: str) -> str:
    """Determine category from title and snippet keywords."""
    combined = f"{title} {snippet}".lower()
    if any(k in combined for k in ["road closed", "road closure", "traffic divert", "traffic diversion", "submerged road", "underpass closed"]):
        return "Road Closure"
    if any(k in combined for k in ["complaint", "resident", "citizen", "grievance", "outrage", "protest", "helpline", "twitter"]):
        return "Citizen Complaint"
    if any(k in combined for k in ["alert", "warning", "advisory", "pmc issues", "imd", "emergency", "discharge"]):
        return "Official Advisory"
    if any(k in combined for k in ["drain", "nullah", "culvert", "choked", "clogged", "sewer", "gutter", "overflowing"]):
        return "Drainage Issue"
    return "Official Advisory"


def assess_severity(title: str, snippet: str, category: str) -> str:
    """Assign severity rating based on keywords and category."""
    combined = f"{title} {snippet}".lower()
    if any(k in combined for k in ["flood alert", "evacuat", "dam discharge", "submerged", "critical", "danger mark"]):
        return "Critical"
    if category in ["Road Closure", "Drainage Issue"] or any(k in combined for k in ["severe", "heavy", "closed", "inundat", "overflow"]):
        return "High"
    if any(k in combined for k in ["moderate", "yellow alert", "advisory", "slow traffic"]):
        return "Medium"
    return "Low"


PUNE_LOCATION_ALIASES: Dict[str, List[str]] = {
    "sinhagad": ["sinhagad", "sinhgad"],
    "sinhgad": ["sinhagad", "sinhgad"],
    "dighi": ["dighi", "dighigaon"],
    "dighigaon": ["dighi", "dighigaon"],
    "fc road": ["fc road", "fergusson"],
    "fergusson": ["fc road", "fergusson"],
    "deccan": ["deccan", "deccan gymkhana"],
    "kothrud": ["kothrud"],
    "baner": ["baner"],
    "hadapsar": ["hadapsar"],
    "hinjawadi": ["hinjawadi", "hinjewadi"],
    "hinjewadi": ["hinjawadi", "hinjewadi"],
    "shivajinagar": ["shivajinagar", "shivaji nagar"],
    "viman nagar": ["viman nagar", "vimannagar"],
    "katraj": ["katraj"],
    "swargate": ["swargate"],
    "karve": ["karve road", "karve nagar", "karvenagar"],
    "aundh": ["aundh"],
    "pashan": ["pashan"],
    "wakad": ["wakad"],
    "bavdhan": ["bavdhan"],
}


def is_video_report(url: str, title: str = "") -> bool:
    """Check if a URL or title represents video footage, reel, or broadcast."""
    u = (url or "").lower()
    t = (title or "").lower()
    return (
        any(k in u for k in ["youtube.com", "youtu.be", "/reel/", "/videos/", "videoshow", "shorts"])
        or any(k in t for k in ["video", "reel", "footage", "live", "watch"])
    )


def get_embed_video_url(url: str) -> Optional[str]:
    """Return embeddable video URL for Streamlit st.video if supported."""
    if not url:
        return None
    u = url.strip()
    if "youtube.com/shorts/" in u:
        return u.replace("youtube.com/shorts/", "youtube.com/watch?v=")
    if "youtube.com/watch" in u or "youtu.be/" in u:
        return u
    if u.endswith((".mp4", ".webm", ".ogg")):
        return u
    return None


def execute_tinyfish_search(query: str, limit: int = 10) -> Dict[str, Any]:
    """Perform a live HTTP query against TinyFish Search API."""
    api_key = get_tinyfish_api_key()
    if not api_key:
        return {
            "status": "missing_key",
            "error": "TINYFISH_API_KEY is not set in environment or .env",
            "results": [],
        }

    headers = {
        "X-API-Key": api_key,
        "Accept": "application/json",
        "User-Agent": "CivicEye-FloodGuard/1.0",
    }
    params = {
        "query": query,
    }

    try:
        response = requests.get(
            TINYFISH_SEARCH_ENDPOINT,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            data = response.json()
            raw_results = data.get("results", [])[:limit]
            return {
                "status": "ok",
                "error": None,
                "query": query,
                "total_results": data.get("total_results", len(raw_results)),
                "results": raw_results,
            }
        elif response.status_code in (401, 403):
            logger.warning("TinyFish API authentication failed (HTTP %s)", response.status_code)
            return {
                "status": "auth_error",
                "error": f"Invalid or expired TinyFish API key (HTTP {response.status_code})",
                "results": [],
            }
        else:
            logger.warning("TinyFish API error (HTTP %s): %s", response.status_code, response.text[:200])
            return {
                "status": "api_error",
                "error": f"TinyFish Search API responded with status {response.status_code}",
                "results": [],
            }
    except requests.RequestException as e:
        logger.error("TinyFish network request failed: %s", e)
        return {
            "status": "network_error",
            "error": f"Network connection to TinyFish API failed: {str(e)}",
            "results": [],
        }


TINYFISH_AGENT_ENDPOINT = "https://agent.tinyfish.ai/v1/automation/run-sse"
AGENT_TIMEOUT_SECONDS = 240


def run_web_agent(url: str, goal: str, timeout: int = AGENT_TIMEOUT_SECONDS) -> Dict[str, Any]:
    """Run a TinyFish Web Agent: a cloud browser opens `url` and carries out `goal`.

    Streams the run's server-sent events and returns
    {"status": "ok", "result": <JSON the agent produced>, "steps": [...], "run_id": str}
    or {"status": <error kind>, "error": str}. A run typically takes 30-90 seconds.
    """
    import json

    api_key = get_tinyfish_api_key()
    if not api_key:
        return {"status": "missing_key", "error": "TINYFISH_API_KEY is not set in .env"}

    steps: List[str] = []
    run_id = None
    try:
        with requests.post(
            TINYFISH_AGENT_ENDPOINT,
            headers={"X-API-Key": api_key, "Content-Type": "application/json", "Accept": "text/event-stream"},
            json={"url": url, "goal": goal},
            stream=True,
            timeout=(15, timeout),
        ) as response:
            if response.status_code in (401, 403):
                return {"status": "auth_error", "error": f"TinyFish rejected the API key (HTTP {response.status_code})"}
            if response.status_code != 200:
                return {"status": "api_error", "error": f"TinyFish agent responded with HTTP {response.status_code}"}
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                try:
                    event = json.loads(line[5:].strip())
                except ValueError:
                    continue
                run_id = event.get("run_id", run_id)
                if event.get("type") == "PROGRESS" and event.get("purpose"):
                    steps.append(event["purpose"])
                elif event.get("type") == "COMPLETE":
                    if event.get("status") != "COMPLETED":
                        return {"status": "agent_failed", "error": event.get("error") or f"Agent run ended {event.get('status')}",
                                "steps": steps, "run_id": run_id}
                    return {"status": "ok", "result": event.get("result"), "steps": steps, "run_id": run_id}
        return {"status": "agent_failed", "error": "Agent stream ended without a result", "steps": steps, "run_id": run_id}
    except requests.RequestException as e:
        logger.error("TinyFish agent request failed: %s", e)
        return {"status": "network_error", "error": f"TinyFish agent request failed: {e}", "steps": steps, "run_id": run_id}


def fetch_pune_civic_intelligence(
    query: str = "pune flood advisory rainfall waterlogging road closure drainage complaint",
    limit: int = 15,
    use_fallback_if_empty: bool = False,
    location_filter: str = "",
) -> Dict[str, Any]:
    """Fetch and structure real-time Pune civic intelligence reports from TinyFish Search API.
    
    Strictly queries live web search results. Never injects hardcoded fake news stories.
    """
    api_key = get_tinyfish_api_key()
    loc_clean = location_filter.strip().lower() if location_filter else ""

    raw_candidates: List[Dict[str, Any]] = []
    seen_urls: set = set()
    last_status = "missing_key"
    last_error = None

    if loc_clean:
        # Search both general alerts and video footage for maximum locality coverage
        q_general = f"{loc_clean} pune waterlogging flood rain drainage road"
        q_video = f"{loc_clean} pune waterlogging video footage"
        
        res1 = execute_tinyfish_search(query=q_video, limit=12)
        res2 = execute_tinyfish_search(query=q_general, limit=12)
        
        last_status = res1["status"] if res1["status"] != "missing_key" else res2["status"]
        last_error = res1.get("error") or res2.get("error")
        
        for r in (res1.get("results", []) + res2.get("results", [])):
            u = r.get("url")
            if u and u not in seen_urls:
                seen_urls.add(u)
                raw_candidates.append(r)
    else:
        res = execute_tinyfish_search(query=query, limit=limit)
        last_status = res["status"]
        last_error = res.get("error")
        raw_candidates = res.get("results", [])

    reports: List[Dict[str, Any]] = []
    source_type = "tinyfish_live" if last_status == "ok" else last_status

    if last_status == "ok" and raw_candidates:
        if loc_clean:
            aliases = PUNE_LOCATION_ALIASES.get(loc_clean, [loc_clean])
            
            filtered_candidates = []
            for item in raw_candidates:
                t_raw = item.get("title") or ""
                t_lower = t_raw.lower()
                s_lower = (item.get("snippet") or "").lower()
                full_text = f"{t_lower} {s_lower}"
                
                # Check whether item matches the queried location
                has_title_alias = any(a in t_lower for a in aliases)
                has_alias = any(a in full_text for a in aliases)
                
                if has_title_alias:
                    priority = 2
                elif has_alias:
                    priority = 1
                else:
                    priority = 0
                
                filtered_candidates.append((priority, item))
            
            # Prioritize items that explicitly mention the target locality
            mention_hits = [item for p, item in filtered_candidates if p > 0]
            if mention_hits:
                title_hits = [item for p, item in filtered_candidates if p == 2]
                snippet_hits = [item for p, item in filtered_candidates if p == 1]
                final_items = (title_hits + snippet_hits)[:limit]
            else:
                final_items = [item for _, item in filtered_candidates][:limit]
        else:
            final_items = raw_candidates[:limit]

        for idx, item in enumerate(final_items):
            title = item.get("title") or "Pune Civic Advisory"
            snippet = item.get("snippet") or ""
            url = item.get("url") or "https://www.pmc.gov.in"
            cat = categorize_report(title, snippet)
            is_vid = is_video_report(url, title)
            embed_url = get_embed_video_url(url)

            # Sanitize locations: strictly the entered place when filtered
            if loc_clean:
                loc_display = location_filter.strip().title()
                if "road" in title.lower() and not loc_display.lower().endswith("road"):
                    loc_display = f"{loc_display} Road"
                locs = [loc_display]
            else:
                locs = extract_pune_locations(f"{title} {snippet}", query_keyword=location_filter)
                if not locs:
                    locs = ["Pune Urban"]

            reports.append({
                "id": f"tf-live-{idx+1}",
                "title": title,
                "snippet": snippet,
                "url": url,
                "date": item.get("date") or "Recently reported",
                "site_name": item.get("site_name") or "Web Search",
                "category": cat,
                "severity": assess_severity(title, snippet, cat),
                "locations": locs,
                "is_video": is_vid,
                "embed_url": embed_url,
            })
    elif use_fallback_if_empty and FALLBACK_CIVIC_REPORTS:
        if loc_clean:
            aliases = PUNE_LOCATION_ALIASES.get(loc_clean, [loc_clean])
            reports = []
            for r in FALLBACK_CIVIC_REPORTS:
                combined_fb = (r["title"] + " " + r["snippet"]).lower()
                if any(a in combined_fb for a in aliases):
                    r_copy = dict(r)
                    r_copy["locations"] = [location_filter.strip().title()]
                    r_copy["is_video"] = is_video_report(r_copy["url"], r_copy["title"])
                    r_copy["embed_url"] = get_embed_video_url(r_copy["url"])
                    reports.append(r_copy)
        else:
            reports = []
            for r in FALLBACK_CIVIC_REPORTS:
                r_copy = dict(r)
                r_copy["is_video"] = is_video_report(r_copy["url"], r_copy["title"])
                r_copy["embed_url"] = get_embed_video_url(r_copy["url"])
                reports.append(r_copy)
        source_type = "cached_fallback"


    # Category breakdown strictly for matching reports
    counts = {
        "Total": len(reports),
        "Official Advisory": sum(1 for r in reports if r["category"] == "Official Advisory"),
        "Road Closure": sum(1 for r in reports if r["category"] == "Road Closure"),
        "Drainage Issue": sum(1 for r in reports if r["category"] == "Drainage Issue"),
        "Citizen Complaint": sum(1 for r in reports if r["category"] == "Citizen Complaint"),
        "Videos": sum(1 for r in reports if r.get("is_video")),
    }

    return {
        "status": last_status,
        "error": last_error,
        "source": source_type,
        "api_key_configured": bool(api_key),
        "api_key_masked": mask_api_key(api_key),
        "query": f"{loc_clean} pune alerts" if loc_clean else query,
        "location_filter": location_filter,
        "counts": counts,
        "reports": reports,
    }
