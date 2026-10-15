"""Deskmate's routes (TECHNICAL-SPEC "Routes")."""

from django.urls import path

from deskmate import views

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
]
