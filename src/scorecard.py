"""Compare saved forecasts with what the buoys measured."""

import pandas as pd

from src import config

FORECAST_DIR = config.ROOT / "data" / "forecasts"
OBSERVATION_DIR = config.ROOT / "data" / "observations"


def _load(folder):
    files = sorted(folder.glob("*.csv"))
    if not files:
        return pd.DataFrame()
    df = pd.concat((pd.read_csv(f, dtype={"buoy": str}) for f in files), ignore_index=True)
    df["time"] = pd.to_datetime(df["time"])
    return df


def load_forecasts(folder=FORECAST_DIR):
    return _load(folder)


def load_observations(folder=OBSERVATION_DIR):
    return _load(folder)


def match(beach_name, forecasts, observations):
    """Pair each forecast hour for a beach with the buoy reading for that hour.

    Returns one row per (forecast issue date, hour) with the forecast and
    observed wave height and how many days ahead the forecast was made.
    """
    columns = ["forecast_date", "time", "lead_days", "forecast_ft", "observed_ft"]
    if forecasts.empty or observations.empty:
        return pd.DataFrame(columns=columns)

    buoy = str(config.BEACHES[beach_name]["buoy"])
    obs = observations[observations["buoy"] == buoy]
    if obs.empty:
        obs = observations[observations["buoy"] == config.FALLBACK_BUOY]

    # Buoys report about every 30 minutes; average onto the forecast's hourly grid.
    hourly = (
        obs.assign(time=obs["time"].dt.round("h"))
        .groupby("time", as_index=False)["obs_wave_height_ft"].mean()
        .rename(columns={"obs_wave_height_ft": "observed_ft"})
    )

    fc = forecasts[forecasts["beach"] == beach_name]
    fc = fc[["forecast_date", "time", "wave_height_ft"]].rename(columns={"wave_height_ft": "forecast_ft"})
    merged = fc.merge(hourly, on="time").dropna(subset=["forecast_ft", "observed_ft"])
    issued = pd.to_datetime(merged["forecast_date"])
    merged["lead_days"] = (merged["time"].dt.normalize() - issued).dt.days
    return merged[columns].sort_values(["forecast_date", "time"]).reset_index(drop=True)


def error_metrics(matched):
    """Mean absolute error and bias (forecast minus observed), in feet."""
    error = matched["forecast_ft"] - matched["observed_ft"]
    return {"mae": error.abs().mean(), "bias": error.mean(), "hours": len(matched)}


def error_by_lead(matched):
    error = (matched["forecast_ft"] - matched["observed_ft"]).abs()
    return error.groupby(matched["lead_days"]).mean().rename("mae")
