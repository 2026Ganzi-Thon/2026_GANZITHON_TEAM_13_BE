from django.conf import settings
from django.db import models
from django.utils import timezone


class RestRecord(models.Model):
    # 쉬기와 건너뛴 날은 같은 테이블에서 유형으로 구분합니다.
    class Type(models.TextChoices):
        REST = "REST", "Rest"
        SKIP = "SKIP", "Skip"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rest_records")
    type = models.CharField(max_length=4, choices=Type.choices)
    breathing_completed = models.BooleanField(default=False)
    record_date = models.DateField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "rest_records"
        # 동시 요청을 포함해 사용자당 날짜별 기록을 한 건으로 제한합니다.
        constraints = [models.UniqueConstraint(fields=["user", "record_date"], name="rest_record_user_date_unique")]
