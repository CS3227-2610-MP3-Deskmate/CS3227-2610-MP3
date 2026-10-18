"""Requester ticket submission and reading within the current workspace (RQ-1)."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from deskmate.accounts.models import Role
from deskmate.tickets.forms import TicketForm
from deskmate.tickets.models import Ticket
from deskmate.views import forbidden


def _requester(view):
    """Apply the existing sign-in and role responses to a ticket view."""

    @wraps(view)
    @login_required(login_url="sign-in", redirect_field_name=None)
    def guarded(request, *args, **kwargs):
        """Check the stored role before any ticket is read."""
        if request.user.role != Role.REQUESTER:
            return forbidden(request, "This page is not for your role.")
        return view(request, *args, **kwargs)

    return guarded


def _ticket_id(value):
    """Return `value` as a normalised decimal ticket identifier (Routes).

    The route accepts only ASCII digits, and leading zeros name the same
    ticket. An identifier too long for the record's integer column cannot
    name one, so it gets the same generic 404 as a missing ticket.
    """
    value = value.lstrip("0") or "0"
    if len(value) > 19:
        raise Http404
    return value


@require_GET
@_requester
def ticket_list(request):
    """List only the current stored workspace's tickets in creation order."""
    return render(
        request,
        "tickets/list.html",
        {
            "title": "Tickets",
            "tickets": Ticket.objects.filter(workspace_id=request.user.workspace_id),
        },
    )


@require_http_methods(["GET", "POST"])
@_requester
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
@_requester
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
        {"title": "Ticket", "ticket": ticket},
    )
