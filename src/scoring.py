"""Rule-based surf score for beginners.

Two functions make up the public interface:

    score_hour(conditions, beach) -> HourScore
    score_day(hours, beach) -> DayScore or None

`conditions` is a dict with the columns from src.fetch.fetch_forecast and
`beach` is one entry from config/beaches.yaml. An ML model can replace
score_hour later as long as it returns an HourScore.
"""

import math
from dataclasses import dataclass

import pandas as pd

GO_POINTS = 70
MAYBE_POINTS = 45

# Points each factor can contribute. They add up to 100.
WEIGHTS = {"size": 35, "wind": 25, "direction": 20, "period": 10, "tide": 10}

# Estimated breaking height, in feet, that a beginner can handle.
MIN_HEIGHT_FT = 1.0
IDEAL_HEIGHT_FT = (1.5, 3.5)
MAX_HEIGHT_FT = 5.0

# Share of a swell's height that reaches a beach from outside its windows.
OUTSIDE_WINDOW_FACTOR = 0.15

LIGHT_WIND_MPH = 6    # below this, direction barely matters
STRONG_WIND_MPH = 15

COMPASS = ["north", "northeast", "east", "southeast",
           "south", "southwest", "west", "northwest"]


@dataclass
class HourScore:
    points: float
    rating: str
    surf_height_ft: float
    swell_dir_deg: float
    swell_period_s: float
    swell_window: str   # "best", "partial" or "outside"
    wind_mph: float
    wind_kind: str      # "offshore", "cross" or "onshore"
    tide_ft: float
    parts: dict         # 0-1 score for each factor in WEIGHTS


@dataclass
class DayScore:
    rating: str
    points: int
    reason: str
    best_time: pd.Timestamp
    best: HourScore
    hourly: list        # (time, rating) for each scored hour, for the timeline


def rating_for(points):
    if points >= GO_POINTS:
        return "Go"
    if points >= MAYBE_POINTS:
        return "Maybe"
    return "Don't Go"


def in_range(deg, start, end):
    """True if deg lies on the clockwise arc from start to end."""
    deg, start, end = deg % 360, start % 360, end % 360
    if start <= end:
        return start <= deg <= end
    return deg >= start or deg <= end


def compass_name(deg):
    return COMPASS[round((deg % 360) / 45) % 8]


def _clamp(x):
    return max(0.0, min(1.0, x))


def _missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def swell_window(direction, beach):
    """Which window a swell direction falls in, and how much size gets through."""
    if in_range(direction, *beach["swell_best"]):
        return "best", 1.0
    partial = beach["swell_partial"]
    if any(in_range(direction, *w) for w in partial["windows"]):
        return "partial", partial["size_factor"]
    return "outside", OUTSIDE_WINDOW_FACTOR


def period_factor(period):
    # Long-period swell grows more as it hits shallow water, so 3 ft at 16s
    # breaks bigger than 3 ft at 7s. Linear approximation, 0.8x to 1.4x.
    return max(0.8, min(1.4, 0.5 + 0.05 * period))


def surf_height(conditions, beach):
    """Estimated breaking height at the beach, plus the swell causing most of it.

    Each swell is scaled by how well its direction fits the beach and by its
    period. Primary and secondary swell are combined by energy (root sum of
    squares) rather than added.
    """
    swells = []
    for prefix in ("swell", "swell2"):
        height = conditions.get(f"{prefix}_height_ft")
        period = conditions.get(f"{prefix}_period_s")
        direction = conditions.get(f"{prefix}_dir_deg")
        if _missing(height) or _missing(period) or _missing(direction) or height <= 0:
            continue
        window, factor = swell_window(direction, beach)
        swells.append({
            "height": height * factor * period_factor(period),
            "period": period,
            "direction": direction,
            "window": window,
        })
    if not swells:
        return 0.0, None
    total = math.sqrt(sum(s["height"] ** 2 for s in swells))
    return total, max(swells, key=lambda s: s["height"])


def size_score(height):
    low, high = IDEAL_HEIGHT_FT
    if height < MIN_HEIGHT_FT or height > MAX_HEIGHT_FT:
        return 0.0
    if height < low:
        return 0.4 + 0.6 * (height - MIN_HEIGHT_FT) / (low - MIN_HEIGHT_FT)
    if height <= high:
        return 1.0
    return 1.0 - 0.7 * (height - high) / (MAX_HEIGHT_FT - high)


def wind_kind(direction, beach):
    start, end = beach["offshore_wind"]
    if in_range(direction, start, end):
        return "offshore"
    if in_range(direction, start + 180, end + 180):
        return "onshore"
    return "cross"


def wind_score(speed, kind):
    if speed <= LIGHT_WIND_MPH:
        return 1.0
    if kind == "offshore":
        return 1.0 if speed <= STRONG_WIND_MPH else 0.5
    # Onshore wind ruins waves faster than side-shore wind.
    worst = 12 if kind == "onshore" else 18
    return _clamp((worst - speed) / (worst - LIGHT_WIND_MPH))


def period_score(period):
    return _clamp((period - 5) / 6)


def tide_score(tide, preferred):
    if _missing(tide):
        return 0.5
    low, high = preferred
    distance = max(low - tide, tide - high, 0)
    return _clamp(1 - distance / 2)


def score_hour(conditions, beach):
    """Score one hour of conditions for one beach."""
    height, swell = surf_height(conditions, beach)
    if swell is None:
        swell = {"period": 0.0, "direction": float("nan"), "window": "outside"}

    wind_mph = conditions["wind_mph"]
    kind = wind_kind(conditions["wind_dir_deg"], beach)
    tide = conditions.get("tide_ft")

    parts = {
        "size": size_score(height),
        "wind": wind_score(wind_mph, kind),
        "direction": {"best": 1.0, "partial": 0.5, "outside": 0.0}[swell["window"]],
        "period": period_score(swell["period"]),
        "tide": tide_score(tide, beach["tide_ft"]),
    }
    points = sum(WEIGHTS[name] * parts[name] for name in WEIGHTS)

    # Hard limits that good scores elsewhere should not be able to outvote.
    if height < MIN_HEIGHT_FT or height > MAX_HEIGHT_FT:
        points = min(points, 25)
    if kind == "onshore" and wind_mph >= STRONG_WIND_MPH:
        points = min(points, MAYBE_POINTS - 1)
    if swell["window"] == "outside":
        points = min(points, GO_POINTS - 1)

    return HourScore(
        points=points,
        rating=rating_for(points),
        surf_height_ft=height,
        swell_dir_deg=swell["direction"],
        swell_period_s=swell["period"],
        swell_window=swell["window"],
        wind_mph=wind_mph,
        wind_kind=kind,
        tide_ft=float("nan") if _missing(tide) else tide,
        parts=parts,
    )


def height_range(height):
    if height < 1:
        return "under 1 ft"
    low = int(height)
    return f"{low}-{low + 1} ft"


def _hour_label(hour):
    if hour == 12:
        return "noon"
    return f"{hour}am" if hour < 12 else f"{hour - 12}pm"


def _time_hint(times, smoothed, best, threshold):
    """Describe the stretch of hours around the best one that clear the threshold."""
    start = end = best
    while start > 0 and smoothed[start - 1] >= threshold:
        start -= 1
    while end < len(times) - 1 and smoothed[end + 1] >= threshold:
        end += 1
    first, last = times[start].hour, times[end].hour + 1
    if start == 0 and end == len(times) - 1:
        return "all day" if times[0].hour <= 9 else "until dark"
    if start == 0:
        return f"before {_hour_label(last)}"
    if end == len(times) - 1:
        return f"after {_hour_label(first)}"
    return f"from {_hour_label(first)} to {_hour_label(last)}"


def _issue(name, score, beach):
    """Plain-English description of what is wrong with one factor."""
    if name == "size":
        if score.surf_height_ft < IDEAL_HEIGHT_FT[0]:
            return "the waves are tiny"
        return "the waves are on the big side for beginners"
    if name == "wind":
        side = "onshore" if score.wind_kind == "onshore" else "side-shore"
        return f"{side} wind is adding chop"
    if name == "direction":
        swell = compass_name(score.swell_dir_deg)
        if score.swell_window == "outside":
            return f"the {swell} swell mostly misses this beach"
        return f"the {swell} swell only partly reaches this beach"
    if name == "period":
        return "the swell is short and weak"
    if score.tide_ft > beach["tide_ft"][1]:
        return "the tide is too high for this spot"
    return "the tide is too low for this spot"


def _sentence(text):
    return text[0].upper() + text[1:] + "."


def build_reason(score, rating, beach, time_hint):
    """One or two short sentences explaining a rating."""
    height = score.surf_height_ft
    size_word = "Tiny" if height < IDEAL_HEIGHT_FT[0] else "Small" if height <= IDEAL_HEIGHT_FT[1] else "Fun-sized"

    if rating == "Go":
        if score.wind_mph <= LIGHT_WIND_MPH:
            wind = "light winds"
        elif score.wind_kind == "offshore":
            wind = "offshore wind"
        else:
            wind = "manageable wind"
        return f"{size_word}, clean waves and {wind}. Good for beginners {time_hint}."

    if height > MAX_HEIGHT_FT:
        return f"Waves around {round(height)} ft are too big for beginners."
    if height < MIN_HEIGHT_FT:
        if score.swell_window == "outside" and not math.isnan(score.swell_dir_deg):
            swell = compass_name(score.swell_dir_deg)
            return f"The swell is coming from the {swell}, which this beach mostly misses, so it will be close to flat."
        return "Close to flat. Not enough swell to ride."
    if score.wind_kind == "onshore" and score.wind_mph >= STRONG_WIND_MPH:
        return f"Strong onshore wind ({round(score.wind_mph)} mph) is blowing it out."

    lost = {name: WEIGHTS[name] * (1 - score.parts[name]) for name in WEIGHTS}
    worst = sorted(lost, key=lost.get, reverse=True)

    if rating == "Maybe":
        main = f"{height_range(height)} waves, but {_issue(worst[0], score, beach)}."
        if time_hint in ("all day", "until dark"):
            return main
        return f"{main} Best chance {time_hint}."

    issues = [_issue(name, score, beach) for name in worst[:2] if lost[name] > 3]
    return _sentence(" and ".join(issues))


def score_day(hours, beach):
    """Rate one day at one beach from its hourly forecast rows.

    Pass only the hours someone could actually surf (daylight, not already
    gone). The day is rated on its best three-hour stretch, since nobody
    surfs all day. Returns None if there are no usable hours.
    """
    hours = hours.dropna(subset=["swell_height_ft", "wind_mph", "wind_dir_deg"])
    if hours.empty:
        return None
    hours = hours.sort_values("time")
    times = list(hours["time"])
    scores = [score_hour(row, beach) for row in hours.to_dict("records")]

    points = pd.Series([s.points for s in scores])
    smoothed = points.rolling(3, center=True, min_periods=1).mean().tolist()
    best = max(range(len(smoothed)), key=smoothed.__getitem__)
    rating = rating_for(smoothed[best])

    threshold = GO_POINTS if rating == "Go" else MAYBE_POINTS
    hint = _time_hint(times, smoothed, best, threshold) if rating != "Don't Go" else ""
    return DayScore(
        rating=rating,
        points=round(smoothed[best]),
        reason=build_reason(scores[best], rating, beach, hint),
        best_time=times[best],
        best=scores[best],
        hourly=[(t, s.rating) for t, s in zip(times, scores)],
    )
