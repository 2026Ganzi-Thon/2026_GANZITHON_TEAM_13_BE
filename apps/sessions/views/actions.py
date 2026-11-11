
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from apps.missions.models import Mission
from apps.sessions.models import MissionSession

import re
from django.db import transaction

def start(request):
    mission_id = request.data.get("missionId")

    # 1. missionId 입력값 검증
    if (
        isinstance(mission_id, bool)
        or not isinstance(mission_id, int)
        or mission_id <= 0
    ):
        return Response(
            {"detail": "Invalid missionId."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 2. 활성화된 미션 조회
    mission = Mission.objects.filter(
        id=mission_id,
        is_active=True,
    ).first()

    if mission is None:
        return Response(
            {"detail": "Mission not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # 3. 사용자 확인
    user = getattr(request, "user", None)

    if user is None or not user.is_authenticated:
        return Response(
            {"detail": "Authentication required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # 4. 미션 수행 기록 생성
    session = MissionSession.objects.create(
        mission=mission,
        user=user,
        status=MissionSession.Status.IN_PROGRESS,
        started_at=timezone.now(),
    )

    # 5. 확정된 API 명세에 맞춰 응답
    return Response(
        {
            "sessionId": session.id,
            "missionId": mission.id,
            "status": session.status,
            "durationSeconds": mission.duration_seconds,
            "startedAt": session.started_at.isoformat(),
        },
        status=status.HTTP_201_CREATED,
    )



def complete(request, sessionId):
    # 1. sessionId 형식 검증
    session_id_text = str(sessionId)

    if not re.fullmatch(r"[1-9][0-9]*", session_id_text):
        return Response(
            {"detail": "Invalid sessionId."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    session_id = int(session_id_text)

    # 2. 사용자 인증 확인
    user = getattr(request, "user", None)

    if user is None or not user.is_authenticated:
        return Response(
            {"detail": "Authentication required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # 3. 세션 조회 및 완료 처리
    with transaction.atomic():
        session = (
            MissionSession.objects.select_for_update()
            .filter(id=session_id, user=user)
            .first()
        )

        if session is None:
            return Response(
                {"detail": "Mission session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if session.status != MissionSession.Status.IN_PROGRESS:
            return Response(
                {"detail": "Mission session cannot be completed."},
                status=status.HTTP_409_CONFLICT,
            )

        completed_at = timezone.now()

        session.status = MissionSession.Status.COMPLETED
        session.completed_at = completed_at
        session.save(
            update_fields=["status", "completed_at"]
        )

        # 4. 오늘 완료한 미션 개수
        today = timezone.localdate(completed_at)

        today_completed_count = (
            MissionSession.objects.filter(
                user=user,
                status=MissionSession.Status.COMPLETED,
                completed_at__date=today,
            ).count()
        )

    # 5. 확정 명세에 맞춘 응답
    return Response(
        {
            "sessionId": session.id,
            "missionId": session.mission_id,
            "status": session.status,
            "completedAt": session.completed_at.isoformat(),
            "todayCompletedCount": today_completed_count,
        },
        status=status.HTTP_200_OK,
    )


def cancel(request, sessionId):
    session_id_text = str(sessionId)

    if not re.fullmatch(r"[1-9][0-9]*", session_id_text):
        return Response(
            {"detail": "Invalid sessionId."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    session_id = int(session_id_text)

    user = getattr(request, "user", None)

    if user is None or not user.is_authenticated:
        return Response(
            {"detail": "Authentication required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    with transaction.atomic():
        session = (
            MissionSession.objects.select_for_update()
            .filter(id=session_id, user=user)
            .first()
        )

        if session is None:
            return Response(
                {"detail": "Mission session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if session.status != MissionSession.Status.IN_PROGRESS:
            return Response(
                {"detail": "Mission session cannot be cancelled."},
                status=status.HTTP_409_CONFLICT,
            )

        session.status = MissionSession.Status.CANCELLED
        session.cancelled_at = timezone.now()
        session.save(
            update_fields=["status", "cancelled_at"]
        )

    return Response(
        {
            "sessionId": session.id,
            "missionId": session.mission_id,
            "status": session.status,
            "cancelledAt": session.cancelled_at.isoformat(),
        },
        status=status.HTTP_200_OK,
    )
