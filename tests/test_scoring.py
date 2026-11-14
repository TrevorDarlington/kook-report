import pandas as pd
import pytest

from src import scoring
from src.config import BEACHES

MALIBU = BEACHES["Malibu Surfrider"]
EL_PORTO = BEACHES["El Porto"]


def conditions(**overrides):
    """A clean, beginner-friendly south swell with light offshore wind."""
    base = {
        "swell_height_ft": 2.5, "swell_period_s": 10, "swell_dir_deg": 200,
        "swell2_height_ft": float("nan"), "swell2_period_s": float("nan"),
        "swell2_dir_deg": float("nan"),
        "wind_mph": 4, "wind_dir_deg": 10, "tide_ft": 2.5,
    }
    base.update(overrides)
    return base


def test_in_range_handles_wrap_through_north():
    assert scoring.in_range(350, 340, 40)
    assert scoring.in_range(10, 340, 40)
    assert not scoring.in_range(180, 340, 40)
    assert scoring.in_range(200, 180, 220)
    assert not scoring.in_range(221, 180, 220)


def test_good_conditions_are_a_go():
    result = scoring.score_hour(conditions(), MALIBU)
    assert result.rating == "Go"
    assert result.swell_window == "best"


def test_swell_outside_window_drops_score_even_with_good_height():
    good = scoring.score_hour(conditions(swell_dir_deg=200), MALIBU)
    blocked = scoring.score_hour(conditions(swell_dir_deg=290), MALIBU)
    assert blocked.swell_window == "outside"
    assert blocked.points < good.points - 30
    assert blocked.rating == "Don't Go"


def test_outside_window_can_never_be_a_go():
    # A huge west swell wraps into Malibu at a rideable size, but we still
    # don't trust it enough to call it a Go.
    result = scoring.score_hour(conditions(swell_height_ft=14, swell_dir_deg=290), MALIBU)
    assert result.surf_height_ft > scoring.MIN_HEIGHT_FT
    assert result.rating != "Go"


def test_partial_window_reduces_size():
    best, _ = scoring.surf_height(conditions(swell_dir_deg=200), MALIBU)
    partial, _ = scoring.surf_height(conditions(swell_dir_deg=235), MALIBU)
    assert partial == pytest.approx(best * MALIBU["swell_partial"]["size_factor"])


def test_same_swell_scores_differently_by_beach():
    west = conditions(swell_dir_deg=275, wind_mph=3)
    assert scoring.score_hour(west, EL_PORTO).points > scoring.score_hour(west, MALIBU).points


def test_secondary_swell_can_carry_the_day():
    # Primary west swell misses Malibu, but a smaller south swell gets in.
    result = scoring.score_hour(
        conditions(swell_dir_deg=280, swell2_height_ft=2.2, swell2_period_s=14, swell2_dir_deg=190),
        MALIBU,
    )
    assert result.swell_window == "best"
    assert result.swell_dir_deg == 190
    assert result.rating == "Go"


def test_too_big_is_dont_go():
    result = scoring.score_hour(conditions(swell_height_ft=8), MALIBU)
    assert result.rating == "Don't Go"


def test_flat_is_dont_go():
    result = scoring.score_hour(conditions(swell_height_ft=0.5), MALIBU)
    assert result.rating == "Don't Go"


def test_strong_onshore_wind_is_dont_go():
    result = scoring.score_hour(conditions(wind_mph=18, wind_dir_deg=190), MALIBU)
    assert result.wind_kind == "onshore"
    assert result.rating == "Don't Go"


def test_offshore_wind_beats_onshore_wind():
    offshore = scoring.score_hour(conditions(wind_mph=10, wind_dir_deg=10), MALIBU)
    onshore = scoring.score_hour(conditions(wind_mph=10, wind_dir_deg=190), MALIBU)
    assert offshore.points > onshore.points


def test_missing_tide_is_neutral_not_an_error():
    result = scoring.score_hour(conditions(tide_ft=float("nan")), MALIBU)
    assert result.parts["tide"] == 0.5


def test_bad_tide_lowers_score():
    good = scoring.score_hour(conditions(tide_ft=2.5), MALIBU)
    bad = scoring.score_hour(conditions(tide_ft=6.5), MALIBU)
    assert bad.points < good.points


def day_frame(wind_by_hour):
    rows = []
    for hour, wind in wind_by_hour.items():
        rows.append({"time": pd.Timestamp(2026, 7, 1, hour), **conditions(wind_mph=wind, wind_dir_deg=190)})
    return pd.DataFrame(rows)


def test_score_day_finds_the_morning_window():
    # Calm until late morning, then the onshore sea breeze fills in.
    winds = {7: 2, 8: 3, 9: 3, 10: 5, 11: 9, 12: 13, 13: 16, 14: 17, 15: 17, 16: 16}
    day = scoring.score_day(day_frame(winds), MALIBU)
    assert day.rating == "Go"
    assert day.best_time.hour < 11
    assert "before" in day.reason


def test_score_day_returns_none_without_hours():
    empty = day_frame({7: 2}).iloc[0:0]
    assert scoring.score_day(empty, MALIBU) is None


def test_reason_mentions_swell_direction_when_blocked():
    winds = {hour: 3 for hour in range(7, 17)}
    frame = day_frame(winds).assign(swell_dir_deg=290)
    day = scoring.score_day(frame, MALIBU)
    assert day.rating == "Don't Go"
    assert "west" in day.reason
