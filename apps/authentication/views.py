import uuid

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken


class GuestCreationThrottle(AnonRateThrottle):
    rate = "10/hour"


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([GuestCreationThrottle])
def create_guest(request):
    User = get_user_model()

    # 로그인 없이 사용할 익명 사용자 생성
    username = f"guest_{uuid.uuid4().hex}"

    user = User(username=username)
    user.set_unusable_password()
    user.save()

    # 익명 사용자에게 JWT 발급
    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "userId": user.id,
            "accessToken": str(refresh.access_token),
            "refreshToken": str(refresh),
        },
        status=status.HTTP_201_CREATED,
    )