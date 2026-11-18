from collections import Counter
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.missions.models import Mission
from apps.sessions.models import MissionSession


SEOUL = ZoneInfo("Asia/Seoul")
WEEKDAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


def _period_bounds(period, local_date):
    if period == "weekly":
        start_date = local_date - timedelta(days=local_date.weekday())
        next_period_date = start_date + timedelta(days=7)
    else:
        start_date = local_date.replace(day=1)
        next_period_date = (start_date + timedelta(days=32)).replace(day=1)
    return start_date, next_period_date


def _completed_sessions(user_id, start_date, next_period_date, as_of):
    start = datetime.combine(start_date, time.min, tzinfo=SEOUL)
    end = datetime.combine(next_period_date, time.min, tzinfo=SEOUL)
    return MissionSession.objects.filter(
        user_id=user_id,
        status=MissionSession.Status.COMPLETED,
        completed_at__gte=start,
        completed_at__lt=end,
        completed_at__lte=as_of,
    )


def summarize_completions(user_id, period):
    as_of = timezone.now()
    start_date, next_period_date = _period_bounds(period, timezone.localdate(as_of, SEOUL))
    completed_times = _completed_sessions(
        user_id, start_date, next_period_date, as_of
    ).values_list("completed_at", flat=True)

    completed_by_weekday = [0] * len(WEEKDAYS)
    active_dates = set()
    for completed_at in completed_times.iterator():
        completed_date = timezone.localdate(completed_at, SEOUL)
        active_dates.add(completed_date)
        completed_by_weekday[completed_date.weekday()] += 1

    return {
        "period": period,
        "time_zone": SEOUL.key,
        "start_date": start_date,
        "end_date": next_period_date - timedelta(days=1),
        "completed_mission_count": sum(completed_by_weekday),
        "active_day_count": len(active_dates),
        "weekday_completions": [
            {"weekday": weekday, "completed_count": count}
            for weekday, count in zip(WEEKDAYS, completed_by_weekday)
        ],
    }


def _percent(numerator, denominator):
    return (Decimal(numerator) * 100 / denominator).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _trend(period, start_date, next_period_date, daily_counts):
    if period == "weekly":
        days = (start_date + timedelta(days=offset) for offset in range(7))
        return [
            {
                "weekday": WEEKDAYS[day.weekday()],
                "date": day,
                "completed_mission_count": daily_counts[day],
            }
            for day in days
        ]

    buckets = []
    week_start = start_date
    while week_start < next_period_date:
        next_week = min(
            week_start + timedelta(days=7 - week_start.weekday()), next_period_date
        )
        buckets.append({
            "week_of_month": len(buckets) + 1,
            "start_date": week_start,
            "end_date": next_week - timedelta(days=1),
            "completed_mission_count": sum(
                daily_counts[week_start + timedelta(days=offset)]
                for offset in range((next_week - week_start).days)
            ),
        })
        week_start = next_week
    return buckets


def summarize_growth(user_id, period):
    as_of = timezone.now()
    start_date, next_period_date = _period_bounds(period, timezone.localdate(as_of, SEOUL))
    previous_start_date, _ = _period_bounds(period, start_date - timedelta(days=1))
    sessions = _completed_sessions(
        user_id, previous_start_date, next_period_date, as_of
    ).values_list("completed_at", "mission__category")

    previous_count = 0
    daily_counts = Counter()
    category_counts = dict.fromkeys(Mission.Category.values, 0)
    for completed_at, category in sessions.iterator():
        completed_date = timezone.localdate(completed_at, SEOUL)
        if completed_date < start_date:
            previous_count += 1
            continue
        daily_counts[completed_date] += 1
        if category in category_counts:
            category_counts[category] += 1

    current_count = sum(daily_counts.values())
    if previous_count:
        growth_rate = _percent(current_count - previous_count, previous_count)
    else:
        growth_rate = None if current_count else 0

    classified_count = sum(category_counts.values())
    return {
        "period": period,
        "time_zone": SEOUL.key,
        "current_period": {
            "start_date": start_date,
            "end_date": next_period_date - timedelta(days=1),
            "completed_mission_count": current_count,
        },
        "previous_period": {
            "start_date": previous_start_date,
            "end_date": start_date - timedelta(days=1),
            "completed_mission_count": previous_count,
        },
        "growth_rate_percent": growth_rate,
        "category_breakdown": [
            {
                "category": category,
                "completed_mission_count": count,
                "percentage": _percent(count, classified_count) if classified_count else 0,
            }
            for category, count in category_counts.items()
        ],
        "trend": _trend(period, start_date, next_period_date, daily_counts),
    }
