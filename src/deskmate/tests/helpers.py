"""Helpers shared by Deskmate's tests: processes started with a chosen
configuration, and checks for internal details in a response."""

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

from deskmate.tests.environment import is_configuration_variable

SRC_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = SRC_DIR.parent
MANAGE_PY = SRC_DIR / "manage.py"
SETTINGS_MODULE = "deskmate.settings"
TIMEOUT_SECONDS = 60

# Text that only a traceback, Django's debug pages, a setting or a source file
# would put in a response. "health/" is a route, so it marks the route list.
_INTERNAL_MARKERS = (
    "Traceback",
    "URLconf",
    "urlpatterns",
    "health/",
    "DEBUG",
    "SECRET_KEY",
    "DATABASES",
    "ALLOWED_HOSTS",
    "ROOT_URLCONF",
    "INSTALLED_APPS",
    "POSTGRES_",
    "DJANGO_",
    SETTINGS_MODULE,
    ".py",
    "site-packages",
)


def _file_paths():
    """Return this machine's paths to the code and to Python, in both separators."""
    roots = {str(REPO_ROOT), sys.prefix, sys.base_prefix}
    paths = roots | {Path(root).as_posix() for root in roots}
    return sorted(path for path in paths if len(path) > 3)


def internal_details(body, values=None):
    """Return what `body` reveals of Deskmate's internals, or an empty list.

    Looks for a traceback, the route list, settings' names, file paths, and each
    of `values`, a mapping from a description to a value such as the secret key.
    Only the descriptions are returned, so no value is printed.
    """
    found = [marker for marker in _INTERNAL_MARKERS if marker in body]
    lowered = body.lower()
    found += [path for path in _file_paths() if path.lower() in lowered]
    found += [label for label, value in (values or {}).items() if value in body]
    return found


def media_type(response):
    """Return the media type of `response`'s Content-Type, without parameters."""
    return response["Content-Type"].split(";")[0].strip().lower()


def cache_directives(response):
    """Return the names of the directives in `response`'s Cache-Control header."""
    header = response.get("Cache-Control", "")
    return {part.split("=")[0].strip().lower() for part in header.split(",")}


def unused_port():
    """Return a local TCP port that nothing is listening on."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def run_python(arguments, environment, timeout=TIMEOUT_SECONDS):
    """Run Python with `arguments`, configured only by `environment`.

    Drops every variable from the developer's shell that configures Deskmate,
    Django or libpq. Raises subprocess.TimeoutExpired, after stopping the
    process, if it is still running after `timeout` seconds.
    """
    env = {
        name: value
        for name, value in os.environ.items()
        if not is_configuration_variable(name)
    }
    env.update(environment)
    env["PYTHONPATH"] = str(SRC_DIR)
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, *arguments],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def run_manage(arguments, environment, timeout=TIMEOUT_SECONDS):
    """Run `src/manage.py` with `arguments`, configured only by `environment`."""
    return run_python([str(MANAGE_PY), *arguments], environment, timeout)


def run_probe(path, environment, urlconf=None, host=None):
    """Start Deskmate in a new process configured by `environment`, request `path`.

    `urlconf` replaces Deskmate's routes for that request. Returns the finished
    process and the probe's result: whether debug is on, the status and body.
    """
    arguments = ["-m", "deskmate.tests.probe", path]
    if urlconf or host:
        arguments.append(urlconf or "")
    if host:
        arguments.append(host)
    environment = {**environment, "DJANGO_SETTINGS_MODULE": SETTINGS_MODULE}
    process = run_python(arguments, environment)
    if process.returncode != 0 or not process.stdout.strip():
        raise AssertionError(
            f"The probe exited with {process.returncode}.\n{process.stderr}"
        )
    return process, json.loads(process.stdout.strip().splitlines()[-1])
