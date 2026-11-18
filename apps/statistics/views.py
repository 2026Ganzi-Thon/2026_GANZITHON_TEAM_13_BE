from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import SummaryQuerySerializer, SummarySerializer
from .services import summarize_completions


@api_view(['GET'])
def summary(request):
    user = request.user
    if user is None or not user.is_authenticated:
        return Response({"detail": "Authentication required."}, status=401)

    query = SummaryQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    result = summarize_completions(user.pk, query.validated_data["period"])
    return Response(SummarySerializer(result).data)


@api_view(['GET'])
def growth(request):
    return Response({"detail": "Not implemented yet"}, status=501)
