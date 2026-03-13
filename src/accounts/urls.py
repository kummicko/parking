from django.urls import path
from . import views

app_name = "accounts"


urlpatterns = [
    # The name='login' is crucial as it's referenced by LOGIN_URL in settings.py
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
]
