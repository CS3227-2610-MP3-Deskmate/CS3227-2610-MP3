"""PLT-3.1-3.6: the operator-only SoC LLM production probe.

The provider is faked at the `urlopen` boundary, so no test contacts SoC LLM.
"""

import http.client
import json
from urllib.error import URLError

import pytest
from django.contrib.sessions.models import Session
from django.db import connection

from deskmate.tests.environment import valid_environment
from deskmate.tests.helpers import cache_directives, media_type, run_manage
from deskmate.tests.signing_in import REQUESTER, sign_in_as

TOKEN = "t" * 40
KEY = "synthetic-key"
PROBE = "/health/llm/"
PROVIDER = "https://soclaas-api.comp.nus.edu.sg/v1/chat/completions"
EXPECTED_BODY = {
    "model": "llama3.1:8b",
    "messages": [
        {"role": "system", "content": "You are a health check. Reply with exactly OK."},
        {"role": "user", "content": "Reply with OK."},
    ],
    "max_tokens": 8,
    "temperature": 0,
    "stream": False,
}


class FakeProvider:
    """A fake `urlopen` that records each request and returns a chosen answer."""

    def __init__(self, body=b"", status=200):
        self.requests = []
        self.body = body
        self.status = status
        self.make_response = FakeResponse

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        return self.make_response(self.status, self.body)


class FakeResponse:
    """The small part of an HTTP response the probe reads."""

    def __init__(self, status, body):
        self.status = status
        self.body = body
        self.position = 0

    def read(self, amount):
        chunk = self.body[self.position : self.position + amount]
        self.position += len(chunk)
        return chunk

    def read1(self, amount):
        return self.read(amount)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def provider_body(content="OK"):
    return json.dumps({"choices": [{"message": {"content": content}}]}).encode()


def request_body(request):
    return json.loads(request.data.decode("utf-8"))


@pytest.fixture
def provider(monkeypatch):
    fake = FakeProvider(body=provider_body())
    monkeypatch.setenv("SOC_LLM_PROBE_TOKEN", TOKEN)
    monkeypatch.setenv("SOC_LLM_API_KEY", KEY)
    monkeypatch.setattr("deskmate.llm.urlopen", fake)
    return fake


def assert_probe(response, status, body):
    assert response.status_code == status
    assert media_type(response) == "application/json"
    assert json.loads(response.content) == body


def get_probe(client, headers=None):
    return client.get(PROBE, headers=headers or {})


@pytest.mark.ac("PLT-3.1")
def test_llm_probe_valid_token_sends_fixed_request_and_returns_ok(client, provider):
    response = get_probe(client, {"Authorization": f"Bearer {TOKEN}"})
    assert_probe(response, 200, {"status": "ok"})
    assert len(provider.requests) == 1
    request, timeout = provider.requests[0]
    assert request.full_url == PROVIDER
    assert request.get_method() == "POST"
    assert request_body(request) == EXPECTED_BODY
    assert request.get_header("Authorization") == f"Bearer {KEY}"
    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("Accept") == "application/json"
    headers = {name.lower(): value for name, value in request.header_items()}
    assert headers == {
        "authorization": f"Bearer {KEY}",
        "content-type": "application/json",
        "accept": "application/json",
    }
    assert timeout == 10


@pytest.mark.ac("PLT-3.1")
def test_llm_probe_accepts_any_non_empty_content(client, provider):
    provider.body = provider_body("  anything  ")
    response = get_probe(client, {"Authorization": f"Bearer {TOKEN}"})
    assert_probe(response, 200, {"status": "ok"})


@pytest.mark.ac("PLT-3.2")
@pytest.mark.parametrize(
    "body,status",
    [
        (b"not json", 200),
        (b"{}", 200),
        (b'{"choices": []}', 200),
        (b'{"choices": [{"message": {"content": "   "}}]}', 200),
        (provider_body(), 500),
        (provider_body(), 429),
        pytest.param(b"x" * 70000, 200, id="oversized"),
    ],
)
def test_llm_probe_bad_provider_answer_returns_error(client, provider, body, status):
    provider.body, provider.status = body, status
    response = get_probe(client, {"Authorization": f"Bearer {TOKEN}"})
    assert_probe(response, 503, {"status": "error"})


MAX_BODY = 65536  # The probe's response limit (llm-health.md "Request").


def nested_arrays(depth):
    return "[" * depth + "]" * depth


def deepest(prefix, suffix):
    """Return `prefix`, the deepest arrays that fit the limit, then `suffix`."""
    depth = (MAX_BODY - len(prefix) - len(suffix)) // 2
    return (prefix + nested_arrays(depth) + suffix).encode()


# Issue #104: arrays nested past the parser's limit but within the body limit.
NESTED = {
    "issue-32000-arrays": nested_arrays(32000).encode(),
    "arrays-filling-limit": deepest("", ""),
    "as-choices": deepest('{"choices": ', "}"),
    "as-message": deepest('{"choices": [{"message": ', "}]}"),
    "as-content": deepest('{"choices": [{"message": {"content": ', "}}]}"),
    "mid-depth-arrays": nested_arrays(900).encode(),
}


@pytest.mark.ac("PLT-3.2")
@pytest.mark.parametrize("body", NESTED.values(), ids=NESTED.keys())
def test_llm_probe_deeply_nested_provider_body_returns_error(client, provider, body):
    assert len(body) <= MAX_BODY
    provider.body, provider.status = body, 200
    response = get_probe(client, {"Authorization": f"Bearer {TOKEN}"})
    assert_probe(response, 503, {"status": "error"})


@pytest.mark.ac("PLT-3.2")
def test_llm_probe_body_too_deep_to_parse_returns_error(client, provider, monkeypatch):
    # Whether real nesting overflows depends on the stack, so every stdlib
    # JSON parse of this one body raises as the C scanner does when it does.
    target = nested_arrays(32000)
    parse, hits = json.JSONDecoder.raw_decode, []

    def too_deep(decoder, document, *args, **kwargs):
        if document == target:
            hits.append(document)
            raise RecursionError("synthetic: nested too deeply to parse")
        return parse(decoder, document, *args, **kwargs)

    monkeypatch.setattr(json.JSONDecoder, "raw_decode", too_deep)
    provider.body, provider.status = target.encode(), 200
    response = get_probe(client, {"Authorization": f"Bearer {TOKEN}"})
    assert_probe(response, 503, {"status": "error"})
    assert len(hits) == 1 and len(provider.requests) == 1


@pytest.mark.ac("PLT-3.2")
def test_llm_probe_transport_error_returns_error(client, provider, monkeypatch):
    def fail(*args, **kwargs):
        raise URLError("unreachable")

    monkeypatch.setattr("deskmate.llm.urlopen", fail)
    response = get_probe(client, {"Authorization": f"Bearer {TOKEN}"})
    assert_probe(response, 503, {"status": "error"})


@pytest.mark.ac("PLT-3.2")
def test_llm_probe_missing_key_returns_error_without_provider_call(
    client, provider, monkeypatch
):
    monkeypatch.delenv("SOC_LLM_API_KEY")
    response = get_probe(client, {"Authorization": f"Bearer {TOKEN}"})
    assert_probe(response, 503, {"status": "error"})
    assert provider.requests == []


@pytest.mark.ac("PLT-3.3")
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": ""},
        {"Authorization": f"Bearer {'x' * 40}"},
        {"Authorization": f"bearer {TOKEN}"},
        {"Authorization": f"Bearer  {TOKEN}"},
        {"Authorization": f"Bearer {TOKEN} "},
        {"Authorization": f"Token {TOKEN}"},
        {"Authorization": TOKEN},
        {"Authorization": "Bearer \u00e9" * 40},
    ],
)
def test_llm_probe_bad_token_returns_generic_404(client, provider, headers):
    response = get_probe(client, headers)
    generic = client.get("/no-such-route/")
    assert response.status_code == generic.status_code == 404
    assert response.content == generic.content
    assert response["Content-Type"] == generic["Content-Type"]
    assert provider.requests == []


@pytest.mark.ac("PLT-3.3")
def test_llm_probe_without_token_configured_returns_generic_404(
    client, provider, monkeypatch
):
    monkeypatch.delenv("SOC_LLM_PROBE_TOKEN")
    response = get_probe(client, {"Authorization": f"Bearer {TOKEN}"})
    generic = client.get("/no-such-route/")
    assert response.status_code == generic.status_code == 404
    assert response.content == generic.content
    assert provider.requests == []


@pytest.mark.ac("PLT-3.3")
def test_llm_probe_path_without_trailing_slash_returns_404(client, provider):
    # Django's test client reads "//" as a host, so only the single-slash form
    # is requested here; the route table has no redirect for it.
    response = client.get("/health/llm", headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 404
    assert provider.requests == []


@pytest.mark.ac("PLT-3.4")
@pytest.mark.parametrize(
    "method", ["HEAD", "OPTIONS", "TRACE", "POST", "PUT", "DELETE"]
)
def test_llm_probe_other_methods_return_405(client, provider, method):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = client.generic(method, PROBE, headers=headers)
    assert response.status_code == 405
    assert response.content == b""
    assert provider.requests == []


@pytest.mark.ac("PLT-3.4")
def test_llm_probe_query_and_headers_do_not_change_request(client, provider):
    response = client.get(
        PROBE + "?model=other&url=https://evil.example/",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "X-Model": "other",
            "Cookie": "session=whatever",
        },
    )
    assert_probe(response, 200, {"status": "ok"})
    request, _ = provider.requests[0]
    assert request.full_url == PROVIDER
    assert request_body(request) == EXPECTED_BODY
    assert request.get_header("X-Model") is None


@pytest.mark.ac("PLT-3.4")
@pytest.mark.parametrize("status", [200, 404, 405, 503])
def test_llm_probe_responses_use_cache_and_framing_controls(client, provider, status):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    if status == 200:
        response = client.get(PROBE, headers=headers)
    elif status == 404:
        response = client.get(PROBE)
    elif status == 405:
        response = client.post(PROBE, headers=headers)
    else:
        provider.body = b"bad"
        response = client.get(PROBE, headers=headers)
    assert response.status_code == status
    assert "no-store" in cache_directives(response)
    assert response["X-Frame-Options"] == "DENY"


@pytest.mark.ac("PLT-3.5")
def test_llm_probe_signed_in_session_does_not_touch_database(
    make_account, database_outage, provider
):
    browser, _ = sign_in_as(make_account, REQUESTER)
    with database_outage():
        response = browser.get(PROBE, headers={"Authorization": f"Bearer {TOKEN}"})
    assert_probe(response, 200, {"status": "ok"})


@pytest.mark.ac("PLT-3.5")
def test_llm_probe_does_not_write_database(client, provider, django_db_blocker):
    with django_db_blocker.unblock():
        before = (connection.introspection.table_names(), Session.objects.count())
    get_probe(client, {"Authorization": f"Bearer {TOKEN}"})
    with django_db_blocker.unblock():
        after = (connection.introspection.table_names(), Session.objects.count())
    assert before == after


@pytest.mark.ac("PLT-3.5")
def test_llm_probe_app_starts_without_either_variable(monkeypatch):
    environment = valid_environment()
    environment.pop("SOC_LLM_API_KEY", None)
    environment.pop("SOC_LLM_PROBE_TOKEN", None)
    process = run_manage(["check"], environment)
    assert process.returncode == 0, process.stderr


@pytest.mark.ac("PLT-3.2")
def test_llm_probe_incomplete_read_returns_error(client, provider, monkeypatch):
    def truncated(*args, **kwargs):
        raise http.client.IncompleteRead(b"partial")

    monkeypatch.setattr("deskmate.llm.urlopen", truncated)
    response = get_probe(client, {"Authorization": f"Bearer {TOKEN}"})
    assert_probe(response, 503, {"status": "error"})


@pytest.mark.ac("PLT-3.6")
def test_llm_probe_total_deadline_stops_a_trickling_response(
    client, provider, monkeypatch
):
    clock = [0.0]

    def now():
        return clock[0]

    class Trickle(FakeResponse):
        def read1(self, amount):
            clock[0] += 0.6
            return b"x"

    provider.body = provider_body()
    provider.status = 200
    provider.make_response = Trickle
    monkeypatch.setattr("deskmate.llm.time.monotonic", now)
    response = get_probe(client, {"Authorization": f"Bearer {TOKEN}"})
    assert_probe(response, 503, {"status": "error"})
    assert clock[0] <= 10.8


@pytest.mark.ac("PLT-3.6")
def test_llm_probe_timeout_returns_error_without_retry(client, provider, monkeypatch):
    calls = []

    def slow(*args, **kwargs):
        calls.append(kwargs.get("timeout"))
        raise TimeoutError("timed out")

    monkeypatch.setattr("deskmate.llm.urlopen", slow)
    response = get_probe(client, {"Authorization": f"Bearer {TOKEN}"})
    assert_probe(response, 503, {"status": "error"})
    assert calls == [10]


@pytest.mark.ac("PLT-3.2")
def test_llm_probe_never_logs_key_or_provider_text(
    client, provider, written_output, monkeypatch
):
    provider.body = b'{"choices": [{"message": {"content": "SECRET ANSWER"}}]}'
    get_probe(client, {"Authorization": f"Bearer {TOKEN}"})
    provider.body = b'{"error": "SECRET PROVIDER ERROR"}'
    get_probe(client, {"Authorization": f"Bearer {TOKEN}"})
    text = written_output.text()
    assert KEY not in text
    assert TOKEN not in text
    assert "SECRET ANSWER" not in text
    assert "SECRET PROVIDER ERROR" not in text
