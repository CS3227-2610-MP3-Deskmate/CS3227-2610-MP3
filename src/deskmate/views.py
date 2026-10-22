"""Deskmate's views: the home page, the health check, and the
message pages, such as Forbidden, that any route can return."""

from django import db
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from deskmate import llm


@require_GET
def home(request):
    """Render the home page (PLT-1.1)."""
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


def message_page(request, title, message, status):
    """Return a `status` page titled `title` whose only other text is `message`."""
    context = {"title": title, "message": message}
    return render(request, "deskmate/message.html", context, status=status)


def forbidden(request, message):
    """Return a 403 page titled Forbidden whose only other text is `message`."""
    return message_page(request, "Forbidden", message, 403)


def csrf_failure(request, reason=""):
    """Refuse a request to any route that failed Django's CSRF checks (ACC-1.8).

    `reason` is never shown, so the page gives no internal details.
    """
    return forbidden(
        request, "This form has expired. Go back, reload the page and try again."
    )


@require_GET
def llm_probe(request):
    """Run the one SoC LLM production probe (PLT-3)."""
    if not llm.token_matches(request.headers.get("Authorization", "")):
        raise Http404
    ok = llm.probe()
    return JsonResponse({"status": "ok" if ok else "error"}, status=200 if ok else 503)


def llm_probe_no_slash(request):
    """Refuse the path without its trailing slash (PLT-3.3)."""
    raise Http404
