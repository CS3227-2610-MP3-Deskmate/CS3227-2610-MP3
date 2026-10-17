"""Signing in and out, each role's placeholder page (ACC-1), and creating demo
workspaces (ACC-2)."""

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from deskmate.accounts import demo, sessions
from deskmate.accounts.forms import SignInForm
from deskmate.accounts.models import Role
from deskmate.views import forbidden

# The URL name of each role's page in deskmate.urls.
ROLE_PAGES = {Role.REQUESTER: "requester", Role.SUPPORT_OFFICER: "support"}


@sensitive_post_parameters()
@require_http_methods(["GET", "POST"])
def sign_in(request):
    """Show the sign-in page, and sign in a visitor who submits an account's details.

    A signed-in user, including one who has just signed in, goes to their own
    role's page, whatever was submitted; `next` is never read (ACC-1.1, 1.3,
    1.5, 1.7). Signing in records its time, from which the session's 8 hours
    run (ACC-1.6).
    """
    if not request.user.is_authenticated:
        data = request.POST if request.method == "POST" else None
        form = SignInForm(request, data=data)
        if not form.is_valid():
            context = {"title": "Sign in", "form": form}
            return render(request, "accounts/sign_in.html", context)
        login(request, form.get_user())
        sessions.record_sign_in(request.session)
    return redirect(ROLE_PAGES[request.user.role])


@require_POST
def sign_out(request):
    """Sign the visitor out, if they were signed in; go to sign-in (ACC-1.2)."""
    logout(request)
    return redirect("sign-in")


@require_POST
def demo_workspace(request):
    """Create a demo workspace and show its accounts' passwords, this once (ACC-2).

    A signed-in user goes to their own role's page and nothing is created
    (ACC-2.7). Nothing the request sends is read, and nothing is put in the
    session (ACC-2.5, 2.6).
    """
    if request.user.is_authenticated:
        return redirect(ROLE_PAGES[request.user.role])
    context = {"title": "Demo workspace created", "accounts": demo.create_workspace()}
    return render(request, "accounts/demo_workspace.html", context)


@require_GET
@login_required(login_url="sign-in", redirect_field_name=None)
def role_page(request, role):
    """Show `role`'s page to a user whose stored role is `role` (ACC-1.2, 1.5).

    Signed-out visitors go to the sign-in page with no query (ACC-1.4), and
    users with the other role get 403.
    """
    if request.user.role != role:
        return forbidden(request, "This page is not for your role.")
    context = {"title": role.label, "username": request.user.username}
    return render(request, "accounts/role_page.html", context)
