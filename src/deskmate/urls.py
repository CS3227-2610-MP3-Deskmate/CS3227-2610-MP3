"""Deskmate's routes (TECHNICAL-SPEC "Routes")."""

from django.urls import path

from deskmate import views
from deskmate.accounts import views as accounts

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("sign-in/", accounts.sign_in, name="sign-in"),
    path("sign-out/", accounts.sign_out, name="sign-out"),
    *(
        path(f"{name}/", accounts.role_page, {"role": role}, name=name)
        for role, name in accounts.ROLE_PAGES.items()
    ),
]
