"""Orchestrates a trip plan: geocode → truck routes → checkpoints → weather → risk → ranking."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from routing.domain.checkpoints import Checkpoint, Span, Track, build_track, sample_checkpoints
from routing.domain.geo import LatLng, decode_flexible_polyline, simplify
from routing.domain.recommend import RouteCandidate, explain, rank, summarize_risk
from routing.domain.risk import RiskAssessment, RiskLevel, Weather, assess
from routing.services.here import HereClient, HereRoute, Place
from routing.services.weather import OpenMeteoClient

METERS_PER_MILE = 1609.344
# ~30 m; keeps the map line faithful while cutting payload size by ~10x.
DISPLAY_TOLERANCE_DEG = 0.0003


@dataclass(frozen=True, slots=True)
class PlanRequest:
    origin: str
    destination: str
    departure: datetime
    load_lbs: int
    interval_miles: int


class PlaceOut(TypedDict):
    label: str
    lat: float
    lng: float


class WeatherOut(TypedDict):
    wind_mph: float
    gust_mph: float
    rain_in_hr: float
    snow_in_hr: float
    temperature_f: float


class CheckpointOut(TypedDict):
    mile: float
    lat: float
    lng: float
    eta: str
    weather: WeatherOut
    risk: str
    risk_score: int
    reasons: list[str]


class RouteOut(TypedDict):
    id: int
    rank: int
    recommended: bool
    distance_miles: float
    duration_s: float
    departure: str
    arrival: str
    miles_by_risk: dict[str, float]
    average_risk: float
    max_risk: str
    geometry: list[tuple[float, float]]  # [lng, lat], GeoJSON order
    checkpoints: list[CheckpointOut]
    notices: list[str]


class PlanOut(TypedDict):
    origin: PlaceOut
    destination: PlaceOut
    departure: str
    load_lbs: int
    interval_miles: int
    recommended_route_id: int
    recommendation_reason: str
    routes: list[RouteOut]


def plan_trip(request: PlanRequest, here: HereClient, weather: OpenMeteoClient) -> PlanOut:
    origin = here.geocode(request.origin)
    destination = here.geocode(request.destination)
    departure = request.departure.astimezone(UTC)
    routes = here.truck_routes(origin.position, destination.position, departure, request.load_lbs)

    tracks = [_track(route) for route in routes]
    checkpoints = [sample_checkpoints(t, request.interval_miles, departure) for t in tracks]

    flat = [cp for cps in checkpoints for cp in cps]
    series = weather.hourly(
        [cp.position for cp in flat],
        start=min(cp.eta for cp in flat).date(),
        # +1 h so the hour containing the final ETA is always inside the range.
        end=(max(cp.eta for cp in flat) + timedelta(hours=1)).date(),
    )
    weather_iter = iter(series)
    assessed: list[list[tuple[Checkpoint, Weather, RiskAssessment]]] = []
    for route, track, cps in zip(routes, tracks, checkpoints, strict=True):
        # Report miles on HERE's road distance rather than our straight-segment estimate.
        scale = route.length_m / METERS_PER_MILE / track.length_mi
        rows = []
        for cp in cps:
            w = next(weather_iter).at(cp.eta)
            rows.append((replace(cp, mile=cp.mile * scale), w, assess(w, request.load_lbs)))
        assessed.append(rows)

    candidates = [
        RouteCandidate(
            risk=summarize_risk([(cp.mile, a.level) for cp, _, a in rows]),
            duration_s=route.duration_s,
        )
        for route, rows in zip(routes, assessed, strict=True)
    ]
    order = rank(candidates)
    best = order[0]
    runner_up = candidates[order[1]] if len(order) > 1 else None

    return PlanOut(
        origin=_place_out(origin),
        destination=_place_out(destination),
        departure=departure.isoformat(),
        load_lbs=request.load_lbs,
        interval_miles=request.interval_miles,
        recommended_route_id=best,
        recommendation_reason=explain(candidates[best], runner_up),
        routes=[
            _route_out(
                i, order.index(i) + 1, i == best, route, track, rows, candidates[i], departure
            )
            for i, (route, track, rows) in enumerate(zip(routes, tracks, assessed, strict=True))
        ],
    )


def _track(route: HereRoute) -> Track:
    """One track across all sections, with span offsets shifted onto the joined polyline."""
    points: list[LatLng] = []
    spans: list[Span] = []
    for section in route.sections:
        decoded = decode_flexible_polyline(section.polyline)
        # Consecutive sections share their joining vertex; keep it once.
        shift = max(len(points) - 1, 0)
        if points:
            decoded = decoded[1:]
        points.extend(decoded)
        spans.extend(Span(offset=s.offset + shift, duration_s=s.duration_s) for s in section.spans)
    return build_track(points, spans, route.duration_s)


def _place_out(place: Place) -> PlaceOut:
    return PlaceOut(label=place.label, lat=place.position[0], lng=place.position[1])


def _route_out(
    route_id: int,
    route_rank: int,
    recommended: bool,
    route: HereRoute,
    track: Track,
    rows: list[tuple[Checkpoint, Weather, RiskAssessment]],
    candidate: RouteCandidate,
    departure: datetime,
) -> RouteOut:
    risk = candidate.risk
    return RouteOut(
        id=route_id,
        rank=route_rank,
        recommended=recommended,
        distance_miles=round(route.length_m / METERS_PER_MILE, 1),
        duration_s=route.duration_s,
        departure=departure.isoformat(),
        arrival=(departure + timedelta(seconds=route.duration_s)).isoformat(),
        miles_by_risk={level.label: round(risk.miles(level), 1) for level in RiskLevel},
        average_risk=round(risk.average_risk, 3),
        max_risk=risk.max_level.label,
        geometry=[
            (round(lng, 5), round(lat, 5))
            for lat, lng in simplify(track.points, DISPLAY_TOLERANCE_DEG)
        ],
        checkpoints=[_checkpoint_out(cp, w, a) for cp, w, a in rows],
        notices=route.notices,
    )


def _checkpoint_out(cp: Checkpoint, w: Weather, a: RiskAssessment) -> CheckpointOut:
    return CheckpointOut(
        mile=round(cp.mile, 1),
        lat=round(cp.position[0], 5),
        lng=round(cp.position[1], 5),
        eta=cp.eta.isoformat(timespec="seconds"),
        weather=WeatherOut(
            wind_mph=w.wind_mph,
            gust_mph=w.gust_mph,
            rain_in_hr=w.rain_in_hr,
            snow_in_hr=w.snow_in_hr,
            temperature_f=w.temperature_f,
        ),
        risk=a.level.label,
        risk_score=int(a.level),
        reasons=list(a.reasons),
    )
