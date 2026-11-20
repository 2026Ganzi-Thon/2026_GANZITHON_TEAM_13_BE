from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from . import actions, history


class SessionCollectionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return actions.start(request)

    def get(self, request):
        return history.list_records(request)

    def delete(self, request):
        return history.delete_records(request)


class SessionCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, sessionId):
        return actions.complete(request, sessionId)


class SessionCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, sessionId):
        return actions.cancel(request, sessionId)