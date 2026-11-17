import streamlit as st

from src import config, scorecard, ui

MIN_HOURS = 48  # matched hours needed before the numbers mean anything

LEAD_LABELS = {0: "Same day", 1: "1 day ahead", 2: "2 days ahead", 3: "3 days ahead"}


@st.cache_data(ttl=3600, show_spinner=False)
def load_history():
    return scorecard.load_forecasts(), scorecard.load_observations()


ui.hero(
    "How right were we?",
    "Every morning we save the forecast. Later we check it against what the nearest buoy measured.",
    small=True,
)

try:
    forecasts, observations = load_history()
except Exception:
    st.error("Couldn't read the saved forecast history. Try again in a few minutes.")
    st.stop()

beach_name = st.selectbox("Beach", list(config.BEACHES))
matched = scorecard.match(beach_name, forecasts, observations)

if len(matched) < MIN_HOURS:
    days_saved = forecasts["forecast_date"].nunique() if not forecasts.empty else 0
    st.info(
        f"Still collecting data. We have {days_saved} day(s) of saved forecasts and "
        f"{len(matched)} forecast hours that can be checked against a buoy so far. "
        f"The scorecard turns on once there are at least {MIN_HOURS}. Check back in a few days."
    )
    st.stop()

metrics = scorecard.error_metrics(matched)
st.html(
    '<div class="card"><div class="stats three">'
    f'<div class="stat"><div class="label">Typical miss</div><div class="value">{metrics["mae"]:.1f} ft</div>'
    '<div class="note">mean absolute error</div></div>'
    f'<div class="stat"><div class="label">Bias</div><div class="value">{metrics["bias"]:+.1f} ft</div>'
    '<div class="note">forecast minus buoy</div></div>'
    f'<div class="stat"><div class="label">Compared</div><div class="value">{metrics["hours"]:,}</div>'
    '<div class="note">forecast hours</div></div>'
    '</div></div>'
)
direction = "high" if metrics["bias"] > 0 else "low"
st.caption(
    f"On average the wave height forecast was off by {metrics['mae']:.1f} ft, and it "
    f"tended to run {direction}. Buoy: NDBC {config.BEACHES[beach_name]['buoy']}."
)

ui.section("Forecast vs. buoy")
leads = sorted(matched["lead_days"].unique())
lead = st.radio("Forecast made", leads, format_func=lambda d: LEAD_LABELS.get(d, f"{d} days ahead"), horizontal=True)
series = (
    matched[matched["lead_days"] == lead]
    .set_index("time")[["forecast_ft", "observed_ft"]]
    .rename(columns={"forecast_ft": "Forecast", "observed_ft": "Buoy"})
)
st.line_chart(series, y_label="Wave height (ft)", color=["#0B7285", "#E8590C"])

ui.section("Error by how far ahead we forecast")
by_lead = scorecard.error_by_lead(matched)
by_lead.index = [LEAD_LABELS.get(d, f"{d} days ahead") for d in by_lead.index]
st.bar_chart(by_lead, x_label="Mean absolute error (ft)", color="#0B7285", horizontal=True, sort=False, height=220)

st.caption(
    "This checks offshore wave height only, because that is what buoys measure. "
    "It does not tell us whether a Go rating was actually a good day to surf. "
    "See the About page for more on what this can and can't show."
)
