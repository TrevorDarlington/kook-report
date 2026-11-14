import pandas as pd
import streamlit as st

from src import config, scoring

st.title("About Kook Report")

st.markdown(
    """
Kook Report is a free surf forecast for beginners and students in Los Angeles.
"Kook" is surfer slang for a beginner. We are two of them.

It answers one question: **should I go surf today?**

### Why not just use Surfline?

Surfline is good, but it is built for people who already know how to read a
forecast. A beginner opens it and sees swell charts, period, wind arrows and a
rating like "Fair", and still doesn't know whether to drive to the beach. A lot
of the detail is also behind a subscription.

We wanted something a friend could check in ten seconds from the dorms: Go,
Maybe or Don't Go, and one sentence saying why.

### How the score works

Every daylight hour at every beach gets a score out of 100. It is a set of
written rules, not a trained model, so you can see exactly why a beach got the
rating it did.
"""
)

explanations = {
    "size": "Estimated breaking wave height. "
            f"{scoring.IDEAL_HEIGHT_FT[0]}-{scoring.IDEAL_HEIGHT_FT[1]} ft is ideal for learning. "
            f"Under {scoring.MIN_HEIGHT_FT:.0f} ft is flat and over {scoring.MAX_HEIGHT_FT:.0f} ft is too big.",
    "wind": "Light or offshore wind keeps waves smooth. Onshore wind makes them choppy.",
    "direction": "Whether the swell is coming from an angle the beach can actually receive.",
    "period": "Seconds between waves. Longer-period swell makes cleaner, better organized waves.",
    "tide": "Each beach has a tide range where it breaks best.",
}
st.table(pd.DataFrame(
    {"Points": [scoring.WEIGHTS[k] for k in explanations], "What we look at": list(explanations.values())},
    index=[k.capitalize() for k in explanations],
))

st.markdown(
    f"""
A day is rated on its best three-hour stretch: **Go** at {scoring.GO_POINTS} points or more,
**Maybe** at {scoring.MAYBE_POINTS} or more, **Don't Go** below that. A few rules
override the points. Flat or oversized surf and strong onshore wind are always
Don't Go, and a beach can never be a Go on a swell from outside its window.

### Why swell direction matters so much

A buoy can report 4 ft waves while a beach a few miles away is flat. Each beach
faces a particular direction, and headlands and islands block swell from other
angles. Malibu faces south and is hidden from west swells by Point Dume. El
Porto faces west and picks up winter swells that Malibu never sees, while Palos
Verdes blocks most south swell from reaching it.

So for each beach we set a best swell window, a partial window where swell
arrives at reduced size, and treat everything else as mostly blocked
({scoring.OUTSIDE_WINDOW_FACTOR:.0%} of its size). We use the direction of the
primary swell and the secondary swell separately, not the blended wave
direction, because a small swell from the right angle can beat a big one from
the wrong angle.
"""
)

rows = []
for name, beach in config.BEACHES.items():
    partial = ", ".join(f"{a}-{b}" for a, b in beach["swell_partial"]["windows"])
    rows.append({
        "Beach": name,
        "Best swell (deg)": "{}-{}".format(*beach["swell_best"]),
        "Partial swell (deg)": f"{partial} at {beach['swell_partial']['size_factor']:.0%} size",
        "Offshore wind (deg)": "{}-{}".format(*beach["offshore_wind"]),
        "Tide (ft)": "{}-{}".format(*beach["tide_ft"]),
    })
st.dataframe(pd.DataFrame(rows), hide_index=True)
st.caption("Directions are where the swell or wind comes from. 180 is south, 270 is west.")

st.markdown(
    """
### Where the data comes from

All of it is free and public.

- **Waves and swell:** Open-Meteo Marine API (wave height, plus primary and secondary swell height, period and direction)
- **Wind:** Open-Meteo Weather API
- **Tides:** NOAA CO-OPS tide predictions, Santa Monica station
- **What actually happened:** NOAA NDBC buoys 46268 (Topanga Nearshore) and 46221 (Santa Monica Bay), used for the Accuracy page

### Limitations

We would rather tell you what this can't do than have you find out in the water.

- **The beach settings are our best guesses.** The swell windows, wind directions
  and tide ranges come from maps and reading, not years of local experience. We
  are checking them with local surfers.
- **Buoys measure offshore wave height, not the waves breaking at the beach.**
  Our accuracy page can tell you whether the swell forecast was right. It cannot
  tell you whether "Go" was really a good day.
- **Wave size at the beach is an estimate.** We scale the offshore swell with a
  simple rule. Sandbars, which shift every few weeks, are not in any free data.
- **The wave model is coarse.** Its grid cells are several miles wide, so two
  nearby beaches can get nearly the same raw forecast.
- **We don't know about crowds, water quality, rip currents or hazards.** After
  rain, check the LA County beach water quality report before going in.
- **A forecast is a forecast.** Look at the ocean before you paddle out. If in
  doubt, don't go out.
"""
)
