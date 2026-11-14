from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from src import config, fetch, scorecard, scoring

RATING_COLORS = {"Go": "#1B8A5A", "Maybe": "#B7791F", "Don't Go": "#B83232"}

st.markdown(
    """
    <style>
    .block-container {padding-top: 3.5rem; max-width: 640px;}
    .card {background: white; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px;
           border-left: 8px solid var(--c); box-shadow: 0 1px 3px rgba(11, 37, 51, 0.12);}
    .card-top {display: flex; justify-content: space-between; align-items: center; gap: 8px;}
    .beach {font-size: 1.15rem; font-weight: 700;}
    .badge {background: var(--c); color: white; font-weight: 700; font-size: 1.05rem;
            padding: 4px 14px; border-radius: 999px; white-space: nowrap;}
    .reason {font-size: 1.05rem; margin: 8px 0 6px 0; line-height: 1.35;}
    .stats {font-size: 0.85rem; color: #4A6572;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=1800, show_spinner=False)
def live_forecast(beach_name):
    return fetch.fetch_forecast(beach_name)


@st.cache_data(ttl=1800, show_spinner=False)
def saved_forecast(today):
    """The forecast the daily collector saved this morning, if there is one."""
    path = scorecard.FORECAST_DIR / f"{today}.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, parse_dates=["time"])


def get_forecast(beach_name, today):
    """Live forecast, falling back to this morning's saved copy if the API is down."""
    try:
        return live_forecast(beach_name), "live"
    except Exception:
        saved = saved_forecast(today.isoformat())
        if not saved.empty:
            rows = saved[saved["beach"] == beach_name]
            if not rows.empty:
                return rows, "saved"
    return None, "failed"


def card(beach_name, day):
    color = RATING_COLORS[day.rating]
    best = day.best
    swell = f"{best.swell_period_s:.0f}s {scoring.compass_name(best.swell_dir_deg)} swell"
    wind_kind = "side-shore" if best.wind_kind == "cross" else best.wind_kind
    wind = f"{best.wind_mph:.0f} mph {wind_kind} wind"
    stats = [scoring.height_range(best.surf_height_ft), swell, wind]
    if not pd.isna(best.tide_ft):
        stats.append(f"{best.tide_ft:.1f} ft tide")
    st.markdown(
        f"""
        <div class="card" style="--c: {color}">
          <div class="card-top"><span class="beach">{beach_name}</span><span class="badge">{day.rating}</span></div>
          <div class="reason">{day.reason}</div>
          <div class="stats">{" &middot; ".join(stats)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def message_card(beach_name, text):
    st.markdown(
        f"""
        <div class="card" style="--c: #9FB3BD">
          <div class="card-top"><span class="beach">{beach_name}</span></div>
          <div class="reason">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


now = datetime.now(ZoneInfo(config.TIMEZONE)).replace(tzinfo=None)
today = now.date()
this_hour = now.replace(minute=0, second=0, microsecond=0)

st.title("Kook Report")
st.markdown("**Should I go surf today?** A beginner's forecast for four LA beaches.")

forecasts, sources = {}, set()
with st.spinner("Loading the forecast..."):
    for name in config.BEACHES:
        forecasts[name], source = get_forecast(name, today)
        sources.add(source)


def surfable_hours(forecast, day):
    """Daylight hours on a given day that haven't already passed."""
    hours = forecast[(forecast["time"].dt.date == day) & (forecast["is_day"] == 1)]
    return hours[hours["time"] >= this_hour]


loaded = [f for f in forecasts.values() if f is not None]
days = [today + timedelta(days=i) for i in range(config.FORECAST_DAYS)]
if loaded and all(surfable_hours(f, today).empty for f in loaded):
    days = days[1:]
    st.info("It's too dark to surf today, so here is tomorrow.")

picked = st.segmented_control(
    "Day",
    days,
    default=days[0],
    format_func=lambda d: "Today" if d == today else d.strftime("%a %-d"),
    label_visibility="collapsed",
)
picked = picked or days[0]

results = []
for name, beach in config.BEACHES.items():
    forecast = forecasts[name]
    if forecast is None:
        results.append((name, None, "Couldn't load the forecast for this beach. Try again in a few minutes."))
        continue
    day = scoring.score_day(surfable_hours(forecast, picked), beach)
    if day is None:
        results.append((name, None, "No forecast data for this day."))
    else:
        results.append((name, day, None))

if "saved" in sources:
    st.warning("The live forecast feed is not responding, so some beaches are showing the forecast saved this morning.")
if sources == {"failed"}:
    st.error("The forecast service is not responding right now. Nothing is wrong on your end. Try again in a few minutes.")

# Best beach first; beaches without a score go last.
results.sort(key=lambda r: -r[1].points if r[1] else 1)
for name, day, text in results:
    if day:
        card(name, day)
    else:
        message_card(name, text)

st.caption(
    "Sizes are our estimate of breaking wave height during the best part of the day. "
    "Scores are for beginners on soft-top boards. Forecasts can be wrong, so look at the "
    "water before you paddle out and never surf alone at a spot you don't know."
)
