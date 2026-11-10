from django.urls import path

from .views.endpoints import SessionCancelView, SessionCollectionView, SessionCompleteView

app_name = "sessions"
urlpatterns = [
    path("mission-sessions", SessionCollectionView.as_view(), name="collection"),
    path("mission-sessions/<str:sessionId>/complete", SessionCompleteView.as_view(), name="complete"),
    path("mission-sessions/<str:sessionId>/cancel", SessionCancelView.as_view(), name="cancel"),
]
