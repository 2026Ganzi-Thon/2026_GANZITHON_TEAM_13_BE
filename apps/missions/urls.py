from django.urls import path

from . import views

app_name = "missions"
urlpatterns = [
    path("missions/random", views.random_mission, name="random-mission"),
    path("missions", views.mission_list, name="mission-list"),
]
