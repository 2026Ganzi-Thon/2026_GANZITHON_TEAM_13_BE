from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def summary(request):
    return Response({"detail": "Not implemented yet"}, status=501)


@api_view(['GET'])
def growth(request):
    return Response({"detail": "Not implemented yet"}, status=501)
