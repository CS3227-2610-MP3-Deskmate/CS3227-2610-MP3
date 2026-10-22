"""PLT-3.6/PLT-8.5: real urllib reads share one total provider deadline.

Transport tests use real urllib over loopback, including verified TLS. The
HTTPError ownership test fakes urlopen; no test contacts SoC LLM.
"""

import io
import json
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Thread
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from deskmate import llm
from deskmate.tests.test_migration import (
    CLOCK_STEP_SECONDS,
    make_certificate,
    server_context,
)

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
    def serve(chunks, context=None, observe_close=False):
        stopped = Event()
        peer_closed = Event()
        requests = []

        class Server(HTTPServer):
            def get_request(self):
                connection, address = super().get_request()
                connection.settimeout(0.5)
                if context is not None:
                    try:
                        connection = context.wrap_socket(connection, server_side=True)
                    except OSError:
                        connection.close()
                        raise
                return connection, address

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
                    if observe_close:
                        self.connection.settimeout(1)
                        if not self.connection.recv(1):
                            peer_closed.set()
                except (ConnectionResetError, BrokenPipeError):
                    peer_closed.set()
                except OSError:
                    # A deadline closes the client while this server is sending.
                    pass

            def log_message(self, *_):
                pass

        with Server(("127.0.0.1", 0), Handler) as server:
            worker = Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.01},
                daemon=True,
            )
            monkeypatch.setattr(
                llm,
                "PROVIDER_URL",
                f"{'https' if context else 'http'}://127.0.0.1:"
                f"{server.server_port}/v1/chat/completions",
            )
            worker.start()
            try:
                yield SimpleNamespace(requests=requests, peer_closed=peer_closed)
            finally:
                stopped.set()
                server.shutdown()
                server.server_close()
                worker.join(timeout=1)
                assert not worker.is_alive(), "loopback provider did not stop"

    return serve


@pytest.fixture(scope="module")
def tls_certificates(tmp_path_factory):
    """Reuse CI's OpenSSL helpers for a synthetic CA and an IP-bound certificate."""
    directory = tmp_path_factory.mktemp("llm-certificates")
    make_certificate(directory, "trusted-ca")
    make_certificate(directory, "trusted", "IP:127.0.0.1", "trusted-ca")
    time.sleep(CLOCK_STEP_SECONDS)
    return directory


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


@pytest.mark.ac("PLT-3.1", "PLT-3.6", "PLT-8.5")
@pytest.mark.parametrize("slow", [False, True], ids=["success", "trickling-headers"])
def test_llm_deadline_verified_https_obeys_total_budget(
    loopback_provider, tls_certificates, monkeypatch, slow
):
    monkeypatch.setenv("SSL_CERT_FILE", str(tls_certificates / "trusted-ca.pem"))
    chunks = [(0, STATUS)]
    if slow:
        chunks += [(0.075, b"X-Slow: synthetic\r\n")] * 16
    chunks += [(0, HEADERS + BODY)]
    with loopback_provider(
        chunks, server_context(tls_certificates, "trusted")
    ) as provider:
        started = time.monotonic()
        assert llm.reply(b"{}") == (None if slow else CONTENT)
        assert time.monotonic() - started < LATEST_RETURN
        assert provider.requests == [("/v1/chat/completions", b"{}")]


@pytest.mark.ac("PLT-3.2", "PLT-8.5")
def test_llm_deadline_https_wrong_hostname_is_refused(
    loopback_provider, tls_certificates, monkeypatch
):
    monkeypatch.setenv("SSL_CERT_FILE", str(tls_certificates / "trusted-ca.pem"))
    with loopback_provider(
        [(0, STATUS + HEADERS + BODY)], server_context(tls_certificates, "trusted")
    ) as provider:
        # The trusted certificate covers only the IP address, not localhost.
        monkeypatch.setattr(
            llm, "PROVIDER_URL", llm.PROVIDER_URL.replace("127.0.0.1", "localhost")
        )
        assert llm.reply(b"{}") is None
        assert provider.requests == []


@pytest.mark.ac("PLT-3.6", "PLT-8.5")
def test_llm_deadline_opening_timeout_closes_peer_connection(loopback_provider):
    with loopback_provider(
        [(0, STATUS + b"X-Incomplete: waiting")], observe_close=True
    ) as provider:
        assert llm.reply(b"{}") is None
        assert provider.peer_closed.wait(1), "client left the timed-out connection open"
        assert len(provider.requests) == 1


@pytest.mark.ac("PLT-3.2", "PLT-8.5")
def test_llm_deadline_http_error_closes_owned_body(monkeypatch):
    body = io.BytesIO(b"synthetic-provider-error")
    error = HTTPError(llm.PROVIDER_URL, 503, "synthetic", {}, body)
    calls = []

    def refuse(request, timeout):
        calls.append(request)
        raise error

    monkeypatch.setenv("SOC_LLM_API_KEY", KEY)
    monkeypatch.setattr(llm, "urlopen", refuse)
    assert llm.reply(b"{}") is None
    assert body.closed
    assert len(calls) == 1
