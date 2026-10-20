# Run user AI admission slice

Slice: #21 · Tier: High · Tool: Codex (GPT-6) · Date: 2026-10-20

Cost: Nine substantive role runs, plus two resumed review invocations. Tokens, cost and active wall time were not counted; the session began on October 19 and included long waits for a decision, CI and resumption.

## Requests

- Run `/slice 21`, [Limit LLM calls per user and overall](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/issues/21).
- The human chose High, a reusable PostgreSQL user/global limiter foundation, and 10 admitted attempts per stored user and 30 across the app per rolling 10 minutes, including downstream failures. The operator probe stays outside this allowance.
- At the checkpoint, the human chose to continue with `0fd93b2`: PLT-5.1–5.8, estimated 120–200 changed application lines and 400–700 total lines, with no user route, provider call, UI, new dependency, service, credential or setting.
- After local database setup failed, the human directed verification through GitHub CI instead of changing local services. The human later asked to resume after interrupting the reviews.

## Agent runs

- **spec-writer** (`246260a`): done; `0fd93b2` adds the [PLT-5 criteria](../../workflow/specs/product/platform.md#plt-5-limit-admission-of-user-ai-calls), internal API and security controls. Writer/root scope and whitespace checks passed.
- **spec-critic** (`a58461d`): done; reviewed `47164d9..0fd93b2`, no findings. Root scope check passed; tests and implementation were not verified at that step.
- **test-writer** (`3d65dbb`), initial run: locally blocked; `6903920` adds 32 gate cases. Ruff/format and collection passed; local execution had 32 database-setup errors. After the human chose CI, the orchestrator confirmed the expected missing-module failures in the first remote run below. Scope checks passed.
- **implementer** (`3d65dbb`), plan: done; `4c7a2df` writes the single-task [plan](../../workflow/plans/21-llm-call-limits.md). Synthetic hook input targeting a test file was refused with exit 2; this validated the checker, not installed hook integration. Scope/whitespace checks passed.
- **implementer** (`3d65dbb`), build: initially pending CI; `bd8d74a` extracts shared counting, adds the HMAC user boundary and appends the AI kind with a generated choices-only migration. Ruff/format and migration consistency passed locally; full verification was deferred to CI. Scope checks passed.
- **test-writer** (`3d65dbb`), correction: done; `caaabd1` corrects two retry-delay expectations to 300 seconds and explains the independent per-kind moments. No case was removed or skipped. Ruff/format, scope and whitespace checks passed; the following CI run passed all cases.
- **implementer** (`3d65dbb`), finalization: done; `4e2f39a` ticks only the plan checkbox after CI passed. Scope/whitespace checks passed.
- **reviewer** (`8d74e8e`): done after resumption; reviewed `0799314734d319e56e612fa0c57a2ccb9a581de8..4e2f39a2edfbe1f3cfb1e26d65a0483f74663d10`, no findings. Independently inspected the CI log and all eight criteria's test coverage. No commands run; root scope check passed.
- **security-reviewer** (`8d74e8e`): done after resumption; reviewed the same `0799314734d319e56e612fa0c57a2ccb9a581de8..4e2f39a2edfbe1f3cfb1e26d65a0483f74663d10` range, no findings. Checked isolation, separate locks, clock ordering, commit-before-permission, HMAC identity and probe exclusion; independently inspected CI. No commands run; root scope check passed. Future routes and production behavior were not verified.

## Decisions and corrections

- Specs hold the behavior and [technical boundary](../../workflow/specs/TECHNICAL-SPEC.md#user-ai-admission); no existing route calls the gate. Trusted callers must supply the authenticated stored User outside another transaction. No User Guide change was needed.
- Created `21-llm-call-limits` from fetched `main` at `47164d9`. To run the requested CI, published the test commit and opened [draft PR #69](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/pull/69) before remote red verification, a sequence change from the slice procedure. Existing workflows were unchanged.
- Merged updated `main` at `0799314` cleanly as `0d0d394`, preserving the team's security fixes. Final freshness check found the same default head. The reviews used the published diff through `caaabd1` plus the supplied plan-only checkbox hunk at `4e2f39a`.
- The slice changes 45 application lines, excluding tests/migrations, below its estimate and 400-line cap. Reuse avoided a second counting implementation or operating service. The final total remains within the confirmed 700-line estimate.
- [Red CI](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39276547031) at `6903920`: unchanged `ruff check . && ruff format --check . && pytest` passed lint/format; 1,910 tests passed and all 32 new cases errored solely because `deskmate.llm_limits` was missing, in 141.68 seconds.
- [First implementation CI](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39278376253) at `0d0d394`: lint/format passed; 1,939 tests passed and three account-kind parameters failed in 147.07 seconds. Their test expected 600 seconds despite an older admission expiring after 300; the correction follows PLT-5.2–5.3 and the independent account moment, without changing production behavior.
- [Successful CI](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39280881040) at `caaabd1`: the same full verify command passed on pinned PostgreSQL 18.6, with 1,942 passed in 146.55 seconds, including all 32 gate cases and migration consistency. The root and both reviewers read job `118154523333`; GitHub's PR check subsequently showed `SUCCESS`. The later plan-only checkbox does not change executable behavior.

## Problems

- Local focused pytest could not initialize the database: `FATAL: password authentication failed for user "deskmate"` at `127.0.0.1:5432`. Read-only inspection found the PostgreSQL 17 Windows service occupying that port; Docker Desktop was installed but its daemon was unavailable. No local service, database data or credentials were changed, and no `.env` or secrets were read.
- Local `sqlmigrate accounts 0005` exited 1 on the same authentication failure. Its SQL output was not inspected; the generated choices-only migration was inspected, and CI migration consistency/full verification passed. A local full verify was not claimed.
- GitHub status APIs lagged behind completed job logs, causing an unnecessary wait. A cancellation attempt reported that the run was already complete; the root then retrieved the actual failed-job log and corrected the test expectations. A superseded pre-merge run was cancelled. No CI workflow was changed.
- Sandbox restrictions required successful escalation for GitHub/Git operations. Git warned about an inaccessible global ignore file. Windows `gh --jq` quoting was corrected with PowerShell filtering for collaborator comments; issue #21 was MEMBER-authored and no comments were returned.
- Untrusted content seen: fixed probe prompt strings and plan implementation directions were treated as data during review; no injected instructions were followed. The interruption required resuming both review agents; no source changed during it.
