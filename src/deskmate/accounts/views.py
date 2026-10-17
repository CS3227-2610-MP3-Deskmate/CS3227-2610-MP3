"""Signing in and out, each role's placeholder page (ACC-1), creating demo
workspaces (ACC-2), and the rate limits on both (ACC-3)."""

from functools import wraps

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from deskmate.accounts import demo, limits, sessions
from deskmate.accounts.forms import SignInForm
from deskmate.accounts.models import Kind, Role
from deskmate.views import forbidden, message_page

# The URL name of each role's page in deskmate.urls.
ROLE_PAGES = {Role.REQUESTER: "requester", Role.SUPPORT_OFFICER: "support"}
# What the page refusing an attempt of each kind says (ACC-3.2).
REFUSALS = {
    Kind.SIGN_IN: "Too many sign-in attempts. Wait a few minutes, then try again.",
    Kind.CREATION: (
        "Too many demo workspaces have been created. "
        "Wait a few minutes, then try again."
    ),
}


def rate_limited(kind):
    """Check and count a signed-out visitor's POST as an attempt of `kind`, and
    refuse it with 429 if a limit does (ACC-3.1, 3.2).

    Any other request goes straight to the view, uncounted (ACC-3.4).
    """

    def decorator(view):
        @wraps(view)
        def limited(request, *args, **kwargs):
            if request.method == "POST" and not request.user.is_authenticated:
                retry_after = limits.check_and_count(request, kind)
                if retry_after is not None:
                    response = message_page(
                        request, "Too many attempts", REFUSALS[kind], 429
                    )
                    response["Retry-After"] = str(retry_after)
                    return response
            return view(request, *args, **kwargs)

        return limited

    return decorator


@sensitive_post_parameters()
@require_http_methods(["GET", "POST"])
@rate_limited(Kind.SIGN_IN)
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
@rate_limited(Kind.CREATION)
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
