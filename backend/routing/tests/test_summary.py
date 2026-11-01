from datetime import UTC, datetime, timedelta

from routing.domain.risk import RiskLevel, Weather
from routing.domain.summary import AssessedPoint, hazards, weather_stats

L, M, H, S = RiskLevel.LOW, RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.SEVERE
T0 = datetime(2026, 11, 2, 8, tzinfo=UTC)


def point(
    i: int,
    level: RiskLevel = L,
    rain: float = 0,
    snow: float = 0,
    wind: float = 5,
    temp: float = 50,
) -> AssessedPoint:
    return AssessedPoint(
        mile=i * 10.0,
        eta=T0 + timedelta(minutes=10 * i),
        weather=Weather(
            wind_mph=wind, gust_mph=wind + 10, rain_in_hr=rain, snow_in_hr=snow, temperature_f=temp
        ),
        level=level,
        reasons=(f"reason {i}",) if level > L else (),
    )


def test_weather_stats_peaks_and_wet_miles() -> None:
    stats = weather_stats(
        [point(0), point(1, rain=0.2, wind=30), point(2), point(3, snow=0.6, temp=28), point(4)]
    )
    assert stats.max_wind_mph == 30
    assert stats.max_gust_mph == 40
    assert stats.max_rain_in_hr == 0.2
    assert stats.max_snow_in_hr == 0.6
    assert (stats.min_temperature_f, stats.max_temperature_f) == (28, 50)
    # Each wet checkpoint makes both adjacent 10-mile stretches wet.
    assert stats.wet_miles == 20
    assert stats.snow_miles == 20


def test_trace_precipitation_is_dry() -> None:
    assert weather_stats([point(0, rain=0.005), point(1)]).wet_miles == 0


def test_hazards_merge_contiguous_elevated_stretches() -> None:
    levels = [L, M, H, L, L, L, S, L]
    points = [point(i, level) for i, level in enumerate(levels)]
    found = hazards(points)
    assert [(h.from_mile, h.to_mile, h.level) for h in found] == [(0, 30, H), (50, 70, S)]
    assert found[0].reasons == ("reason 2",)
    assert found[1].from_eta == T0 + timedelta(minutes=50)


def test_no_hazards_when_all_low() -> None:
    assert hazards([point(0), point(1), point(2)]) == []
