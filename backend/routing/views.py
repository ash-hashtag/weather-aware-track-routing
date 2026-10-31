from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from routing.planner import PlanRequest, plan_trip
from routing.serializers import PlacesQuerySerializer, PlanRequestSerializer
from routing.services.here import HereClient, HereError
from routing.services.weather import OpenMeteoClient, WeatherError


def here_client() -> HereClient:
    return HereClient(settings.HERE_API_KEY)


@api_view(["GET"])
def health(_request: Request) -> Response:
    return Response({"status": "ok"})


@api_view(["POST"])
def plan(request: Request) -> Response:
    serializer = PlanRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    try:
        result = plan_trip(
            PlanRequest(
                origin=data["origin"],
                destination=data["destination"],
                departure=data["departure"],
                load_lbs=data["load_lbs"],
                interval_miles=int(data["interval_miles"]),
            ),
            here=here_client(),
            weather=OpenMeteoClient(),
        )
    except (HereError, WeatherError) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    return Response(result)


@api_view(["GET"])
def places(request: Request) -> Response:
    serializer = PlacesQuerySerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    try:
        found = here_client().autosuggest(data["q"], (data["lat"], data["lng"]))
    except HereError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    return Response([{"label": p.label, "lat": p.position[0], "lng": p.position[1]} for p in found])
