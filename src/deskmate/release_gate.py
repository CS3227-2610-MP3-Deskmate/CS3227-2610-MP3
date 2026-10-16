"""Admit a production submission using fresh CI and complete Actions history.

The CLI consumes the workflow's GitHub identity, CHECKED_SHA, RELEASE_CI_RUN_ID,
RELEASE_RECOVERY_BASELINE, RELEASE_JOB_DEADLINE and read-only GITHUB_TOKEN.
It never reads provider credentials or acknowledges recovery itself.
"""

import json
import math
import os
import re
import sys
import time
from datetime import datetime

if __package__:
    from .release import request
else:
    from release import request


class _Blocked(Exception):
    pass


def _require(condition):
    if not condition:
        raise _Blocked


def _positive(value):
    _require(type(value) is int and value > 0)
    return value


def _timestamp(value):
    _require(
        isinstance(value, str)
        and re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})",
            value,
        )
    )
    return datetime.fromisoformat(value)


def _path(value, filename):
    # A GitHub @ref suffix is metadata, never part of an API request destination.
    return isinstance(value, str) and re.fullmatch(
        re.escape(f".github/workflows/{filename}") + r"(?:@[^\s@]+)?", value
    )


def _completion(run, jobs):
    _require(
        run.get("status") == "completed"
        and isinstance(run.get("conclusion"), str)
        and run["conclusion"]
        and jobs
        and any(job["name"] == "production" for job in jobs)
    )
    ends = []
    for job in jobs:
        _require(
            job.get("status") == "completed"
            and isinstance(job.get("conclusion"), str)
            and job["conclusion"]
        )
        start = _timestamp(job.get("started_at"))
        end = _timestamp(job.get("completed_at"))
        _require(start <= end)
        ends.append(end)
    return max(ends)


class _Gate:
    def __init__(self):
        self.repository = os.environ["GITHUB_REPOSITORY"]
        _require(
            re.fullmatch(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{1,100}", self.repository)
            and self.repository.split("/")[1] not in (".", "..")
        )
        fields = (
            "GITHUB_RUN_ID",
            "GITHUB_RUN_NUMBER",
            "GITHUB_RUN_ATTEMPT",
            "RELEASE_CI_RUN_ID",
        )
        numbers = []
        for field in fields:
            value = os.environ[field]
            _require(re.fullmatch(r"[1-9][0-9]*", value))
            numbers.append(int(value))
        self.run_id, self.number, self.attempt, self.ci_id = numbers
        self.sha = os.environ["CHECKED_SHA"]
        _require(re.fullmatch(r"[0-9a-f]{40}", self.sha))
        baseline = os.environ["RELEASE_RECOVERY_BASELINE"]
        _require(re.fullmatch(r"[1-9][0-9]*:[1-9][0-9]*", baseline))
        self.baseline = tuple(map(int, baseline.split(":")))
        self.token = os.environ["GITHUB_TOKEN"]
        _require(
            self.token.strip() and "\r" not in self.token and "\n" not in self.token
        )
        self.deadline = float(os.environ["RELEASE_JOB_DEADLINE"])
        _require(math.isfinite(self.deadline) and time.monotonic() < self.deadline)
        self.reads = 0

    def _api(self, path):
        # Round the deadline down so subtraction cannot extend the request budget.
        remaining = math.nextafter(self.deadline, -math.inf) - time.monotonic()
        self.reads += 1
        _require(remaining > 0 and self.reads <= 10000)
        status, _, body = request(
            f"https://api.github.com/repos/{self.repository}/actions/{path}",
            self.token,
            timeout=min(10, remaining),
        )
        _require(time.monotonic() < self.deadline and status == 200)
        document = json.loads(body)
        _require(isinstance(document, dict))
        return document

    def _list(self, path, key):
        # Construct pages locally; never use response Link destinations.
        documents, identities = [], set()
        total = None
        page = 1
        while True:
            document = self._api(f"{path}?per_page=100&page={page}")
            count = document.get("total_count")
            _require(type(count) is int and 0 <= count <= 100000)
            if total is None:
                total = count
            _require(count == total)
            batch = document.get(key)
            _require(
                isinstance(batch, list)
                and len(batch) == min(100, total - len(documents))
            )
            for item in batch:
                _require(isinstance(item, dict))
                identity = _positive(item.get("id"))
                _require(identity not in identities)
                identities.add(identity)
            documents.extend(batch)
            if len(documents) == total:
                return documents
            page += 1

    def _workflow(self, filename, name):
        workflow = self._api(f"workflows/{filename}")
        _require(
            workflow.get("name") == name
            and _path(workflow.get("path"), filename)
            and workflow.get("state") == "active"
        )
        return _positive(workflow.get("id"))

    def _run(self, run, workflow, filename, name):
        _require(
            _positive(run.get("workflow_id")) == workflow
            and _path(run.get("path"), filename)
            and run.get("name") == name
            and run.get("repository", {}).get("full_name") == self.repository
        )
        return tuple(
            _positive(run.get(key)) for key in ("id", "run_number", "run_attempt")
        )

    def _jobs(self, run, attempt):
        jobs = self._list(f"runs/{run}/attempts/{attempt}/jobs", "jobs")
        for job in jobs:
            _require(
                _positive(job.get("run_id")) == run
                and _positive(job.get("run_attempt")) == attempt
                and isinstance(job.get("name"), str)
                and job["name"]
            )
        return jobs

    def _admit(self):
        ci = self._api(f"runs/{self.ci_id}")
        workflow = self._workflow("ci.yml", "CI")
        _require(self._run(ci, workflow, "ci.yml", "CI")[0] == self.ci_id)
        expected = {
            "event": "push",
            "head_branch": "main",
            "head_sha": self.sha,
            "status": "completed",
            "conclusion": "success",
        }
        _require(
            all(ci.get(key) == value for key, value in expected.items())
            and ci.get("head_repository", {}).get("full_name") == self.repository
        )
        workflow = self._workflow("deploy.yml", "Deploy")
        runs = self._list(f"workflows/{workflow}/runs", "workflow_runs")
        indexed = {}
        for run in runs:
            identity, number, attempt = self._run(run, workflow, "deploy.yml", "Deploy")
            _require(number not in indexed)
            indexed[number] = (identity, attempt)
        _require(indexed and len(indexed) == max(indexed))
        _require(indexed.get(self.number) == (self.run_id, self.attempt))
        attempts = {}
        for run in runs:
            identity, number, latest = self._run(run, workflow, "deploy.yml", "Deploy")
            for attempt in range(1, latest + 1):
                detail = self._api(f"runs/{identity}/attempts/{attempt}")
                _require(
                    self._run(detail, workflow, "deploy.yml", "Deploy")
                    == (identity, number, attempt)
                )
                if (identity, attempt) == (self.run_id, self.attempt):
                    _require(
                        detail.get("status") == "in_progress"
                        and detail.get("conclusion") is None
                    )
                    continue
                jobs = self._jobs(identity, attempt)
                attempts[identity, attempt] = (detail, jobs)
        _require(self.baseline in attempts)
        baseline, jobs = attempts[self.baseline]
        _require(
            baseline["run_number"] < self.number
            or (
                baseline["run_number"] == self.number
                and baseline["run_attempt"] < self.attempt
            )
        )
        boundary = _completion(baseline, jobs)
        for identity, (run, jobs) in attempts.items():
            if identity == self.baseline:
                continue
            if run["run_number"] > self.number and run.get("status") == "queued":
                _require(
                    run.get("conclusion") is None
                    and all(
                        job.get("status") == "queued"
                        and job.get("started_at") is None
                        and job.get("completed_at") is None
                        and job.get("conclusion") is None
                        for job in jobs
                    )
                )
                continue
            completed = _completion(run, jobs)
            production = [job for job in jobs if job["name"] == "production"]
            _require(
                completed < boundary
                or run.get("conclusion") == "success"
                or all(job.get("conclusion") == "skipped" for job in production)
            )


def main():
    """Return a safe admission result without logging configuration or responses."""
    try:
        _Gate()._admit()
    except Exception:  # noqa: BLE001 -- transport/API exceptions can contain secrets.
        print("recovery: blocked", file=sys.stderr)
        return 1
    print("recovery: passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
