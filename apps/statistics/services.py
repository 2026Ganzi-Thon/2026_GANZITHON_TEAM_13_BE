from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.sessions.models import MissionSession


SEOUL = ZoneInfo("Asia/Seoul")
WEEKDAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


def summarize_completions(user_id, period):
    today = timezone.localdate(timezone.now(), SEOUL)
    if period == "weekly":
        start_date = today - timedelta(days=today.weekday())
        next_period_date = start_date + timedelta(days=7)
    else:
        start_date = today.replace(day=1)
        next_period_date = (start_date + timedelta(days=32)).replace(day=1)

    start = datetime.combine(start_date, time.min, tzinfo=SEOUL)
    end = datetime.combine(next_period_date, time.min, tzinfo=SEOUL)
    completed_times = MissionSession.objects.filter(
        user_id=user_id,
        status=MissionSession.Status.COMPLETED,
        completed_at__gte=start,
        completed_at__lt=end,
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
