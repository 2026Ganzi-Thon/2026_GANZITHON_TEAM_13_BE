from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def random_mission(request):
    return Response({"detail": "Not implemented yet"}, status=501)


@api_view(['GET'])
def mission_list(request):
    return Response({"detail": "Not implemented yet"}, status=501)
