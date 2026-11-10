from django.urls import path

from . import views

app_name = "rest"
urlpatterns = [
    path("guidance", views.guidance, name="guidance"),
    path("breathing", views.breathing, name="breathing"),
    path("records", views.create_record, name="create-record"),
    path("records/today", views.today_records, name="today-records"),
]
