"""A URLconf whose only route fails, so tests can cause an unexpected server error."""

from django.urls import path

FAILING_PATH = "/test-failure/"
FAILURE_MESSAGE = "synthetic failure 5e1c9a"


class SyntheticFailureError(Exception):
    """An error that no code handles, as a bug in a view would raise."""


def fail(request):
    """Raise SyntheticFailureError for every request."""
    raise SyntheticFailureError(FAILURE_MESSAGE)


urlpatterns = [path(FAILING_PATH.lstrip("/"), fail)]
