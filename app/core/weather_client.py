"""WeatherAPI Integration Client.

Fetches live meteorological observations and precipitation forecasts for Pune
using the official WeatherAPI service.
"""

import time
import logging
import urllib.request
import urllib.parse
import json
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.config import settings

logger = logging.getLogger(__name__)

# WeatherAPI Base URL
WEATHERAPI_BASE_URL = "http://api.weatherapi.com/v1"

class HourlyForecast(BaseModel):
    time: str
    temp_c: float
    condition_text: str
    condition_icon: str
    precip_mm: float
    chance_of_rain: int
    will_it_rain: int

class PuneWeatherData(BaseModel):
    location_name: str = "Pune"
    region: str = "Maharashtra"
    country: str = "India"
    lat: float = 18.5204
    lon: float = 73.8567
    temp_c: float = 24.0
    feelslike_c: float = 24.5
    condition_text: str = "Partly cloudy"
    condition_icon: str = "//cdn.weatherapi.com/weather/64x64/day/116.png"
    humidity: int = 75
    precip_mm: float = 0.0
    cloud: int = 50
    wind_kph: float = 10.0
    daily_chance_of_rain: int = 40
    max_rain_chance: int = 45
    total_precip_mm: float = 1.2
    is_live: bool = False
    last_updated: str = ""
    hourly_forecast: List[HourlyForecast] = Field(default_factory=list)

# In-memory cache to respect API rate limits and avoid UI lag
_CACHE: Dict[str, Any] = {
    "timestamp": 0.0,
    "data": None
}
CACHE_TTL_SECONDS = 300  # 5 minutes cache

def fetch_live_pune_weather(force_refresh: bool = False) -> PuneWeatherData:
    """Fetch live Pune weather forecast from WeatherAPI with in-memory caching.
    
    Falls back gracefully to realistic baseline telemetry if offline or unconfigured.
    """
    global _CACHE
    now = time.time()
    
    # Check cache unless forced
    if not force_refresh and _CACHE["data"] is not None and (now - _CACHE["timestamp"]) < CACHE_TTL_SECONDS:
        return _CACHE["data"]

    api_key = settings.WEATHER_API_KEY.strip()
    if not api_key:
        logger.warning("No WEATHER_API_KEY configured. Returning fallback Pune weather.")
        return _get_fallback_weather("API Key not configured")

    try:
        query_params = urllib.parse.urlencode({
            "key": api_key,
            "q": "Pune",
            "days": 1,
            "aqi": "no",
            "alerts": "yes"
        })
        url = f"{WEATHERAPI_BASE_URL}/forecast.json?{query_params}"
        
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "FloodGuard-PMC-Intelligence/1.0"}
        )
        
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status != 200:
                logger.error(f"WeatherAPI error: HTTP {response.status}")
                return _get_fallback_weather(f"HTTP {response.status}")
            
            raw_payload = json.loads(response.read().decode("utf-8"))
            
            curr = raw_payload.get("current", {})
            loc = raw_payload.get("location", {})
            fday = raw_payload.get("forecast", {}).get("forecastday", [{}])[0]
            day_info = fday.get("day", {})
            raw_hours = fday.get("hour", [])
            
            hourly_list: List[HourlyForecast] = []
            max_chance = int(day_info.get("daily_chance_of_rain", 0))
            
            for h in raw_hours:
                h_chance = int(h.get("chance_of_rain", 0))
                if h_chance > max_chance:
                    max_chance = h_chance
                
                hourly_list.append(HourlyForecast(
                    time=h.get("time", "")[-5:],  # HH:MM
                    temp_c=float(h.get("temp_c", 22.0)),
                    condition_text=h.get("condition", {}).get("text", "Clear"),
                    condition_icon=h.get("condition", {}).get("icon", ""),
                    precip_mm=float(h.get("precip_mm", 0.0)),
                    chance_of_rain=h_chance,
                    will_it_rain=int(h.get("will_it_rain", 0))
                ))
            
            weather_obj = PuneWeatherData(
                location_name=loc.get("name", "Pune"),
                region=loc.get("region", "Maharashtra"),
                country=loc.get("country", "India"),
                lat=float(loc.get("lat", 18.5204)),
                lon=float(loc.get("lon", 73.8567)),
                temp_c=float(curr.get("temp_c", 22.0)),
                feelslike_c=float(curr.get("feelslike_c", 22.0)),
                condition_text=curr.get("condition", {}).get("text", "Overcast"),
                condition_icon=curr.get("condition", {}).get("icon", ""),
                humidity=int(curr.get("humidity", 70)),
                precip_mm=float(curr.get("precip_mm", 0.0)),
                cloud=int(curr.get("cloud", 50)),
                wind_kph=float(curr.get("wind_kph", 8.0)),
                daily_chance_of_rain=int(day_info.get("daily_chance_of_rain", 35)),
                max_rain_chance=max_chance,
                total_precip_mm=float(day_info.get("totalprecip_mm", 1.5)),
                is_live=True,
                last_updated=curr.get("last_updated", "Just now"),
                hourly_forecast=hourly_list
            )
            
            # Update cache
            _CACHE["timestamp"] = now
            _CACHE["data"] = weather_obj
            logger.info("Successfully fetched live WeatherAPI Pune data.")
            return weather_obj

    except Exception as e:
        logger.error(f"Failed to query WeatherAPI: {e}")
        return _get_fallback_weather(str(e))

def _get_fallback_weather(reason: str) -> PuneWeatherData:
    """Provide realistic Pune baseline weather when offline or on API failure."""
    hours: List[HourlyForecast] = []
    for hr in range(24):
        hours.append(HourlyForecast(
            time=f"{hr:02d}:00",
            temp_c=22.0 + (3.0 if 10 <= hr <= 16 else 0.0),
            condition_text="Scattered Showers",
            condition_icon="//cdn.weatherapi.com/weather/64x64/day/296.png",
            precip_mm=0.8 if 14 <= hr <= 20 else 0.1,
            chance_of_rain=55 if 14 <= hr <= 20 else 25,
            will_it_rain=1 if 14 <= hr <= 20 else 0
        ))
    
    return PuneWeatherData(
        location_name="Pune",
        region="Maharashtra",
        country="India",
        temp_c=23.5,
        feelslike_c=24.0,
        condition_text="Monsoon Precipitation Band",
        condition_icon="//cdn.weatherapi.com/weather/64x64/day/296.png",
        humidity=82,
        precip_mm=2.4,
        cloud=85,
        wind_kph=12.0,
        daily_chance_of_rain=65,
        max_rain_chance=78,
        total_precip_mm=14.5,
        is_live=False,
        last_updated=f"Simulated Baseline ({reason})",
        hourly_forecast=hours
    )
