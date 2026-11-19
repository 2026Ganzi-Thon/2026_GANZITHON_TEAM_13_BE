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


class GrowthPeriodSerializer(serializers.Serializer):
    startDate = serializers.DateField(source="start_date")
    endDate = serializers.DateField(source="end_date")
    completedMissionCount = serializers.IntegerField(source="completed_mission_count")


class CategoryBreakdownSerializer(serializers.Serializer):
    category = serializers.CharField()
    completedMissionCount = serializers.IntegerField(source="completed_mission_count")
    percentage = serializers.FloatField()


class TrendBucketSerializer(serializers.Serializer):
    weekday = serializers.CharField(required=False)
    date = serializers.DateField(required=False)
    weekOfMonth = serializers.IntegerField(source="week_of_month", required=False)
    startDate = serializers.DateField(source="start_date", required=False)
    endDate = serializers.DateField(source="end_date", required=False)
    completedMissionCount = serializers.IntegerField(source="completed_mission_count")


class GrowthSerializer(serializers.Serializer):
    period = serializers.CharField()
    timeZone = serializers.CharField(source="time_zone")
    currentPeriod = GrowthPeriodSerializer(source="current_period")
    previousPeriod = GrowthPeriodSerializer(source="previous_period")
    growthRatePercent = serializers.FloatField(source="growth_rate_percent", allow_null=True)
    categoryBreakdown = CategoryBreakdownSerializer(source="category_breakdown", many=True)
    trend = TrendBucketSerializer(many=True)
