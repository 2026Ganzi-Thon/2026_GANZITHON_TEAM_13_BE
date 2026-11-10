from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def guidance(request):
    return Response({"detail": "Not implemented yet"}, status=501)


@api_view(['GET'])
def breathing(request):
    return Response({"detail": "Not implemented yet"}, status=501)


@api_view(['POST'])
def create_record(request):
    return Response({"detail": "Not implemented yet"}, status=501)


@api_view(['GET'])
def today_records(request):
    return Response({"detail": "Not implemented yet"}, status=501)
