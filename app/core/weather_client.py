"""Live Pune weather for flood and overflow prediction.

Sources, in order:
1. WeatherAPI.com (needs WEATHER_API_KEY in .env)
2. Open-Meteo (free, no key) when WeatherAPI is unconfigured or fails
3. A fixed monsoon baseline when both are unreachable (marked is_live=False)

The forecast is always the next 24 hours from now (not "today"), so late-evening
requests still see tomorrow morning's rain.
"""

import json
import logging
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

WEATHERAPI_BASE_URL = "http://api.weatherapi.com/v1"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
PUNE_LAT, PUNE_LON = 18.5204, 73.8567


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
    lat: float = PUNE_LAT
    lon: float = PUNE_LON
    temp_c: float = 24.0
    feelslike_c: float = 24.5
    condition_text: str = "Partly cloudy"
    condition_icon: str = "//cdn.weatherapi.com/weather/64x64/day/116.png"
    humidity: int = 75
    precip_mm: float = 0.0
    cloud: int = 50
    wind_kph: float = 10.0
    daily_chance_of_rain: int = 40
    max_rain_chance: int = 45  # highest hourly chance of rain over the next 24 h
    total_precip_mm: float = 1.2  # forecast rain over the next 24 h
    next_6h_precip_mm: float = 0.0
    next_24h_precip_mm: float = 0.0
    is_live: bool = False
    source: str = "Baseline"
    last_updated: str = ""
    hourly_forecast: List[HourlyForecast] = Field(default_factory=list)


_CACHE: Dict[str, Any] = {"timestamp": 0.0, "data": None}
CACHE_TTL_SECONDS = 300


def fetch_live_pune_weather(force_refresh: bool = False) -> PuneWeatherData:
    """Return the current Pune weather and next-24 h forecast, cached for 5 minutes."""
    now = time.time()
    if not force_refresh and _CACHE["data"] is not None and (now - _CACHE["timestamp"]) < CACHE_TTL_SECONDS:
        return _CACHE["data"]

    weather: Optional[PuneWeatherData] = None
    errors: List[str] = []
    if settings.WEATHER_API_KEY.strip():
        try:
            weather = _fetch_weatherapi(settings.WEATHER_API_KEY.strip())
        except Exception as e:
            logger.error(f"WeatherAPI failed: {e}")
            errors.append(f"WeatherAPI: {e}")
    if weather is None:
        try:
            weather = _fetch_open_meteo()
        except Exception as e:
            logger.error(f"Open-Meteo failed: {e}")
            errors.append(f"Open-Meteo: {e}")
    if weather is None:
        return _get_fallback_weather("; ".join(errors) or "no weather source reachable")

    _CACHE["timestamp"] = now
    _CACHE["data"] = weather
    return weather


def _get_json(url: str) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "FloodGuard-PMC-Intelligence/1.0"})
    with urllib.request.urlopen(req, timeout=6) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def _next_24h(hours: List[HourlyForecast], stamps: List[datetime], now: datetime) -> List[HourlyForecast]:
    """Hours from the current hour onwards, at most 24."""
    start = now.replace(minute=0, second=0, microsecond=0)
    picked = [h for h, t in zip(hours, stamps) if t >= start]
    return picked[:24]


def _with_forecast_totals(w: PuneWeatherData) -> PuneWeatherData:
    hours = w.hourly_forecast
    w.next_6h_precip_mm = round(sum(h.precip_mm for h in hours[:6]), 1)
    w.next_24h_precip_mm = round(sum(h.precip_mm for h in hours), 1)
    w.total_precip_mm = w.next_24h_precip_mm
    if hours:
        w.max_rain_chance = max(h.chance_of_rain for h in hours)
    return w


def _fetch_weatherapi(api_key: str) -> PuneWeatherData:
    query = urllib.parse.urlencode({"key": api_key, "q": f"{PUNE_LAT},{PUNE_LON}", "days": 2, "aqi": "no", "alerts": "yes"})
    payload = _get_json(f"{WEATHERAPI_BASE_URL}/forecast.json?{query}")
    curr = payload.get("current", {})
    loc = payload.get("location", {})
    days = payload.get("forecast", {}).get("forecastday", [])

    hours: List[HourlyForecast] = []
    stamps: List[datetime] = []
    for day in days:
        for h in day.get("hour", []):
            stamps.append(datetime.strptime(h["time"], "%Y-%m-%d %H:%M"))
            hours.append(HourlyForecast(
                time=h.get("time", "")[-5:],
                temp_c=float(h.get("temp_c", 22.0)),
                condition_text=h.get("condition", {}).get("text", "Clear"),
                condition_icon=h.get("condition", {}).get("icon", ""),
                precip_mm=float(h.get("precip_mm", 0.0)),
                chance_of_rain=int(h.get("chance_of_rain", 0)),
                will_it_rain=int(h.get("will_it_rain", 0)),
            ))
    local_now = datetime.strptime(loc["localtime"], "%Y-%m-%d %H:%M") if loc.get("localtime") else datetime.now()
    today = days[0].get("day", {}) if days else {}

    return _with_forecast_totals(PuneWeatherData(
        location_name="Pune",
        region=loc.get("region", "Maharashtra"),
        country=loc.get("country", "India"),
        lat=float(loc.get("lat", PUNE_LAT)),
        lon=float(loc.get("lon", PUNE_LON)),
        temp_c=float(curr.get("temp_c", 22.0)),
        feelslike_c=float(curr.get("feelslike_c", 22.0)),
        condition_text=curr.get("condition", {}).get("text", "Overcast"),
        condition_icon=curr.get("condition", {}).get("icon", ""),
        humidity=int(curr.get("humidity", 70)),
        precip_mm=float(curr.get("precip_mm", 0.0)),
        cloud=int(curr.get("cloud", 50)),
        wind_kph=float(curr.get("wind_kph", 8.0)),
        daily_chance_of_rain=int(today.get("daily_chance_of_rain", 0)),
        is_live=True,
        source="WeatherAPI.com",
        last_updated=curr.get("last_updated", "Just now"),
        hourly_forecast=_next_24h(hours, stamps, local_now),
    ))


# WMO weather codes used by Open-Meteo
_WMO_TEXT = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 61: "Light rain", 63: "Moderate rain",
    65: "Heavy rain", 80: "Rain showers", 81: "Heavy rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
}


def _fetch_open_meteo() -> PuneWeatherData:
    query = urllib.parse.urlencode({
        "latitude": PUNE_LAT,
        "longitude": PUNE_LON,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,cloud_cover,wind_speed_10m,weather_code",
        "hourly": "temperature_2m,precipitation,precipitation_probability,weather_code",
        "timezone": "Asia/Kolkata",
        "forecast_days": 2,
    })
    payload = _get_json(f"{OPEN_METEO_URL}?{query}")
    curr = payload.get("current", {})
    hourly = payload.get("hourly", {})

    hours: List[HourlyForecast] = []
    stamps: List[datetime] = []
    for i, t in enumerate(hourly.get("time", [])):
        stamps.append(datetime.strptime(t, "%Y-%m-%dT%H:%M"))
        precip = float(hourly["precipitation"][i] or 0.0)
        chance = int(hourly["precipitation_probability"][i] or 0)
        hours.append(HourlyForecast(
            time=t[-5:],
            temp_c=float(hourly["temperature_2m"][i] or 0.0),
            condition_text=_WMO_TEXT.get(int(hourly["weather_code"][i] or 0), "Cloudy"),
            condition_icon="",
            precip_mm=precip,
            chance_of_rain=chance,
            will_it_rain=int(precip > 0.1 or chance >= 50),
        ))
    local_now = datetime.strptime(curr["time"], "%Y-%m-%dT%H:%M") if curr.get("time") else datetime.now()
    upcoming = _next_24h(hours, stamps, local_now)

    return _with_forecast_totals(PuneWeatherData(
        temp_c=float(curr.get("temperature_2m", 24.0)),
        feelslike_c=float(curr.get("apparent_temperature", 24.0)),
        condition_text=_WMO_TEXT.get(int(curr.get("weather_code", 2)), "Cloudy"),
        condition_icon="",
        humidity=int(curr.get("relative_humidity_2m", 70)),
        precip_mm=float(curr.get("precipitation", 0.0)),
        cloud=int(curr.get("cloud_cover", 50)),
        wind_kph=float(curr.get("wind_speed_10m", 8.0)),
        daily_chance_of_rain=max((h.chance_of_rain for h in upcoming), default=0),
        is_live=True,
        source="Open-Meteo",
        last_updated=curr.get("time", "").replace("T", " "),
        hourly_forecast=upcoming,
    ))


def _get_fallback_weather(reason: str) -> PuneWeatherData:
    """Fixed monsoon baseline used only when no weather service can be reached."""
    start = datetime.now().replace(minute=0, second=0, microsecond=0)
    hours: List[HourlyForecast] = []
    for i in range(24):
        hr = (start + timedelta(hours=i)).hour
        wet = 14 <= hr <= 20
        hours.append(HourlyForecast(
            time=f"{hr:02d}:00",
            temp_c=22.0 + (3.0 if 10 <= hr <= 16 else 0.0),
            condition_text="Scattered showers",
            condition_icon="//cdn.weatherapi.com/weather/64x64/day/296.png",
            precip_mm=0.8 if wet else 0.1,
            chance_of_rain=55 if wet else 25,
            will_it_rain=1 if wet else 0,
        ))

    return _with_forecast_totals(PuneWeatherData(
        temp_c=23.5,
        feelslike_c=24.0,
        condition_text="Monsoon baseline (offline)",
        condition_icon="//cdn.weatherapi.com/weather/64x64/day/296.png",
        humidity=82,
        precip_mm=0.4,
        cloud=85,
        wind_kph=12.0,
        daily_chance_of_rain=65,
        is_live=False,
        source="Offline baseline",
        last_updated=f"Baseline ({reason})",
        hourly_forecast=hours,
    ))
