"""Provisional query contract; this does not establish a final team API contract."""
import math

from rest_framework import serializers


class RecommendationQuerySerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    radius = serializers.IntegerField(default=500, min_value=1, max_value=20000)

    def validate(self, attrs):
        errors = {
            field: "A finite coordinate is required."
            for field in ("latitude", "longitude")
            if not math.isfinite(attrs[field])
        }
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
