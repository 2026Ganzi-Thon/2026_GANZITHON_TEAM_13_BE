"""Provisional query contract; this does not establish a final team API contract."""
import math

from rest_framework import serializers


# Fixed IDs from the canonical catalog in dev's scripts/seed_missions.sql.
MISSION_IDS = range(1, 19)


class RecommendationQuerySerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    radius = serializers.IntegerField(default=500, min_value=1, max_value=20000)
    missionId = serializers.ChoiceField(
        choices=MISSION_IDS,
        source="mission_id",
        required=False,
        error_messages={"invalid_choice": "Enter a mission ID between 1 and 18."},
    )

    def validate(self, attrs):
        errors = {
            field: "A finite coordinate is required."
            for field in ("latitude", "longitude")
            if not math.isfinite(attrs[field])
        }
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
