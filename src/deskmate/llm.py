"""SoC LLM calls, made only by the probe (PLT-3) and the AI gateway (PLT-8).

The probe sends one server-authored request with no user input. Each call checks
only the response's shape. It never retries, follows no redirect, uses no
proxy, bounds response reads by one deadline, and never logs the key, token or
provider's text.
"""

import hmac
import http.client
import io
import json
import os
import ssl
import time
from functools import partial
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPHandler,
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


class _DeadlineReader(io.RawIOBase):
    """Bound each raw socket read, including reads inside a buffered line."""

    def __init__(self, raw, deadline):
        super().__init__()
        self._raw = raw
        self._deadline = deadline

    def readable(self):
        """Allow a buffered reader to read this stream."""
        return True

    def readinto(self, buffer):
        """Read once with only the shared deadline's remaining time."""
        if self._deadline is not None:
            remaining = self._deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("provider deadline exceeded")
            self._raw._sock.settimeout(remaining)
        return self._raw.readinto(buffer)

    def close(self):
        """Release the owned socket stream, even after a failed read."""
        try:
            self._raw.close()
        finally:
            super().close()


class _DeadlineResponse(http.client.HTTPResponse):
    """Keep stdlib parsing over a stream that bounds every socket read."""

    def __init__(self, sock, *args, deadline, **kwargs):
        super().__init__(sock, *args, **kwargs)
        # HTTPResponse has not read anything yet, so detaching loses no bytes.
        raw = self.fp.detach()
        self.fp = None
        try:
            self.fp = io.BufferedReader(_DeadlineReader(raw, deadline))
        except BaseException:
            raw.close()
            raise


class _DeadlineHandler(HTTPSHandler, HTTPHandler):
    """Use the deadline response for both standard HTTP connection types."""

    def __init__(self, deadline, **kwargs):
        super().__init__(**kwargs)
        self._deadline = deadline

    def do_open(self, http_class, request, **kwargs):
        """Give only this request's connection a deadline response factory."""

        def connection(*args, **kwargs):
            """Create the unchanged connection with a per-call response factory."""
            result = http_class(*args, **kwargs)
            result.response_class = partial(_DeadlineResponse, deadline=self._deadline)
            return result

        return super().do_open(connection, request, **kwargs)


def _opener(deadline=None):
    """Return an opener with system TLS, no redirect, no proxy and no User-Agent."""
    opener = build_opener(
        ProxyHandler({}),
        _NoRedirect,
        _DeadlineHandler(deadline, context=ssl.create_default_context()),
    )
    opener.addheaders = []
    return opener


def urlopen(request, timeout=None):
    """Open `request` with the probe's TLS, proxy and redirect rules.

    Tests replace this function, so no test contacts SoC LLM. DNS and connection
    attempts retain stdlib timing; the response reads share the call's deadline.
    """
    deadline = getattr(request, "_llm_deadline", None)
    if deadline is None and timeout is not None:
        deadline = time.monotonic() + timeout
    return _opener(deadline).open(request, timeout=timeout)


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


def _content(body):
    """Return the `content` of the provider answer the AI contract allows, or None."""
    try:
        document = json.loads(body.decode("utf-8"))
    # RecursionError: JSON nested too deeply to parse.
    except (UnicodeError, ValueError, RecursionError):
        return None
    if not isinstance(document, dict):
        return None
    choices = document.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str) and content.strip() != "":
        return content
    return None


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
    return reply(_BODY) is not None


def reply(body):
    """Send the JSON bytes `body` to the provider once; return the answer's content.

    Reads `SOC_LLM_API_KEY` on each call. Returns None, without a request when
    the key is unset or empty, on every failure the probe's contract lists.
    """
    key = os.environ.get("SOC_LLM_API_KEY", "")
    if not key:
        return None
    request = Request(
        PROVIDER_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    deadline = time.monotonic() + TIMEOUT_SECONDS
    request._llm_deadline = deadline
    try:
        response = urlopen(request, timeout=TIMEOUT_SECONDS)
        with response:
            if response.status != 200:
                return None
            answer = _read_body(response, deadline)
    except HTTPError as error:
        try:
            error.close()
        except OSError:
            pass
        return None
    except (URLError, OSError, http.client.HTTPException, ValueError):
        return None
    if answer is None or time.monotonic() > deadline:
        return None
    return _content(answer)
