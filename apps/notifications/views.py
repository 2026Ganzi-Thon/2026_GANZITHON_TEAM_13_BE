from rest_framework.decorators import api_view, authentication_classes
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response

from apps.anonymous_auth.authentication import AnonymousBearerAuthentication


@api_view(['GET', 'PATCH'])
@authentication_classes([AnonymousBearerAuthentication])
def notification_settings(request):
    user = request.user
    if user is None or not user.is_authenticated:
        raise NotAuthenticated("Authentication required.")

    return Response({"detail": "Not implemented yet"}, status=501)
