from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    # 사용자 모델에 의존하며 날짜별 중복을 막는 제약을 함께 생성합니다.
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="RestRecord",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("type", models.CharField(choices=[("REST", "Rest"), ("SKIP", "Skip")], max_length=4)),
                ("breathing_completed", models.BooleanField(default=False)),
                ("record_date", models.DateField()),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rest_records", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "rest_records", "constraints": [models.UniqueConstraint(fields=("user", "record_date"), name="rest_record_user_date_unique")]},
        ),
    ]
