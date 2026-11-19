from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET', 'PATCH'])
def notification_settings(request):
    return Response({"detail": "Not implemented yet"}, status=501)
