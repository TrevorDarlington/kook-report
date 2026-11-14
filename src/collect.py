"""Daily snapshot: save today's forecast and recent buoy observations as CSVs.

Run by GitHub Actions once a day, or by hand with `python -m src.collect`
from the repo root.

  data/forecasts/YYYY-MM-DD.csv     the 4-day forecast issued on that date, all beaches
  data/observations/YYYY-MM-DD.csv  what the buoys measured on that date
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from src import config, fetch

DATA_DIR = config.ROOT / "data"
FORECAST_DIR = DATA_DIR / "forecasts"
OBSERVATION_DIR = DATA_DIR / "observations"

# The buoy feed keeps about 45 days, so each run also fills in any recent
# day that a failed run missed. Forecasts can't be recovered the same way:
# a missed day is gone.
BACKFILL_DAYS = 7


def save_forecasts(today):
    frames = []
    for name in config.BEACHES:
        try:
            frames.append(fetch.fetch_forecast(name))
        except Exception as error:
            print(f"WARNING: forecast for {name} failed: {error}")
    if not frames:
        raise RuntimeError("No forecast could be fetched for any beach")
    df = pd.concat(frames, ignore_index=True)
    df.insert(0, "forecast_date", today.isoformat())
    path = FORECAST_DIR / f"{today.isoformat()}.csv"
    df.to_csv(path, index=False)
    print(f"Saved {len(df)} forecast rows to {path.name}")


def save_observations(today):
    stations = sorted({b["buoy"] for b in config.BEACHES.values()} | {config.FALLBACK_BUOY})
    frames = []
    for station in stations:
        try:
            frames.append(fetch.fetch_buoy(station))
        except Exception as error:
            print(f"WARNING: buoy {station} failed: {error}")
    if not frames:
        print("WARNING: no buoy returned data, skipping observations")
        return
    obs = pd.concat(frames, ignore_index=True)

    # Only complete days are saved, so start from yesterday.
    for days_ago in range(1, BACKFILL_DAYS + 1):
        day = today - timedelta(days=days_ago)
        path = OBSERVATION_DIR / f"{day.isoformat()}.csv"
        if path.exists():
            continue
        day_obs = obs[obs["time"].dt.date == day]
        if day_obs.empty:
            print(f"WARNING: no observations for {day}")
            continue
        day_obs.to_csv(path, index=False)
        print(f"Saved {len(day_obs)} observation rows to {path.name}")


def main():
    FORECAST_DIR.mkdir(parents=True, exist_ok=True)
    OBSERVATION_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(ZoneInfo(config.TIMEZONE)).date()
    save_observations(today)
    save_forecasts(today)


if __name__ == "__main__":
    main()
