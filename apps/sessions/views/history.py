from datetime import timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework.response import Response

from apps.sessions.models import MissionSession


SEOUL = ZoneInfo("Asia/Seoul")


def _period_bounds(period):
    now = timezone.localtime(timezone.now(), SEOUL)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        start = midnight - timedelta(days=midnight.weekday())
        return start, start + timedelta(days=7)

    start = midnight.replace(day=1)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start, end


def _serialize_datetime(value):
    return timezone.localtime(value, SEOUL).isoformat() if value is not None else None


def list_records(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return Response({"detail": "Authentication required."}, status=401)

    session_status = request.query_params.get("status")
    period = request.query_params.get("period")
    if session_status is not None and session_status not in MissionSession.Status.values:
        return Response({"detail": "Invalid status."}, status=400)
    if period is not None and period not in ("week", "month", "all"):
        return Response({"detail": "Invalid period."}, status=400)

    records = MissionSession.objects.filter(user=user)
    if session_status is not None:
        records = records.filter(status=session_status)
    if period in ("week", "month"):
        start, end = _period_bounds(period)
        records = records.filter(started_at__gte=start, started_at__lt=end)

    return Response({
        "records": [
            {
                "id": record.id,
                "missionId": record.mission_id,
                "status": record.status,
                "startedAt": _serialize_datetime(record.started_at),
                "completedAt": _serialize_datetime(record.completed_at),
                "cancelledAt": _serialize_datetime(record.cancelled_at),
            }
            for record in records.order_by("-started_at", "-id")
        ]
    })


def delete_records(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return Response({"detail": "Authentication required."}, status=401)

    MissionSession.objects.filter(user=user).delete()
    return Response(status=204)
