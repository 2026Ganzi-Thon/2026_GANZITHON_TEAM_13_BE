from django.urls import path

from . import views

app_name = "statistics"
urlpatterns = [
    path("summary", views.summary, name="summary"),
    path("growth", views.growth, name="growth"),
]
