"""Deskmate's routes (TECHNICAL-SPEC "Routes")."""

from django.urls import path, re_path

from deskmate import views
from deskmate.accounts import views as accounts
from deskmate.accounts.models import Role
from deskmate.knowledge import views as knowledge
from deskmate.tickets import views as tickets

urlpatterns = [
    path(
        "support/create-requester/",
        accounts.create_requester,
        name="create-requester",
    ),
    path(
        "support/reset-requester-password/",
        accounts.reset_requester_password,
        name="reset-requester-password",
    ),
    path("support/articles/", knowledge.article_list, name="article-list"),
    path("support/articles/new/", knowledge.article_form, name="article-new"),
    re_path(
        r"^support/articles/(?P<article_id>[0-9]+)/edit/$",
        knowledge.article_form,
        name="article-edit",
    ),
    path(
        "support/tickets/",
        tickets.ticket_list,
        {"role": Role.SUPPORT_OFFICER},
        name="support-ticket-list",
    ),
    re_path(
        r"^support/tickets/(?P<ticket_id>[0-9]+)/$",
        tickets.ticket_detail,
        {"role": Role.SUPPORT_OFFICER},
        name="support-ticket-detail",
    ),
    re_path(
        r"^support/tickets/(?P<ticket_id>[0-9]+)/resolve/$",
        tickets.ticket_resolve,
        {"role": Role.SUPPORT_OFFICER},
        name="support-ticket-resolve",
    ),
    re_path(
        r"^support/tickets/(?P<ticket_id>[0-9]+)/key-sentences/$",
        tickets.ticket_key_sentences,
        {"role": Role.SUPPORT_OFFICER},
        name="support-ticket-key-sentences",
    ),
    path(
        "requester/articles/",
        knowledge.article_reading_list,
        name="article-read-list",
    ),
    re_path(
        r"^requester/articles/(?P<article_id>[0-9]+)/$",
        knowledge.article_reading,
        name="article-read",
    ),
    path("requester/tickets/", tickets.ticket_list, name="ticket-list"),
    path("requester/tickets/new/", tickets.ticket_create, name="ticket-new"),
    path(
        "requester/tickets/new/suggest-articles/",
        tickets.ticket_suggest_articles,
        name="ticket-suggest-articles",
    ),
    re_path(
        r"^requester/tickets/(?P<ticket_id>[0-9]+)/$",
        tickets.ticket_detail,
        name="ticket-detail",
    ),
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("health/llm", views.llm_probe_no_slash, name="health-llm-no-slash"),
    path("health/llm/", views.llm_probe, name="health-llm"),
    path("sign-in/", accounts.sign_in, name="sign-in"),
    path("sign-out/", accounts.sign_out, name="sign-out"),
    path("demo-workspace/", accounts.demo_workspace, name="demo-workspace"),
    path("requester/", accounts.role_page, {"role": Role.REQUESTER}, name="requester"),
    path(
        "support/", accounts.role_page, {"role": Role.SUPPORT_OFFICER}, name="support"
    ),
]
