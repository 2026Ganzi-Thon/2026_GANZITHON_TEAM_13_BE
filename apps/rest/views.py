
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import RestRecord


# 안내 문구는 최종 콘텐츠 확정 전까지 사용하는 임시 문구입니다.
GUIDANCE = {
    "REST": "오늘은 잠시 쉬어가도 괜찮아요.",
    "SKIP": "오늘을 건너뛰어도 괜찮아요. 다시 시작할 수 있어요.",
}


def serialize_record(record):
    # API 응답에서는 필드 이름을 camelCase로 전달합니다.
    return {
        "id": record.id,
        "type": record.type,
        "breathingCompleted": record.breathing_completed,
        "recordDate": record.record_date.isoformat(),
        "createdAt": record.created_at.isoformat(),
    }


@api_view(["GET"])
def guidance(request):
    # 요청한 쉬기 유형에 맞는 안내를 반환합니다.
    record_type = request.query_params.get("type")
    if record_type not in GUIDANCE:
        return Response(
            {"detail": "type must be REST or SKIP."},
            status=400,
        )

    return Response({
        "type": record_type,
        "message": GUIDANCE[record_type],
    })


@api_view(["GET"])
def breathing(request):
    # 들숨 4초, 날숨 6초를 세 번 반복합니다.
    return Response({
        "inhaleSeconds": 4,
        "exhaleSeconds": 6,
        "repeatCount": 3,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_record(request):
    # 기록은 인증된 사용자별로 관리합니다.
    user = request.user

    if user is None or not user.is_authenticated:
        return Response(
            {"detail": "Authentication required."},
            status=401,
        )

    record_type = request.data.get("type")

    if record_type not in (RestRecord.Type.REST, RestRecord.Type.SKIP):
        return Response(
            {"detail": "type must be REST or SKIP."},
            status=400,
        )

    completed = request.data.get("breathingCompleted")

    if "breathingCompleted" in request.data and not isinstance(completed, bool):
        return Response(
            {"detail": "breathingCompleted must be a boolean."},
            status=400,
        )

    defaults = {"type": record_type}

    # 완료 여부를 생략하면 기존 값은 유지하고,
    # 새 기록은 모델 기본값을 사용합니다.
    if completed is not None:
        defaults["breathing_completed"] = completed

    # 프로젝트 시간대의 오늘 기록을 생성하거나 기존 기록을 갱신합니다.
    record, created = RestRecord.objects.update_or_create(
        user=user,
        record_date=timezone.localdate(),
        defaults=defaults,
    )

    return Response(
        serialize_record(record),
        status=201 if created else 200,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def today_records(request):
    # 기록이 없는 경우에도 정상 응답에 null을 담습니다.
    user = request.user

    if user is None or not user.is_authenticated:
        return Response(
            {"detail": "Authentication required."},
            status=401,
        )

    record = RestRecord.objects.filter(
        user=user,
        record_date=timezone.localdate(),
    ).first()

    return Response({
        "record": serialize_record(record) if record else None,
    })
