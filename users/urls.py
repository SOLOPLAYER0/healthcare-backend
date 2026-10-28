from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    # Extra (not required by the assignment): exchange a refresh token for a new access token.
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
]
