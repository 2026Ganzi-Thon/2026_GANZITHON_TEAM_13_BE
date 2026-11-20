import io
import json
import os
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APIClient


def provider_place(place_id="1", distance="100", **overrides):
    """Synthetic provider fixture used only by automated tests."""
    document = {
        "id": place_id,
        "place_name": "테스트 공원",
        "address_name": "테스트 지번 주소",
        "road_address_name": "테스트 도로명 주소",
        "y": "37.5",
        "x": "127.0",
        "distance": distance,
        "place_url": f"https://place.map.kakao.com/{place_id}",
    }
    document.update(overrides)
    return document


def provider_response(documents):
    return io.BytesIO(json.dumps({"documents": documents}).encode("utf-8"))


class PlaceRecommendationTests(SimpleTestCase):
    """Exercise the full view/service path with no DB, secrets, or network."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("places:recommendations")
        self.coordinates = {"latitude": "37.5", "longitude": "127.0"}
        self.environment = patch.dict(os.environ, {"KAKAO_REST_API_KEY": "test-only-key"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.http = patch("apps.places.services.urlopen")
        self.urlopen = self.http.start()
        self.addCleanup(self.http.stop)
        self.urlopen.side_effect = [provider_response([]), provider_response([])]

    def get(self, **parameters):
        return self.client.get(self.url, {**self.coordinates, **parameters})

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status)
        self.assertEqual(response.json()["code"], code)
        self.assertNotIn("test-only-key", response.content.decode())

    def test_request_mapping_default_radius_and_timeout(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"places": []})
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertNotIn("Location", response)
        self.assertEqual(self.urlopen.call_count, 2)
        for keyword, call in zip(("공원", "산책로"), self.urlopen.call_args_list):
            request = call.args[0]
            parsed = urlsplit(request.full_url)
            self.assertEqual(parsed.scheme, "https")
            self.assertEqual(parsed.netloc, "dapi.kakao.com")
            self.assertEqual(parsed.path, "/v2/local/search/keyword.json")
            self.assertEqual(parse_qs(parsed.query), {
                "query": [keyword], "x": ["127.0"], "y": ["37.5"],
                "radius": ["500"], "sort": ["distance"], "page": ["1"], "size": ["15"],
            })
            self.assertEqual(request.get_method(), "GET")
            self.assertEqual(request.get_header("Authorization"), "KakaoAK test-only-key")
            self.assertEqual(call.kwargs["timeout"], 3)

    def test_extract_sort_deduplicate_and_limit(self):
        self.urlopen.side_effect = [
            provider_response([provider_place(str(i), str(i * 50)) for i in range(7, 0, -1)]),
            provider_response([provider_place("1", "40"), provider_place("8", "600")]),
        ]
        response = self.get(missionId=11)
        self.assertEqual(response.status_code, 200)
        places = response.json()["places"]
        self.assertEqual([place["placeId"] for place in places], ["1", "2", "3", "4", "5"])
        self.assertEqual(places[0], {
            "placeId": "1", "name": "테스트 공원", "address": "테스트 도로명 주소",
            "latitude": 37.5, "longitude": 127.0, "distanceMeters": 40.0,
            "placeUrl": "https://place.map.kakao.com/1",
        })

    def test_address_falls_back_to_land_address(self):
        self.urlopen.side_effect = [
            provider_response([provider_place(road_address_name="")]), provider_response([]),
        ]
        self.assertEqual(self.get().json()["places"][0]["address"], "테스트 지번 주소")

    def test_same_name_different_provider_ids_are_not_merged(self):
        self.urlopen.side_effect = [
            provider_response([provider_place("1"), provider_place("2")]), provider_response([]),
        ]
        self.assertEqual(len(self.get().json()["places"]), 2)

    def test_radius_boundary_is_included_and_outside_is_excluded(self):
        self.urlopen.side_effect = [
            provider_response([provider_place("1", "500"), provider_place("2", "501")]),
            provider_response([]),
        ]
        self.assertEqual([p["placeId"] for p in self.get().json()["places"]], ["1"])

    def test_mission_search_passes_and_applies_each_supported_radius(self):
        for radius in (500, 1000, 2000):
            with self.subTest(radius=radius):
                self.urlopen.side_effect = [provider_response([
                    provider_place("1", str(radius)),
                    provider_place("2", str(radius + 1)),
                ])]
                response = self.get(missionId=12, radius=radius)
                self.assertEqual(response.status_code, 200)
                self.assertEqual([place["placeId"] for place in response.json()["places"]], ["1"])
                params = parse_qs(urlsplit(self.urlopen.call_args.args[0].full_url).query)
                self.assertEqual(params["radius"], [str(radius)])

    def test_missing_coordinates_are_invalid_before_external_call(self):
        for parameters in ({}, {"latitude": "37.5"}, {"longitude": "127.0"}, {"missionId": 12}):
            with self.subTest(parameters=parameters):
                self.assert_error(self.client.get(self.url, parameters), 400, "invalid_parameters")
        self.urlopen.assert_not_called()

    def test_invalid_coordinate_types_ranges_and_nonfinite_values(self):
        cases = {
            "latitude": ("", "null", "abc", "true", "NaN", "inf", "-Infinity", "90.1", "-90.1"),
            "longitude": ("", "null", "abc", "false", "NaN", "inf", "-Infinity", "180.1", "-180.1"),
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    response = self.get(**{field: value})
                    self.assert_error(response, 400, "invalid_parameters")
                    self.assertIn(field, response.json()["detail"])
        self.urlopen.assert_not_called()

    def test_invalid_radius(self):
        for value in ("", "null", "abc", "true", "NaN", "inf", "0", "-1", "20001", "1.5"):
            with self.subTest(value=value):
                self.assert_error(self.get(radius=value), 400, "invalid_parameters")
        self.urlopen.assert_not_called()

    def test_valid_coordinate_and_radius_boundaries(self):
        for latitude, longitude, radius in ((-90, -180, 1), (90, 180, 20000), (0, 0, 500)):
            with self.subTest(latitude=latitude, longitude=longitude, radius=radius):
                self.urlopen.side_effect = [provider_response([]), provider_response([])]
                self.assertEqual(self.get(latitude=latitude, longitude=longitude, radius=radius).status_code, 200)

    def test_supported_missions_select_their_keywords_without_a_db_lookup(self):
        for mission_id, expected in (
            (11, ["공원", "산책로"]), (12, ["편의점"]), (13, ["도서관"]),
            (17, ["공원"]), (18, ["공원"]),
        ):
            with self.subTest(mission_id=mission_id):
                self.urlopen.reset_mock()
                self.urlopen.side_effect = [provider_response([]) for _ in expected]
                response = self.get(missionId=mission_id)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"places": []})
                queries = [parse_qs(urlsplit(call.args[0].full_url).query)
                           for call in self.urlopen.call_args_list]
                self.assertEqual([query["query"][0] for query in queries], expected)
                self.assertTrue(all("missionId" not in query for query in queries))

    def test_missions_without_search_return_an_empty_list_without_a_key(self):
        with patch.dict(os.environ, {"KAKAO_REST_API_KEY": ""}):
            for mission_id in (*range(1, 11), 14, 15, 16):
                with self.subTest(mission_id=mission_id):
                    response = self.get(missionId=mission_id)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json(), {"places": []})
        self.urlopen.assert_not_called()

    def test_invalid_mission_ids_are_rejected_without_searching(self):
        for mission_id in ("", "unresolved-mission", "11.5", "0", "-1", "19", [12, 13], [12, 12]):
            with self.subTest(mission_id=mission_id):
                response = self.get(missionId=mission_id)
                self.assert_error(response, 400, "invalid_parameters")
                self.assertIn("missionId", response.json()["detail"])
        self.urlopen.assert_not_called()

    def test_missing_or_blank_key_is_configuration_error(self):
        for key in (None, "", "   "):
            with self.subTest(key=key), patch.dict(os.environ):
                if key is None:
                    os.environ.pop("KAKAO_REST_API_KEY", None)
                else:
                    os.environ["KAKAO_REST_API_KEY"] = key
                self.assert_error(self.get(), 503, "places_not_configured")
        self.urlopen.assert_not_called()

    def test_timeouts(self):
        for parameters in ({}, {"missionId": 12}):
            for error in (TimeoutError(), URLError(TimeoutError())):
                with self.subTest(parameters=parameters, error=error):
                    self.urlopen.side_effect = error
                    self.assert_error(self.get(**parameters), 504, "places_provider_timeout")

    def test_provider_authentication_errors(self):
        for parameters in ({}, {"missionId": 12}):
            for status in (401, 403):
                with self.subTest(parameters=parameters, status=status):
                    self.urlopen.side_effect = HTTPError("https://provider.invalid", status, "secret detail", {}, None)
                    self.assert_error(self.get(**parameters), 502, "places_provider_auth_error")

    def test_other_http_errors_do_not_expose_provider_body(self):
        for status in (400, 429, 500):
            with self.subTest(status=status):
                self.urlopen.side_effect = HTTPError("https://provider.invalid", status, "secret detail", {}, None)
                response = self.get()
                self.assert_error(response, 502, "places_provider_error")
                self.assertNotIn("secret detail", response.content.decode())

    def test_network_and_read_errors(self):
        for error in (URLError("DNS failure"), ConnectionResetError()):
            with self.subTest(error=error):
                self.urlopen.side_effect = error
                self.assert_error(self.get(), 502, "places_provider_error")

    def test_invalid_json_or_response_shape(self):
        for body in (b"not json", b"\xff", b"[]", b"{}", b'{"documents":null}', b'{"documents":{}}'):
            with self.subTest(body=body):
                self.urlopen.side_effect = [io.BytesIO(body)]
                self.assert_error(self.get(), 502, "places_provider_error")

    def test_malformed_place_is_provider_error(self):
        for document in (
            None, {}, provider_place(distance="NaN"), provider_place(distance="-1"),
            provider_place(distance=""), provider_place(x="181"), provider_place(y=None),
            provider_place(id=""), provider_place(place_name=""), provider_place(place_url=""),
        ):
            with self.subTest(document=document):
                self.urlopen.side_effect = [provider_response([document])]
                self.assert_error(self.get(), 502, "places_provider_error")

    def test_second_keyword_failure_does_not_return_partial_success(self):
        self.urlopen.side_effect = [provider_response([provider_place()]), TimeoutError()]
        response = self.get()
        self.assert_error(response, 504, "places_provider_timeout")
        self.assertNotIn("places", response.json())

    def test_unsupported_method_does_not_call_provider(self):
        self.assertEqual(self.client.post(self.url, {}, format="json").status_code, 405)
        self.urlopen.assert_not_called()
