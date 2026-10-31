"""HERE Geocoding/Autosuggest and Routing v8 (truck mode) client."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from routing.domain.checkpoints import Span
from routing.domain.geo import LatLng

LBS_TO_KG = 0.45359237

GEOCODE_URL = "https://geocode.search.hereapi.com/v1/geocode"
AUTOSUGGEST_URL = "https://autosuggest.search.hereapi.com/v1/autosuggest"
ROUTES_URL = "https://router.hereapi.com/v8/routes"


class HereError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Place:
    label: str
    position: LatLng


@dataclass(frozen=True, slots=True)
class RouteSection:
    polyline: str
    spans: list[Span]
    length_m: float
    duration_s: float


@dataclass(frozen=True, slots=True)
class HereRoute:
    sections: list[RouteSection]
    notices: list[str]

    @property
    def length_m(self) -> float:
        return sum(s.length_m for s in self.sections)

    @property
    def duration_s(self) -> float:
        return sum(s.duration_s for s in self.sections)


class HereClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None) -> None:
        if not api_key:
            raise HereError("HERE_API_KEY is not configured")
        self._api_key = api_key
        self._http = http or httpx.Client(timeout=20)

    def geocode(self, query: str) -> Place:
        data = self._get(GEOCODE_URL, {"q": query, "limit": 1})
        items = data.get("items") or []
        if not items:
            raise HereError(f"Could not find a location for {query!r}")
        return _place(items[0])

    def autosuggest(self, query: str, near: LatLng) -> list[Place]:
        data = self._get(
            AUTOSUGGEST_URL,
            {
                "q": query,
                "at": f"{near[0]},{near[1]}",
                "limit": 6,
            },
        )
        return [_place(item) for item in data.get("items") or [] if "position" in item]

    def truck_routes(
        self, origin: LatLng, destination: LatLng, departure: datetime, load_lbs: float
    ) -> list[HereRoute]:
        """Up to three truck routes (fastest + two alternatives)."""
        data = self._get(
            ROUTES_URL,
            {
                "transportMode": "truck",
                "origin": f"{origin[0]},{origin[1]}",
                "destination": f"{destination[0]},{destination[1]}",
                "departureTime": departure.isoformat(timespec="seconds"),
                "alternatives": 2,
                "vehicle[grossWeight]": round(load_lbs * LBS_TO_KG),
                "return": "polyline,summary",
                "spans": "duration",
            },
        )
        routes = [_route(r) for r in data.get("routes") or []]
        if not routes:
            notices = "; ".join(n.get("title", "") for n in data.get("notices") or [])
            raise HereError(f"No truck route found. {notices}".strip())
        return routes

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._http.get(url, params={**params, "apiKey": self._api_key})
        except httpx.HTTPError as exc:
            raise HereError(f"HERE request failed: {exc}") from exc
        if response.status_code != 200:
            raise HereError(f"HERE returned {response.status_code}: {response.text[:200]}")
        result: dict[str, Any] = response.json()
        return result


def _place(item: dict[str, Any]) -> Place:
    pos = item["position"]
    return Place(label=item.get("title", ""), position=(pos["lat"], pos["lng"]))


def _route(route: dict[str, Any]) -> HereRoute:
    sections = [
        RouteSection(
            polyline=s["polyline"],
            spans=[
                Span(offset=sp["offset"], duration_s=sp["duration"]) for sp in s.get("spans", [])
            ],
            length_m=s["summary"]["length"],
            duration_s=s["summary"]["duration"],
        )
        for s in route["sections"]
    ]
    notices = [
        n.get("title", n.get("code", "")) for s in route["sections"] for n in s.get("notices", [])
    ]
    return HereRoute(sections=sections, notices=notices)
