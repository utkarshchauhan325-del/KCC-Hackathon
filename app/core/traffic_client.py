"""TomTom Traffic Intelligence Client.

Fetches live road traffic flow, vehicle speed, and congestion data across
Pune municipal corridors using the official TomTom Traffic Flow API.
"""

import time
import logging
import urllib.request
import urllib.parse
import json
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field
from app.config import settings

logger = logging.getLogger(__name__)

TOMTOM_FLOW_BASE_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json"

class TrafficFlowData(BaseModel):
    location_id: str = ""
    current_speed_kmh: float = 25.0
    free_flow_kmh: float = 40.0
    current_travel_time_sec: int = 300
    free_flow_travel_time_sec: int = 240
    congestion_pct: int = 35
    traffic_level: str = "Moderate Flow"
    road_closure: bool = False
    confidence: float = 1.0
    is_live: bool = False
    last_updated: str = ""

# In-memory segment cache (point -> (timestamp, data))
_TRAFFIC_CACHE: Dict[str, Tuple[float, TrafficFlowData]] = {}
TRAFFIC_CACHE_TTL = 300  # 5 minutes

def fetch_point_traffic_flow(
    lat: float,
    lng: float,
    location_id: str = "",
    water_level_pct: float = 0.0,
    force_refresh: bool = False
) -> TrafficFlowData:
    """Fetch live traffic flow segment data for a specific geographic coordinate from TomTom."""
    cache_key = f"{lat:.4f},{lng:.4f},{int(water_level_pct)}"
    now = time.time()

    if not force_refresh and cache_key in _TRAFFIC_CACHE:
        ts, cached_data = _TRAFFIC_CACHE[cache_key]
        if (now - ts) < TRAFFIC_CACHE_TTL:
            return cached_data

    api_key = settings.TOMTOM_API_KEY.strip()
    if not api_key:
        logger.warning("TOMTOM_API_KEY is not configured. Returning fallback traffic.")
        return _get_fallback_traffic(lat, lng, location_id, water_level_pct, "API Key Missing")

    try:
        query_params = urllib.parse.urlencode({
            "key": api_key,
            "point": f"{lat},{lng}",
            "unit": "KMPH"
        })
        url = f"{TOMTOM_FLOW_BASE_URL}?{query_params}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "FloodGuard-Municipal-Intelligence/1.0"}
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                return _get_fallback_traffic(lat, lng, location_id, water_level_pct, f"HTTP {response.status}")

            payload = json.loads(response.read().decode("utf-8"))
            fs = payload.get("flowSegmentData", {})

            curr_speed = float(fs.get("currentSpeed", 25.0))
            free_speed = max(10.0, float(fs.get("freeFlowSpeed", 40.0)))
            curr_time = int(fs.get("currentTravelTime", 300))
            free_time = max(10, int(fs.get("freeFlowTravelTime", 240)))
            road_closed = bool(fs.get("roadClosure", False))
            conf = float(fs.get("confidence", 1.0))

            # Ratio of speed loss and travel time delay from TomTom
            speed_ratio = min(1.0, max(0.0, curr_speed / free_speed))
            time_delay_factor = min(1.0, max(0.0, (curr_time - free_time) / max(1, curr_time)))
            tomtom_jam = (1.0 - speed_ratio) * 70.0 + (time_delay_factor * 30.0)

            # Inundation surcharge factor:
            # Waterlogging onto carriage lanes reduces vehicle crawl speed
            if water_level_pct > 35.0:
                water_jam = ((water_level_pct - 35.0) / 65.0) * 88.0
            else:
                water_jam = 0.0

            raw_congestion = max(tomtom_jam, (tomtom_jam * 0.30 + water_jam * 0.70))
            if road_closed:
                raw_congestion = 99.0

            congestion_pct = min(99, max(5, int(round(raw_congestion))))

            # Effective speed considering road congestion
            effective_speed = round(max(6.0, free_speed * (1.0 - (congestion_pct / 115.0))), 1)
            effective_time = int(free_time * (1.0 + (congestion_pct / 40.0)))

            if road_closed or congestion_pct >= 75:
                traffic_level = "Gridlock (Severe)"
            elif congestion_pct >= 50:
                traffic_level = "Heavy Congestion"
            elif congestion_pct >= 25:
                traffic_level = "Moderate Flow"
            else:
                traffic_level = "Free Flow"

            flow_data = TrafficFlowData(
                location_id=location_id,
                current_speed_kmh=effective_speed,
                free_flow_kmh=round(free_speed, 1),
                current_travel_time_sec=effective_time,
                free_flow_travel_time_sec=free_time,
                congestion_pct=congestion_pct,
                traffic_level=traffic_level,
                road_closure=road_closed,
                confidence=conf,
                is_live=True,
                last_updated="TomTom Live Flow Sync"
            )

            _TRAFFIC_CACHE[cache_key] = (now, flow_data)
            return flow_data

    except Exception as e:
        logger.warning(f"TomTom API call failed for ({lat}, {lng}): {e}")
        return _get_fallback_traffic(lat, lng, location_id, water_level_pct, str(e))


def _get_fallback_traffic(lat: float, lng: float, location_id: str, water_level_pct: float = 0.0, reason: str = "") -> TrafficFlowData:
    """Generate realistic localized traffic metrics based on Pune corridor density and water level."""
    density_seed = int((lat * 1000) % 19 + (lng * 1000) % 23)
    base_congestion = int(25 + (density_seed * 2.5) % 45)
    
    if water_level_pct > 35:
        water_impact = ((water_level_pct - 35) / 65.0) * 85.0
        congestion_pct = min(98, max(base_congestion, int(base_congestion * 0.35 + water_impact * 0.65)))
    else:
        congestion_pct = min(90, max(12, base_congestion))

    free_speed = 45.0
    curr_speed = round(max(7.0, free_speed * (1.0 - (congestion_pct / 115.0))), 1)

    if congestion_pct >= 75:
        traffic_level = "Gridlock (Severe)"
    elif congestion_pct >= 50:
        traffic_level = "Heavy Congestion"
    elif congestion_pct >= 25:
        traffic_level = "Moderate Flow"
    else:
        traffic_level = "Free Flow"

    return TrafficFlowData(
        location_id=location_id,
        current_speed_kmh=curr_speed,
        free_flow_kmh=free_speed,
        current_travel_time_sec=int(250 * (1 + congestion_pct / 40.0)),
        free_flow_travel_time_sec=250,
        congestion_pct=congestion_pct,
        traffic_level=traffic_level,
        road_closure=False,
        confidence=0.85,
        is_live=False,
        last_updated=f"Model Baseline ({reason[:16]})"
    )

def fetch_bulk_traffic(locations: List[Dict[str, Any]], force_refresh: bool = False) -> Dict[str, TrafficFlowData]:
    """Fetch traffic flow data for municipal locations using TomTom Traffic Flow API.
    
    Coordinates are clustered or fetched concurrently with a thread pool to guarantee fast response
    times while keeping within safe API concurrency limits.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: Dict[str, TrafficFlowData] = {}
    
    def _worker(loc: Dict[str, Any]) -> Tuple[str, TrafficFlowData]:
        loc_id = loc.get("id", "")
        lat = float(loc.get("lat", 18.5204))
        lng = float(loc.get("lng", 73.8567))
        water_pct = float(loc.get("water_level_pct", 0.0))
        t_data = fetch_point_traffic_flow(lat, lng, location_id=loc_id, water_level_pct=water_pct, force_refresh=force_refresh)
        return loc_id, t_data

    # Use max 8 workers
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_worker, loc): loc.get("id", "") for loc in locations}
        for future in as_completed(futures):
            try:
                lid, data = future.result()
                results[lid] = data
            except Exception as ex:
                lid = futures[future]
                results[lid] = _get_fallback_traffic(18.5204, 73.8567, lid, 0.0, str(ex))

    return results


