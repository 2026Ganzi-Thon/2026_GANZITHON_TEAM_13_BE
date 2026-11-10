from django.urls import include, path

urlpatterns = [
    path("api/", include("health.urls")),
    path("", include("apps.missions.urls")),
    path("", include("apps.sessions.urls")),
    path("rest/", include("apps.rest.urls")),
    path("places/", include("apps.places.urls")),
    path("statistics/", include("apps.statistics.urls")),
    path("settings/notifications", include("apps.notifications.urls")),
]
