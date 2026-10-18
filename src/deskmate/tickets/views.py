"""Workspace ticket submission, reading and resolution (RQ-1, RQ-2, RQ-3)."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from deskmate.accounts.models import Role
from deskmate.tickets.forms import ResolutionForm, TicketForm
from deskmate.tickets.models import Ticket
from deskmate.views import forbidden


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
    return render(
        request,
        "tickets/form.html",
        {"title": "New ticket", "form": form.redisplay()},
    )


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
