"""PLT-3.6/PLT-8.5: real urllib reads share one total provider deadline.

Only the provider URL and time limit change; no test replaces the opener or
contacts SoC LLM. All request and response data is synthetic.
"""

import json
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Thread
from types import SimpleNamespace

import pytest

from deskmate import llm

KEY = "synthetic-deadline-key"
TOKEN = "synthetic-deadline-token-" * 2
CONTENT = "synthetic-provider-content"
HEADER_VALUE = "synthetic-provider-header"
BODY = json.dumps({"choices": [{"message": {"content": CONTENT}}]}).encode()
STATUS = b"HTTP/1.1 200 OK\r\n"
HEADERS = (
    f"Content-Length: {len(BODY)}\r\n"
    f"X-Provider-Detail: {HEADER_VALUE}\r\n"
    "Connection: close\r\n\r\n"
).encode()
LIMIT = 0.4
# Each trickle lasts at least 1.2 seconds on the unfixed implementation.
# Allow a full additional deadline for CI scheduling without hiding that bug.
LATEST_RETURN = LIMIT + 0.4


@pytest.fixture
def loopback_provider(monkeypatch):
    """Serve timed raw HTTP chunks, with interruptible and bounded cleanup."""
    monkeypatch.setenv("SOC_LLM_API_KEY", KEY)
    monkeypatch.setenv("SOC_LLM_PROBE_TOKEN", TOKEN)
    monkeypatch.setattr(llm, "TIMEOUT_SECONDS", LIMIT)

    @contextmanager
    def serve(chunks):
        stopped = Event()
        requests = []

        class Handler(BaseHTTPRequestHandler):
            timeout = 0.5

            def do_POST(self):
                try:
                    body = self.rfile.read(int(self.headers["Content-Length"]))
                    requests.append((self.path, body))
                    for delay, chunk in chunks:
                        if stopped.wait(delay):
                            return
                        self.connection.sendall(chunk)
                except OSError:
                    # A deadline closes the client while this server is sending.
                    pass

            def log_message(self, *_):
                pass

        with HTTPServer(("127.0.0.1", 0), Handler) as server:
            worker = Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.01},
                daemon=True,
            )
            monkeypatch.setattr(
                llm,
                "PROVIDER_URL",
                f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
            )
            worker.start()
            try:
                yield SimpleNamespace(requests=requests)
            finally:
                stopped.set()
                server.shutdown()
                server.server_close()
                worker.join(timeout=1)
                assert not worker.is_alive(), "loopback provider did not stop"

    return serve


def probe(client):
    """Request the actual probe route with a synthetic operator token."""
    return client.get("/health/llm/", headers={"Authorization": f"Bearer {TOKEN}"})


@pytest.mark.ac("PLT-3.1", "PLT-3.6", "PLT-8.5")
@pytest.mark.parametrize("delay", [0, 0.1], ids=["immediate", "headers-and-body"])
def test_llm_deadline_complete_response_within_budget_succeeds(
    loopback_provider, delay
):
    with loopback_provider([(delay, STATUS + HEADERS), (delay, BODY)]) as provider:
        assert llm.reply(b"{}") == CONTENT
        assert provider.requests == [("/v1/chat/completions", b"{}")]


SLOW_OPENING = [
    pytest.param(
        [(0.075, bytes([byte])) for byte in STATUS] + [(0, HEADERS + BODY)],
        id="trickling-status-line",
    ),
    pytest.param(
        [(0, STATUS)]
        + [
            (0.075, f"X-Slow-{index}: {HEADER_VALUE}\r\n".encode())
            for index in range(16)
        ]
        + [(0, HEADERS + BODY)],
        id="trickling-header-lines",
    ),
    pytest.param(
        [(0, STATUS + b"X-Slow: ")]
        + [(0.075, b"x")] * 16
        + [(0, b"\r\n" + HEADERS + BODY)],
        id="trickling-single-header",
    ),
]


@pytest.mark.ac("PLT-3.2", "PLT-3.6", "PLT-8.5")
@pytest.mark.parametrize("chunks", SLOW_OPENING)
def test_llm_deadline_trickling_opening_returns_generic_error_without_retry(
    client, loopback_provider, written_output, chunks
):
    # Warm Django's routing and middleware outside the provider time measurement.
    assert client.get("/").status_code == 200
    with loopback_provider(chunks) as provider:
        started = time.monotonic()
        response = probe(client)
        elapsed = time.monotonic() - started
        assert response.status_code == 503
        assert response.json() == {"status": "error"}
        assert len(provider.requests) == 1
        assert client.get("/").status_code == 200
        disclosed = response.content.decode() + written_output.text()
        for value in (KEY, TOKEN, CONTENT, HEADER_VALUE):
            assert value not in disclosed
        assert elapsed < LATEST_RETURN, (
            f"provider opening took {elapsed:.3f}s for a {LIMIT:.3f}s deadline"
        )


@pytest.mark.ac("PLT-3.6", "PLT-8.5")
def test_llm_deadline_headers_and_body_exceed_shared_budget_returns_error(
    loopback_provider, monkeypatch
):
    # Both phases fit individually; together they cannot fit the total budget.
    # The 0.2s allowance still distinguishes a fresh timeout after headers.
    monkeypatch.setattr(llm, "TIMEOUT_SECONDS", 0.8)
    with loopback_provider([(0.55, STATUS + HEADERS), (0.55, BODY)]) as provider:
        started = time.monotonic()
        assert llm.reply(b"{}") is None
        elapsed = time.monotonic() - started
        assert provider.requests == [("/v1/chat/completions", b"{}")]
        assert elapsed < 1.0
