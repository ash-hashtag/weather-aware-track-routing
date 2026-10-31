"""Open-Meteo hourly forecast client, with the hour lookup used at each checkpoint ETA."""

import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import httpx
from django.core.cache import cache

from routing.domain.geo import LatLng
from routing.domain.risk import Weather

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = ("wind_speed_10m", "wind_gusts_10m", "rain", "showers", "snowfall", "temperature_2m")
BATCH_SIZE = 100
CACHE_TTL_S = 30 * 60
# ~1 km; checkpoints closer than this share one forecast.
COORD_PRECISION = 2


class WeatherError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class HourlySeries:
    """Hourly values at one location. Times are unix seconds (UTC) on the hour.

    `rain`, `showers` and `snowfall` are totals for the hour *ending* at each timestamp, which
    is what makes them usable as in/hr rates.
    """

    times: list[int]
    wind_mph: list[float]
    gust_mph: list[float]
    rain_in: list[float]
    showers_in: list[float]
    snow_in: list[float]
    temperature_f: list[float]

    def at(self, moment: datetime) -> Weather:
        """Weather at `moment`: instantaneous values from the nearest hour, precipitation from
        the hour that contains it."""
        hours = (moment.timestamp() - self.times[0]) / 3600
        last = len(self.times) - 1
        nearest = max(0, min(round(hours), last))
        containing = max(0, min(math.ceil(hours), last))
        return Weather(
            wind_mph=self.wind_mph[nearest],
            gust_mph=self.gust_mph[nearest],
            rain_in_hr=self.rain_in[containing] + self.showers_in[containing],
            snow_in_hr=self.snow_in[containing],
            temperature_f=self.temperature_f[nearest],
        )


class OpenMeteoClient:
    def __init__(self, http: httpx.Client | None = None) -> None:
        self._http = http or httpx.Client(timeout=30)

    def hourly(self, locations: list[LatLng], start: date, end: date) -> list[HourlySeries]:
        """Hourly series for each location (same order), covering whole UTC days start..end."""
        keys = [_round(loc) for loc in locations]
        found: dict[LatLng, HourlySeries] = {}
        missing: list[LatLng] = []
        for key in dict.fromkeys(keys):
            cached = cache.get(_cache_key(key, start, end))
            if isinstance(cached, HourlySeries):
                found[key] = cached
            else:
                missing.append(key)

        for i in range(0, len(missing), BATCH_SIZE):
            batch = missing[i : i + BATCH_SIZE]
            for key, series in zip(batch, self._fetch(batch, start, end), strict=True):
                found[key] = series
                cache.set(_cache_key(key, start, end), series, CACHE_TTL_S)

        return [found[key] for key in keys]

    def _fetch(self, batch: list[LatLng], start: date, end: date) -> list[HourlySeries]:
        params = {
            "latitude": ",".join(str(lat) for lat, _ in batch),
            "longitude": ",".join(str(lng) for _, lng in batch),
            "hourly": ",".join(HOURLY_VARS),
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "temperature_unit": "fahrenheit",
            "timezone": "GMT",
            "timeformat": "unixtime",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
        try:
            response = self._http.get(FORECAST_URL, params=params)
        except httpx.HTTPError as exc:
            raise WeatherError(f"Open-Meteo request failed: {exc}") from exc
        if response.status_code != 200:
            raise WeatherError(f"Open-Meteo returned {response.status_code}: {response.text[:200]}")

        payload: Any = response.json()
        items: list[dict[str, Any]] = payload if isinstance(payload, list) else [payload]
        return [_series(item["hourly"]) for item in items]


def _series(hourly: dict[str, Any]) -> HourlySeries:
    def values(name: str) -> list[float]:
        return [float(v) if v is not None else 0.0 for v in hourly[name]]

    return HourlySeries(
        times=[int(t) for t in hourly["time"]],
        wind_mph=values("wind_speed_10m"),
        gust_mph=values("wind_gusts_10m"),
        rain_in=values("rain"),
        showers_in=values("showers"),
        snow_in=values("snowfall"),
        temperature_f=values("temperature_2m"),
    )


def _round(loc: LatLng) -> LatLng:
    return (round(loc[0], COORD_PRECISION), round(loc[1], COORD_PRECISION))


def _cache_key(loc: LatLng, start: date, end: date) -> str:
    return f"om:{loc[0]}:{loc[1]}:{start}:{end}"
