"""Data models and dataset for Pune Municipal Corporation FloodGuard Intelligence."""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# 53 Municipal Monitoring Locations across Pune
PUNE_LOCATIONS: List[Dict[str, Any]] = [
    {
        "id": "LOC-01",
        "name": "MG Road Junction",
        "zone": "Central",
        "ward": "Ward 14 - Camp",
        "lat": 18.5186,
        "lng": 73.8785,
        "risk_level": "Critical",
        "risk_score": 92,
        "rainfall_3h": 38,
        "water_level_pct": 90,
        "trend_24h": "up",
        "status": "Waterlogging",
        "drain_type": "Box Culvert 1200mm",
        "blockage_pct": 78,
        "last_updated": "2 mins ago"
    },
    {
        "id": "LOC-02",
        "name": "FC Road Junction",
        "zone": "Central",
        "ward": "Ward 09 - Shivajinagar",
        "lat": 18.5255,
        "lng": 73.8415,
        "risk_level": "Critical",
        "risk_score": 87,
        "rainfall_3h": 32,
        "water_level_pct": 80,
        "trend_24h": "up",
        "status": "Waterlogging",
        "drain_type": "Stormwater Drain 900mm",
        "blockage_pct": 65,
        "last_updated": "3 mins ago"
    },
    {
        "id": "LOC-03",
        "name": "Swargate Metro",
        "zone": "Central",
        "ward": "Ward 18 - Swargate",
        "lat": 18.5018,
        "lng": 73.8586,
        "risk_level": "High",
        "risk_score": 76,
        "rainfall_3h": 28,
        "water_level_pct": 70,
        "trend_24h": "up",
        "status": "Rising",
        "drain_type": "Twin RCC Pipe 1000mm",
        "blockage_pct": 52,
        "last_updated": "5 mins ago"
    },
    {
        "id": "LOC-04",
        "name": "Pune Station Underpass",
        "zone": "Central",
        "ward": "Ward 12 - Railway Stn",
        "lat": 18.5284,
        "lng": 73.8744,
        "risk_level": "Medium",
        "risk_score": 58,
        "rainfall_3h": 18,
        "water_level_pct": 60,
        "trend_24h": "down",
        "status": "Normal",
        "drain_type": "Sump Pump Line 600mm",
        "blockage_pct": 34,
        "last_updated": "7 mins ago"
    },
    {
        "id": "LOC-05",
        "name": "Kothrud",
        "zone": "West",
        "ward": "Ward 22 - Kothrud North",
        "lat": 18.5074,
        "lng": 73.8077,
        "risk_level": "Medium",
        "risk_score": 52,
        "rainfall_3h": 16,
        "water_level_pct": 50,
        "trend_24h": "stable",
        "status": "Stable",
        "drain_type": "Open Nala Conduit",
        "blockage_pct": 28,
        "last_updated": "10 mins ago"
    },
    {
        "id": "LOC-06",
        "name": "Deccan Gymkhana",
        "zone": "Central",
        "ward": "Ward 10 - Deccan",
        "lat": 18.5167,
        "lng": 73.8410,
        "risk_level": "Critical",
        "risk_score": 89,
        "rainfall_3h": 34,
        "water_level_pct": 85,
        "trend_24h": "up",
        "status": "Waterlogging",
        "drain_type": "River Discharge Outfall",
        "blockage_pct": 72,
        "last_updated": "1 min ago"
    },
    {
        "id": "LOC-07",
        "name": "Khadki Bazar",
        "zone": "North",
        "ward": "Ward 04 - Khadki",
        "lat": 18.5642,
        "lng": 73.8340,
        "risk_level": "Medium",
        "risk_score": 55,
        "rainfall_3h": 20,
        "water_level_pct": 58,
        "trend_24h": "stable",
        "status": "Normal",
        "drain_type": "Stormwater Culvert",
        "blockage_pct": 30,
        "last_updated": "12 mins ago"
    },
    {
        "id": "LOC-08",
        "name": "Aundh Bridge",
        "zone": "West",
        "ward": "Ward 07 - Aundh",
        "lat": 18.5580,
        "lng": 73.8070,
        "risk_level": "Low",
        "risk_score": 24,
        "rainfall_3h": 12,
        "water_level_pct": 32,
        "trend_24h": "down",
        "status": "Normal",
        "drain_type": "Elevated Discharge Conduit",
        "blockage_pct": 15,
        "last_updated": "15 mins ago"
    },
    {
        "id": "LOC-09",
        "name": "Yerwada Bridge",
        "zone": "East",
        "ward": "Ward 15 - Yerwada",
        "lat": 18.5480,
        "lng": 73.8820,
        "risk_level": "Medium",
        "risk_score": 60,
        "rainfall_3h": 22,
        "water_level_pct": 62,
        "trend_24h": "up",
        "status": "Rising",
        "drain_type": "Riverbank Embankment Outfall",
        "blockage_pct": 40,
        "last_updated": "6 mins ago"
    },
    {
        "id": "LOC-10",
        "name": "Karve Nagar Canal",
        "zone": "West",
        "ward": "Ward 24 - Karve Nagar",
        "lat": 18.4910,
        "lng": 73.8180,
        "risk_level": "Low",
        "risk_score": 28,
        "rainfall_3h": 14,
        "water_level_pct": 35,
        "trend_24h": "stable",
        "status": "Normal",
        "drain_type": "Canal Feed Drain",
        "blockage_pct": 18,
        "last_updated": "14 mins ago"
    },
    {
        "id": "LOC-11",
        "name": "Hadapsar Gadital",
        "zone": "East",
        "ward": "Ward 28 - Hadapsar",
        "lat": 18.5020,
        "lng": 73.9280,
        "risk_level": "High",
        "risk_score": 75,
        "rainfall_3h": 29,
        "water_level_pct": 72,
        "trend_24h": "up",
        "status": "Rising",
        "drain_type": "Highway Drainage Trench",
        "blockage_pct": 58,
        "last_updated": "4 mins ago"
    },
    {
        "id": "LOC-12",
        "name": "Bibwewadi Lake Area",
        "zone": "South",
        "ward": "Ward 31 - Bibwewadi",
        "lat": 18.4720,
        "lng": 73.8610,
        "risk_level": "Low",
        "risk_score": 22,
        "rainfall_3h": 11,
        "water_level_pct": 30,
        "trend_24h": "down",
        "status": "Normal",
        "drain_type": "Detention Pond Feeder",
        "blockage_pct": 12,
        "last_updated": "18 mins ago"
    },
    {
        "id": "LOC-13",
        "name": "Kondhwa Khurd",
        "zone": "South",
        "ward": "Ward 35 - Kondhwa",
        "lat": 18.4680,
        "lng": 73.8890,
        "risk_level": "High",
        "risk_score": 72,
        "rainfall_3h": 27,
        "water_level_pct": 68,
        "trend_24h": "up",
        "status": "Rising",
        "drain_type": "Masonry Channel 800mm",
        "blockage_pct": 55,
        "last_updated": "8 mins ago"
    },
    {
        "id": "LOC-14",
        "name": "Pimpri Chinchwad Link",
        "zone": "North",
        "ward": "Ward 02 - PCMC Border",
        "lat": 18.6180,
        "lng": 73.8050,
        "risk_level": "Medium",
        "risk_score": 50,
        "rainfall_3h": 17,
        "water_level_pct": 52,
        "trend_24h": "stable",
        "status": "Normal",
        "drain_type": "Inter-Municipal Collector",
        "blockage_pct": 32,
        "last_updated": "20 mins ago"
    },
    {
        "id": "LOC-15",
        "name": "Dapodi River Confluence",
        "zone": "North",
        "ward": "Ward 05 - Dapodi",
        "lat": 18.5790,
        "lng": 73.8290,
        "risk_level": "Critical",
        "risk_score": 91,
        "rainfall_3h": 37,
        "water_level_pct": 88,
        "trend_24h": "up",
        "status": "Waterlogging",
        "drain_type": "Pavana-Mula Confluence Inflow",
        "blockage_pct": 80,
        "last_updated": "2 mins ago"
    },
    {
        "id": "LOC-16",
        "name": "Sangamwadi Bridge",
        "zone": "Central",
        "ward": "Ward 13 - Sangamwadi",
        "lat": 18.5370,
        "lng": 73.8680,
        "risk_level": "Critical",
        "risk_score": 88,
        "rainfall_3h": 35,
        "water_level_pct": 82,
        "trend_24h": "up",
        "status": "Waterlogging",
        "drain_type": "River Overflow Channel",
        "blockage_pct": 68,
        "last_updated": "4 mins ago"
    }
]

# Generate remaining to reach exact 53 locations across zones
ZONE_NAMES = ["Central", "West", "East", "North", "South"]
for i in range(17, 54):
    z = ZONE_NAMES[(i % len(ZONE_NAMES))]
    if i in [17, 21, 25, 29, 33, 37, 41, 45, 49, 53]:
        r_level = "High"
        r_score = 68 + (i % 8)
        rf = 25 + (i % 6)
        wl = 65 + (i % 12)
        tr = "up"
        st_text = "Rising"
    elif i % 3 == 0:
        r_level = "Medium"
        r_score = 48 + (i % 12)
        rf = 18 + (i % 5)
        wl = 45 + (i % 15)
        tr = "stable"
        st_text = "Normal"
    else:
        r_level = "Medium" if i % 2 == 0 else "Low"
        r_score = 30 + (i % 25)
        rf = 12 + (i % 7)
        wl = 30 + (i % 20)
        tr = "down" if r_level == "Low" else "stable"
        st_text = "Normal" if r_level == "Low" else "Stable"

    # Distribute geographically inside the actual municipal boundaries of the respective zone
    ZONE_BASES = {
        "Central": {"lat": 18.5200, "lng": 73.8550, "lat_span": 0.015, "lng_span": 0.018},
        "West":    {"lat": 18.5250, "lng": 73.7950, "lat_span": 0.025, "lng_span": 0.020},
        "East":    {"lat": 18.5300, "lng": 73.9250, "lat_span": 0.025, "lng_span": 0.025},
        "North":   {"lat": 18.5900, "lng": 73.8350, "lat_span": 0.022, "lng_span": 0.025},
        "South":   {"lat": 18.4650, "lng": 73.8600, "lat_span": 0.020, "lng_span": 0.022},
    }
    zb = ZONE_BASES[z]
    lat_offset = (((i * 17) % 100 - 50) / 50.0) * zb["lat_span"]
    lng_offset = (((i * 31) % 100 - 50) / 50.0) * zb["lng_span"]

    PUNE_LOCATIONS.append({
        "id": f"LOC-{i:02d}",
        "name": f"Sub-Sector {i} ({z} Ward {i % 20 + 1})",
        "zone": z,
        "ward": f"Ward {i % 20 + 1}",
        "lat": round(zb["lat"] + lat_offset, 4),
        "lng": round(zb["lng"] + lng_offset, 4),
        "risk_level": r_level,
        "risk_score": r_score,
        "rainfall_3h": rf,
        "water_level_pct": wl,
        "trend_24h": tr,
        "status": st_text,
        "drain_type": "Standard RCC Pipe",
        "blockage_pct": int(r_score * 0.7),
        "last_updated": f"{i % 30 + 1} mins ago"
    })

# Align counts exactly to image:
# 53 Total Locations:
# Critical: 5 (9%)
# High: 17 (32%)
# Medium: 23 (43%)
# Low: 8 (16%)
# Active waterlogging: 8
# Drainage risk: 23

# KPI Summary
KPIS = {
    "critical_locations": 5,
    "critical_diff": "+2",
    "high_risk_locations": 17,
    "high_risk_diff": "+4",
    "active_waterlogging": 8,
    "active_waterlogging_diff": "+1",
    "drainage_risk": 23,
    "drainage_risk_diff": "+6",
    "total_locations": 53
}

# 24h Rainfall Forecast Data (matches bar chart in screenshot)
RAINFALL_FORECAST = [
    {"hour": "Now", "rainfall_mm": 12},
    {"hour": "3h", "rainfall_mm": 34},
    {"hour": "6h", "rainfall_mm": 52},
    {"hour": "12h", "rainfall_mm": 74},
    {"hour": "24h", "rainfall_mm": 32}
]

# Water Level Trend Data (matches line chart in screenshot)
WATER_LEVEL_TREND = [
    {"time": "Now", "MG Road": 38, "FC Road": 28},
    {"time": "3h", "MG Road": 52, "FC Road": 36},
    {"time": "6h", "MG Road": 54, "FC Road": 40},
    {"time": "12h", "MG Road": 78, "FC Road": 60},
    {"time": "24h", "MG Road": 90, "FC Road": 58}
]

# Recent Alerts (matches list in screenshot)
RECENT_ALERTS = [
    {
        "id": "ALT-01",
        "severity": "critical",
        "title": "Heavy rainfall alert",
        "subtitle": "Pune region - IMD nowcast",
        "time": "12 min ago",
    },
    {
        "id": "ALT-02",
        "severity": "high",
        "title": "Water level rising",
        "subtitle": "Mula-Mutha River",
        "time": "28 min ago",
    },
    {
        "id": "ALT-03",
        "severity": "medium",
        "title": "Drainage blockage detected",
        "subtitle": "Deccan Gymkhana",
        "time": "1 hour ago",
    },
    {
        "id": "ALT-04",
        "severity": "medium",
        "title": "High risk at FC Road",
        "subtitle": "Risk score increased to 87",
        "time": "2 hours ago",
    }
]

# Municipal CCTV cameras. The first three are the assigned demo cameras: their scores are
# fixed to the results of analysing each camera's video, and the same numbers are shown
# under the camera on the CCTV page and for its linked location on the dashboard.
# To change a camera's figures, edit them here only.
CCTV_CAMERAS = [
    {
        "id": "CAM-PUNE-01",
        "name": "MG Road Main Cross",
        "zone": "Central",
        "status": "LIVE",
        "location_id": "LOC-01",  # MG Road Junction on the dashboard
        "video": "WhatsApp_Video_2026-10-08_at_1.37.27_AM.mp4",
        "drainage_score": 70,
        "garbage_score": 83,
        "composite_score": 61,
        "risk_level": "Critical",
        "garbage_coverage_pct": 55,
        "violations": 0,
        "water_depth_cm": 28,
        "blockage_index": 78,
        "ai_status": "Blocked drain and heavy garbage around the inlet",
        "lat": 18.5186,
        "lng": 73.8785,
        "stream_fps": 30,
        "incidents_today": 2
    },
    {
        "id": "CAM-PUNE-02",
        "name": "FC Road Ferguson College Gate",
        "zone": "Central",
        "status": "LIVE",
        "location_id": "LOC-02",  # FC Road Junction
        "video": "WhatsApp_Video_2026-10-08_at_1.36.15_AM.mp4",
        "drainage_score": None,  # no drain in view, so not assessed
        "garbage_score": 37,
        "composite_score": 14,
        "risk_level": "Low",
        "garbage_coverage_pct": 4,
        "violations": 1,
        "water_depth_cm": 6,
        "blockage_index": 35,
        "ai_status": "Garbage dumped from a vehicle at the roadside",
        "lat": 18.5255,
        "lng": 73.8415,
        "stream_fps": 30,
        "incidents_today": 2
    },
    {
        "id": "CAM-PUNE-03",
        "name": "Swargate Metro Multi-Modal Hub",
        "zone": "Central",
        "status": "LIVE",
        "location_id": "LOC-03",  # Swargate Metro
        "video": "",
        "drainage_score": 55,
        "garbage_score": 62,
        "composite_score": 47,
        "risk_level": "High",
        "garbage_coverage_pct": 12,
        "violations": 0,
        "water_depth_cm": 15,
        "blockage_index": 52,
        "ai_status": "Garbage near the storm inlet, slow runoff",
        "lat": 18.5018,
        "lng": 73.8586,
        "stream_fps": 28,
        "incidents_today": 1
    },
    {
        "id": "CAM-PUNE-04",
        "name": "Pune Railway Station Underpass",
        "zone": "Central",
        "status": "LIVE",
        "risk_level": "Medium",
        "water_depth_cm": 11,
        "blockage_index": 34,
        "ai_status": "Submersible Pumps Operating",
        "lat": 18.5284,
        "lng": 73.8744,
        "stream_fps": 30,
        "incidents_today": 1
    },
    {
        "id": "CAM-PUNE-05",
        "name": "Deccan Gymkhana River Outfall",
        "zone": "Central",
        "status": "LIVE",
        "risk_level": "Critical",
        "water_depth_cm": 26,
        "blockage_index": 72,
        "ai_status": "Sewer Surcharge Backflow",
        "lat": 18.5167,
        "lng": 73.8410,
        "stream_fps": 30,
        "incidents_today": 5
    },
    {
        "id": "CAM-PUNE-06",
        "name": "Karve Road Kothrud Flyover",
        "zone": "West",
        "status": "LIVE",
        "risk_level": "Medium",
        "water_depth_cm": 8,
        "blockage_index": 28,
        "ai_status": "Normal Surface Flow",
        "lat": 18.5074,
        "lng": 73.8077,
        "stream_fps": 30,
        "incidents_today": 0
    }
]

# Municipal Priority Queue (Matches badge count 3)
PRIORITY_QUEUE = [
    {
        "id": "INC-PMC-1082",
        "location": "MG Road Junction",
        "zone": "Central",
        "category": "Drainage & Sewer Surcharge",
        "reported_at": "12 mins ago",
        "severity": 5,
        "risk_score": 92,
        "review_status": "pending_review",
        "description": "Critical storm culvert blockage with 28cm water accumulation. Debris and plastic waste trapping drainage grate.",
        "assigned_crew": "Unit-04 Quick Reaction",
        "suggested_action": "Deploy 500 GPM Mobile Pump + Jetting Machine",
        "evidence_crop": "data/sample_crops/drain_blockage_01.jpg"
    },
    {
        "id": "INC-PMC-1083",
        "location": "FC Road Commercial Belt",
        "zone": "Central",
        "category": "Illegal Commercial Waste Dumping",
        "reported_at": "35 mins ago",
        "severity": 4,
        "risk_score": 87,
        "review_status": "pending_review",
        "description": "Commercial delivery mini-truck dumped bulky corrugated waste directly onto storm inlet. Suspect plate detected.",
        "plate_text": "MH 12 QX 4821",
        "assigned_crew": "Solid Waste Enforcement",
        "suggested_action": "Issue Municipal Fine Notice + Clear Inlet",
        "evidence_crop": "data/sample_crops/dumping_violator_01.jpg"
    },
    {
        "id": "INC-PMC-1084",
        "location": "Deccan Gymkhana Outfall",
        "zone": "Central",
        "category": "Mula-Mutha Backflow Alert",
        "reported_at": "54 mins ago",
        "severity": 5,
        "risk_score": 89,
        "review_status": "pending_review",
        "description": "River stage elevation exceeds sluice gate threshold by 0.35m. Flap gate choked by floating hyacinth.",
        "assigned_crew": "Hydraulic Drainage Division",
        "suggested_action": "Engage Flap Gate Clearance Crane",
        "evidence_crop": "data/sample_crops/river_backflow_01.jpg"
    }
]

# Active Operations & Interventions
OPERATIONS_INTERVENTIONS = [
    {
        "id": "OP-701",
        "type": "Mobile Dewatering Pump (500 GPM)",
        "location": "MG Road Junction",
        "status": "Deployed & Pumping",
        "crew_head": "S. Patil (Junior Engineer)",
        "units": 2,
        "water_discharged_m3": 1420,
        "eta_cleared": "45 mins"
    },
    {
        "id": "OP-702",
        "type": "High Pressure Silt Suction Tanker",
        "location": "FC Road Junction",
        "status": "En Route (ETA 8 mins)",
        "crew_head": "V. Kadam (Roads & Drainage)",
        "units": 1,
        "water_discharged_m3": 0,
        "eta_cleared": "1 hour 20 mins"
    },
    {
        "id": "OP-703",
        "type": "Traffic Police Diversion Protocol",
        "location": "Pune Station Underpass",
        "status": "Active Advisory",
        "crew_head": "Traffic Ward 3",
        "units": 4,
        "water_discharged_m3": 0,
        "eta_cleared": "Active until rainfall recedes"
    },
    {
        "id": "OP-704",
        "type": "Robotic Drain Inspection & Clearance",
        "location": "Deccan Gymkhana Sluice Gate",
        "status": "Operating",
        "crew_head": "Disaster Cell Engr. 2",
        "units": 1,
        "water_discharged_m3": 850,
        "eta_cleared": "30 mins"
    }
]

def get_all_attribute_ranked_locations(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Return all 53 Pune monitoring locations enriched with WeatherAPI precipitation,
    TomTom live traffic, and deterministic multi-attribute ranking across all 4 pillars
    (Precipitation mm, Traffic gridlock %, Conduit saturation %, and Blockage %).
    """
    from app.core.weather_client import fetch_live_pune_weather
    from app.core.scoring import rank_locations_by_all_attributes

    weather = fetch_live_pune_weather(force_refresh=force_refresh)
    ranked = rank_locations_by_all_attributes(
        locations=PUNE_LOCATIONS,
        weather_rain_chance=weather.max_rain_chance,
        weather_total_precip_mm=weather.next_24h_precip_mm,
        current_temp=weather.temp_c,
        humidity=weather.humidity,
        force_refresh_traffic=force_refresh,
        hourly_precip_mm=[h.precip_mm for h in weather.hourly_forecast],
    )
    return apply_camera_scores(ranked)


ASSIGNED_CAMERAS = [c for c in CCTV_CAMERAS if c.get("location_id")]
_CAMERA_BAND_TO_LEVEL = {"Critical": "Critical", "High": "High", "Watch": "Medium", "Low": "Low"}


def camera_for_location(location_id: str) -> Optional[Dict[str, Any]]:
    return next((c for c in ASSIGNED_CAMERAS if c["location_id"] == location_id), None)


def apply_camera_scores(locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Show a camera-covered location with the camera's own scores, then re-rank.

    Keeps the dashboard and the CCTV page on the same numbers.
    """
    for loc in locations:
        cam = camera_for_location(loc.get("id", ""))
        if cam is None:
            continue
        loc["composite_score"] = float(cam["composite_score"])
        loc["risk_score"] = int(cam["composite_score"])
        loc["risk_level"] = _CAMERA_BAND_TO_LEVEL.get(cam["risk_level"], cam["risk_level"])
        loc["blockage_pct"] = cam["blockage_index"]
        loc["cctv_camera"] = cam["id"]
        loc["status"] = cam["ai_status"]
    locations.sort(key=lambda x: (x["composite_score"], x.get("precip_mm", 0)), reverse=True)
    for idx, loc in enumerate(locations, 1):
        loc["priority_rank"] = idx
    return locations


def location_for_job(filename: Optional[str], source_gps: Optional[str]) -> Dict[str, Any]:
    """Best guess at the monitored location an analysed video came from.

    A video assigned to a camera maps to that camera's location; otherwise the
    nearest monitored location to the video's GPS; otherwise MG Road Junction.
    """
    by_id = {l["id"]: l for l in PUNE_LOCATIONS}
    for cam in ASSIGNED_CAMERAS:
        if cam.get("video") and filename == cam["video"]:
            return by_id[cam["location_id"]]
    if source_gps:
        try:
            lat, lng = (float(p.strip()) for p in source_gps.split(",")[:2])
            return min(PUNE_LOCATIONS, key=lambda l: (l["lat"] - lat) ** 2 + (l["lng"] - lng) ** 2)
        except ValueError:
            pass
    return PUNE_LOCATIONS[0]

def get_weather_adjusted_locations(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Return all 53 Pune monitoring locations ranked on the basis of all attributes."""
    return get_all_attribute_ranked_locations(force_refresh=force_refresh)

def get_busiest_traffic_corridor(locations: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Identify and return the single most busiest corridor across Pune based on TomTom traffic."""
    from app.core.scoring import get_busiest_location
    if locations is None:
        locations = get_all_attribute_ranked_locations()
    return get_busiest_location(locations)

def get_live_pune_kpis(locations: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Calculate dynamic KPIs from active weather and traffic adjusted location scores."""
    if locations is None:
        locations = get_weather_adjusted_locations()

    crit = sum(1 for l in locations if l.get("risk_level") == "Critical")
    high = sum(1 for l in locations if l.get("risk_level") == "High")
    waterlog = sum(1 for l in locations if "Waterlogging" in l.get("status", "") or l.get("water_level_pct", 0) >= 75)
    drain = sum(1 for l in locations if l.get("blockage_pct", 0) >= 50)

    return {
        "critical_locations": crit,
        "critical_diff": f"+{max(1, crit - 3)}",
        "high_risk_locations": high,
        "high_risk_diff": f"+{max(1, high - 12)}",
        "active_waterlogging": waterlog,
        "active_waterlogging_diff": f"+{max(1, waterlog - 5)}",
        "drainage_risk": drain,
        "drainage_risk_diff": f"+{max(1, drain - 18)}",
    }


