from datetime import time

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import NotificationSetting


class AnonymousNotificationSettingTests(SimpleTestCase):
    def test_get_and_patch_require_the_existing_user_identity(self):
        client = APIClient()
        url = reverse("notifications:notification-settings") + "?userId=1"
        for method in ("get", "patch"):
            with self.subTest(method=method):
                response = getattr(client, method)(url)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "Authentication required."})


class NotificationSettingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="notification-owner")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("notifications:notification-settings")

    def patch_settings(self, payload):
        return self.client.patch(self.url, payload, format="json")

    def test_get_returns_defaults_without_creating_a_row(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"enabled": False, "notificationTime": "09:00"})
        self.assertFalse(NotificationSetting.objects.exists())

    def test_enabled_can_be_toggled_without_resetting_the_time(self):
        NotificationSetting.objects.create(user=self.user, notification_time=time(18, 30))
        for enabled in (True, False):
            with self.subTest(enabled=enabled):
                response = self.patch_settings({"enabled": enabled})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"enabled": enabled, "notificationTime": "18:30"})
                self.assertEqual(NotificationSetting.objects.get(user=self.user).enabled, enabled)

    def test_time_only_patch_keeps_enabled(self):
        NotificationSetting.objects.create(user=self.user, enabled=True)
        for notification_time in ("00:00", "23:59"):
            with self.subTest(notification_time=notification_time):
                response = self.patch_settings({"notificationTime": notification_time})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"enabled": True, "notificationTime": notification_time})

    def test_first_partial_patch_uses_the_default_for_the_omitted_field(self):
        response = self.patch_settings({"enabled": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"enabled": True, "notificationTime": "09:00"})

    def test_changes_persist_across_clients(self):
        payload = {"enabled": True, "notificationTime": "07:05"}
        response = self.patch_settings(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)

        another_client = APIClient()
        another_client.force_authenticate(user=self.user)
        response = another_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)
        self.assertEqual(NotificationSetting.objects.filter(user=self.user).count(), 1)

    def test_empty_patch_does_not_create_or_change_settings(self):
        response = self.patch_settings({})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"enabled": False, "notificationTime": "09:00"})
        self.assertFalse(NotificationSetting.objects.exists())

        NotificationSetting.objects.create(user=self.user, enabled=True, notification_time=time(6, 45))
        response = self.patch_settings({})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"enabled": True, "notificationTime": "06:45"})

    def test_invalid_payloads_are_rejected_without_partial_writes(self):
        setting = NotificationSetting.objects.create(user=self.user)
        for field, values in {
            "enabled": (None, 1, "true", {}),
            "notificationTime": (None, 930, "", "9:30", "09:3", "24:00", "10:60", "09:30:00", "09:30+09:00"),
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    payload = {"enabled": True, "notificationTime": "07:30", field: value}
                    response = self.patch_settings(payload)
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(field, response.json())

        response = self.patch_settings([{"enabled": True}])
        self.assertEqual(response.status_code, 400)
        setting.refresh_from_db()
        self.assertFalse(setting.enabled)
        self.assertEqual(setting.notification_time, time(9, 0))

    def test_owner_is_derived_from_request_user(self):
        other = get_user_model().objects.create_user(username="other-notification-owner")
        other_setting = NotificationSetting.objects.create(user=other, enabled=True, notification_time=time(20, 0))

        response = self.client.get(self.url, {"userId": other.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"enabled": False, "notificationTime": "09:00"})

        response = self.patch_settings({"userId": other.pk, "enabled": False})
        self.assertEqual(response.status_code, 400)
        self.assertIn("userId", response.json())

        response = self.client.patch(self.url + f"?userId={other.pk}", {"notificationTime": "08:00"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(NotificationSetting.objects.get(user=self.user).notification_time, time(8, 0))
        other_setting.refresh_from_db()
        self.assertTrue(other_setting.enabled)
        self.assertEqual(other_setting.notification_time, time(20, 0))
