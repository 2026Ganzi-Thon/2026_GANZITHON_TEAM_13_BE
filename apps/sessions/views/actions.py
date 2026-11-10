from rest_framework.response import Response


def start(request):
    return Response({"detail": "Not implemented yet"}, status=501)


def complete(request, sessionId):
    return Response({"detail": "Not implemented yet"}, status=501)


def cancel(request, sessionId):
    return Response({"detail": "Not implemented yet"}, status=501)
