from django.urls import path

from . import views

app_name = "places"
urlpatterns = [
    path("recommendations", views.recommendations, name="recommendations"),
]
