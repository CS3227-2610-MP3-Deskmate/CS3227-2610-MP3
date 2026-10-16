"""PLT-2: fresh CI and complete attempt history admit provider submission.

All GitHub API documents are synthetic. Hosted main-review/environment controls
remain manual; these tests establish only the local admission decision.
"""

import copy
import importlib
import re
import secrets
import ssl
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit

import pytest

from deskmate.tests.test_release import response

REPOSITORY = "synthetic-owner/deskmate"
SHA = "a" * 40
WORKFLOW_ID = 88
CI_WORKFLOW_ID = 77
CI_ID = 9001
BASELINE_ID = 1002
CURRENT_ID = 1004
ORIGIN = datetime(2026, 1, 1, tzinfo=UTC)


def timestamp(minutes):
    return (ORIGIN + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def run_document(number, attempt=1, status="completed", conclusion="success"):
    return {
        "id": 1000 + number,
        "name": "Deploy",
        "path": ".github/workflows/deploy.yml",
        "workflow_id": WORKFLOW_ID,
        "run_number": number,
        "run_attempt": attempt,
        "event": "workflow_run",
        "head_branch": "main",
        "head_sha": SHA,
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": REPOSITORY},
        "status": status,
        "conclusion": conclusion,
        "created_at": timestamp(number * 10 - 2),
        "run_started_at": timestamp(number * 10 - 1),
        "updated_at": timestamp(number * 10),
    }


def production_job(run, conclusion=None, completed=None):
    skipped = conclusion == "skipped"
    completed = timestamp(run["run_number"] * 10) if completed is None else completed
    return {
        "id": run["id"] * 1000 + run["run_attempt"],
        "run_id": run["id"],
        "run_attempt": run["run_attempt"],
        "name": "production",
        "status": "completed",
        "conclusion": conclusion or run["conclusion"],
        # Real skipped jobs can have equal, non-null start/end timestamps.
        "started_at": completed if skipped else timestamp(run["run_number"] * 10 - 1),
        "completed_at": completed,
        "steps": [],
    }


class GitHubHistory:
    """A bounded, authenticated fake of read-only Actions history endpoints."""

    def __init__(self):
        self.now = 1000.0
        self.deadline = 1900.0
        self.token = secrets.token_urlsafe(24)
        self.calls = []
        self.errors = []
        self.runs = {}
        self.jobs = {}
        self.overrides = {}
        self.delay = 0
        for number in range(1, 5):
            self.add_attempt(number)
        self.runs[CURRENT_ID][1].update(status="in_progress", conclusion=None)
        self.jobs[CURRENT_ID, 1][0].update(
            status="in_progress", conclusion=None, completed_at=None
        )
        self.ci = {
            **run_document(9),
            "id": CI_ID,
            "name": "CI",
            "path": ".github/workflows/ci.yml",
            "workflow_id": CI_WORKFLOW_ID,
            "event": "push",
        }
        self.workflow = {
            "id": WORKFLOW_ID,
            "name": "Deploy",
            "path": ".github/workflows/deploy.yml",
            "state": "active",
        }

    def add_attempt(self, number, attempt=1, **changes):
        document = run_document(number, attempt)
        document.update(changes)
        self.runs.setdefault(document["id"], {})[attempt] = document
        self.jobs[document["id"], attempt] = [production_job(document)]
        return document

    def latest(self, run_id):
        attempts = self.runs[run_id]
        return attempts[max(attempts)]

    def request(self, url, token=None, timeout=10):
        try:
            return self._request(url, token, timeout)
        except AssertionError as error:
            # main() safely suppresses arbitrary exception details. Preserve fake
            # violations so that they cannot masquerade as valid blocked results.
            self.errors.append(str(error))
            raise

    def _request(self, url, token, timeout):
        parsed = urlsplit(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "api.github.com"
        assert not parsed.fragment
        assert token == self.token
        prefix = f"/repos/{REPOSITORY}/actions/"
        assert parsed.path.startswith(prefix), "Only fixed repository Actions API reads"
        assert 0 < timeout <= min(10, self.deadline - self.now)
        query = parse_qs(parsed.query)
        page = int(query.get("page", [1])[0])
        per_page = int(query.get("per_page", [30])[0])
        assert 1 <= per_page <= 100
        self.calls.append(
            SimpleNamespace(url=url, path=parsed.path, page=page, timeout=timeout)
        )
        assert len(self.calls) < 2000, "Admission must remain bounded"
        self.now += self.delay
        key = (parsed.path.removeprefix(prefix), page)
        if key in self.overrides:
            result = self.overrides[key]
            if isinstance(result, Exception):
                raise result
            return result
        endpoint = key[0]
        workflow_path = r"(?:88|deploy\.yml|%2Egithub%2Fworkflows%2Fdeploy\.yml)"
        if endpoint in ("workflows/ci.yml", "workflows/77"):
            return response(
                {
                    "id": CI_WORKFLOW_ID,
                    "name": "CI",
                    "path": ".github/workflows/ci.yml",
                    "state": "active",
                }
            )
        if re.fullmatch(rf"workflows/{workflow_path}", endpoint, re.IGNORECASE):
            return response(self.workflow)
        if endpoint == f"runs/{CI_ID}":
            return response(self.ci)
        if re.fullmatch(rf"workflows/{workflow_path}/runs", endpoint, re.IGNORECASE):
            documents = sorted(
                (self.latest(run_id) for run_id in self.runs),
                key=lambda run: run["run_number"],
                reverse=True,
            )
            # The API supports filters, but a restrictive filter cannot establish
            # complete Deploy history (including skipped pull-request attempts).
            if "event" in query:
                documents = [
                    run for run in documents if run["event"] == query["event"][0]
                ]
            return self.paginate(url, "workflow_runs", documents, page, per_page)
        match = re.fullmatch(r"runs/(\d+)(?:/attempts/(\d+))?(/jobs)?", endpoint)
        assert match, f"Unexpected Actions API endpoint: {endpoint}"
        run_id, attempt, jobs = match.groups()
        run_id = int(run_id)
        if run_id not in self.runs:
            return response({}, 404)
        attempt = int(attempt) if attempt else max(self.runs[run_id])
        if attempt not in self.runs[run_id]:
            return response({}, 404)
        if jobs:
            assert "/attempts/" in endpoint, (
                "Latest-only jobs hide earlier rerun attempts"
            )
            return self.paginate(
                url, "jobs", self.jobs[run_id, attempt], page, per_page
            )
        return response(self.runs[run_id][attempt])

    @staticmethod
    def paginate(url, key, documents, page, per_page):
        start = (page - 1) * per_page
        headers = {}
        if start + per_page < len(documents):
            parsed = urlsplit(url)
            headers["Link"] = (
                f"<{parsed.scheme}://{parsed.netloc}{parsed.path}"
                f'?per_page={per_page}&page={page + 1}>; rel="next"'
            )
        return response(
            {"total_count": len(documents), key: documents[start : start + per_page]},
            **headers,
        )


@pytest.fixture
def gate():
    # A missing module is the expected initial TDD failure, not a collection error.
    return importlib.import_module("deskmate.release_gate")


@pytest.fixture
def history(gate, monkeypatch):
    state = GitHubHistory()
    environment = {
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_RUN_ID": str(CURRENT_ID),
        "GITHUB_RUN_NUMBER": "4",
        "GITHUB_RUN_ATTEMPT": "1",
        "CHECKED_SHA": SHA,
        "RELEASE_CI_RUN_ID": str(CI_ID),
        "RELEASE_RECOVERY_BASELINE": f"{BASELINE_ID}:1",
        "RELEASE_JOB_DEADLINE": str(state.deadline),
        "GITHUB_TOKEN": state.token,
    }
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    for name in (
        "VERCEL_TOKEN",
        "VERCEL_ORG_ID",
        "VERCEL_PROJECT_ID",
        "VERCEL_PUBLIC_HOSTNAME",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(gate, "request", state.request)
    monkeypatch.setattr(gate.time, "monotonic", lambda: state.now)
    monkeypatch.setattr(
        gate.time, "sleep", lambda seconds: setattr(state, "now", state.now + seconds)
    )
    yield state
    assert state.errors == []


def assert_blocked(gate, history, capsys):
    assert gate.main() == 1
    captured = capsys.readouterr()
    assert "recovery: blocked" in captured.out + captured.err
    assert history.token not in captured.out + captured.err
    assert "Traceback" not in captured.out + captured.err
    return captured.out + captured.err


@pytest.mark.ac("PLT-2.1", "PLT-2.2", "PLT-2.4", "PLT-2.5", "PLT-2.6")
def test_release_gate_valid_ci_and_history_admit_without_vercel_credentials(
    gate, history, capsys
):
    assert gate.main() == 0
    assert any(call.path.endswith(f"/runs/{CI_ID}") for call in history.calls)
    assert any(
        call.path.endswith("/runs/1002/attempts/1/jobs") for call in history.calls
    )
    captured = capsys.readouterr()
    assert "recovery: blocked" not in captured.out + captured.err
    assert history.token not in captured.out + captured.err


@pytest.mark.ac("PLT-2.1", "PLT-2.2", "PLT-2.5", "PLT-2.6")
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "in_progress"),
        ("conclusion", "failure"),
        ("event", "pull_request"),
        ("head_branch", "other"),
        ("head_sha", "b" * 40),
        ("repository", {"full_name": "other-owner/deskmate"}),
        ("head_repository", {"full_name": "fork-owner/deskmate"}),
        ("workflow_id", WORKFLOW_ID),
        ("path", ".github/workflows/unrelated.yml"),
        ("id", CI_ID + 1),
    ],
    ids=[
        "pending",
        "failed",
        "pr",
        "branch",
        "sha",
        "repository",
        "fork",
        "workflow",
        "path",
        "run-id",
    ],
)
def test_release_gate_refetches_ci_and_rejects_each_ineligible_source(
    gate, history, capsys, field, value
):
    history.ci[field] = value
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.1", "PLT-2.5", "PLT-2.6")
@pytest.mark.parametrize(
    "field",
    [
        "status",
        "conclusion",
        "event",
        "head_branch",
        "head_sha",
        "repository",
        "head_repository",
    ],
)
def test_release_gate_missing_ci_evidence_blocks(gate, history, capsys, field):
    history.ci.pop(field)
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.5", "PLT-2.6")
@pytest.mark.parametrize(
    "name",
    [
        "GITHUB_REPOSITORY",
        "GITHUB_RUN_ID",
        "GITHUB_RUN_NUMBER",
        "GITHUB_RUN_ATTEMPT",
        "CHECKED_SHA",
        "RELEASE_CI_RUN_ID",
        "RELEASE_RECOVERY_BASELINE",
        "RELEASE_JOB_DEADLINE",
        "GITHUB_TOKEN",
    ],
)
def test_release_gate_missing_required_input_blocks_without_api_call(
    gate, history, monkeypatch, capsys, name
):
    monkeypatch.delenv(name)
    assert_blocked(gate, history, capsys)
    assert history.calls == []


@pytest.mark.ac("PLT-2.4", "PLT-2.5", "PLT-2.6")
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("GITHUB_REPOSITORY", "synthetic-owner"),
        ("GITHUB_REPOSITORY", "synthetic-owner/deskmate/other"),
        ("GITHUB_RUN_ID", "0"),
        ("GITHUB_RUN_NUMBER", "-1"),
        ("GITHUB_RUN_ATTEMPT", "1.0"),
        ("RELEASE_CI_RUN_ID", "not-a-run"),
        ("CHECKED_SHA", "a" * 39),
        ("CHECKED_SHA", "g" * 40),
        ("RELEASE_RECOVERY_BASELINE", "1002"),
        ("RELEASE_RECOVERY_BASELINE", "1002:0"),
        ("RELEASE_RECOVERY_BASELINE", "1002:1:2"),
        ("RELEASE_JOB_DEADLINE", "nan"),
        ("RELEASE_JOB_DEADLINE", "inf"),
        ("GITHUB_TOKEN", ""),
    ],
)
def test_release_gate_invalid_input_blocks_before_any_api_request(
    gate, history, monkeypatch, capsys, name, value
):
    monkeypatch.setenv(name, value)
    assert_blocked(gate, history, capsys)
    assert history.calls == []


@pytest.mark.ac("PLT-2.5", "PLT-2.6")
@pytest.mark.parametrize(
    "escaped",
    [
        r"owner\x2fdeskmate\x3fpage=2",
        r"owner\x2f..\x2fother",
        r"owner\x2fdeskmate\x40evil.test",
        r"owner\x2fdeskmate\x0a",
    ],
)
def test_release_gate_repository_payload_cannot_redirect_authenticated_api_reads(
    gate, history, monkeypatch, capsys, escaped
):
    monkeypatch.setenv(
        "GITHUB_REPOSITORY", escaped.encode("ascii").decode("unicode_escape")
    )
    assert_blocked(gate, history, capsys)
    assert history.calls == []


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
@pytest.mark.parametrize("remaining", [-0.01, 0, 0.01, 9.99, 10, 10.01])
def test_release_gate_api_requests_obey_remaining_shared_job_deadline(
    gate, history, monkeypatch, capsys, remaining
):
    history.deadline = history.now + remaining
    monkeypatch.setenv("RELEASE_JOB_DEADLINE", str(history.deadline))
    if remaining <= 0:
        assert_blocked(gate, history, capsys)
        assert history.calls == []
    else:
        assert gate.main() == 0
        assert history.calls
        assert all(call.timeout <= min(10, remaining) for call in history.calls)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
def test_release_gate_api_response_arriving_at_deadline_blocks(gate, history, capsys):
    history.delay = history.deadline - history.now
    assert_blocked(gate, history, capsys)
    assert len(history.calls) == 1


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
@pytest.mark.parametrize(
    "failure",
    [
        response({}, 401),
        response({}, 403),
        response({}, 404),
        response({}, 302),
        response({}, 429),
        response({}, 503),
        response(b"not JSON"),
        response([]),
        TimeoutError(),
        URLError("synthetic unavailable"),
        ssl.SSLCertVerificationError("synthetic invalid TLS"),
    ],
    ids=[
        "unauthorized",
        "forbidden",
        "missing",
        "redirect",
        "rate-limit",
        "provider-error",
        "malformed",
        "wrong-type",
        "timeout",
        "transport",
        "tls",
    ],
)
def test_release_gate_uncertain_github_evidence_fails_closed(
    gate, history, capsys, failure
):
    history.overrides[f"runs/{CI_ID}", 1] = failure
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.5", "PLT-2.6")
def test_release_gate_api_exception_and_body_never_enter_logs(gate, history, capsys):
    private = secrets.token_urlsafe(24)
    history.overrides[f"runs/{CI_ID}", 1] = RuntimeError(private + history.token)
    output = assert_blocked(gate, history, capsys)
    assert private not in output


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
@pytest.mark.parametrize("baseline", ["9999:1", "1002:2", "1004:1", "1005:1"])
def test_release_gate_missing_active_or_future_baseline_cannot_acknowledge_history(
    gate, history, monkeypatch, capsys, baseline
):
    if baseline == "1005:1":
        history.add_attempt(5, status="queued", conclusion=None)
        history.jobs[1005, 1] = []
    monkeypatch.setenv("RELEASE_RECOVERY_BASELINE", baseline)
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
@pytest.mark.parametrize(
    "changes",
    [
        {"status": "in_progress", "conclusion": None},
        {"workflow_id": CI_WORKFLOW_ID},
        {"repository": {"full_name": "other-owner/deskmate"}},
    ],
    ids=["unfinished", "different-workflow", "different-repository"],
)
def test_release_gate_baseline_must_be_completed_attempt_of_this_deploy_workflow(
    gate, history, capsys, changes
):
    history.runs[BASELINE_ID][1].update(changes)
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
def test_release_gate_baseline_acknowledges_its_failed_attempt_after_operator_recovery(
    gate, history
):
    history.runs[BASELINE_ID][1]["conclusion"] = "failure"
    history.jobs[BASELINE_ID, 1][0]["conclusion"] = "failure"
    assert gate.main() == 0


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
@pytest.mark.parametrize(
    "offset", [-1, 0, 1], ids=["strictly-before", "same-time-ambiguous", "after"]
)
def test_release_gate_only_trustworthy_completion_strictly_before_baseline_is_covered(
    gate, history, capsys, offset
):
    older = history.runs[1001][1]
    older["conclusion"] = "failure"
    history.jobs[1001, 1][0].update(
        conclusion="failure", completed_at=timestamp(20 + offset)
    )
    if offset < 0:
        assert gate.main() == 0
    else:
        assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
def test_release_gate_cutoff_uses_last_completed_job_not_run_updated_at(gate, history):
    history.runs[BASELINE_ID][1]["updated_at"] = timestamp(10)
    history.jobs[BASELINE_ID, 1].append(
        {
            **production_job(history.runs[BASELINE_ID][1]),
            "id": 222,
            "name": "post-release",
            "completed_at": timestamp(25),
        }
    )
    history.runs[1001][1]["conclusion"] = "failure"
    history.jobs[1001, 1][0].update(conclusion="failure", completed_at=timestamp(24))
    assert gate.main() == 0


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
@pytest.mark.parametrize("completed", [None, "not-a-time"])
def test_release_gate_missing_or_invalid_baseline_job_completion_blocks(
    gate, history, capsys, completed
):
    history.jobs[BASELINE_ID, 1][0]["completed_at"] = completed
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
def test_release_gate_unfinished_older_attempt_is_not_covered_by_old_run_timestamp(
    gate, history, capsys
):
    history.runs[1001][1].update(
        status="in_progress", conclusion=None, updated_at=timestamp(1)
    )
    history.jobs[1001, 1][0].update(
        status="in_progress", conclusion=None, completed_at=None
    )
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
@pytest.mark.parametrize(
    "conclusion",
    [
        "failure",
        "cancelled",
        "timed_out",
        "startup_failure",
        "action_required",
        "neutral",
        None,
    ],
)
def test_release_gate_executed_unacknowledged_attempt_blocks_queued_release(
    gate, history, capsys, conclusion
):
    history.runs[1003][1]["conclusion"] = conclusion
    history.jobs[1003, 1][0]["conclusion"] = conclusion
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
def test_release_gate_later_rerun_of_older_run_remains_unacknowledged(
    gate, history, capsys
):
    rerun = history.add_attempt(1, 2, conclusion="failure")
    rerun["updated_at"] = timestamp(35)
    history.jobs[1001, 2][0].update(
        conclusion="failure", started_at=timestamp(34), completed_at=timestamp(35)
    )
    assert_blocked(gate, history, capsys)
    assert any("/runs/1001/attempts/2" in call.path for call in history.calls)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
def test_release_gate_successful_latest_rerun_does_not_erase_prior_failed_attempt(
    gate, history, capsys
):
    history.runs[1003][1]["conclusion"] = "failure"
    history.jobs[1003, 1][0]["conclusion"] = "failure"
    history.add_attempt(3, 2)
    history.jobs[1003, 2][0]["completed_at"] = timestamp(35)
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
def test_release_gate_current_rerun_checks_its_prior_attempt(
    gate, history, monkeypatch, capsys
):
    history.runs[CURRENT_ID][1].update(status="completed", conclusion="cancelled")
    history.jobs[CURRENT_ID, 1][0].update(
        status="completed", conclusion="cancelled", completed_at=timestamp(40)
    )
    history.add_attempt(4, 2, status="in_progress", conclusion=None)
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
def test_release_gate_acknowledged_rerun_still_rechecks_ci(
    gate, history, monkeypatch, capsys
):
    history.runs[CURRENT_ID][1].update(status="completed", conclusion="failure")
    history.jobs[CURRENT_ID, 1][0].update(
        status="completed", conclusion="failure", completed_at=timestamp(40)
    )
    history.add_attempt(4, 2, status="in_progress", conclusion=None)
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    monkeypatch.setenv("RELEASE_RECOVERY_BASELINE", f"{CURRENT_ID}:1")
    assert gate.main() == 0
    history.ci["conclusion"] = "failure"
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.5", "PLT-2.6")
def test_release_gate_genuine_skipped_pr_attempt_with_timestamps_is_settled(
    gate, history
):
    history.runs[1003][1].update(
        event="pull_request",
        conclusion="skipped",
        head_branch="feature",
        head_repository={"full_name": "fork-owner/deskmate"},
    )
    history.jobs[1003, 1] = [production_job(history.runs[1003][1], "skipped")]
    assert gate.main() == 0


@pytest.mark.ac("PLT-2.4", "PLT-2.5", "PLT-2.6")
@pytest.mark.parametrize(
    "problem", ["empty", "missing-production", "executed-production", "incomplete-job"]
)
def test_release_gate_skipped_run_label_without_complete_no_submission_evidence_blocks(
    gate, history, capsys, problem
):
    history.runs[1003][1].update(event="pull_request", conclusion="skipped")
    skipped = production_job(history.runs[1003][1], "skipped")
    if problem == "empty":
        history.jobs[1003, 1] = []
    elif problem == "missing-production":
        history.jobs[1003, 1] = [{**skipped, "name": "unrelated"}]
    elif problem == "executed-production":
        history.jobs[1003, 1] = [
            skipped,
            {**skipped, "id": 333, "conclusion": "cancelled"},
        ]
    else:
        history.jobs[1003, 1] = [
            {**skipped, "status": "in_progress", "conclusion": None}
        ]
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
def test_release_gate_future_queued_attempt_with_no_production_execution_is_excluded(
    gate, history
):
    history.add_attempt(5, status="queued", conclusion=None)
    history.jobs[1005, 1] = []
    assert gate.main() == 0


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
@pytest.mark.parametrize(
    "problem", ["executed-current-attempt", "failed-prior-attempt", "in-progress"]
)
def test_release_gate_future_run_is_excluded_only_if_lock_queued_without_execution(
    gate, history, capsys, problem
):
    if problem == "failed-prior-attempt":
        history.add_attempt(5, 1, conclusion="failure")
        history.jobs[1005, 1][0]["conclusion"] = "failure"
        history.add_attempt(5, 2, status="queued", conclusion=None)
        history.jobs[1005, 2] = []
    else:
        history.add_attempt(
            5,
            status="queued" if problem == "executed-current-attempt" else "in_progress",
            conclusion=None,
        )
        history.jobs[1005, 1][0].update(
            status="in_progress",
            conclusion=None,
            started_at=timestamp(45),
            completed_at=None,
        )
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
@pytest.mark.parametrize("missing", [1001, 1003, CURRENT_ID])
def test_release_gate_missing_or_gapped_workflow_run_history_blocks(
    gate, history, capsys, missing
):
    history.runs.pop(missing)
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
def test_release_gate_missing_intermediate_attempt_blocks_despite_successful_latest(
    gate, history, capsys
):
    history.add_attempt(3, 3)
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
@pytest.mark.parametrize(
    "problem", ["missing-jobs", "false-count", "duplicate-job", "invalid-timestamp"]
)
def test_release_gate_missing_or_uncertain_historical_completion_cannot_be_covered(
    gate, history, capsys, problem
):
    history.runs[1001][1]["conclusion"] = "failure"
    job = history.jobs[1001, 1][0]
    job["conclusion"] = "failure"
    if problem == "missing-jobs":
        history.jobs[1001, 1] = []
    elif problem == "false-count":
        history.overrides["runs/1001/attempts/1/jobs", 1] = response(
            {"total_count": 2, "jobs": [job]}
        )
    elif problem == "duplicate-job":
        history.jobs[1001, 1].append(copy.deepcopy(job))
    else:
        job["completed_at"] = "unknown"
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
@pytest.mark.parametrize("kind", ["runs", "jobs"])
def test_release_gate_complete_history_requires_all_pages_before_admission(
    gate, history, monkeypatch, capsys, kind
):
    if kind == "runs":
        for number in range(5, 103):
            history.add_attempt(number)
        history.runs[CURRENT_ID][1].update(status="completed", conclusion="success")
        history.jobs[CURRENT_ID, 1][0].update(
            status="completed", conclusion="success", completed_at=timestamp(40)
        )
        history.runs[1102][1].update(status="in_progress", conclusion=None)
        monkeypatch.setenv("GITHUB_RUN_ID", "1102")
        monkeypatch.setenv("GITHUB_RUN_NUMBER", "102")
        rerun = history.add_attempt(1, 2, conclusion="failure")
        history.jobs[1001, 2][0].update(
            conclusion="failure", completed_at=timestamp(1015)
        )
        rerun["updated_at"] = timestamp(1015)
    else:
        history.runs[1003][1]["conclusion"] = "skipped"
        skipped = production_job(history.runs[1003][1], "skipped")
        history.jobs[1003, 1] = [
            {**skipped, "id": 30000 + index} for index in range(101)
        ]
        history.jobs[1003, 1][-1]["conclusion"] = "cancelled"
    assert_blocked(gate, history, capsys)
    assert any(call.page > 1 for call in history.calls)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
def test_release_gate_baseline_cutoff_uses_last_job_on_later_page(gate, history):
    job = history.jobs[BASELINE_ID, 1][0]
    history.jobs[BASELINE_ID, 1] = [
        {**job, "id": 20000 + index} for index in range(101)
    ]
    history.jobs[BASELINE_ID, 1][-1]["completed_at"] = timestamp(25)
    history.runs[1001][1]["conclusion"] = "failure"
    history.jobs[1001, 1][0].update(conclusion="failure", completed_at=timestamp(24))
    assert gate.main() == 0
    assert any(
        call.path.endswith("/runs/1002/attempts/1/jobs") and call.page > 1
        for call in history.calls
    )


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
@pytest.mark.parametrize(
    "problem", ["missing-total", "truncated", "duplicate", "wrong-workflow"]
)
def test_release_gate_inconclusive_run_listing_blocks(gate, history, capsys, problem):
    documents = [
        history.latest(run_id) for run_id in sorted(history.runs, reverse=True)
    ]
    body = {"total_count": 4, "workflow_runs": documents}
    if problem == "missing-total":
        body.pop("total_count")
    elif problem == "truncated":
        body["workflow_runs"] = documents[:1]
    elif problem == "duplicate":
        body["workflow_runs"] = [documents[0], documents[0], *documents[2:]]
    else:
        documents[1]["workflow_id"] = CI_WORKFLOW_ID
    for workflow in ("88", "deploy.yml"):
        history.overrides[f"workflows/{workflow}/runs", 1] = response(body)
    assert_blocked(gate, history, capsys)


@pytest.mark.ac("PLT-2.4", "PLT-2.6")
@pytest.mark.parametrize(
    ("name", "value"), [("GITHUB_RUN_NUMBER", "3"), ("GITHUB_RUN_ATTEMPT", "2")]
)
def test_release_gate_current_identity_must_match_authenticated_run(
    gate, history, monkeypatch, capsys, name, value
):
    monkeypatch.setenv(name, value)
    assert_blocked(gate, history, capsys)
