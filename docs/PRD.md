# Kook Report: Product Requirements

Status: v1. Last updated November 2026.

## Problem

Beginner surfers in Los Angeles can't easily tell whether today is a good day to go. Existing forecasts such as Surfline are written for experienced surfers: they show swell height, period, direction, wind and tide and leave the interpretation to the reader, and more of the detail is paid. Beginners either skip good days, or drive to the beach and find conditions that are flat, blown out, or too big to be safe.

## Target user

A college student or other beginner in LA who has surfed fewer than about 20 times, rides a soft-top, has no car or limited time, and decides the night before or the morning of. They check on a phone. They don't know what swell period means and shouldn't have to.

TODO: update this once we have user research findings.

## Goals

1. Answer "should I go surf today?" in under ten seconds, with no surf knowledge needed.
2. Explain every rating in one plain sentence so users learn why.
3. Be honest about accuracy by publishing how our forecasts compare with buoy measurements.
4. Stay free, with no login.

## Success metrics

| Metric | Target for the first 8 weeks |
| --- | --- |
| Beginners who can state the rating and reason for a beach after 10 seconds (hallway test) | 8 of 10 |
| Wave height mean absolute error, same-day forecast against buoy | Under 1 ft |
| Days with a successful data collection run | 95% |
| Weekly returning users (Streamlit analytics) | 25 |
| Sessions where a user says the rating matched what they found | 70% of those we ask |

## Requirements for v1

- Go, Maybe or Don't Go for four beaches, today plus three days, with a one-sentence reason.
- Scoring uses wave size, swell period, primary and secondary swell direction, wind and tide. Swell outside a beach's window must lower the score even when wave height looks good.
- Per-beach settings live in one config file so they can be tuned without code changes.
- Accuracy scorecard with charts and error metrics, and a friendly message while data is still being collected.
- About page covering method, data sources and limitations.
- Works on a phone. Handles API failures without crashing.

## Non-goals

- Serving intermediate or advanced surfers. If a day is great for them and dangerous for beginners, we say Don't Go.
- Beaches outside Santa Monica Bay.
- Live cams, crowd levels or water quality.
- Accounts, notifications or a native app.
- A machine learning model. v1 is rule-based so that we can explain it and collect the data a model would need.

## Risks

| Risk | What we are doing about it |
| --- | --- |
| A Go rating sends a beginner into unsafe conditions | Hard caps on size and wind, conservative thresholds, and a visible reminder to check the water first |
| Beach settings are wrong because we are not locals | Reasoning is written next to each setting, and we are reviewing them with local surfers |
| Buoy comparison measures offshore height, not beach conditions | Stated plainly on the scorecard and About pages, and session feedback is on the roadmap |
| A free API changes or goes down | Retries, caching, a fallback to the saved morning forecast, and clear error messages |
| Users don't trust a student project over Surfline | The public accuracy scorecard |
