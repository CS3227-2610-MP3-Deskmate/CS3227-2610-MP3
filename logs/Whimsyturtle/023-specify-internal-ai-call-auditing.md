# Specify internal AI call auditing

Slice: #22 · Tier: High · Tool: Codex (GPT-6) · Date: 2026-10-20

Cost: Three role invocations: spec-writer, spec-critic and a resumed spec-writer correction. Wall time, tokens and monetary cost were not measured.

## Requests

- Run `/slice 22`, [Record LLM calls in an audit log](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/issues/22).
- The human chose an internal user-call audit helper with time, keyed user hash, feature and success/failure metadata, with 30-day cleanup on writes; the operator probe stays database-independent. The presented estimate was 100–180 changed application lines and 350–650 total, with one table/migration and no new dependency, service, credential or setting.
- The human subsequently confirmed High tier and directed verification through existing GitHub CI using a draft PR because Docker on this computer is unavailable.

## Agent runs

- **spec-writer** (`246260a`): done; `994bd84` adds [PLT-6.1–PLT-6.8](../../workflow/specs/product/platform.md#plt-6-record-internal-ai-call-audit-metadata), its technical boundary and privacy controls across four spec files. Writer and orchestrator scope checks and whitespace checks passed; changed sections were read back.
- **spec-critic** (`a58461d`): done; reviewed `0799314734d319e56e612fa0c57a2ccb9a581de8..994bd840ca395612a85675ab887d74bb8183fedd`. Found ambiguous retention guarantees under overlapping invocations and ambiguous key selection in local debug. Read-only scope and whitespace checks passed. No implementation, test, CI or deployment verification was claimed.
- **spec-writer**, correction (`246260a`): done; `bd162f3` resolves those two findings by defining pruning per invocation and using Django's effective secret key. Writer and orchestrator scope checks and whitespace checks passed; affected sections were read back. The correction did not receive another critic run; the slice procedure permits one correction run before the checkpoint.

## Decisions and corrections

- Created `22-llm-audit` from fetched `main` at `0799314` in `.claude/worktrees/22-llm-audit`, preserving the clean primary checkout on slice #21. PR #69 remained open and unmerged. This slice does not import or depend on it; PLT-5 is reserved for that work.
- The checkpoint is the spec diff `0799314..bd162f3`: eight criteria in one requirement, with 39 inserted and two deleted spec lines and no application changes. The original estimate and scope remain the proposed implementation budget; no added capability or operating service is proposed.
- The human's CI direction will be followed by pushing the slice branch and opening a draft PR once the spec checkpoint is agreed and failing tests are ready. This is earlier PR creation than the slice's delivery step. Existing CI and deployment workflows remain outside the requested change; no push or PR creation occurred in this checkpoint session.
- Tests, plan, implementation and code/security reviews have not started. The next decision is agreement to the concrete criteria before step 4; author checking of this log is also pending.

## Problems

- Baseline `pytest -q src/deskmate/tests/test_health.py --maxfail=1`, with the existing primary `.venv` active in Git Bash, exited 1: the first health test errored during database setup with `FATAL: password authentication failed for user "deskmate"` at `127.0.0.1:5432`; pytest reported one warning and one error in 0.97 seconds. This was not a successful full verify run.
- `docker info` exited 1 because the daemon pipe was unavailable, with an additional inaccessible Docker configuration warning. No local service, credentials or database contents were changed, and no secrets or `.env` files were read.
- The writer's system `python3` alias was unavailable; the existing `.venv` Python ran scope checks successfully. Git emitted global-ignore permission and line-ending warnings; scope and whitespace checks still completed successfully. Git/GitHub access needed sandbox escalation, which succeeded.
- Untrusted content seen: none reported by the role agents; collaborator-authored issue metadata and agent handoffs were treated as data.
