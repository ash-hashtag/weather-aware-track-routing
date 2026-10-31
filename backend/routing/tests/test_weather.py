from datetime import UTC, datetime

from routing.services.weather import HourlySeries

T0 = int(datetime(2026, 11, 2, tzinfo=UTC).timestamp())


def series() -> HourlySeries:
    hours = range(4)
    return HourlySeries(
        times=[T0 + h * 3600 for h in hours],
        wind_mph=[10.0, 20.0, 30.0, 40.0],
        gust_mph=[15.0, 25.0, 35.0, 45.0],
        rain_in=[0.0, 0.1, 0.2, 0.3],
        showers_in=[0.0, 0.01, 0.02, 0.03],
        snow_in=[0.0, 0.0, 1.0, 0.0],
        temperature_f=[30.0, 31.0, 32.0, 33.0],
    )


def test_wind_from_nearest_hour_precip_from_containing_hour() -> None:
    w = series().at(datetime(2026, 11, 2, 1, 20, tzinfo=UTC))
    assert w.wind_mph == 20.0  # 01:00 is nearest
    # 01:20 falls in the hour ending 02:00; rain and showers are summed.
    assert w.rain_in_hr == 0.2 + 0.02
    assert w.snow_in_hr == 1.0


def test_lookup_is_clamped_to_series_range() -> None:
    w = series().at(datetime(2026, 11, 3, tzinfo=UTC))
    assert w.wind_mph == 40.0
