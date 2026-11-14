"""Fetch forecasts (Open-Meteo, NOAA CO-OPS) and buoy observations (NOAA NDBC).

Every function returns a DataFrame with a `time` column in Los Angeles
local time. Heights are in feet, wind in mph.

Run `python -m src.fetch` from the repo root to print a sample of everything.
"""

import io
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from src import config

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
TIDE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
BUOY_URL = "https://www.ndbc.noaa.gov/data/realtime2/{station}.txt"

METERS_TO_FEET = 3.28084
TIMEOUT = 15


def _get(url, params=None, attempts=3):
    for attempt in range(attempts):
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            return response
        except requests.RequestException:
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)


def fetch_waves(lat, lon):
    """Hourly wave forecast from the Open-Meteo Marine API.

    wave_height_ft is the combined sea state, which is what a buoy measures.
    swell_* is the primary swell and swell2_* the secondary swell. Scoring
    uses the swell columns because each beach only works for some directions.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join([
            "wave_height",
            "swell_wave_height", "swell_wave_period", "swell_wave_direction",
            "secondary_swell_wave_height", "secondary_swell_wave_period",
            "secondary_swell_wave_direction",
        ]),
        "length_unit": "imperial",
        "timezone": config.TIMEZONE,
        "forecast_days": config.FORECAST_DAYS,
    }
    hourly = _get(MARINE_URL, params).json()["hourly"]
    return pd.DataFrame({
        "time": pd.to_datetime(hourly["time"]),
        "wave_height_ft": hourly["wave_height"],
        "swell_height_ft": hourly["swell_wave_height"],
        "swell_period_s": hourly["swell_wave_period"],
        "swell_dir_deg": hourly["swell_wave_direction"],
        "swell2_height_ft": hourly["secondary_swell_wave_height"],
        "swell2_period_s": hourly["secondary_swell_wave_period"],
        "swell2_dir_deg": hourly["secondary_swell_wave_direction"],
    }).astype({"wave_height_ft": float, "swell_height_ft": float, "swell_period_s": float,
               "swell_dir_deg": float, "swell2_height_ft": float, "swell2_period_s": float,
               "swell2_dir_deg": float})


def fetch_wind(lat, lon):
    """Hourly wind forecast, plus a daylight flag, from the Open-Meteo weather API."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,wind_gusts_10m,wind_direction_10m,is_day",
        "wind_speed_unit": "mph",
        "timezone": config.TIMEZONE,
        "forecast_days": config.FORECAST_DAYS,
    }
    hourly = _get(WEATHER_URL, params).json()["hourly"]
    return pd.DataFrame({
        "time": pd.to_datetime(hourly["time"]),
        "wind_mph": hourly["wind_speed_10m"],
        "gust_mph": hourly["wind_gusts_10m"],
        "wind_dir_deg": hourly["wind_direction_10m"],
        "is_day": hourly["is_day"],
    })


def fetch_tides(station):
    """Hourly tide predictions (feet above MLLW) from NOAA CO-OPS."""
    today = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%Y%m%d")
    params = {
        "product": "predictions",
        "station": station,
        "datum": "MLLW",
        "interval": "h",
        "units": "english",
        "time_zone": "lst_ldt",
        "format": "json",
        "begin_date": today,
        "range": config.FORECAST_DAYS * 24,
    }
    data = _get(TIDE_URL, params).json()
    if "predictions" not in data:
        raise ValueError(f"No tide predictions for station {station}: {data}")
    df = pd.DataFrame(data["predictions"])
    return pd.DataFrame({
        "time": pd.to_datetime(df["t"]),
        "tide_ft": df["v"].astype(float),
    })


def fetch_forecast(beach_name):
    """One hourly table for a beach: waves, wind and tide for the next 4 days.

    Waves and wind are required. If the tide API is down the tide column is
    left empty and scoring treats tide as neutral.
    """
    beach = config.BEACHES[beach_name]
    waves = fetch_waves(beach["lat"], beach["lon"])
    wind = fetch_wind(beach["lat"], beach["lon"])
    df = waves.merge(wind, on="time")
    try:
        df = df.merge(fetch_tides(beach["tide_station"]), on="time", how="left")
    except (requests.RequestException, ValueError, KeyError):
        df["tide_ft"] = float("nan")
    df.insert(0, "beach", beach_name)
    return df


def fetch_buoy(station):
    """Recent observed waves from an NDBC buoy (about the last 45 days).

    This is wave height measured offshore at the buoy, not the height of
    the waves breaking at the beach.
    """
    text = _get(BUOY_URL.format(station=station)).text
    # First line is the header, second line is units; "MM" means missing.
    raw = pd.read_csv(io.StringIO(text), sep=r"\s+", skiprows=[1], na_values="MM")
    utc = pd.to_datetime(
        raw[["#YY", "MM", "DD", "hh", "mm"]].rename(
            columns={"#YY": "year", "MM": "month", "DD": "day", "hh": "hour", "mm": "minute"}
        ),
        utc=True,
    )
    df = pd.DataFrame({
        "time": utc.dt.tz_convert(config.TIMEZONE).dt.tz_localize(None),
        "buoy": station,
        "obs_wave_height_ft": (raw["WVHT"] * METERS_TO_FEET).round(2),
        "obs_dominant_period_s": raw["DPD"],
        "obs_wave_dir_deg": raw["MWD"],
    })
    return df.dropna(subset=["obs_wave_height_ft"]).sort_values("time").reset_index(drop=True)


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    for name in config.BEACHES:
        forecast = fetch_forecast(name)
        print(f"\n{name}: {len(forecast)} forecast hours")
        print(forecast[forecast["time"].dt.hour.isin([6, 12, 18])]
              .drop(columns="beach").to_string(index=False))

    for station in sorted({b["buoy"] for b in config.BEACHES.values()}):
        buoy = fetch_buoy(station)
        print(f"\nBuoy {station}: {len(buoy)} observations, latest 3")
        print(buoy.tail(3).to_string(index=False))
