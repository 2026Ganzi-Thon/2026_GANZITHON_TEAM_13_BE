from django.http import QueryDict
from rest_framework import serializers


class SummaryQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=("weekly", "monthly"))

    def to_internal_value(self, data):
        if isinstance(data, QueryDict) and len(data.getlist("period")) > 1:
            raise serializers.ValidationError({"period": ["Specify the period only once."]})
        return super().to_internal_value(data)


class WeekdayCompletionSerializer(serializers.Serializer):
    weekday = serializers.CharField()
    completedCount = serializers.IntegerField(source="completed_count")


class SummarySerializer(serializers.Serializer):
    period = serializers.CharField()
    timeZone = serializers.CharField(source="time_zone")
    startDate = serializers.DateField(source="start_date")
    endDate = serializers.DateField(source="end_date")
    completedMissionCount = serializers.IntegerField(source="completed_mission_count")
    activeDayCount = serializers.IntegerField(source="active_day_count")
    weekdayCompletions = WeekdayCompletionSerializer(
        source="weekday_completions", many=True
    )
