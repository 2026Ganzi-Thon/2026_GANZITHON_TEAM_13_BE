from hashlib import sha256
from secrets import token_urlsafe
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction


def hash_token(token: bytes) -> str:
    return sha256(token).hexdigest()


class AnonymousCredential(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="anonymous_credential",
    )
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    revoked_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    @transaction.atomic
    def issue(cls):
        token = token_urlsafe(32)
        user = get_user_model().objects.create_user(
            username=f"anonymous_{uuid4().hex}",
        )
        cls.objects.create(user=user, token_hash=hash_token(token.encode("ascii")))
        return user, token
