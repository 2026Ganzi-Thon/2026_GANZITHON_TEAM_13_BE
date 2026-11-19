from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import AnonymousCredential


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def issue_anonymous_token(request):
    user, token = AnonymousCredential.issue()
    return Response(
        {"userId": user.pk, "token": token},
        status=status.HTTP_201_CREATED,
        headers={"Cache-Control": "no-store"},
    )
