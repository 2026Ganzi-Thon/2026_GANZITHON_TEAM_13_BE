from rest_framework.decorators import api_view, authentication_classes
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response

from apps.anonymous_auth.authentication import AnonymousBearerAuthentication

from .serializers import GrowthSerializer, SummaryQuerySerializer, SummarySerializer
from .services import summarize_completions, summarize_growth


def _statistics_response(request, summarize, serializer_class):
    user = request.user
    if user is None or not user.is_authenticated:
        raise NotAuthenticated("Authentication required.")

    query = SummaryQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    result = summarize(user.pk, query.validated_data["period"])
    return Response(serializer_class(result).data)


@api_view(['GET'])
@authentication_classes([AnonymousBearerAuthentication])
def summary(request):
    return _statistics_response(request, summarize_completions, SummarySerializer)


@api_view(['GET'])
@authentication_classes([AnonymousBearerAuthentication])
def growth(request):
    return _statistics_response(request, summarize_growth, GrowthSerializer)
