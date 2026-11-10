from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health_check(request):
    """Report application liveness without querying the database."""
    return Response({"status": "ok"})
