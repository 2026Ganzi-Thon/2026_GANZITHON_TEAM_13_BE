from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import create_guest

urlpatterns = [
    path("guest", create_guest, name="guest-create"),
    path("refresh", TokenRefreshView.as_view(), name="token-refresh"),
]