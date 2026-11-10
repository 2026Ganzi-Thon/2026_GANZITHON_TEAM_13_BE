from django.test import SimpleTestCase
from django.urls import Resolver404, URLResolver, get_resolver, resolve, reverse
from rest_framework.test import APIClient


# HTTP operations sharing a path must reach the same dispatcher.
ENDPOINTS = [
    ("/missions/random", "missions:random-mission", {}, {"GET"}),
    ("/missions", "missions:mission-list", {}, {"GET"}),
    ("/mission-sessions", "sessions:collection", {}, {"POST", "GET", "DELETE"}),
    ("/mission-sessions/example-id/complete", "sessions:complete", {"sessionId": "example-id"}, {"POST"}),
    ("/mission-sessions/example-id/cancel", "sessions:cancel", {"sessionId": "example-id"}, {"POST"}),
    ("/rest/guidance", "rest:guidance", {}, {"GET"}),
    ("/rest/breathing", "rest:breathing", {}, {"GET"}),
    ("/rest/records", "rest:create-record", {}, {"POST"}),
    ("/rest/records/today", "rest:today-records", {}, {"GET"}),
    ("/places/recommendations", "places:recommendations", {}, {"GET"}),
    ("/statistics/summary", "statistics:summary", {}, {"GET"}),
    ("/statistics/growth", "statistics:growth", {}, {"GET"}),
    ("/settings/notifications", "notifications:notification-settings", {}, {"GET", "PATCH"}),
]


class ApiRoutingTests(SimpleTestCase):
    # No test database is created; any database query fails this test class.
    def setUp(self):
        self.client = APIClient()

    def test_all_16_operations_return_consistent_json_without_redirect(self):
        self.assertEqual(sum(len(methods) for _, _, _, methods in ENDPOINTS), 16)
        for url, name, kwargs, methods in ENDPOINTS:
            for method in methods:
                with self.subTest(method=method, url=url):
                    self.assertEqual(reverse(name, kwargs=kwargs), url)
                    self.assertEqual(resolve(url).view_name, name)
                    self.assertEqual(resolve(url).kwargs, kwargs)
                    response = self.client.generic(method, url)
                    self.assertEqual(response.status_code, 501)
                    self.assertEqual(response.json(), {"detail": "Not implemented yet"})
                    self.assertEqual(response["Content-Type"], "application/json")
                    self.assertNotIn("Location", response)

    def test_unsupported_methods_return_405(self):
        for url, _, _, methods in ENDPOINTS:
            for method in {"GET", "POST", "PUT", "PATCH", "DELETE"} - methods:
                with self.subTest(method=method, url=url):
                    response = self.client.generic(method, url)
                    self.assertEqual(response.status_code, 405)
                    allowed = {item.strip() for item in response["Allow"].split(",")}
                    self.assertTrue(methods <= allowed)
                    self.assertNotIn(method, allowed)

    def test_each_url_has_one_matching_pattern_for_all_its_methods(self):
        # resolve() alone would hide duplicate patterns after the first match.
        def matching_callbacks(patterns, remaining):
            matches = []
            for pattern in patterns:
                matched = pattern.pattern.match(remaining)
                if matched is None:
                    continue
                tail, _, _ = matched
                if isinstance(pattern, URLResolver):
                    matches.extend(matching_callbacks(pattern.url_patterns, tail))
                elif not tail:
                    matches.append(pattern.callback)
            return matches

        for url, _, _, methods in ENDPOINTS:
            with self.subTest(url=url, methods=methods):
                callbacks = matching_callbacks(get_resolver().url_patterns, url.lstrip("/"))
                self.assertEqual(len(callbacks), 1)
                self.assertIs(callbacks[0], resolve(url).func)
                for method in methods:
                    self.assertEqual(self.client.generic(method, url).status_code, 501)

    def test_trailing_slashes_and_api_prefix_are_not_aliases(self):
        for url, _, _, _ in ENDPOINTS:
            for invalid_url in (url + "/", "/api" + url):
                with self.subTest(url=invalid_url):
                    with self.assertRaises(Resolver404):
                        resolve(invalid_url)
                    response = self.client.get(invalid_url)
                    self.assertEqual(response.status_code, 404)
                    self.assertNotIn("Location", response)

    def test_sessions_dispatch_to_separate_owner_modules(self):
        from unittest.mock import patch

        from rest_framework.response import Response

        cases = [
            ("POST", "/mission-sessions", "actions.start"),
            ("POST", "/mission-sessions/42/complete", "actions.complete"),
            ("POST", "/mission-sessions/42/cancel", "actions.cancel"),
            ("GET", "/mission-sessions", "history.list_records"),
            ("DELETE", "/mission-sessions", "history.delete_records"),
        ]
        for method, url, handler in cases:
            with self.subTest(method=method, url=url):
                with patch("apps.sessions.views." + handler) as mocked:
                    mocked.return_value = Response({"detail": "Not implemented yet"}, status=501)
                    self.assertEqual(self.client.generic(method, url).status_code, 501)
                    mocked.assert_called_once()
