from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import services
from .serializers import RecommendationQuerySerializer


@api_view(['GET'])
def recommendations(request):
    """Recommend nearby places with an optional mission context."""
    # Preserve an explicitly blank radius as invalid, rather than treating it
    # as an omitted optional HTML form field and applying the default.
    query = request.query_params
    serializer = RecommendationQuerySerializer(data=query.dict())
    serializer.is_valid()
    errors = serializer.errors
    if len(query.getlist("missionId")) > 1:
        errors["missionId"] = ["Provide missionId only once."]
    if errors:
        return Response(
            {"code": "invalid_parameters", "detail": errors}, status=400
        )

    try:
        places = services.recommend_places(**serializer.validated_data)
    except services.MissingAPIKey:
        return Response(
            {"code": "places_not_configured", "detail": "KAKAO_REST_API_KEY is not configured."},
            status=503,
        )
    except services.ProviderTimeout:
        return Response(
            {"code": "places_provider_timeout", "detail": "Place search provider timed out."},
            status=504,
        )
    except services.ProviderAuthenticationError:
        return Response(
            {"code": "places_provider_auth_error", "detail": "Place search provider rejected authentication or access."},
            status=502,
        )
    except services.ProviderError:
        return Response(
            {"code": "places_provider_error", "detail": "Place search provider request or response failed."},
            status=502,
        )

    return Response({"places": places})
