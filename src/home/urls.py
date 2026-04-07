from django.urls import path
from . import views

app_name = "home"

urlpatterns = [
    path("", views.index, name="index"),
    path("korisnici/", views.users, name="users"),
    path("users/form/", views.create_user_form, name="create_user_form"),
    path("users/create/", views.create_user, name="create_user"),
    path("users/list/", views.user_list, name="user_list"),
    path("users/<int:pk>/", views.user_detail, name="user_detail"),
    path("users/<int:pk>/edit/form/", views.edit_user_form, name="edit_user_form"),
    path("users/<int:pk>/edit/", views.edit_user, name="edit_user"),
    path("users/<int:pk>/payment/form/", views.create_payment_form, name="create_payment_form"),
    path("users/<int:pk>/payment/", views.create_payment, name="create_payment"),
    path("payments/<int:payment_pk>/edit/form/", views.edit_payment_form, name="edit_payment_form"),
    path("payments/<int:payment_pk>/edit/", views.edit_payment, name="edit_payment"),
    path("users/<int:pk>/subscription/form/", views.create_subscription_form, name="create_subscription_form"),
    path("users/<int:pk>/subscription/", views.create_subscription, name="create_subscription"),
    path("subscriptions/<int:sub_pk>/edit/form/", views.edit_subscription_form, name="edit_subscription_form"),
    path("subscriptions/<int:sub_pk>/edit/", views.edit_subscription, name="edit_subscription"),
    path("spots/", views.spots, name="spots"),
    path("spots/list/", views.spot_list, name="spot_list"),
    path("spots/form/", views.create_spot_form, name="create_spot_form"),
    path("spots/create/", views.create_spot, name="create_spot"),
    path("spots/<int:pk>/edit/form/", views.edit_spot_form, name="edit_spot_form"),
    path("spots/<int:pk>/edit/", views.edit_spot, name="edit_spot"),
    path("config/form/", views.pricing_config_form, name="pricing_config_form"),
    path("config/save/", views.save_pricing_config, name="save_pricing_config"),
    path("pomoc/", views.help, name="help"),
]
