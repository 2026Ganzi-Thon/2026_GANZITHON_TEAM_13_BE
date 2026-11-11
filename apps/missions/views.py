
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Mission


def serialize_mission(mission, include_image=False):
    result = {
        "missionId": mission.id,
        "title": mission.title,
        "description": mission.description,
        "category": mission.category,
        "durationSeconds": mission.duration_seconds,
    }

    if include_image:
        result["imageUrl"] = mission.image_url

    return result


def get_filtered_missions(request):
    category = request.query_params.get("category")

    if category not in ("INDOOR", "OUTDOOR"):
        return None

    return Mission.objects.filter(
        category=category,
        is_active=True,
    )


@api_view(["GET"])
def random_mission(request):
    missions = get_filtered_missions(request)

    if missions is None:
        return Response(
            {"detail": "category must be INDOOR or OUTDOOR."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    mission = missions.order_by("?").first()

    if mission is None:
        return Response(
            {"detail": "No missions available."},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        serialize_mission(mission, include_image=True),
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
def mission_list(request):
    missions = get_filtered_missions(request)

    if missions is None:
        return Response(
            {"detail": "category must be INDOOR or OUTDOOR."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    result = [
        serialize_mission(mission)
        for mission in missions.order_by("id")
    ]

    return Response(
        {"missions": result},
        status=status.HTTP_200_OK,
    )
