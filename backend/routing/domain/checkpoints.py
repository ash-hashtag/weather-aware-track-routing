"""Turn a route geometry + timing into evenly spaced checkpoints with ETAs."""

import bisect
import itertools
from dataclasses import dataclass
from datetime import datetime, timedelta

from routing.domain.geo import LatLng, haversine_mi


@dataclass(frozen=True, slots=True)
class Span:
    """A run of polyline segments starting at vertex `offset` that takes `duration_s` to drive.

    Mirrors HERE's `spans=duration`, so per-segment ETAs reflect road speeds rather than an
    average speed over the whole route.
    """

    offset: int
    duration_s: float


@dataclass(frozen=True, slots=True)
class Track:
    points: list[LatLng]
    cum_miles: list[float]
    cum_seconds: list[float]

    @property
    def length_mi(self) -> float:
        return self.cum_miles[-1]


@dataclass(frozen=True, slots=True)
class Checkpoint:
    mile: float
    position: LatLng
    eta: datetime


def build_track(points: list[LatLng], spans: list[Span], total_duration_s: float) -> Track:
    """Cumulative distance and drive time at every polyline vertex.

    Each span's duration is spread over its segments in proportion to their length. Without
    spans, the total duration is spread over the whole line the same way.
    """
    if len(points) < 2:
        raise ValueError("A track needs at least two points")

    seg_miles = [haversine_mi(a, b) for a, b in itertools.pairwise(points)]
    seg_count = len(seg_miles)
    if not spans:
        spans = [Span(offset=0, duration_s=total_duration_s)]

    seg_seconds = [0.0] * seg_count
    for i, span in enumerate(spans):
        start = span.offset
        end = spans[i + 1].offset if i + 1 < len(spans) else seg_count
        if start >= end:
            continue
        span_miles = sum(seg_miles[start:end])
        for seg in range(start, end):
            share = seg_miles[seg] / span_miles if span_miles > 0 else 1 / (end - start)
            seg_seconds[seg] = span.duration_s * share

    cum_miles = [0.0]
    cum_seconds = [0.0]
    for miles, seconds in zip(seg_miles, seg_seconds, strict=True):
        cum_miles.append(cum_miles[-1] + miles)
        cum_seconds.append(cum_seconds[-1] + seconds)
    return Track(points=points, cum_miles=cum_miles, cum_seconds=cum_seconds)


def sample_checkpoints(track: Track, interval_mi: float, departure: datetime) -> list[Checkpoint]:
    """Checkpoints at 0, interval, 2*interval, … miles, plus the destination."""
    if interval_mi <= 0:
        raise ValueError("interval_mi must be positive")

    targets: list[float] = []
    mile = 0.0
    while mile < track.length_mi:
        targets.append(mile)
        mile += interval_mi
    targets.append(track.length_mi)

    return [_checkpoint_at(track, target, departure) for target in targets]


def _checkpoint_at(track: Track, mile: float, departure: datetime) -> Checkpoint:
    i, t = _locate(track, mile)
    seconds = track.cum_seconds[i - 1] + t * (track.cum_seconds[i] - track.cum_seconds[i - 1])
    return Checkpoint(
        mile=mile,
        position=_position_at(track, mile),
        eta=departure + timedelta(seconds=seconds),
    )


def slice_track(track: Track, start_mi: float, end_mi: float) -> list[LatLng]:
    """The track's geometry between two mile marks, with interpolated endpoints."""
    start = _position_at(track, start_mi)
    end = _position_at(track, end_mi)
    lo = bisect.bisect_right(track.cum_miles, start_mi)
    hi = bisect.bisect_left(track.cum_miles, end_mi)
    return [start, *track.points[lo:hi], end]


def _locate(track: Track, mile: float) -> tuple[int, float]:
    """Segment index i (between vertices i-1 and i) containing `mile`, and the fraction along it."""
    i = max(1, min(bisect.bisect_left(track.cum_miles, mile), len(track.cum_miles) - 1))
    m0, m1 = track.cum_miles[i - 1], track.cum_miles[i]
    return i, (mile - m0) / (m1 - m0) if m1 > m0 else 0.0


def _position_at(track: Track, mile: float) -> LatLng:
    i, t = _locate(track, mile)
    (lat0, lng0), (lat1, lng1) = track.points[i - 1], track.points[i]
    return (lat0 + t * (lat1 - lat0), lng0 + t * (lng1 - lng0))
