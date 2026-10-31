"""Geometry helpers: distances, HERE flexible polyline decoding, line simplification."""

import math
from collections.abc import Iterator

type LatLng = tuple[float, float]

EARTH_RADIUS_MI = 3958.7613

_FLEXPOLYLINE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
_FLEXPOLYLINE_VALUES = {char: i for i, char in enumerate(_FLEXPOLYLINE_ALPHABET)}


def haversine_mi(a: LatLng, b: LatLng) -> float:
    lat1, lng1 = math.radians(a[0]), math.radians(a[1])
    lat2, lng2 = math.radians(b[0]), math.radians(b[1])
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def decode_flexible_polyline(encoded: str) -> list[LatLng]:
    """Decode a HERE flexible polyline (https://github.com/heremaps/flexible-polyline).

    Any third dimension (elevation etc.) is decoded and discarded.
    """
    values = _varints(encoded)
    version = next(values)
    if version != 1:
        raise ValueError(f"Unsupported flexible polyline version: {version}")
    header = next(values)
    factor = 10 ** (header & 15)
    has_third_dim = (header >> 4) & 7 != 0

    points: list[LatLng] = []
    lat = lng = 0
    for raw_lat in values:
        lat += _zigzag(raw_lat)
        lng += _zigzag(next(values))
        if has_third_dim:
            next(values)
        points.append((lat / factor, lng / factor))
    return points


def _varints(encoded: str) -> Iterator[int]:
    result = shift = 0
    for char in encoded:
        value = _FLEXPOLYLINE_VALUES[char]
        result |= (value & 0x1F) << shift
        if value & 0x20:
            shift += 5
        else:
            yield result
            result = shift = 0
    if shift:
        raise ValueError("Truncated flexible polyline")


def _zigzag(value: int) -> int:
    return ~(value >> 1) if value & 1 else value >> 1


def simplify(points: list[LatLng], tolerance_deg: float) -> list[LatLng]:
    """Ramer-Douglas-Peucker simplification in degree space (fine for display)."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        max_dist, index = 0.0, -1
        for i in range(start + 1, end):
            dist = _perpendicular_distance(points[i], points[start], points[end])
            if dist > max_dist:
                max_dist, index = dist, i
        if index != -1 and max_dist > tolerance_deg:
            keep[index] = True
            stack.append((start, index))
            stack.append((index, end))
    return [p for p, k in zip(points, keep, strict=True) if k]


def _perpendicular_distance(p: LatLng, a: LatLng, b: LatLng) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dx == 0 and dy == 0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))
