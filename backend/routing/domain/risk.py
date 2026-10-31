"""Weather risk classification, per the assessment's risk and load rules.

Band edges: the lower bound of each band is inclusive (e.g. rain of exactly 0.25 in/hr is
High, wind of exactly 35 mph is High). The Severe band for rain/snow includes its upper bound
because No Travel is defined as strictly greater (">1.00", ">3.0").
"""

from dataclasses import dataclass
from enum import IntEnum


class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return self.name.lower()


@dataclass(frozen=True, slots=True)
class Weather:
    wind_mph: float
    gust_mph: float
    rain_in_hr: float
    snow_in_hr: float
    temperature_f: float


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    level: RiskLevel
    wind: RiskLevel
    rain: RiskLevel
    snow: RiskLevel
    reasons: tuple[str, ...]


def classify_wind(mph: float) -> RiskLevel:
    if mph < 25:
        return RiskLevel.LOW
    if mph < 35:
        return RiskLevel.MODERATE
    if mph < 45:
        return RiskLevel.HIGH
    if mph < 55:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


def classify_rain(in_hr: float) -> RiskLevel:
    if in_hr < 0.10:
        return RiskLevel.LOW
    if in_hr < 0.25:
        return RiskLevel.MODERATE
    if in_hr < 0.50:
        return RiskLevel.HIGH
    if in_hr <= 1.00:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


def classify_snow(in_hr: float) -> RiskLevel:
    if in_hr < 0.5:
        return RiskLevel.LOW
    if in_hr < 1.0:
        return RiskLevel.MODERATE
    if in_hr < 2.0:
        return RiskLevel.HIGH
    if in_hr <= 3.0:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


def load_adjusted_wind(mph: float, load_lbs: float) -> RiskLevel | None:
    """Escalation from the load rules, or None when no load rule applies."""
    if mph >= 55:
        return RiskLevel.NO_TRAVEL
    if mph >= 45 and load_lbs > 30_000:
        return RiskLevel.NO_TRAVEL
    if mph >= 35 and load_lbs > 40_000:
        return RiskLevel.SEVERE
    return None


def assess(weather: Weather, load_lbs: float) -> RiskAssessment:
    wind = classify_wind(weather.wind_mph)
    rain = classify_rain(weather.rain_in_hr)
    snow = classify_snow(weather.snow_in_hr)

    reasons: list[str] = []
    if wind > RiskLevel.LOW:
        reasons.append(f"Wind {weather.wind_mph:.0f} mph ({wind.label})")
    if rain > RiskLevel.LOW:
        reasons.append(f"Rain {weather.rain_in_hr:.2f} in/hr ({rain.label})")
    if snow > RiskLevel.LOW:
        reasons.append(f"Snow {weather.snow_in_hr:.2f} in/hr ({snow.label})")

    level = max(wind, rain, snow)
    loaded = load_adjusted_wind(weather.wind_mph, load_lbs)
    if loaded is not None and loaded > wind:
        reasons.append(
            f"{load_lbs:,.0f} lb load in {weather.wind_mph:.0f} mph wind ({loaded.label})"
        )
        level = max(level, loaded)

    return RiskAssessment(level=level, wind=wind, rain=rain, snow=snow, reasons=tuple(reasons))
