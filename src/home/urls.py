from django.urls import path
from . import views

app_name = "home"

urlpatterns = [
    path("", views.index, name="index"),
    path("korisnici/", views.users, name="users"),
    path("users/form/", views.create_user_form, name="create_user_form"),
    path("users/create/", views.create_user, name="create_user"),
    path("users/list/", views.user_list, name="user_list"),
    path("users/<int:pk>/edit/form/", views.edit_user_form, name="edit_user_form"),
    path("users/<int:pk>/edit/", views.edit_user, name="edit_user"),
    path("spots/", views.spots, name="spots"),
    path("spots/list/", views.spot_list, name="spot_list"),
    path("spots/form/", views.create_spot_form, name="create_spot_form"),
    path("spots/create/", views.create_spot, name="create_spot"),
    path("spots/<int:pk>/edit/form/", views.edit_spot_form, name="edit_spot_form"),
    path("spots/<int:pk>/edit/", views.edit_spot, name="edit_spot"),
]
