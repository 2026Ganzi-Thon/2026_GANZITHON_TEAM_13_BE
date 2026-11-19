"""Kakao keyword candidates, without DB access or walkability guarantees.

Search each keyword's first distance-sorted page (15 candidates), merge by
provider ID, and return at most five. distanceMeters is Kakao's distance to the
search center, not a walking route distance. No fallback or synthetic places.
"""
import json
import math
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
DEFAULT_KEYWORDS = ("공원", "산책로")
# Only these seeded missions need a place search.
MISSION_KEYWORDS = {
    11: DEFAULT_KEYWORDS,
    12: ("편의점",),
    13: ("도서관",),
    17: ("공원",),
    18: ("공원",),
}
REQUEST_TIMEOUT_SECONDS = 3
MAX_RESULTS = 5


class MissingAPIKey(Exception):
    pass


class ProviderError(Exception):
    pass


class ProviderAuthenticationError(ProviderError):
    pass


class ProviderTimeout(ProviderError):
    pass


def _search(keyword, latitude, longitude, radius, api_key):
    query = urlencode({
        "query": keyword,
        "x": longitude,
        "y": latitude,
        "radius": radius,
        "sort": "distance",
        "page": 1,
        "size": 15,
    })
    request = Request(
        f"{SEARCH_URL}?{query}",
        headers={"Authorization": f"KakaoAK {api_key}"},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except HTTPError as exc:
        status = exc.code
        exc.close()
        if status in (401, 403):
            raise ProviderAuthenticationError() from exc
        raise ProviderError() from exc
    except TimeoutError as exc:
        raise ProviderTimeout() from exc
    except URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise ProviderTimeout() from exc
        raise ProviderError() from exc
    except (OSError, ValueError, UnicodeError) as exc:
        raise ProviderError() from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("documents"), list):
        raise ProviderError()
    return payload["documents"]


def _normalize(document):
    """Fail explicitly on malformed provider data instead of fabricating values."""
    try:
        if not isinstance(document, dict):
            raise ValueError()
        for field in ("id", "place_name", "place_url"):
            if not isinstance(document[field], str) or not document[field].strip():
                raise ValueError()
        address = document.get("road_address_name") or document["address_name"]
        if not isinstance(address, str):
            raise ValueError()
        values = [document[field] for field in ("y", "x", "distance")]
        if any(isinstance(value, bool) for value in values):
            raise ValueError()
        latitude, longitude, distance = map(float, values)
        if not all(math.isfinite(value) for value in (latitude, longitude, distance)):
            raise ValueError()
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180 and distance >= 0):
            raise ValueError()
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ProviderError() from exc

    return {
        "placeId": document["id"],
        "name": document["place_name"],
        "address": address,
        "latitude": latitude,
        "longitude": longitude,
        "distanceMeters": distance,
        "placeUrl": document["place_url"],
    }


def recommend_places(latitude, longitude, radius=500, *, mission_id=None):
    keywords = DEFAULT_KEYWORDS if mission_id is None else MISSION_KEYWORDS.get(mission_id, ())
    if not keywords:
        return []

    api_key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    if not api_key:
        raise MissingAPIKey()

    places = {}
    for keyword in keywords:
        for document in _search(keyword, latitude, longitude, radius, api_key):
            place = _normalize(document)
            if place["distanceMeters"] > radius:
                continue
            previous = places.get(place["placeId"])
            if previous is None or place["distanceMeters"] < previous["distanceMeters"]:
                places[place["placeId"]] = place

    return sorted(
        places.values(), key=lambda place: (place["distanceMeters"], place["placeId"])
    )[:MAX_RESULTS]
