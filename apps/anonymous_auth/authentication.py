from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .models import AnonymousCredential, hash_token


class AnonymousBearerAuthentication(BaseAuthentication):
    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts or parts[0].lower() != b"bearer":
            return None
        if len(parts) != 2:
            raise AuthenticationFailed("Invalid bearer token.")

        credential = (
            AnonymousCredential.objects.select_related("user")
            .filter(
                token_hash=hash_token(parts[1]),
                revoked_at__isnull=True,
                user__is_active=True,
            )
            .first()
        )
        if credential is None:
            raise AuthenticationFailed("Invalid bearer token.")

        return credential.user, credential

    def authenticate_header(self, request):
        return "Bearer"
