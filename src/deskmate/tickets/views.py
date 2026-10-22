"""Workspace ticket submission, reading, resolution and AI actions (RQ-1–6)."""

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
# RQ-6's signs 1-4, looked for in a prepared field, and sign 5, in a saved one.
_SIGNS = (
    re.compile(
        r"\b(?:ignore|disregard|forget|override)\s+(?:(?:all|any|my|of|the|your)\s+)"
        r"{0,3}(?:previous|prior|above|earlier|preceding)\s+"
        r"(?:instructions?|prompts?|rules?)\b"
    ),
    re.compile(r"(?:^|\n)[ \t]*(?:system|assistant)[ \t]*:"),
    re.compile(r"<\|[a-z0-9_]{1,40}\|>"),
    re.compile("untrusted_text"),
)
_HIDDEN = re.compile(
    r"[\u200b\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff\U000e0001"
    r"\U000e0020-\U000e007f]"
)
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


def _possible_manipulation(title, description):
    """Return whether a saved ticket title or description shows an RQ-6 sign.

    The flag is a hint, not a verdict: the fixed signs can flag harmless text
    and miss manipulation. Each field is checked on its own.
    """
    for field in (title, description):
        prepared = llm_gateway.remove_guarded(field).casefold()
        if _HIDDEN.search(field) or any(sign.search(prepared) for sign in _SIGNS):
            return True
    return False


@require_GET
@_ticket_role
def ticket_list(request):
    """List only the current stored workspace's tickets in creation order."""
    tickets = list(Ticket.objects.filter(workspace_id=request.user.workspace_id))
    flagged = set()
    if request.user.role == Role.SUPPORT_OFFICER:
        flagged = {
            ticket.pk
            for ticket in tickets
            if _possible_manipulation(ticket.title, ticket.description)
        }
    return render(
        request,
        "tickets/list.html",
        {
            "title": "Tickets",
            "tickets": tickets,
            "flagged_tickets": flagged,
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


# How many articles one keyset page reads, so a large workspace is never
# materialised in one query while matching stops as soon as three match.
_ARTICLE_PAGE = 100
_ARTICLE_PHRASE_STOPWORDS = {
    "and",
    "are",
    "but",
    "can",
    "could",
    "for",
    "from",
    "has",
    "have",
    "help",
    "how",
    "not",
    "please",
    "should",
    "that",
    "the",
    "their",
    "them",
    "there",
    "these",
    "they",
    "this",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "will",
    "with",
    "won",
    "wont",
    "would",
    "you",
    "your",
}


def _alphanumeric_words(text):
    """Yield whole alphanumeric words after folding the complete input (RQ-5.3)."""
    word = []
    for character in text.casefold():
        if character.isalnum():
            word.append(character)
        elif word:
            yield "".join(word)
            word.clear()
    if word:
        yield "".join(word)


def _matching_articles(workspace_id, phrases):
    """Return the earliest three articles sharing a retained phrase word (RQ-5.3).

    Articles are read in ascending identity, one page at a time, and the read
    stops as soon as three match. A phrase list with no retained words matches
    nothing and reads no article.
    """
    retained_words = {
        word
        for phrase in phrases
        for word in _alphanumeric_words(phrase)
        if len(word) >= 3 and word not in _ARTICLE_PHRASE_STOPWORDS
    }
    if not retained_words:
        return []
    matches = []
    last_pk = None
    while len(matches) < 3:
        page = Article.objects.filter(workspace_id=workspace_id)
        if last_pk is not None:
            page = page.filter(pk__gt=last_pk)
        articles = list(page.order_by("pk").only("pk", "title", "body")[:_ARTICLE_PAGE])
        if not articles:
            break
        for article in articles:
            if any(
                word in retained_words
                for source in (article.title, article.body)
                for word in _alphanumeric_words(source)
            ):
                matches.append(article)
                if len(matches) == 3:
                    break
        last_pk = articles[-1].pk
    return matches


@require_POST
@_ticket_role
def ticket_suggest_articles(request):
    """Suggest workspace articles for a draft, without creating a ticket (RQ-5)."""
    form = TicketForm(data=request.POST)
    if not form.is_valid():
        return _new_ticket_page(request, form)
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
            suggestions = _matching_articles(request.user.workspace_id, phrases)
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
    flagged = request.user.role == Role.SUPPORT_OFFICER and _possible_manipulation(
        ticket.title, ticket.description
    )
    return render(
        request,
        "tickets/detail.html",
        {
            "title": "Ticket",
            "ticket": ticket,
            "flagged": flagged,
            **_navigation(request.user.role),
        },
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
            "flagged": _possible_manipulation(ticket.title, ticket.description),
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
