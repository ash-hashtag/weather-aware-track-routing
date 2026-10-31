from datetime import timedelta
from typing import Any

from django.utils import timezone
from rest_framework import serializers

# Open-Meteo forecasts reach 16 days; leave room for the trip itself.
MAX_DEPARTURE_AHEAD = timedelta(days=10)


class PlanRequestSerializer(serializers.Serializer[dict[str, Any]]):
    origin = serializers.CharField(max_length=200)
    destination = serializers.CharField(max_length=200)
    departure = serializers.DateTimeField()
    load_lbs = serializers.IntegerField(min_value=1, max_value=200_000)
    interval_miles = serializers.ChoiceField(choices=[10, 25, 50], default=25)

    def validate_departure(self, value: Any) -> Any:
        now = timezone.now()
        if value < now - timedelta(hours=1):
            raise serializers.ValidationError("Departure must not be in the past.")
        if value > now + MAX_DEPARTURE_AHEAD:
            raise serializers.ValidationError("Departure must be within the next 10 days.")
        return value


class PlacesQuerySerializer(serializers.Serializer[dict[str, Any]]):
    q = serializers.CharField(min_length=2, max_length=200)
    lat = serializers.FloatField(min_value=-90, max_value=90, default=39.8)
    lng = serializers.FloatField(min_value=-180, max_value=180, default=-98.6)
