from datetime import timedelta
from typing import Any

import pytest
from django.test import Client
from django.utils import timezone

from routing import views
from routing.services.here import HereError


def payload(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "origin": "Chicago, IL",
        "destination": "Denver, CO",
        "departure": (timezone.now() + timedelta(hours=2)).isoformat(),
        "load_lbs": 35_000,
        "interval_miles": 25,
    }
    return {**data, **overrides}


def post(data: dict[str, Any]) -> Any:
    return Client().post("/api/plan/", data, content_type="application/json")


@pytest.mark.parametrize(
    "overrides",
    [
        {"interval_miles": 15},
        {"load_lbs": 0},
        {"departure": (timezone.now() - timedelta(days=1)).isoformat()},
        {"departure": (timezone.now() + timedelta(days=30)).isoformat()},
    ],
)
def test_plan_rejects_invalid_input(overrides: dict[str, Any]) -> None:
    assert post(payload(**overrides)).status_code == 400


def test_plan_maps_upstream_errors_to_502(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise HereError("boom")

    monkeypatch.setattr(views, "here_client", lambda: None)
    monkeypatch.setattr(views, "plan_trip", fail)
    response = post(payload())
    assert response.status_code == 502
    assert response.json() == {"detail": "boom"}
