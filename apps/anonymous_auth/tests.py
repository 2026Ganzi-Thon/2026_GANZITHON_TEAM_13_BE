from hashlib import sha256
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.missions.models import Mission

from .models import AnonymousCredential


class AnonymousAuthTests(TestCase):
    def issue(self):
        response = self.client.post("/auth/anonymous")
        self.assertEqual(response.status_code, 201)
        return response

    def authenticate(self, token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def test_issues_new_users_and_only_stores_token_hashes(self):
        first = self.issue()
        first_data = first.json()
        second_data = self.client.post(
            "/auth/anonymous", HTTP_AUTHORIZATION="Bearer stale-token"
        ).json()

        self.assertEqual(first["Cache-Control"], "no-store")
        self.assertEqual(set(first_data), {"userId", "token"})
        self.assertNotEqual(first_data["userId"], second_data["userId"])
        self.assertNotEqual(first_data["token"], second_data["token"])
        for data in (first_data, second_data):
            with self.subTest(user_id=data["userId"]):
                credential = AnonymousCredential.objects.get(user_id=data["userId"])
                self.assertRegex(data["token"], r"^[A-Za-z0-9_-]{43}$")
                self.assertEqual(
                    credential.token_hash, sha256(data["token"].encode("ascii")).hexdigest()
                )
                self.assertFalse(credential.user.has_usable_password())
                self.assertFalse(credential.user.is_staff)
                self.assertFalse(credential.user.is_superuser)
                self.assertIsNone(credential.revoked_at)

    def test_issuance_failure_rolls_back_new_user(self):
        with patch.object(AnonymousCredential.objects, "create", side_effect=IntegrityError):
            with self.assertRaises(IntegrityError):
                AnonymousCredential.issue()

        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(AnonymousCredential.objects.exists())

    def test_bearer_tokens_isolate_session_actions_history_and_statistics(self):
        first = self.issue().json()
        second = self.issue().json()
        owner = self.authenticate(first["token"])
        other = self.authenticate(second["token"])
        mission = Mission.objects.create(
            title="Read", category=Mission.Category.INDOOR, duration_seconds=60
        )

        started = owner.post("/mission-sessions", {"missionId": mission.pk}, format="json")
        self.assertEqual(started.status_code, 201)
        session_id = started.json()["sessionId"]
        for action in ("complete", "cancel"):
            response = other.post(f"/mission-sessions/{session_id}/{action}")
            self.assertEqual(response.status_code, 404)

        completed = owner.post(f"/mission-sessions/{session_id}/complete")
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json()["todayCompletedCount"], 1)

        # A fresh client can reuse the original token after an app restart.
        owner = self.authenticate(first["token"])
        self.assertEqual(other.get("/mission-sessions").json()["records"], [])
        self.assertEqual(owner.get("/mission-sessions").json()["records"][0]["id"], session_id)
        for client, expected in ((owner, 1), (other, 0)):
            summary = client.get("/statistics/summary", {"period": "weekly"})
            self.assertEqual(summary.status_code, 200)
            self.assertEqual(summary.json()["completedMissionCount"], expected)
            growth = client.get("/statistics/growth", {"period": "weekly"})
            self.assertEqual(growth.status_code, 200)
            self.assertEqual(growth.json()["currentPeriod"]["completedMissionCount"], expected)

        self.assertEqual(other.delete("/mission-sessions").status_code, 204)
        self.assertEqual(len(owner.get("/mission-sessions").json()["records"]), 1)

    def test_protected_apis_require_authentication(self):
        operations = (
            ("GET", "/mission-sessions"),
            ("POST", "/mission-sessions"),
            ("DELETE", "/mission-sessions"),
            ("POST", "/mission-sessions/1/complete"),
            ("POST", "/mission-sessions/1/cancel"),
            ("GET", "/statistics/summary"),
            ("GET", "/statistics/growth"),
            ("GET", "/settings/notifications"),
            ("PATCH", "/settings/notifications"),
        )
        for method, path in operations:
            with self.subTest(method=method, path=path):
                response = self.client.generic(method, path)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response["WWW-Authenticate"], "Bearer")
                self.assertEqual(response.json(), {"detail": "Authentication required."})

    def test_rejects_forged_malformed_revoked_and_inactive_credentials(self):
        data = self.issue().json()
        token = data["token"]
        forged = ("a" if token[0] != "a" else "b") + token[1:]
        credential = AnonymousCredential.objects.get(user_id=data["userId"])
        path = "/mission-sessions"

        for header in (f"Bearer {forged}", "Bearer", f"Bearer {token} extra", f"Basic {token}"):
            with self.subTest(header=header):
                response = self.client.get(path, HTTP_AUTHORIZATION=header)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response["WWW-Authenticate"], "Bearer")

        authenticated = self.authenticate(token)
        self.assertEqual(authenticated.get(path).status_code, 200)
        credential.revoked_at = timezone.now()
        credential.save(update_fields=["revoked_at"])
        response = authenticated.get(path)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["WWW-Authenticate"], "Bearer")

        credential.revoked_at = None
        credential.save(update_fields=["revoked_at"])
        get_user_model().objects.filter(pk=data["userId"]).update(is_active=False)
        self.assertEqual(authenticated.get(path).status_code, 401)

    def test_authenticates_both_notification_settings_operations(self):
        client = self.authenticate(self.issue().json()["token"])
        for method in ("GET", "PATCH"):
            with self.subTest(method=method):
                response = client.generic(method, "/settings/notifications")
                self.assertEqual(response.status_code, 501)
                self.assertEqual(response.json(), {"detail": "Not implemented yet"})

    def test_public_apis_remain_available_with_or_without_a_token(self):
        for client in (self.client, self.authenticate("stale-token")):
            self.assertEqual(client.get("/api/health/").json(), {"status": "ok"})
            response = client.get("/missions", {"category": "INDOOR"})
            self.assertEqual(response.status_code, 200)
