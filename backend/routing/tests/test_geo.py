import pytest

from routing.domain.geo import decode_flexible_polyline, haversine_mi, simplify


def test_decode_flexible_polyline_reference_vector() -> None:
    # Example from https://github.com/heremaps/flexible-polyline
    points = decode_flexible_polyline("BFoz5xJ67i1B1B7PzIhaxL7Y")
    assert points == [
        (50.10228, 8.69821),
        (50.10201, 8.69567),
        (50.10063, 8.69150),
        (50.09878, 8.68752),
    ]


def test_decode_flexible_polyline_with_third_dimension() -> None:
    # Example with elevation from the same spec; the third dimension is dropped.
    points = decode_flexible_polyline("BlBoz5xJ67i1BU1B7PUzIhaUxL7YU")
    assert points[0] == (50.10228, 8.69821)
    assert len(points) == 4


def test_haversine_one_degree_latitude() -> None:
    assert haversine_mi((0, 0), (1, 0)) == pytest.approx(69.09, abs=0.01)


def test_simplify_drops_collinear_points() -> None:
    line = [(0.0, float(i)) for i in range(10)]
    assert simplify(line, 0.001) == [(0.0, 0.0), (0.0, 9.0)]


def test_simplify_keeps_corners() -> None:
    line = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
    assert simplify(line, 0.001) == line
