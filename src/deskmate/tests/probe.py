"""Starts Deskmate from the environment and makes one request, for tests that
need a fresh process.

Usage: python -m deskmate.tests.probe <path> [<urlconf>] [<host>]

Prints one JSON line: whether debug is on, and the response's status and body.
Anything Deskmate logs goes to the process's own standard error.
"""

import json
import sys

import django
from django.conf import settings
from django.test import Client, override_settings


def main(arguments):
    """Request the path in `arguments`, with the URLconf if one follows it."""
    django.setup()
    path = arguments[0]
    overrides = (
        {"ROOT_URLCONF": arguments[1]} if len(arguments) > 1 and arguments[1] else {}
    )
    headers = {"HTTP_HOST": arguments[2]} if len(arguments) > 2 else {}
    with override_settings(**overrides):
        response = Client(raise_request_exception=False).get(path, **headers)
    database = settings.DATABASES["default"]
    result = {
        "debug": settings.DEBUG,
        "status": response.status_code,
        "body": response.content.decode("utf-8", "replace"),
        "allowed_hosts": settings.ALLOWED_HOSTS,
        "database_options": {
            name: database.get("OPTIONS", {}).get(name)
            for name in ("sslmode", "sslrootcert", "connect_timeout", "pool")
        },
        "connection_max_age": database.get("CONN_MAX_AGE", 0),
    }
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
