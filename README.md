# Kook Report

A free surf forecast for beginner surfers in Los Angeles that answers one question: should I go surf today?

**Live app:** TODO: add the Streamlit link after deploying

![Screenshot of Kook Report](docs/screenshot.png)

TODO: take a screenshot of the app on a phone, save it as `docs/screenshot.png`, and delete this line.

## What it does

"Kook" is surfer slang for a beginner. Kook Report gives each beach a Go, Maybe or Don't Go rating for today and the next three days, with one sentence explaining why.

- Ratings for four beaches: Malibu Surfrider, Santa Monica Pier, Venice Breakwater and El Porto
- A plain-English reason for every rating, including the best time of day to go
- An accuracy scorecard that compares our past forecasts with what the buoys measured
- An About page that explains the scoring and what it can't tell you
- Free, no account, built to be read on a phone

## Why we built this

TODO (write this ourselves): the story of why we started this. Two or three sentences.

## What we learned from other beginners

TODO (write this ourselves): user research findings. Who we talked to, how many people, what they said they struggle with when reading a surf forecast, and what we changed because of it.

## How the score works

The score is a set of written rules, not a trained model. Every daylight hour at every beach gets up to 100 points:

| Factor | Points | What we look at |
| --- | --- | --- |
| Size | 35 | Estimated breaking height. 1.5 to 3.5 ft is ideal for learning. |
| Wind | 25 | Light or offshore wind is good. Onshore wind makes chop. |
| Swell direction | 20 | Whether the swell comes from an angle the beach can receive. |
| Swell period | 10 | Longer-period swell makes cleaner waves. |
| Tide | 10 | Each beach has a tide range where it breaks best. |

A day is rated on its best three-hour stretch. 70 or more is Go, 45 or more is Maybe, anything lower is Don't Go. Some rules override the points: flat or oversized surf and strong onshore wind are always Don't Go, and a beach can't be a Go on a swell from outside its window.

Swell direction is the part most simple forecasts skip. A buoy can show 4 ft waves while Malibu is flat, because Malibu faces south and Point Dume blocks west swell. Each beach has a best swell window, a partial window where swell arrives at reduced size, and everything else is treated as mostly blocked. We score the primary and secondary swell separately instead of using the blended wave direction.

All beach settings are in [config/beaches.yaml](config/beaches.yaml), with a comment above each beach explaining the reasoning. The scoring is in [src/scoring.py](src/scoring.py) behind one function, `score_hour(conditions, beach)`, so a model can replace the rules later.

## Data sources

Everything is free and needs no API key.

| Data | Source |
| --- | --- |
| Wave height, swell height, period and direction | Open-Meteo Marine API |
| Wind speed and direction | Open-Meteo Weather API |
| Tide predictions | NOAA CO-OPS, Santa Monica station 9410840 |
| Observed waves | NOAA NDBC buoys 46268 (Topanga Nearshore) and 46221 (Santa Monica Bay) |

The app caches API responses for 30 minutes. If the forecast API is down, it falls back to the forecast saved that morning.

## Accuracy scorecard

A GitHub Actions job runs every morning and saves two CSVs to `data/`: the forecast issued that day and the buoy readings from the day before. The scorecard page joins them by hour and shows:

- Mean absolute error of forecast wave height, in feet
- Bias, meaning whether the forecast runs high or low
- Error by lead time, from same-day to three days ahead
- A chart of forecast against buoy readings

Until about two days of overlapping data exist, the page shows a "collecting data" message.

## Limitations

- The beach settings are our best guesses from maps and reading. We are still checking them with local surfers.
- Buoys measure offshore wave height, not breaking height at the beach. The scorecard checks the swell forecast. It does not prove that a Go day was a good day to surf.
- Breaking height is estimated from offshore swell with a simple rule. Sandbars change every few weeks and are not in any free data.
- The wave model grid is several miles wide, so nearby beaches get similar raw forecasts.
- We don't cover crowds, water quality, rip currents or other hazards.
- We have no labeled data on what a good beginner day is, so the rule weights are judgment calls.

## Why not Surfline?

Surfline is built for experienced surfers. It shows a lot of data and expects you to know what it means, and much of the detail is behind a subscription. A beginner needs less: is it small enough, is it clean enough, and when should I go. Kook Report does only that, for free, and shows how often it has been right.

## Run it locally

```
pip install -r requirements.txt
streamlit run app.py
python -m pytest
```

## Roadmap

- Replace the rules with an ML model once we have enough forecast and observation history, plus ratings from real sessions
- More beaches: Zuma, Topanga, Manhattan Beach, Sunset
- A mobile app with a morning notification when a beach turns Go
- Let users report how the session went, to build labels for the model

## Team

TODO (write this ourselves): names, what each of us worked on, and links.

## Credits

Built with Claude as a coding assistant. Released under the MIT License.
