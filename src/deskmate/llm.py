"""The one fixed SoC LLM production probe (PLT-3, AI contract llm-health.md).

The probe sends one server-authored request with no user input, then checks
only the response's shape. It never retries, follows no redirect, uses no
proxy, enforces a total deadline, and never logs the key, the token or the
provider's text.
"""

import hmac
import http.client
import json
import os
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

PROVIDER_URL = "https://soclaas-api.comp.nus.edu.sg/v1/chat/completions"
MODEL = "llama3.1:8b"
TIMEOUT_SECONDS = 10
MAX_BODY = 65536
_BODY = json.dumps(
    {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a health check. Reply with exactly OK.",
            },
            {"role": "user", "content": "Reply with OK."},
        ],
        "max_tokens": 8,
        "temperature": 0,
        "stream": False,
    }
).encode("utf-8")


class _NoRedirect(HTTPRedirectHandler):
    """Return redirects to the caller without contacting their destination."""

    def redirect_request(self, *args, **kwargs):
        """Refuse to follow a redirect."""
        return


def _opener():
    """Return an opener with system TLS, no redirect, no proxy and no User-Agent."""
    opener = build_opener(
        ProxyHandler({}),
        _NoRedirect,
        HTTPSHandler(context=ssl.create_default_context()),
    )
    opener.addheaders = []
    return opener


def urlopen(request, timeout=None):
    """Open `request` with the probe's TLS, proxy and redirect rules.

    Tests replace this function, so no test contacts SoC LLM.
    """
    return _opener().open(request, timeout=timeout)


def token_matches(header):
    """Return whether `header` is exactly `Bearer <SOC_LLM_PROBE_TOKEN>`."""
    expected = os.environ.get("SOC_LLM_PROBE_TOKEN", "")
    if not expected or len(expected) < 32:
        return False
    if any(not 0x20 <= ord(character) <= 0x7E for character in expected):
        return False
    try:
        supplied = header.encode("latin-1")
    except UnicodeEncodeError:
        return False
    return hmac.compare_digest(supplied, f"Bearer {expected}".encode("ascii"))


def _shape_ok(body):
    """Return whether `body` is the provider answer the AI contract allows."""
    try:
        document = json.loads(body.decode("utf-8"))
    except (UnicodeError, ValueError):
        return False
    if not isinstance(document, dict):
        return False
    choices = document.get("choices")
    if not isinstance(choices, list) or not choices:
        return False
    first = choices[0]
    if not isinstance(first, dict):
        return False
    message = first.get("message")
    if not isinstance(message, dict):
        return False
    content = message.get("content")
    return isinstance(content, str) and content.strip() != ""


def _read_body(response, deadline):
    """Read at most MAX_BODY bytes, giving up when `deadline` passes.

    Each read is bounded by the time left, so a provider that trickles bytes
    cannot hold the request past the total limit.
    """
    chunks = []
    total = 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        socket = getattr(getattr(response, "fp", None), "raw", None)
        socket = getattr(socket, "_sock", None)
        if socket is not None:
            socket.settimeout(remaining)
        read = getattr(response, "read1", response.read)
        chunk = read(min(65536, MAX_BODY + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_BODY:
            return None
    return b"".join(chunks)


def probe():
    """Return whether one provider call returned an allowed answer."""
    key = os.environ.get("SOC_LLM_API_KEY", "")
    if not key:
        return False
    request = Request(
        PROVIDER_URL,
        data=_BODY,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    deadline = time.monotonic() + TIMEOUT_SECONDS
    try:
        response = urlopen(request, timeout=TIMEOUT_SECONDS)
        with response:
            if response.status != 200:
                return False
            body = _read_body(response, deadline)
    except (HTTPError, URLError, OSError, http.client.HTTPException, ValueError):
        return False
    if body is None or time.monotonic() > deadline:
        return False
    return _shape_ok(body)
