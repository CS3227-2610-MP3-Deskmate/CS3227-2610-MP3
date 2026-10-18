"""Deskmate's routes (TECHNICAL-SPEC "Routes")."""

from django.urls import path, re_path

from deskmate import views
from deskmate.accounts import views as accounts
from deskmate.accounts.models import Role
from deskmate.knowledge import views as knowledge
from deskmate.tickets import views as tickets

urlpatterns = [
    path("support/articles/", knowledge.article_list, name="article-list"),
    path("support/articles/new/", knowledge.article_form, name="article-new"),
    re_path(
        r"^support/articles/(?P<article_id>[0-9]+)/edit/$",
        knowledge.article_form,
        name="article-edit",
    ),
    path("requester/tickets/", tickets.ticket_list, name="ticket-list"),
    path("requester/tickets/new/", tickets.ticket_create, name="ticket-new"),
    re_path(
        r"^requester/tickets/(?P<ticket_id>[0-9]+)/$",
        tickets.ticket_detail,
        name="ticket-detail",
    ),
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("sign-in/", accounts.sign_in, name="sign-in"),
    path("sign-out/", accounts.sign_out, name="sign-out"),
    path("demo-workspace/", accounts.demo_workspace, name="demo-workspace"),
    path("requester/", accounts.role_page, {"role": Role.REQUESTER}, name="requester"),
    path(
        "support/", accounts.role_page, {"role": Role.SUPPORT_OFFICER}, name="support"
    ),
]
