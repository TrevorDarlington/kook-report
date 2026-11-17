from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from src import config, fetch, scorecard, scoring, ui

SHORT_COMPASS = {"north": "N", "northeast": "NE", "east": "E", "southeast": "SE",
                 "south": "S", "southwest": "SW", "west": "W", "northwest": "NW"}


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


def hour_label(time):
    return time.strftime("%-I%p").lower()


def stat(label, value, note=""):
    return (f'<div class="stat"><div class="label">{label}</div>'
            f'<div class="value">{value}</div><div class="note">{note}</div></div>')


def card(beach_name, day, top=False):
    color = ui.RATING_COLORS[day.rating]
    best = day.best
    wind_kind = "side-shore" if best.wind_kind == "cross" else best.wind_kind
    direction = SHORT_COMPASS[scoring.compass_name(best.swell_dir_deg)]
    stats = [
        stat("Waves", scoring.height_range(best.surf_height_ft).replace(" ft", ""), "ft"),
        stat("Swell", f"{best.swell_period_s:.0f}s", f"from {direction}"),
        stat("Wind", f"{best.wind_mph:.0f}", f"mph {wind_kind}"),
        stat("Tide", "n/a" if pd.isna(best.tide_ft) else f"{best.tide_ft:.1f}", "ft"),
    ]
    segments = "".join(f'<span style="background: {ui.RATING_COLORS[r]}"></span>' for _, r in day.hourly)
    first, last = day.hourly[0][0], day.hourly[-1][0] + timedelta(hours=1)
    tag = '<div class="tag">Best bet</div>' if top else ""
    st.html(
        f'<div class="card {"top" if top else ""}" style="--c: {color}">'
        f'<div class="card-head"><div>{tag}<div class="beach">{beach_name}</div></div>'
        f'<span class="pill">{day.rating}</span></div>'
        f'<div class="reason">{day.reason}</div>'
        f'<div class="timeline">{segments}</div>'
        f'<div class="timeline-labels"><span>{hour_label(first)}</span><span>hour by hour</span>'
        f'<span>{hour_label(last)}</span></div>'
        f'<div class="stats">{"".join(stats)}</div>'
        f'</div>'
    )


def message_card(beach_name, text):
    st.html(
        f'<div class="card"><div class="card-head"><div class="beach">{beach_name}</div></div>'
        f'<div class="reason" style="color: var(--muted); margin-bottom: 0">{text}</div></div>'
    )


def outlook(scores, days, today):
    """Grid of every beach against every day, so the week reads at a glance."""
    head = "".join(f"<th>{'Today' if d == today else d.strftime('%a')}</th>" for d in days)
    rows = []
    for name in config.BEACHES:
        cells = []
        for d in days:
            day = scores[name].get(d)
            if day is None:
                cells.append('<td><span class="chip" style="background: #EEF3F5; color: #8FA3AD">-</span></td>')
                continue
            label = "No" if day.rating == "Don't Go" else day.rating
            cells.append(f'<td><span class="chip" style="background: {ui.RATING_TINTS[day.rating]}; '
                         f'color: {ui.RATING_COLORS[day.rating]}">{label}</span></td>')
        rows.append(f'<tr><td class="name">{name}</td>{"".join(cells)}</tr>')
    st.html(f'<table class="outlook"><tr><th></th>{head}</tr>{"".join(rows)}</table>')


now = datetime.now(ZoneInfo(config.TIMEZONE)).replace(tzinfo=None)
today = now.date()
this_hour = now.replace(minute=0, second=0, microsecond=0)

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

# Score every beach for every day once; the cards and the outlook grid both use it.
scores = {
    name: {d: scoring.score_day(surfable_hours(forecasts[name], d), beach) for d in days}
    if forecasts[name] is not None else {}
    for name, beach in config.BEACHES.items()
}

picked = st.session_state.get("day")
if picked not in days:
    picked = days[0]

ranked = sorted(
    config.BEACHES,
    key=lambda name: -scores[name][picked].points if scores[name].get(picked) else 1,
)
top = scores[ranked[0]].get(picked)
day_name = "today" if picked == today else picked.strftime("%A")

if top is None:
    ui.hero("No forecast right now", "We couldn't reach the forecast service. Try again in a few minutes.",
            f"Should I go surf {day_name}?")
elif top.rating == "Go":
    ui.hero("Yes, go.", f"Best bet is <b>{ranked[0]}</b>. {top.reason}", f"Should I go surf {day_name}?")
elif top.rating == "Maybe":
    ui.hero("Maybe.", f"Your best shot is <b>{ranked[0]}</b>. {top.reason}", f"Should I go surf {day_name}?")
else:
    ui.hero("Not a beach day.", "Nothing looks good for beginners. Check the next few days below.",
            f"Should I go surf {day_name}?")

if days[0] != today:
    st.caption("It's too dark to surf today, so the forecast starts tomorrow.")

st.segmented_control(
    "Day",
    days,
    default=days[0],
    key="day",
    format_func=lambda d: "Today" if d == today else d.strftime("%a %-d"),
    label_visibility="collapsed",
    width="stretch",
)

if "saved" in sources:
    st.warning("The live forecast feed is not responding, so some beaches are showing the forecast saved this morning.")

for position, name in enumerate(ranked):
    day = scores[name].get(picked)
    if forecasts[name] is None:
        message_card(name, "Couldn't load the forecast for this beach. Try again in a few minutes.")
    elif day is None:
        message_card(name, "No forecast data for this day.")
    else:
        card(name, day, top=position == 0 and day.rating != "Don't Go")

st.html(
    '<div class="legend">'
    + "".join(f'<span><i style="background: {ui.RATING_COLORS[r]}"></i>{r}</span>' for r in ui.RATING_COLORS)
    + "</div>"
)

ui.section("Next few days")
outlook(scores, days, today)

st.html(
    '<div class="fineprint">Wave size is our estimate of breaking height at the best hour of the day. '
    "Ratings are for beginners on soft-top boards. Forecasts can be wrong, so look at the water "
    "before you paddle out and never surf alone at a spot you don't know.</div>"
)
