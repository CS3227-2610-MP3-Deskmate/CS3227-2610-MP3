"""Deskmate's Django settings, read from environment variables when imported.

Each variable is checked against its row in the TECHNICAL-SPEC Configuration
table. If any that is required in the current debug mode is unset or invalid,
importing this module raises SystemExit naming each one but showing no value,
so neither the web server nor a management command starts (PLT-1.7). It is
SystemExit rather than ImproperlyConfigured because manage.py catches that
while it loads settings.
"""

import os
import re
import secrets

_LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "::1")


def _is_port(value):
    """Return whether `value` is a whole number from 1 to 65535 in digits only."""
    match = re.fullmatch("0*([1-9][0-9]{0,4})", value)
    return match is not None and int(match[1]) <= 65535


def _is_strong_key(value):
    """Return whether `value` is a secret key the Configuration table allows."""
    return (
        len(value) >= 50
        and len(set(value)) >= 5
        and not value.startswith("django-insecure-")
    )


def _host_names(value):
    """Return the names in the comma-separated `value`, ignoring blank items."""
    return [name.strip() for name in value.split(",") if name.strip()]


def _production_host(value):
    """Accept one exact provider hostname, using the existing list syntax."""
    names = _host_names(value)
    return len(names) == 1 and re.fullmatch(
        r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.vercel\.app", names[0]
    )


def _invalid_variables(environ, debug):
    """Return the variables required in this debug mode that are unset or invalid.

    Each check takes the variable's value, or "" if it is unset, and returns
    something true if the value is valid: `bool` accepts any non-empty value.
    """
    checks = {
        "POSTGRES_HOST": bool,
        "POSTGRES_PORT": _is_port,
        "POSTGRES_DB": bool,
        "POSTGRES_USER": bool,
        "POSTGRES_PASSWORD": bool,
    }
    production = environ.get("VERCEL_ENV") == "production"
    if not debug or production:
        checks["DJANGO_SECRET_KEY"] = _is_strong_key
        checks["DJANGO_ALLOWED_HOSTS"] = _host_names
    if production:
        checks["DJANGO_ALLOWED_HOSTS"] = _production_host
        checks["DJANGO_DEBUG"] = lambda value: value != "true"
        checks["POSTGRES_HOST"] = lambda value: value and value not in _LOOPBACK_HOSTS
    return [
        name for name, is_valid in checks.items() if not is_valid(environ.get(name, ""))
    ]


# Only exactly "true" turns debug on (PLT-1.6).
DEBUG = os.environ.get("DJANGO_DEBUG") == "true"

_invalid = _invalid_variables(os.environ, DEBUG)
if _invalid:
    raise SystemExit(
        "\n".join(
            f"Deskmate cannot start: {name} is not set or is invalid."
            for name in _invalid
        )
    )

# With debug off the key was checked above. With debug on and no key, a new
# random key is made on each start (SECURITY-SPEC "Secrets and settings").
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or secrets.token_urlsafe(50)
ALLOWED_HOSTS = _host_names(os.environ.get("DJANGO_ALLOWED_HOSTS", ""))

INSTALLED_APPS = [
    "deskmate",
    "deskmate.accounts",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
]
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
ROOT_URLCONF = "deskmate.urls"
WSGI_APPLICATION = "deskmate.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ["POSTGRES_HOST"],
        "PORT": os.environ["POSTGRES_PORT"],
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "CONN_MAX_AGE": 0,
        # Every attempt to connect gives up after 5 seconds (TECHNICAL-SPEC).
        "OPTIONS": {"connect_timeout": 5},
    }
}
if os.environ["POSTGRES_HOST"] not in _LOOPBACK_HOSTS:
    DATABASES["default"]["OPTIONS"].update(sslmode="verify-full", sslrootcert="system")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

# A session ends when the browser closes or 8 hours after signing in (ACC-1.6).
# Django sets a database session's expiry only when it saves the session, and
# nothing saves it after sign-in, so activity does not extend it.
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# With debug off, the session and CSRF cookies are sent only over HTTPS.
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
# The origin of each allowed host over HTTPS (ACC-1.8).
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]

# Unexpected errors in requests, with their tracebacks, go to standard error
# whether or not debug is on (PLT-1.4). They do not propagate, so Django's own
# debug-only console handler does not print them twice.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"stderr": {"class": "logging.StreamHandler"}},
    "loggers": {
        "django.request": {
            "handlers": ["stderr"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
