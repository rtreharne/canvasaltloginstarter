from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("auth/request-link", views.request_link, name="request-link"),
    path("auth/magic", views.magic_login, name="magic-login"),
    path("app/home", views.app_home, name="app-home"),
]
