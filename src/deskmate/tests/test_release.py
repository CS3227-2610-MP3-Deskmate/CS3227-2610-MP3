"""PLT-2: verification uses provider identity and bounded public smoke checks.

Synthetic provider fields follow https://vercel.com/openapi.json:
GET /v13/deployments/{idOrUrl} and GET /v4/aliases/{idOrAlias}.
The official CLI creates deployments; this helper only verifies its returned ID.
"""

import importlib
import io
import json
import secrets
import ssl
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.error import URLError
from urllib.parse import urlsplit

import pytest

DEPLOYMENT = "dpl_synthetic"
OWNER = "team_synthetic"
PROJECT = "prj_synthetic"
HOST = "deskmate-synthetic.vercel.app"
CLI_HOST = "deployment-synthetic.vercel.app"
# PLT-1.1's sentence, and the sentence a previous deployment's home page showed.
SENTENCE = (
    b"Deskmate is a service desk: Requesters raise tickets and Support Officers "
    b"resolve them."
)
PREVIOUS_SENTENCE = b"Deskmate is under construction."
HOME = (
    b"<!doctype html><html><head><title>Deskmate</title></head>"
    b"<body><h1>Deskmate</h1><p>" + SENTENCE + b"</p>\n"
    b'<p><a href="/sign-in/">Sign in</a></p></body></html>'
)
SIGN_IN_LINK = b'<a href="/sign-in/">Sign in</a>'
OTHER_LINK = b'<a href="/other/">Other</a>'
# Home pages that a browser renders unlike PLT-1.1's page but a checker reading
# only the visible markup could pass. Each changes HOME at one place, keeping
# its title, heading, text and Sign in link, so it is invalid in one way only.
UNREADABLE_HOMES = [
    pytest.param(
        SIGN_IN_LINK,
        b'<span><template shadowrootmode="open">'
        b'<a href="https://evil.example/">Sign in</a></template>'
        + SIGN_IN_LINK
        + b"</span>",
        # The shadow root's link is shown in place of the unslotted Sign in link.
        id="declarative-shadow-root-replaces-link",
    ),
    pytest.param(
        b"<head>",
        b'<head><noscript><base href="https://evil.example/"></noscript>',
        id="base-inside-noscript",
    ),
    pytest.param(
        # Inside SVG or MathML, <style> holds markup, and <p> leaves the foreign
        # element, so the browser shows the extra link as an ordinary one.
        b"</body>",
        b"<svg><style><p>" + OTHER_LINK + b"</p></style></svg></body>",
        id="style-inside-svg-hides-link",
    ),
    pytest.param(
        b"</body>",
        b"<math><style><p>" + OTHER_LINK + b"</p></style></math></body>",
        id="style-inside-math-hides-link",
    ),
    # A browser ignores the slash on a non-void element, so each element stays
    # open and hides, or turns into text, the markup after it.
    pytest.param(
        SIGN_IN_LINK, b"<template/>" + SIGN_IN_LINK, id="self-closing-template"
    ),
    pytest.param(
        SIGN_IN_LINK, b"<noscript/>" + SIGN_IN_LINK, id="self-closing-noscript"
    ),
    pytest.param(b"<head>", b"<head><style/>", id="self-closing-style-in-head"),
    pytest.param(
        SIGN_IN_LINK, b"<textarea/>" + SIGN_IN_LINK, id="self-closing-textarea"
    ),
    pytest.param(
        # With scripting on, <noscript> holds "<template>" as text, so the
        # browser shows the link that follows it.
        b"</body>",
        b"<noscript><template></noscript>" + OTHER_LINK + b"</template></body>",
        id="crossed-noscript-and-template",
    ),
    pytest.param(
        b"</body>",
        b'<script>document.write("Other")</script></body>',
        id="script",
    ),
    pytest.param(
        b"</body>",
        b"<iframe srcdoc=\"<a href='/other/'>Other</a>\"></iframe></body>",
        id="iframe",
    ),
    pytest.param(
        b"</body>",
        b'<object data="https://evil.example/"></object></body>',
        id="object",
    ),
    pytest.param(b"</body>", b'<embed src="https://evil.example/"></body>', id="embed"),
    # A browser ends each of these comments at the first ">", so it shows the
    # link that a parser reading on to "]]>" or "-->" hides.
    pytest.param(
        b"</body>",
        b"<![CDATA[x>" + OTHER_LINK + b"]]></body>",
        id="cdata-declaration-hides-link",
    ),
    pytest.param(
        b"</body>",
        b"<!-->" + OTHER_LINK + b"--></body>",
        id="abrupt-empty-comment-hides-link",
    ),
    pytest.param(
        b"</body>",
        b"<!--->" + OTHER_LINK + b"--></body>",
        id="abrupt-dash-comment-hides-link",
    ),
    # The check fails any comment, even a harmless one.
    pytest.param(b"</body>", b"<!-- note --></body>", id="comment"),
    pytest.param(
        # After a frameset, a browser drops the body and shows only the frames.
        b"</head>",
        b'</head><frameset><frame src="https://evil.example/"></frameset>',
        id="frameset",
    ),
    pytest.param(
        # Even with no frame, a browser drops the body and shows a blank page.
        b"</head>",
        b"</head><frameset></frameset>",
        id="empty-frameset",
    ),
    pytest.param(
        # No inner text, so only the script flag fails this page.
        b"</body>",
        b'<script src="https://evil.example/x.js"></script></body>',
        id="empty-script",
    ),
    pytest.param(
        # With scripting on, a browser shows no link, but read as markup the
        # page has exactly one valid link, so only the noscript flag fails it.
        SIGN_IN_LINK,
        b"<noscript>" + SIGN_IN_LINK + b"</noscript>",
        id="noscript-wraps-link",
    ),
]


def response(body, status=200, content_type="application/json", **headers):
    if not isinstance(body, bytes):
        body = json.dumps(body).encode()
    return status, {"Content-Type": content_type, **headers}, body


def home_with(old, new):
    """Return a text/html response holding HOME with `old` replaced by `new`."""
    assert HOME.count(old) == 1
    return response(HOME.replace(old, new), content_type="text/html")


@pytest.fixture
def release():
    return importlib.import_module("deskmate.release")


@pytest.fixture
def scenario(release, monkeypatch):
    deployment = {
        "id": DEPLOYMENT,
        "ownerId": OWNER,
        "projectId": PROJECT,
        "target": "production",
        "readyState": "READY",
    }
    mapping = {"alias": HOST, "deploymentId": DEPLOYMENT, "projectId": PROJECT}
    replies = {
        "deployment": [response(deployment)],
        "mapping": [response(mapping)],
        "home": [response(HOME, content_type="text/html; charset=utf-8")],
        "health": [response({"status": "ok"})],
        "http_home": [response(b"", 308, Location=f"https://{HOST}/")],
        "http_health": [response(b"", 308, Location=f"https://{HOST}/health/")],
    }
    state = SimpleNamespace(
        now=1000.0,
        deadline=1900.0,
        replies=replies,
        calls=[],
        delays={},
        deployment=deployment,
        mapping=mapping,
        token=secrets.token_urlsafe(24),
    )

    def sleep(seconds):
        assert seconds > 0
        state.now += seconds

    def request(url, token=None, timeout=10):
        parsed = urlsplit(url)
        if parsed.netloc == "api.vercel.com":
            assert parsed.scheme == "https"
            if parsed.path == f"/v13/deployments/{DEPLOYMENT}":
                stage = "deployment"
            else:
                assert parsed.path == f"/v4/aliases/{HOST}"
                stage = "mapping"
            assert token == state.token
        else:
            assert parsed.netloc == HOST
            assert not parsed.query
            assert token is None
            assert parsed.path in ("/", "/health/")
            stage = "home" if parsed.path == "/" else "health"
            if parsed.scheme == "http":
                stage = "http_" + stage
            else:
                assert parsed.scheme == "https"
        assert 0 < timeout <= min(10, state.deadline - state.now)
        state.calls.append((stage, timeout, state.now))
        state.now += state.delays.get(stage, 0)
        queue = state.replies[stage]
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(release.time, "monotonic", lambda: state.now)
    monkeypatch.setattr(release.time, "sleep", sleep)
    monkeypatch.setattr(release, "request", request)
    return state


def verify(release, scenario):
    return release.verify_release(
        DEPLOYMENT, OWNER, PROJECT, HOST, scenario.token, scenario.deadline
    )


@pytest.mark.ac("PLT-2.2", "PLT-2.3", "PLT-2.7")
def test_release_valid_identity_mapping_and_public_pages_succeed(release, scenario):
    verify(release, scenario)
    stages = [call[0] for call in scenario.calls]
    assert stages[:2] == ["deployment", "mapping"]
    assert set(stages[2:]) == {"home", "health", "http_home", "http_health"}


@pytest.mark.ac("PLT-1.1", "PLT-2.3")
@pytest.mark.parametrize("wrapper", ["template", "noscript"])
def test_release_home_wrapper_hiding_extra_link_fails(release, scenario, wrapper):
    hidden = f"<{wrapper}>".encode() + OTHER_LINK + f"</{wrapper}>".encode()
    # The Sign in link after the wrapper keeps the rest of the page valid.
    scenario.replies["home"] = [home_with(SIGN_IN_LINK, hidden + SIGN_IN_LINK)]
    with pytest.raises(release.ReleaseError, match="home"):
        verify(release, scenario)
    assert [call[0] for call in scenario.calls].count("home") == 1


@pytest.mark.ac("PLT-1.1", "PLT-2.3")
@pytest.mark.parametrize(("old", "new"), UNREADABLE_HOMES)
def test_release_home_markup_unread_as_browser_reads_it_fails(
    release, scenario, old, new
):
    scenario.replies["home"] = [home_with(old, new)]
    with pytest.raises(release.ReleaseError, match="home"):
        verify(release, scenario)
    assert [call[0] for call in scenario.calls].count("home") == 1


@pytest.mark.ac("PLT-1.1", "PLT-2.3")
def test_release_home_previous_sentence_fails(release, scenario):
    # A healthy previous deployment still shows the earlier home page.
    scenario.replies["home"] = [home_with(SENTENCE, PREVIOUS_SENTENCE)]
    with pytest.raises(release.ReleaseError, match="home"):
        verify(release, scenario)
    assert [call[0] for call in scenario.calls].count("home") == 1


@pytest.mark.ac("PLT-1.1", "PLT-2.3")
def test_release_home_style_in_head_passes(release, scenario):
    scenario.replies["home"] = [
        home_with(b"</title>", b"</title><style>p > a { color: #1f5f8b; }</style>")
    ]
    verify(release, scenario)
    assert [call[0] for call in scenario.calls].count("home") == 1


@pytest.mark.ac("PLT-1.1", "PLT-2.3")
def test_release_home_real_page_passes(release, scenario, client):
    page = client.get("/")
    assert page.status_code == 200
    scenario.replies["home"] = [
        response(page.content, content_type=page["Content-Type"])
    ]
    verify(release, scenario)
    assert [call[0] for call in scenario.calls].count("home") == 1


@pytest.mark.ac("PLT-2.3", "PLT-2.5")
@pytest.mark.parametrize(
    "field", ["id", "ownerId", "projectId", "target", "readyState"]
)
@pytest.mark.parametrize("value", [None, "wrong"])
def test_release_missing_or_wrong_deployment_identity_fails_before_public_checks(
    release, scenario, field, value
):
    document = scenario.deployment.copy()
    if value is None:
        document.pop(field)
    else:
        document[field] = value
    scenario.replies["deployment"] = [response(document)]
    with pytest.raises(release.ReleaseError, match="deployment"):
        verify(release, scenario)
    assert [call[0] for call in scenario.calls] == ["deployment"]


@pytest.mark.ac("PLT-2.3")
@pytest.mark.parametrize("field", ["alias", "deploymentId", "projectId"])
@pytest.mark.parametrize("value", [None, "previous-deployment"])
def test_release_missing_or_wrong_mapping_cannot_pass_using_healthy_old_site(
    release, scenario, field, value
):
    document = scenario.mapping.copy()
    if value is None:
        document.pop(field)
    else:
        document[field] = value
    scenario.replies["mapping"] = [response(document)]
    with pytest.raises(release.ReleaseError, match="mapping"):
        verify(release, scenario)
    assert [call[0] for call in scenario.calls] == ["deployment", "mapping"]


@pytest.mark.ac("PLT-2.3")
def test_release_conflicting_nested_mapping_fails(release, scenario):
    document = {**scenario.mapping, "deployment": {"id": "dpl_previous"}}
    scenario.replies["mapping"] = [response(document)]
    with pytest.raises(release.ReleaseError, match="mapping"):
        verify(release, scenario)


@pytest.mark.ac("PLT-2.3", "PLT-2.4")
@pytest.mark.parametrize("stage", ["deployment", "mapping", "health"])
@pytest.mark.parametrize(
    "transient",
    [
        response(b"not JSON", 429),
        response({"status": "error"}, 503),
        URLError("temporary transport failure"),
        TimeoutError("temporary timeout"),
    ],
    ids=["rate-limit", "unhealthy-503", "transport", "timeout"],
)
def test_release_transient_failure_retries_before_validating_body(
    release, scenario, stage, transient
):
    scenario.replies[stage].insert(0, transient)
    verify(release, scenario)
    assert [call[0] for call in scenario.calls].count(stage) == 2


@pytest.mark.ac("PLT-2.3", "PLT-2.4")
@pytest.mark.parametrize("stage", ["deployment", "mapping", "health"])
@pytest.mark.parametrize("status", [301, 401, 403, 404])
def test_release_terminal_http_status_fails_without_retry(
    release, scenario, stage, status
):
    scenario.replies[stage] = [response(b"private response", status)]
    with pytest.raises(release.ReleaseError, match=stage):
        verify(release, scenario)
    assert [call[0] for call in scenario.calls].count(stage) == 1


@pytest.mark.ac("PLT-2.3", "PLT-2.4", "PLT-2.7")
@pytest.mark.parametrize(
    "error",
    [
        ssl.SSLCertVerificationError("invalid certificate"),
        URLError(ssl.SSLCertVerificationError("hostname mismatch")),
    ],
)
def test_release_invalid_tls_fails_immediately(release, scenario, error):
    scenario.replies["home"] = [error]
    with pytest.raises(release.ReleaseError, match="home"):
        verify(release, scenario)
    assert [call[0] for call in scenario.calls].count("home") == 1


@pytest.mark.ac("PLT-2.3", "PLT-2.7")
@pytest.mark.parametrize(
    ("stage", "bad_response"),
    [
        ("health", response({"status": "error"})),
        ("health", response({"status": "ok", "extra": True})),
        ("health", response(b"not JSON")),
        ("health", response({"status": "ok"}, content_type="text/html")),
        ("home", response(HOME, content_type="application/json")),
        (
            "home",
            response(
                HOME.replace(b"<title>Deskmate", b"<title>Other"),
                content_type="text/html",
            ),
        ),
        ("home", response(HOME + b"<h2>Extra heading</h2>", content_type="text/html")),
        ("home", response(HOME + b"Extra text", content_type="text/html")),
        (
            "home",
            response(
                HOME.replace(b'<a href="/sign-in/">Sign in</a>', b"Sign in"),
                content_type="text/html",
            ),
        ),
        (
            "home",
            response(
                HOME.replace(b'href="/sign-in/"', b'href="/sign-in"'),
                content_type="text/html",
            ),
        ),
        (
            "home",
            response(
                HOME.replace(
                    b'<a href="/sign-in/">Sign in</a>',
                    b'<a href="/sign-in/">Sign in</a><a href="/other/"></a>',
                ),
                content_type="text/html",
            ),
        ),
        (
            "home",
            response(
                HOME.replace(b'<a href="/sign-in/">', b'<a href="/other/">'),
                content_type="text/html",
            ),
        ),
        (
            "home",
            response(
                HOME.replace(
                    b'<a href="/sign-in/">',
                    b'<a href="/other/" href="/sign-in/">',
                ),
                content_type="text/html",
            ),
        ),
        (
            "home",
            response(
                HOME.replace(
                    b"<head>",
                    b'<head><base href="https://evil.example/">',
                ),
                content_type="text/html",
            ),
        ),
        (
            "home",
            response(
                HOME.replace(
                    b'<a href="/sign-in/">Sign in</a>',
                    b'<template><a href="/sign-in/">Sign in</a></template>',
                ),
                content_type="text/html",
            ),
        ),
        (
            "home",
            response(
                HOME.replace(
                    b'<a href="/sign-in/">Sign in</a>',
                    b'<a name="top"></a>',
                ),
                content_type="text/html",
            ),
        ),
        ("http_home", response(b"", 200)),
        ("http_health", response(b"", 308, Location=f"https://{HOST}/")),
        ("http_home", response(b"", 308, Location="https://other.vercel.app/")),
    ],
)
def test_release_success_status_with_wrong_content_fails_without_retry(
    release, scenario, stage, bad_response
):
    scenario.replies[stage] = [bad_response]
    with pytest.raises(release.ReleaseError, match=stage.removeprefix("http_")):
        verify(release, scenario)
    assert [call[0] for call in scenario.calls].count(stage) == 1


@pytest.mark.ac("PLT-2.4")
@pytest.mark.parametrize("remaining", [-0.01, 0, 0.01, 9.99, 10, 10.01])
def test_release_requests_never_exceed_job_time_remaining(release, scenario, remaining):
    scenario.deadline = scenario.now + remaining
    if remaining <= 0:
        with pytest.raises(release.ReleaseError, match="deployment"):
            verify(release, scenario)
        assert scenario.calls == []
    else:
        verify(release, scenario)
        assert scenario.calls[0][1] == pytest.approx(min(10, remaining))


@pytest.mark.ac("PLT-2.3", "PLT-2.4")
@pytest.mark.parametrize("job_remaining", [30, 900])
def test_release_mapping_and_public_checks_share_one_deadline(
    release, scenario, job_remaining
):
    start = scenario.now
    scenario.deadline = start + job_remaining
    scenario.delays["mapping"] = 6
    scenario.replies["health"] = [response({"status": "error"}, 503)]
    with pytest.raises(release.ReleaseError, match="health"):
        verify(release, scenario)
    deadline = min(scenario.deadline, start + 120)
    assert scenario.now <= deadline
    assert all(timeout <= deadline - when for _, timeout, when in scenario.calls)
    assert scenario.now == pytest.approx(deadline)


@pytest.mark.ac("PLT-2.4", "PLT-2.5")
def test_release_failure_does_not_log_provider_body_or_token(release, scenario, capsys):
    private_value = secrets.token_urlsafe(24)
    scenario.replies["deployment"] = [response({"private": private_value})]
    with pytest.raises(release.ReleaseError) as caught:
        verify(release, scenario)
    captured = capsys.readouterr()
    text = captured.out + captured.err + str(caught.value)
    assert private_value not in text
    assert scenario.token not in text


@pytest.mark.ac("PLT-2.7")
def test_request_redirect_is_returned_without_fetching_destination(release):
    paths = []

    class Redirect(BaseHTTPRequestHandler):
        def do_GET(self):
            paths.append(self.path)
            self.send_response(302 if self.path == "/" else 200)
            self.send_header("Location", "/destination")
            self.end_headers()

        def log_message(self, *_):
            pass

    with HTTPServer(("127.0.0.1", 0), Redirect) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            status, _, _ = release.request(
                f"http://127.0.0.1:{server.server_port}/", timeout=2
            )
            assert status == 302
            assert paths == ["/"]
        finally:
            server.shutdown()
            thread.join(timeout=2)


@pytest.fixture
def cli(release, monkeypatch):
    state = SimpleNamespace(
        now=1100.0,
        token=secrets.token_urlsafe(24),
        document={
            "id": DEPLOYMENT,
            "ownerId": OWNER,
            "projectId": PROJECT,
            "target": "production",
            "readyState": "READY",
        },
    )
    for name, value in {
        "VERCEL_ORG_ID": OWNER,
        "VERCEL_PROJECT_ID": PROJECT,
        "VERCEL_PUBLIC_HOSTNAME": HOST,
        "VERCEL_TOKEN": state.token,
        "RELEASE_JOB_DEADLINE": "1900",
        "RELEASE_COMPLETED_AT": "1000",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(release.sys, "stdin", io.StringIO(f"https://{CLI_HOST}\n"))
    monkeypatch.setattr(release.time, "monotonic", lambda: state.now)

    def resolve(*args, **kwargs):
        state.now += 1
        return response(state.document)

    state.request = Mock(side_effect=resolve)
    state.verify = Mock()
    monkeypatch.setattr(release, "request", state.request)
    monkeypatch.setattr(release, "verify_release", state.verify)
    return state


@pytest.mark.ac("PLT-2.2", "PLT-2.3", "PLT-2.4")
@pytest.mark.parametrize(
    ("ending", "job_deadline", "deadline", "request_timeout"),
    [("\n", 1900, 1120, 10), ("/\n", 1105, 1105, 5)],
)
def test_release_main_resolves_url_and_preserves_shared_deadline(
    release, cli, monkeypatch, capsys, ending, job_deadline, deadline, request_timeout
):
    monkeypatch.setenv("RELEASE_JOB_DEADLINE", str(job_deadline))
    monkeypatch.setattr(
        release.sys, "stdin", io.StringIO(f"https://{CLI_HOST}{ending}")
    )
    assert release.main() == 0
    cli.request.assert_called_once_with(
        f"https://api.vercel.com/v13/deployments/{CLI_HOST}?teamId={OWNER}",
        cli.token,
        timeout=request_timeout,
    )
    cli.verify.assert_called_once_with(
        DEPLOYMENT, OWNER, PROJECT, HOST, cli.token, deadline
    )
    captured = capsys.readouterr()
    assert f"deployment={DEPLOYMENT}" in captured.out
    assert "verification: passed" in captured.out
    assert captured.err == ""
    assert cli.token not in captured.out


@pytest.mark.ac("PLT-2.3", "PLT-2.4")
def test_release_main_expired_completion_window_makes_no_provider_request(
    release, cli, capsys
):
    cli.now = 1120
    assert release.main() == 1
    cli.request.assert_not_called()
    cli.verify.assert_not_called()
    assert capsys.readouterr().err == "deployment: failed\n"


@pytest.mark.ac("PLT-2.2", "PLT-2.5")
@pytest.mark.parametrize(
    "escaped",
    [
        r"https\x3a\x2f\x2fsynthetic.vercel.app.evil.test",
        r"https\x3a\x2f\x2fsynthetic.vercel.app\x40evil.test",
        r"https\x3a\x2f\x2fsynthetic.vercel.app\x25\x32\x66.evil.test",
        r"https\x3a\x2f\x2fsynthetic.vercel.app\u200b",
    ],
    ids=["suffix", "userinfo", "encoded-separator", "invisible-unicode"],
)
def test_release_main_unsafe_url_is_rejected_before_provider_request(
    release, cli, monkeypatch, capsys, escaped
):
    payload = escaped.encode("ascii").decode("unicode_escape")
    monkeypatch.setattr(release.sys, "stdin", io.StringIO(payload))
    assert release.main() == 1
    cli.request.assert_not_called()
    cli.verify.assert_not_called()
    assert capsys.readouterr().err == "deployment: failed\n"


@pytest.mark.ac("PLT-2.3", "PLT-2.5")
def test_release_main_wrong_owner_fails_before_public_verification(
    release, cli, capsys
):
    cli.document["ownerId"] = "team_other"
    assert release.main() == 1
    cli.verify.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "deployment: failed\n"


@pytest.mark.ac("PLT-2.4", "PLT-2.5")
@pytest.mark.parametrize("failing_call", ["request", "verify"])
def test_release_main_provider_exception_returns_nonzero_without_sensitive_details(
    release, cli, capsys, failing_call
):
    private_detail = secrets.token_urlsafe(24)
    getattr(cli, failing_call).side_effect = RuntimeError(private_detail + cli.token)
    assert release.main() == 1
    captured = capsys.readouterr()
    assert captured.err == "verification: failed\n"
    assert "verification: passed" not in captured.out
    assert private_detail not in captured.out + captured.err
    assert cli.token not in captured.out + captured.err
