from datetime import time

from django.conf import settings
from django.db import models


class NotificationSetting(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_setting",
    )
    enabled = models.BooleanField(default=False)
    notification_time = models.TimeField(default=time(9, 0))
