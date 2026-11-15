from django.conf import settings
from django.db import models
from django.utils import timezone


class MissionSession(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.PROTECT,  # Provisional: deletion policy requires team agreement.
        related_name="sessions",
        db_column="mission_id",
    )
    status = models.CharField(max_length=20, choices=Status.choices)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,  # Provisional: deletion policy requires team agreement.
        related_name="mission_sessions",
        db_column="user_id",
    )
