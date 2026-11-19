from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.response import Response

from .models import NotificationSetting
from .serializers import NotificationSettingSerializer


@api_view(['GET', 'PATCH'])
@parser_classes([JSONParser])
def notification_settings(request):
    user = request.user
    if user is None or not user.is_authenticated:
        return Response({"detail": "Authentication required."}, status=401)

    changes = {}
    if request.method == "PATCH":
        serializer = NotificationSettingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data

    if changes:
        setting, _ = NotificationSetting.objects.update_or_create(user=user, defaults=changes)
    else:
        setting = NotificationSetting.objects.filter(user=user).first() or NotificationSetting()
    return Response(NotificationSettingSerializer(setting).data)
