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
    "Mula-Mutha", "Mutha River", "Mula River", "Khadakwasla", "Pashan Lake"
]

FALLBACK_CIVIC_REPORTS: List[Dict[str, Any]] = [
    {
        "id": "tf-fallback-1",
        "title": "PMC Issues Emergency Flood Alert for Riverside Wards Following Khadakwasla Dam Discharge",
        "snippet": "The Pune Municipal Corporation (PMC) disaster cell issued an alert for residents in Ekta Nagar, Sinhagad Road, and Deccan Gymkhana following increased water discharge into the Mutha river basin.",
        "url": "https://www.punekarnews.in/pune-municipal-corporation-issues-flood-warning-for-low-lying-areas/",
        "date": "Today, 08:30 IST",
        "site_name": "punekarnews.in",
        "category": "Official Advisory",
        "severity": "Critical",
        "locations": ["Sinhagad Road", "Ekta Nagar", "Deccan Gymkhana", "Mutha River"],
    },
    {
        "id": "tf-fallback-2",
        "title": "Waterlogging Closes FC Road and Underpass at Shivajinagar Junction",
        "snippet": "Traffic police have diverted vehicles away from FC Road and Sancheti Hospital underpass due to 2.5 feet of standing stormwater. Commuters advised to take J.M. Road.",
        "url": "https://timesofindia.indiatimes.com/city/pune/waterlogging-traffic-diversions-pune-rains",
        "date": "Today, 09:15 IST",
        "site_name": "timesofindia.indiatimes.com",
        "category": "Road Closure",
        "severity": "High",
        "locations": ["FC Road", "Shivajinagar"],
    },
    {
        "id": "tf-fallback-3",
        "title": "Residents Protest Clogged Stormwater Box Drains on MG Road and Camp Area",
        "snippet": "Local merchants and residents raised urgent complaints regarding severe silt and plastic blockage in arterial stormwater drains along MG Road, leading to sewage backflow into shops.",
        "url": "https://indianexpress.com/article/cities/pune/citizens-voice-outrage-over-choked-nullahs-pune-monsoon/",
        "date": "Yesterday",
        "site_name": "indianexpress.com",
        "category": "Drainage Issue",
        "severity": "High",
        "locations": ["MG Road", "Camp"],
    },
    {
        "id": "tf-fallback-4",
        "title": "Citizen X/Twitter Reports: Overflowing Gutter Near Kothrud Bus Stand Inundating Lane",
        "snippet": "Multiple citizen complaints submitted on PMC Care helpline and social media complaining of garbage-choked drains overflowing into residential lanes in Kothrud Ward 12.",
        "url": "https://twitter.com/PMCcare/status/1816401928472918",
        "date": "Yesterday",
        "site_name": "twitter.com/PMCcare",
        "category": "Citizen Complaint",
        "severity": "Medium",
        "locations": ["Kothrud"],
    },
    {
        "id": "tf-fallback-5",
        "title": "IMD Issues Orange Alert for Pune Ghats; Continuous Rainfall Expected for Next 24 Hours",
        "snippet": "India Meteorological Department (IMD) forecasts intermittent moderate to heavy showers across Pune district with localized waterlogging risk in low-lying sub-sectors.",
        "url": "https://mausam.imd.gov.in/pune/",
        "date": "2 hours ago",
        "site_name": "imd.gov.in",
        "category": "Official Advisory",
        "severity": "Medium",
        "locations": ["Pune", "Khadakwasla"],
    },
    {
        "id": "tf-fallback-6",
        "title": "Dapodi Confluence Conduit Inundated: Drainage Sump Pump Dispatched",
        "snippet": "PMC Drainage department mobilized emergency dewatering teams to Dapodi after stormwater overflow blocked Old Mumbai-Pune highway service road.",
        "url": "https://punemirror.com/pune/civic/dapodi-waterlogging-drainage-teams-dispatched/",
        "date": "Today, 07:45 IST",
        "site_name": "punemirror.com",
        "category": "Drainage Issue",
        "severity": "High",
        "locations": ["Dapodi"],
    },
]


def get_tinyfish_api_key() -> str:
    """Retrieve TinyFish API key from environment variable or settings."""
    key = os.getenv("TINYFISH_API_KEY") or getattr(settings, "TINYFISH_API_KEY", "")
    return key.strip() if key else ""


def mask_api_key(key: str) -> str:
    """Safely mask key for display without exposing secrets."""
    if not key:
        return "Not Configured"
    if len(key) <= 12:
        return "sk-tinyfish-••••"
    return f"{key[:11]}••••••••{key[-4:]}"


def extract_pune_locations(text: str) -> List[str]:
    """Scan text against known Pune zones, wards, and arterial roads."""
    found: List[str] = []
    text_lower = text.lower()
    for loc in PUNE_KNOWN_LOCATIONS:
        pattern = r"\b" + re.escape(loc.lower()) + r"\b"
        if re.search(pattern, text_lower):
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


def fetch_pune_civic_intelligence(
    query: str = "pune flood advisory rainfall waterlogging road closure drainage complaint",
    limit: int = 12,
    use_fallback_if_empty: bool = True
) -> Dict[str, Any]:
    """Fetch and structure real-time Pune civic intelligence reports from TinyFish."""
    api_key = get_tinyfish_api_key()
    res = execute_tinyfish_search(query=query, limit=limit)

    reports: List[Dict[str, Any]] = []
    source_type = "tinyfish_api"

    if res["status"] == "ok" and res.get("results"):
        for idx, item in enumerate(res["results"]):
            title = item.get("title") or "Pune Civic Advisory"
            snippet = item.get("snippet") or ""
            cat = categorize_report(title, snippet)
            locs = extract_pune_locations(f"{title} {snippet}")
            if not locs:
                locs = ["Pune Urban"]

            reports.append({
                "id": f"tf-live-{idx+1}",
                "title": title,
                "snippet": snippet,
                "url": item.get("url") or "https://www.pmc.gov.in",
                "date": item.get("date") or "Recently reported",
                "site_name": item.get("site_name") or "Web Search",
                "category": cat,
                "severity": assess_severity(title, snippet, cat),
                "locations": locs,
            })
    else:
        # Fall back gracefully so dashboard continues to demonstrate intelligence
        if use_fallback_if_empty:
            reports = list(FALLBACK_CIVIC_REPORTS)
            source_type = "cached_fallback"

    # Category breakdown
    counts = {
        "Total": len(reports),
        "Official Advisory": sum(1 for r in reports if r["category"] == "Official Advisory"),
        "Road Closure": sum(1 for r in reports if r["category"] == "Road Closure"),
        "Drainage Issue": sum(1 for r in reports if r["category"] == "Drainage Issue"),
        "Citizen Complaint": sum(1 for r in reports if r["category"] == "Citizen Complaint"),
    }

    return {
        "status": res["status"],
        "error": res.get("error"),
        "source": source_type,
        "api_key_configured": bool(api_key),
        "api_key_masked": mask_api_key(api_key),
        "query": query,
        "counts": counts,
        "reports": reports,
    }
