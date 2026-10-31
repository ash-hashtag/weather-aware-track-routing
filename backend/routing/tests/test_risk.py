import pytest

from routing.domain.risk import (
    RiskLevel,
    Weather,
    assess,
    classify_rain,
    classify_snow,
    classify_wind,
)

L, M, H, S, N = (
    RiskLevel.LOW,
    RiskLevel.MODERATE,
    RiskLevel.HIGH,
    RiskLevel.SEVERE,
    RiskLevel.NO_TRAVEL,
)


@pytest.mark.parametrize(
    ("mph", "level"),
    [(0, L), (24.9, L), (25, M), (34.9, M), (35, H), (44.9, H), (45, S), (54.9, S), (55, N)],
)
def test_wind_bands(mph: float, level: RiskLevel) -> None:
    assert classify_wind(mph) is level


@pytest.mark.parametrize(
    ("rate", "level"),
    [(0, L), (0.09, L), (0.1, M), (0.24, M), (0.25, H), (0.49, H), (0.5, S), (1.0, S), (1.01, N)],
)
def test_rain_bands(rate: float, level: RiskLevel) -> None:
    assert classify_rain(rate) is level


@pytest.mark.parametrize(
    ("rate", "level"),
    [(0, L), (0.49, L), (0.5, M), (0.99, M), (1.0, H), (1.99, H), (2.0, S), (3.0, S), (3.01, N)],
)
def test_snow_bands(rate: float, level: RiskLevel) -> None:
    assert classify_snow(rate) is level


def weather(wind: float = 0, rain: float = 0, snow: float = 0) -> Weather:
    return Weather(wind_mph=wind, gust_mph=wind, rain_in_hr=rain, snow_in_hr=snow, temperature_f=50)


@pytest.mark.parametrize(
    ("wind", "load", "level"),
    [
        (55, 1_000, N),  # >=55 mph: No Travel for any load
        (45, 30_000, S),  # 45-54 at exactly 30,000 lb: no escalation
        (45, 30_001, N),  # 45-54 + >30,000 lb: No Travel
        (54, 45_000, N),
        (35, 40_000, H),  # 35-44 at exactly 40,000 lb: no escalation
        (35, 40_001, S),  # 35-44 + >40,000 lb: Severe
        (44, 30_001, H),  # the 30k rule only applies from 45 mph
        (34, 80_000, M),  # no load rule below 35 mph
    ],
)
def test_load_rules(wind: float, load: int, level: RiskLevel) -> None:
    assert assess(weather(wind=wind), load).level is level


def test_overall_level_is_worst_condition() -> None:
    result = assess(weather(wind=26, rain=0.3, snow=0.6), 10_000)
    assert (result.wind, result.rain, result.snow) == (M, H, M)
    assert result.level is H
    assert len(result.reasons) == 3


def test_load_reason_is_reported() -> None:
    result = assess(weather(wind=40), 42_000)
    assert result.level is S
    assert any("load" in r for r in result.reasons)
