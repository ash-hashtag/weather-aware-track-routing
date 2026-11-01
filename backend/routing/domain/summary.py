"""Per-route weather statistics and hazard stretches, derived from assessed checkpoints.

Uses the same convention as recommend.py: the stretch between two consecutive checkpoints
takes the worse of its two endpoints.
"""

import itertools
from dataclasses import dataclass
from datetime import datetime

from routing.domain.risk import RiskLevel, Weather

# Below this, Open-Meteo's hourly totals are effectively "dry" (rounding noise, drizzle traces).
WET_THRESHOLD_IN_HR = 0.01


@dataclass(frozen=True, slots=True)
class AssessedPoint:
    mile: float
    eta: datetime
    weather: Weather
    level: RiskLevel
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WeatherStats:
    max_wind_mph: float
    max_gust_mph: float
    max_rain_in_hr: float
    max_snow_in_hr: float
    min_temperature_f: float
    max_temperature_f: float
    wet_miles: float
    snow_miles: float


@dataclass(frozen=True, slots=True)
class Hazard:
    """A contiguous stretch at Moderate risk or worse."""

    from_mile: float
    to_mile: float
    from_eta: datetime
    to_eta: datetime
    level: RiskLevel
    reasons: tuple[str, ...]  # from the worst checkpoint in the stretch


def weather_stats(points: list[AssessedPoint]) -> WeatherStats:
    if not points:
        raise ValueError("No checkpoints to summarize")
    weather = [p.weather for p in points]
    wet = snow = 0.0
    for a, b in itertools.pairwise(points):
        miles = b.mile - a.mile
        if max(a.weather.rain_in_hr, b.weather.rain_in_hr) >= WET_THRESHOLD_IN_HR:
            wet += miles
        if max(a.weather.snow_in_hr, b.weather.snow_in_hr) >= WET_THRESHOLD_IN_HR:
            snow += miles
    return WeatherStats(
        max_wind_mph=max(w.wind_mph for w in weather),
        max_gust_mph=max(w.gust_mph for w in weather),
        max_rain_in_hr=max(w.rain_in_hr for w in weather),
        max_snow_in_hr=max(w.snow_in_hr for w in weather),
        min_temperature_f=min(w.temperature_f for w in weather),
        max_temperature_f=max(w.temperature_f for w in weather),
        wet_miles=wet,
        snow_miles=snow,
    )


def hazards(points: list[AssessedPoint]) -> list[Hazard]:
    result: list[Hazard] = []
    run: list[AssessedPoint] = []  # checkpoints spanning the current elevated stretch

    def close_run() -> None:
        if run:
            worst = max(run, key=lambda p: p.level)
            result.append(
                Hazard(
                    from_mile=run[0].mile,
                    to_mile=run[-1].mile,
                    from_eta=run[0].eta,
                    to_eta=run[-1].eta,
                    level=worst.level,
                    reasons=worst.reasons,
                )
            )
            run.clear()

    for a, b in itertools.pairwise(points):
        if max(a.level, b.level) >= RiskLevel.MODERATE:
            if not run:
                run.append(a)
            run.append(b)
        else:
            close_run()
    close_run()
    return result
