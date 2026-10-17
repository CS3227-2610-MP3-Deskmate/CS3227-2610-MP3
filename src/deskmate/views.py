"""Deskmate's views: the placeholder home page, the health check and the
Forbidden page that any route can return."""

from django import db
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def home(request):
    """Render the placeholder home page (PLT-1.1)."""
    return render(request, "deskmate/home.html", {"title": "Deskmate"})


@require_GET
def health(request):
    """Report whether the database answers, as `ok` or `error` (PLT-1.2, 1.3)."""
    try:
        with db.connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except db.Error:
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})


def forbidden(request, message):
    """Return a 403 page titled Forbidden whose only other text is `message`."""
    context = {"title": "Forbidden", "message": message}
    return render(request, "deskmate/forbidden.html", context, status=403)


def csrf_failure(request, reason=""):
    """Refuse a request to any route that failed Django's CSRF checks (ACC-1.8).

    `reason` is never shown, so the page gives no internal details.
    """
    return forbidden(
        request, "This form has expired. Go back, reload the page and try again."
    )
