"""Loads config/beaches.yaml once and exposes it as plain Python objects."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

with open(ROOT / "config" / "beaches.yaml") as f:
    _raw = yaml.safe_load(f)

TIMEZONE = _raw["timezone"]
FORECAST_DAYS = _raw["forecast_days"]
FALLBACK_BUOY = str(_raw["fallback_buoy"])
BEACHES = {b["name"]: b for b in _raw["beaches"]}
