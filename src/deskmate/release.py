"""Verify a completed production deployment without exposing provider responses.

The CLI reads the deployment URL from stdin and configuration from VERCEL_TOKEN,
VERCEL_ORG_ID, VERCEL_PROJECT_ID, VERCEL_PUBLIC_HOSTNAME, RELEASE_JOB_DEADLINE and
RELEASE_COMPLETED_AT. Both times are monotonic seconds on the deployment runner.
"""

import json
import math
import os
import re
import signal
import ssl
import sys
import time
from html.parser import HTMLParser
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

_HOST = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.vercel\.app"
_ID = r"[A-Za-z0-9_-]{1,128}"


class ReleaseError(Exception):
    """A verification failure containing only a safe stage description."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        """Return redirects to the caller without contacting their destination."""
        return


def _timeout(*_):
    raise TimeoutError


def request(url, token=None, timeout=10):
    """Return status, headers and bounded bytes using system TLS, no redirects.

    Linux release jobs also enforce a total wall-clock limit, so repeated small
    reads cannot extend the socket's inactivity timeout indefinitely.
    """
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    opener = build_opener(
        _NoRedirect, HTTPSHandler(context=ssl.create_default_context())
    )
    alarm = hasattr(signal, "setitimer")
    if alarm:
        previous = signal.signal(signal.SIGALRM, _timeout)
        signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        try:
            response = opener.open(Request(url, headers=headers), timeout=timeout)
        except HTTPError as error:
            response = error
        with response:
            status = response.status
            # Classify failures before body reads; redirects need only headers.
            body = response.read(1048577) if status == 200 else b""
            if len(body) > 1048576:
                raise ValueError("oversized response")
            return status, dict(response.headers), body
    finally:
        if alarm:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)


def _check(condition, stage):
    if not condition:
        raise ReleaseError(f"{stage}: failed") from None


def _fetch(url, token, deadline, stage, statuses=(200,)):
    while True:
        remaining = deadline - time.monotonic()
        _check(remaining > 0, stage)
        try:
            status, headers, body = request(url, token, timeout=min(10, remaining))
        except (URLError, OSError, HTTPException) as error:
            _check(not isinstance(getattr(error, "reason", error), ssl.SSLError), stage)
        except ValueError:
            raise ReleaseError(f"{stage}: failed") from None
        else:
            _check(time.monotonic() < deadline, stage)
            if status in statuses:
                return {key.lower(): value for key, value in headers.items()}, body
            _check(status == 429 or 500 <= status < 600, stage)
        remaining = deadline - time.monotonic()
        _check(remaining > 0, stage)
        time.sleep(min(1, remaining))


def _json(body, stage):
    try:
        document = json.loads(body)
    except (ValueError, UnicodeError):
        raise ReleaseError(f"{stage}: failed") from None
    _check(isinstance(document, dict), stage)
    return document


def _api(path, owner_id, token, deadline, stage):
    scope = f"?teamId={owner_id}" if owner_id.startswith("team_") else ""
    _, body = _fetch(f"https://api.vercel.com/{path}{scope}", token, deadline, stage)
    return _json(body, stage)


def _identity(document, deployment_id, owner_id, project_id):
    expected = {
        "id": deployment_id,
        "ownerId": owner_id,
        "projectId": project_id,
        "target": "production",
        "readyState": "READY",
    }
    _check(
        all(document.get(key) == value for key, value in expected.items()), "deployment"
    )


class _HomePage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = {"title": [], "heading": [], "other": []}
        self.counts = {"title": 0, "heading": 0}
        self.links = []
        self.section = "other"
        self.link = None

    def handle_starttag(self, tag, attrs):
        """Count and collect the title, headings, links and other text."""
        if tag == "a":
            self.link = {"href": dict(attrs).get("href"), "text": []}
            self.links.append(self.link)
        section = (
            "title"
            if tag == "title"
            else "heading"
            if re.fullmatch("h[1-6]", tag)
            else None
        )
        if section:
            self.section = section
            self.counts[section] += 1

    def handle_endtag(self, tag):
        """Return to ordinary text after closing a link, title or heading."""
        if tag == "a":
            self.link = None
        if tag == "title" or re.fullmatch("h[1-6]", tag):
            self.section = "other"

    def handle_data(self, data):
        """Collect text, including any unexpected content."""
        self.parts[self.section].append(data)
        if self.link is not None:
            self.link["text"].append(data)


def verify_release(deployment_id, owner_id, project_id, hostname, token, job_deadline):
    """Verify identity, hostname mapping and public pages within one deadline."""
    _check(
        all(re.fullmatch(_ID, value) for value in (deployment_id, owner_id, project_id))
        and re.fullmatch(_HOST, hostname)
        and token
        and math.isfinite(job_deadline),
        "deployment",
    )
    deadline = min(job_deadline, time.monotonic() + 120)
    document = _api(
        f"v13/deployments/{deployment_id}", owner_id, token, deadline, "deployment"
    )
    _identity(document, deployment_id, owner_id, project_id)
    mapping = _api(f"v4/aliases/{hostname}", owner_id, token, deadline, "mapping")
    expected = {
        "alias": hostname,
        "deploymentId": deployment_id,
        "projectId": project_id,
    }
    _check(all(mapping.get(key) == value for key, value in expected.items()), "mapping")
    if "deployment" in mapping:
        _check(
            isinstance(mapping["deployment"], dict)
            and mapping["deployment"].get("id") == deployment_id,
            "mapping",
        )
    for stage, path in (("home", "/"), ("health", "/health/")):
        url = f"https://{hostname}{path}"
        headers, body = _fetch(url, None, deadline, stage)
        media_type = headers.get("content-type", "").split(";")[0].strip().lower()
        if stage == "health":
            _check(media_type == "application/json", stage)
            _check(_json(body, stage) == {"status": "ok"}, stage)
        else:
            _check(media_type == "text/html", stage)
            page = _HomePage()
            try:
                page.feed(body.decode("utf-8"))
                page.close()
            except (ValueError, UnicodeError):
                raise ReleaseError("home: failed") from None
            parts = {
                key: " ".join(" ".join(value).split())
                for key, value in page.parts.items()
            }
            links = [
                {
                    "href": link["href"],
                    "text": " ".join(" ".join(link["text"]).split()),
                }
                for link in page.links
            ]
            _check(
                page.counts == {"title": 1, "heading": 1}
                and parts
                == {
                    "title": "Deskmate",
                    "heading": "Deskmate",
                    "other": "Deskmate is under construction. Sign in",
                }
                and links == [{"href": "/sign-in/", "text": "Sign in"}],
                stage,
            )
        headers, _ = _fetch(
            f"http://{hostname}{path}", None, deadline, stage, (301, 302, 303, 307, 308)
        )
        _check(headers.get("location") == url, stage)


def main():
    """Resolve the CLI URL and verify it, printing only safe release metadata."""
    try:
        owner = os.environ["VERCEL_ORG_ID"]
        project = os.environ["VERCEL_PROJECT_ID"]
        hostname = os.environ["VERCEL_PUBLIC_HOSTNAME"]
        token = os.environ["VERCEL_TOKEN"]
        job_deadline = float(os.environ["RELEASE_JOB_DEADLINE"])
        completed = float(os.environ["RELEASE_COMPLETED_AT"])
        _check(
            all(re.fullmatch(_ID, value) for value in (owner, project))
            and re.fullmatch(_HOST, hostname)
            and token
            and all(math.isfinite(value) for value in (job_deadline, completed))
            and 0 < completed <= time.monotonic(),
            "configuration",
        )
        deadline = min(job_deadline, completed + 120)
        match = re.fullmatch(rf"https://({_HOST})/?", sys.stdin.read(2049).strip())
        _check(match, "deployment")
        document = _api(
            f"v13/deployments/{match[1]}", owner, token, deadline, "deployment"
        )
        deployment = document.get("id")
        _check(
            isinstance(deployment, str) and re.fullmatch(_ID, deployment), "deployment"
        )
        _identity(document, deployment, owner, project)
        print(
            f"owner={owner} project={project} deployment={deployment} "
            f"hostname={hostname}"
        )
        verify_release(deployment, owner, project, hostname, token, deadline)
        print("verification: passed")
        return 0
    except ReleaseError as error:
        print(str(error), file=sys.stderr)
    except Exception:  # noqa: BLE001 -- provider exceptions may contain secrets.
        # Neither config values nor provider/transport exceptions are safe logs.
        print("verification: failed", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
