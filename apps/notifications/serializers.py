import re
from collections.abc import Mapping

from rest_framework import serializers


class NotificationTimeField(serializers.TimeField):
    def to_internal_value(self, data):
        if not isinstance(data, str) or not re.fullmatch(r"[0-9]{2}:[0-9]{2}", data):
            self.fail("invalid", format="HH:MM")
        return super().to_internal_value(data)


class NotificationSettingSerializer(serializers.Serializer):
    enabled = serializers.JSONField(required=False)
    notificationTime = NotificationTimeField(
        source="notification_time", format="%H:%M", input_formats=["%H:%M"], required=False,
    )

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown_fields = data.keys() - self.fields.keys()
            if unknown_fields:
                raise serializers.ValidationError({key: ["Unknown field."] for key in unknown_fields})
        return super().to_internal_value(data)

    def validate_enabled(self, value):
        if not isinstance(value, bool):
            raise serializers.ValidationError("Expected a boolean.")
        return value
