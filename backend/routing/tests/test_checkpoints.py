from datetime import UTC, datetime, timedelta

import pytest

from routing.domain.checkpoints import Span, build_track, sample_checkpoints
from routing.domain.geo import haversine_mi

DEPARTURE = datetime(2026, 11, 2, 8, tzinfo=UTC)
# Due north along a meridian: 1 degree latitude ~= 69.09 mi.
LINE = [(0.0, 0.0), (0.5, 0.0), (1.0, 0.0)]


def test_checkpoints_every_interval_plus_destination() -> None:
    track = build_track(LINE, [], total_duration_s=3600)
    cps = sample_checkpoints(track, 25, DEPARTURE)
    assert [round(cp.mile) for cp in cps] == [0, 25, 50, 69]
    assert cps[0].position == (0.0, 0.0)
    assert cps[-1].position == pytest.approx((1.0, 0.0))
    assert haversine_mi((0, 0), cps[1].position) == pytest.approx(25, abs=0.01)


def test_eta_without_spans_is_proportional_to_distance() -> None:
    track = build_track(LINE, [], total_duration_s=3600)
    cps = sample_checkpoints(track, 25, DEPARTURE)
    assert cps[-1].eta == DEPARTURE + timedelta(hours=1)
    assert (cps[1].eta - DEPARTURE).total_seconds() == pytest.approx(3600 * 25 / track.length_mi)


def test_eta_follows_span_speeds() -> None:
    # First half takes 3 h, second half 1 h: the midpoint is reached after 3 h, not 2 h.
    track = build_track(LINE, [Span(0, 3 * 3600), Span(1, 3600)], total_duration_s=4 * 3600)
    mid = sample_checkpoints(track, track.length_mi / 2, DEPARTURE)[1]
    assert mid.eta == DEPARTURE + timedelta(hours=3)


def test_interval_longer_than_route() -> None:
    track = build_track(LINE, [], total_duration_s=3600)
    cps = sample_checkpoints(track, 100, DEPARTURE)
    assert [round(cp.mile) for cp in cps] == [0, 69]
