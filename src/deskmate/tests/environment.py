"""The configuration the tests give Deskmate, committed here instead of read from
the developer's shell (TECHNICAL-SPEC "Environments").

The database values are the throwaway local and CI credentials in `.env.example`.
No secret key is written here: the tests make a new one on each run
(SECURITY-SPEC "Secrets and settings").
"""

import secrets
import string

DATABASE = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "deskmate",
    "POSTGRES_USER": "deskmate",
    "POSTGRES_PASSWORD": "deskmate",
}

# The host name Django's test client sends.
ALLOWED_HOSTS = "testserver"

_KEY_CHARACTERS = string.ascii_letters + string.digits
_random = secrets.SystemRandom()


def make_secret_key(length=64, distinct=None):
    """Return a new random key of `length` letters and digits.

    The key uses exactly `distinct` different characters, by default as many as
    `length` allows, up to 32. It never starts with `django-insecure-`.
    """
    distinct = min(length, 32) if distinct is None else distinct
    characters = _random.sample(_KEY_CHARACTERS, distinct)
    key = characters + _random.choices(characters, k=length - distinct)
    _random.shuffle(key)
    return "".join(key)


def is_configuration_variable(name):
    """Return whether the variable `name` configures Deskmate, Django or libpq.

    Deskmate's own variables all start with `DJANGO_` or `POSTGRES_`
    (TECHNICAL-SPEC "Configuration"). libpq, which connects to the database,
    also reads `PG` variables such as `PGSSLMODE` for every setting Django
    leaves unset, and their names have no underscore after `PG`.
    """
    return name.upper().startswith(("POSTGRES_", "DJANGO_", "PG"))


def valid_environment(overrides=None):
    """Return variables that configure Deskmate validly with debug off.

    `overrides` replaces some of them; an override of None leaves that variable
    unset.
    """
    environment = {
        **DATABASE,
        "DJANGO_SECRET_KEY": make_secret_key(),
        "DJANGO_ALLOWED_HOSTS": ALLOWED_HOSTS,
    }
    environment.update(overrides or {})
    return {name: value for name, value in environment.items() if value is not None}


def use_test_configuration(environ):
    """Replace every configuration variable in `environ` with the tests' own.

    Keeps `DJANGO_SETTINGS_MODULE`, which pytest-django sets, and leaves
    `DJANGO_DEBUG` unset, so debug is off.
    """
    for name in list(environ):
        if is_configuration_variable(name) and name != "DJANGO_SETTINGS_MODULE":
            del environ[name]
    environ.update(valid_environment())
