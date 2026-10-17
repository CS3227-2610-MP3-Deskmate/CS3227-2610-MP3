"""Deskmate's routes (TECHNICAL-SPEC "Routes")."""

from django.urls import path

from deskmate import views
from deskmate.accounts import views as accounts
from deskmate.accounts.models import Role

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("sign-in/", accounts.sign_in, name="sign-in"),
    path("sign-out/", accounts.sign_out, name="sign-out"),
    path("requester/", accounts.role_page, {"role": Role.REQUESTER}, name="requester"),
    path(
        "support/", accounts.role_page, {"role": Role.SUPPORT_OFFICER}, name="support"
    ),
]
