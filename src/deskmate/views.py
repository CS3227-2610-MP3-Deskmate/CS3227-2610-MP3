"""Deskmate's views: the placeholder home page and the health check."""

from django import db
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def home(request):
    """Render the placeholder home page (PLT-1.1)."""
    return render(request, "deskmate/home.html")


@require_GET
def health(request):
    """Report whether the database answers, as `ok` or `error` (PLT-1.2, 1.3)."""
    try:
        with db.connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except db.Error:
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})
