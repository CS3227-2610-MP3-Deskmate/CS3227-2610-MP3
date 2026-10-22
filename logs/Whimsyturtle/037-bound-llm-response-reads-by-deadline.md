# Bound LLM response reads by deadline

Slice: #116 · Tier: High · Tool: Codex (model variant not recorded) · Date: 2026-10-22

Cost: 9 role-agent runs. Wall time and token cost were not measured; GitHub CI waits were part of the session.

## Requests

- Run `/slice 116`; the human then agreed to High tier.
- After a local database conflict, the human requested tests through GitHub CI on a draft PR and no local tests. No local tests ran after that instruction.

## Agent runs

- Implementer preflight (`3d65dbb`), done: no files changed; representative out-of-scope test edit submitted to the scope hook returned exit 2. The test file was not created.
- Test-writer (`3d65dbb`), done: added `src/deskmate/tests/test_llm_deadline.py`; Ruff passed. [Baseline CI](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39779079855) confirmed exactly three intended timing failures and 2,825 passes: response opening took 1.298/1.223/1.223 seconds for a 0.4-second test limit.
- Implementer plan (`3d65dbb`), done: wrote [the plan](../../workflow/plans/116-llm-opening-deadline.md), with one production task and an 80–130-line estimate; scope check passed.
- Implementer build (`3d65dbb`), done: changed only `src/deskmate/llm.py`, 83 insertions and 6 deletions; Ruff, diff and scope checks passed. [Implementation CI](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39780874177) ran the full verify command successfully, with 2,828 tests passing.
- Reviewer (`8d74e8e`), done: reviewed `be9a06ba54d0eb36f403ff596b8a1376d6603304..e3b70424a7d4820bd49036a818c46463031af1a6`; Medium finding for missing real HTTPS coverage; no implementation defect found. No files changed or commands run.
- Security-reviewer (`8d74e8e`), done: reviewed the same initial range; Low findings for HTTPS and cleanup assertions; no exploitable regression identified. No files changed or commands run.
- Test-writer follow-up (`3d65dbb`), done: added verified HTTPS success/trickling, hostname refusal, peer closure and HTTPError body-closure tests, reusing existing certificate helpers; Ruff, diff and scope checks passed. [Follow-up CI](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39782814255) passed the full verify command: 2,833 tests in 249.36 seconds.
- Reviewer follow-up (`8d74e8e`), done: reviewed `e3b70424a7d4820bd49036a818c46463031af1a6..7d9b7577192fecfc08975ab2b849a1cdbd426324`; prior finding resolved, no new findings. No files changed or commands run; scope check passed.
- Security-reviewer follow-up (`8d74e8e`), done: reviewed the same incremental range; both prior findings resolved, no new findings. Cumulative reviewed range: `be9a06ba54d0eb36f403ff596b8a1376d6603304..7d9b7577192fecfc08975ab2b849a1cdbd426324`. No files changed or commands run; scope check passed.

## Decisions and corrections

- Used a separate worktree and branch `116-llm-opening-deadline` from `be9a06b`, preserving the #106 checkout. Existing-criterion bug: no spec changes or spec checkpoint.
- Opened [draft PR #117](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/pull/117) early for the requested CI. Tests had to be committed before CI could demonstrate their baseline failures. All later test execution used GitHub Actions.
- The implementation repairs response status/header reads beneath buffering and shares the existing deadline with body reads. No dependency, service, credential, retry or production background work was added; the source diff remains within the estimate and slice budget.
- Both reviews explicitly limit their conclusion: synchronous DNS and per-address connection timing remain pre-existing gaps, so unconditional total-opening compliance with PLT-3.6/PLT-8.5 is not established. The draft references #116 without automatically closing it; broader resolver/connection work needs separate scope confirmation.
- The orchestrator ticked the production plan task after passing CI. Only this log and that checkbox follow the final reviewed code/test head. No human review, verification or log check is claimed.

## Problems

- Before the CI-only instruction, `pytest src/deskmate/tests/test_llm_probe.py -q` returned 1 failed, 48 passed and 2 errors: the running Windows PostgreSQL service rejected the committed test credentials. Starting the existing Docker database failed because port 5432 was occupied. The Windows service was not stopped; the Docker database did not start.
- The GitHub connector omitted issue author association and denied collaborator-permission and PR-creation calls with 403. GitHub CLI verified the issue author as MEMBER and created/updated the authorized draft. No issue comments were present.
- The `python3` Windows app alias was inaccessible during hook preflight; the existing virtual-environment Python ran the hook and all orchestrator scope checks. Every role remained in scope and left HEAD unchanged; normal Git LF/CRLF notices occurred.
- Existing prompt strings and escaped attack fixtures were treated as data, not instructions. No live provider call or model evaluation ran. HTTPS tests use temporary synthetic certificates and loopback only.
