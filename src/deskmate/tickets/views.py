"""Workspace ticket submission, reading, resolution and AI actions (RQ-1–5)."""

import re
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from deskmate import llm_gateway
from deskmate.accounts.models import Role
from deskmate.knowledge.models import Article
from deskmate.tickets.forms import ResolutionForm, TicketForm
from deskmate.tickets.models import Ticket
from deskmate.views import forbidden

_KEY_SENTENCE_INSTRUCTIONS = (
    "Extract up to three key sentences from the ticket description in "
    "untrusted_text. Copy each selected sentence exactly, without rewriting, "
    "trimming or adding characters. Each quotation must contain 1 to 1000 "
    "Unicode code points. Return exactly one JSON object with only the field "
    '"sentences", an array of the quoted strings. Return {"sentences": []} if '
    "no suitable sentence is available. Return no explanation or markup."
)
_KEY_SENTENCE_SCHEMA = {
    "type": "object",
    "fields": {
        "sentences": {
            "type": "array",
            "items": {"type": "string", "max_length": 1000},
            "max_items": 3,
        }
    },
}
_ARTICLE_SUGGESTION_INSTRUCTIONS = (
    "Suggest up to three short search phrases that could find knowledge-base "
    "articles relevant to the support request described in untrusted_text. "
    "Base each phrase only on that request. Each phrase must be from 1 to 100 "
    "Unicode code points. Return exactly one JSON object with only the field "
    '"phrases", an array of the phrases. Return {"phrases": []} if no useful '
    "phrase is available. Return no explanation or markup."
)
_ARTICLE_SUGGESTION_SCHEMA = {
    "type": "object",
    "fields": {
        "phrases": {
            "type": "array",
            "items": {"type": "string", "max_length": 100},
            "max_items": 3,
        }
    },
}
_SUGGESTIONS_UNAVAILABLE = "Article suggestions are unavailable. Try again later."
_NO_MATCHING_ARTICLES = "No matching articles found."
_AI_LIMIT_REACHED = "AI limit reached. Try again later."


def _ticket_role(view):
    """Require the route's fixed role, defaulting to Requester."""

    @wraps(view)
    @login_required(login_url="sign-in", redirect_field_name=None)
    def guarded(request, *args, role=Role.REQUESTER, **kwargs):
        """Check the stored role before any ticket is read."""
        if request.user.role != role:
            return forbidden(request, "This page is not for your role.")
        return view(request, *args, **kwargs)

    return guarded


def _navigation(role):
    """Return fixed route names and labels for an authorised ticket reader."""
    support = role == Role.SUPPORT_OFFICER
    return {
        "ticket_list_route": "support-ticket-list" if support else "ticket-list",
        "ticket_detail_route": "support-ticket-detail" if support else "ticket-detail",
        "role_route": "support" if support else "requester",
        "role_label": Role(role).label,
        "can_create_ticket": not support,
        "can_resolve_ticket": support,
    }


def _ticket_id(value):
    """Return `value` as a normalised decimal ticket identifier (Routes).

    The route accepts only ASCII digits, and leading zeros name the same
    ticket. An identifier too long for the record's integer column cannot
    name one, so it gets the same generic 404 as a missing ticket.
    """
    value = value.lstrip("0") or "0"
    if len(value) > 19 or int(value) > 2**63 - 1:
        raise Http404
    return value


@require_GET
@_ticket_role
def ticket_list(request):
    """List only the current stored workspace's tickets in creation order."""
    return render(
        request,
        "tickets/list.html",
        {
            "title": "Tickets",
            "tickets": Ticket.objects.filter(workspace_id=request.user.workspace_id),
            **_navigation(request.user.role),
        },
    )


@require_http_methods(["GET", "POST"])
@_ticket_role
def ticket_create(request):
    """Create a ticket in the current stored workspace (RQ-1.2, RQ-1.5)."""
    form = TicketForm(data=request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.workspace_id = request.user.workspace_id
        ticket.save()
        return redirect("ticket-detail", ticket_id=ticket.pk)
    return _new_ticket_page(request, form)


def _new_ticket_page(request, form, suggestions=None, message=None):
    """Render the New ticket form and, optionally, its suggestion results."""
    return render(
        request,
        "tickets/form.html",
        {
            "title": "New ticket",
            "form": form.redisplay(),
            "suggestions": suggestions,
            "suggestion_message": message,
        },
    )


def _matching_articles(articles, phrases):
    """Return the earliest three of `articles` matching a phrase (RQ-5.3)."""
    folded = [phrase.casefold() for phrase in phrases]
    folded = [phrase for phrase in folded if phrase]
    matches = []
    for article in articles:
        title, body = article.title.casefold(), article.body.casefold()
        if any(phrase in title or phrase in body for phrase in folded):
            matches.append(article)
            if len(matches) == 3:
                break
    return matches


@require_POST
@_ticket_role
def ticket_suggest_articles(request):
    """Suggest workspace articles for a draft, without creating a ticket (RQ-5)."""
    form = TicketForm(data=request.POST)
    if not form.is_valid():
        return _new_ticket_page(request, form)
    articles = list(
        Article.objects.filter(workspace_id=request.user.workspace_id).order_by("pk")
    )
    text = f"{form.cleaned_data['title']}\n\n{form.cleaned_data['description']}"
    result = llm_gateway.call(
        request.user,
        feature="find_a_fix",
        instructions=_ARTICLE_SUGGESTION_INSTRUCTIONS,
        schema=_ARTICLE_SUGGESTION_SCHEMA,
        text=text,
    )
    message = _SUGGESTIONS_UNAVAILABLE
    suggestions = None
    if result["status"] == "refused":
        message = _AI_LIMIT_REACHED
    elif result["status"] == "ok":
        phrases = result["output"]["phrases"]
        if all(phrases):
            suggestions = _matching_articles(articles, phrases)
            message = None if suggestions else _NO_MATCHING_ARTICLES
    return _new_ticket_page(request, form, suggestions, message)


@require_GET
@_ticket_role
def ticket_detail(request, ticket_id):
    """Show a ticket in the current stored workspace, or the generic 404."""
    ticket = get_object_or_404(
        Ticket,
        pk=_ticket_id(ticket_id),
        workspace_id=request.user.workspace_id,
    )
    return render(
        request,
        "tickets/detail.html",
        {"title": "Ticket", "ticket": ticket, **_navigation(request.user.role)},
    )


def _description_fragments(text, quotations):
    """Return source fragments and selection flags, or None for invalid quotes."""
    if any(not quote or quote not in text for quote in quotations):
        return None
    if not quotations:
        return []
    pattern = "|".join(
        re.escape(quote) for quote in sorted(set(quotations), key=len, reverse=True)
    )
    fragments = []
    end = 0
    for match in re.finditer(pattern, text):
        fragments.append((text[end : match.start()], False))
        fragments.append((text[match.start() : match.end()], True))
        end = match.end()
    fragments.append((text[end:], False))
    return fragments


@require_POST
@_ticket_role
def ticket_key_sentences(request, ticket_id):
    """Highlight source quotations for one authorized ticket without saving them."""
    ticket = get_object_or_404(
        Ticket, pk=_ticket_id(ticket_id), workspace_id=request.user.workspace_id
    )
    result = llm_gateway.call(
        request.user,
        feature="key_sentences",
        instructions=_KEY_SENTENCE_INSTRUCTIONS,
        schema=_KEY_SENTENCE_SCHEMA,
        text=ticket.description,
    )
    message = "Key sentences are unavailable. Try again later."
    fragments = None
    if result["status"] == "refused":
        message = "AI limit reached. Try again later."
    elif result["status"] == "ok":
        fragments = _description_fragments(
            ticket.description, result["output"]["sentences"]
        )
        if fragments is not None:
            message = "" if fragments else "No key sentences found."
    return render(
        request,
        "tickets/detail.html",
        {
            "title": "Ticket",
            "ticket": ticket,
            "description_fragments": fragments,
            "key_sentence_message": message,
            **_navigation(request.user.role),
        },
    )


@require_http_methods(["GET", "POST"])
@_ticket_role
def ticket_resolve(request, ticket_id):
    """Save one reply and close only a still-open workspace ticket (RQ-3)."""
    tickets = Ticket.objects.filter(workspace_id=request.user.workspace_id)
    ticket = get_object_or_404(tickets, pk=_ticket_id(ticket_id))
    if not ticket.open:
        return redirect("support-ticket-detail", ticket_id=ticket.pk)
    form = ResolutionForm(data=request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        tickets.filter(pk=ticket.pk, open=True).update(
            reply=form.cleaned_data["reply"], open=False
        )
        return redirect("support-ticket-detail", ticket_id=ticket.pk)
    return render(
        request,
        "tickets/resolve.html",
        {"title": "Resolve ticket", "ticket": ticket, "form": form.redisplay()},
    )
