# Restrict usernames to ASCII

Slice: #48 · Tool: Codex (GPT-6) · Date: 2026-10-18

Cost: 12 role-agent runs; total wall time, tokens and monetary cost were not recorded.

## Requests

- Run `/slice 48`, using the High tier and the agreed ASCII username checkpoint.
- Omit legacy-account handling because the human stated there are no production users.
- Rely on GitHub CI for full verification when local database checks proved slow.
- Publish the branch and create a draft PR; leave the log for review in the PR.

## Agent runs

- spec-writer (`246260a`): done; drafted ACC-1.3/ACC-1.7 and the technical reference in `c7faa7d`; scope and whitespace checks passed.
- spec-critic (`a58461d`): done; found an ambiguous whitespace predicate; read-only scope passed.
- spec-writer (`246260a`): done; clarified the predicate in `686e0e8`; reported an exhaustive match with Python 3.14 trimming, and scope/whitespace checks passed.
- test-writer (`3d65dbb`): done; wrote `6c6f598`; focused red run had 17 failures and 190 passes for the missing behavior; role/demo baseline had 82 passes; lint, format and scope checks passed.
- implementer (`3d65dbb`): done; wrote the plan in `3ccaa30`; scope and whitespace checks passed; no planning-stage tests.
- implementer (`3d65dbb`): done; implemented `2cc4845`; lint/format, migration and scope checks passed; final focused sign-in run had 151 passes in 75.46 seconds. Full-run interruption and test-state failures are recorded below.
- implementer (`3d65dbb`): done; updated the User Guide in `e1d5ba3`; section readback, whitespace and scope checks passed; no prose tests.
- reviewer (`246260a`): done; found one missing assertion protecting rejected usernames from normalization; read-only scope passed.
- security-reviewer (`3d65dbb`): done; no security findings through `e1d5ba3`; read-only scope passed; no commands or tests run.
- test-writer (`3d65dbb`): done; added the assertion in `833d93c`; 22 model cases passed before and after an in-memory mutation diagnostic, which failed once as expected with inherited normalization restored; lint/format, whitespace and scope checks passed.
- reviewer (`246260a`): done; confirmed the finding resolved through `833d93c`; no unresolved findings; read-only scope passed; no commands or tests run.
- security-reviewer (`3d65dbb`): done; no findings in the final test delta through `833d93c`; read-only scope passed; no commands or tests run.

## Decisions and corrections

- Created `48-ascii-usernames` from fetched `main` at `e00c5d5`. The existing checkout was clean, and its previous branch was already included in main. Subsequent fetches still showed that base.
- The human agreed to the [criteria changes](../../workflow/specs/product/accounts.md#acc-1-sign-in-and-out-by-role). No dependency, service, credential, database constraint, account conversion or recovery capability was added; demo generation remains unchanged.
- Root independently reproduced two intended failures and one valid-alphabet pass before implementation. After implementation, demo creation, generated-account sign-in and invalid-fullwidth attempt counting all passed: three focused checks in 15.65 seconds.
- Root independently checked migration SQL (`BEGIN`, no-op, `COMMIT`) and migration drift (`No changes detected`). The generated migration changes validator state only. Final root lint/format checks passed with 83 files already formatted.
- The human preferred full verification in GitHub CI after the local full run became slow. That one-slice direction replaced further local full-suite runs; the plan's original verification step was not rewritten. Full-suite results are recorded by the PR's GitHub checks; no full local-suite pass is claimed.
- The only review finding required a test assertion, not an implementation change. Production-source changes total 55 lines; only ACC-1.3 and ACC-1.7 changed, within the agreed estimate and slice budget.
- The human chose to review the log in the PR, so its author checkbox remains unticked. After the request to publish, `git push -u origin 48-ascii-usernames` and `gh pr create --draft` both exited 0, creating draft [PR #49](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/pull/49). No merge or deployment was performed.

## Problems

- The full local command passed lint/format and reached 76% in `test_migration.py` without reported failures before the requested interruption. It exited 1 without a completion summary, so it is incomplete.
- The first focused run afterward had 3 failures, 148 passes, 4 teardown errors and 1 warning because `test_deskmate` disappeared. Interrupted-run cleanup racing the rerun is an inference. Root subsequently observed no Python processes from that day's test run; unrelated older processes were left alone. A fresh focused run passed all 151 cases without source, test or configuration changes.
- Earlier local logs documented slow `localhost` PostgreSQL connection setup on Windows. No relay, helper service, dependency or configuration workaround was added here; the existing PostgreSQL container stayed running.
- Sandbox restrictions initially blocked GitHub network access, Git index writes and Docker inspection; the same authorized operations succeeded after escalation. Initial PowerShell/native jq quoting failed; native JSON filtering then limited issue/comment reads to repository collaborators. Early focused tests also reported incidental pytest-cache warnings.
- Issue/comment proposals, merge-completion wording, plan directives and escaped attack payloads were treated as data. No push, merge, hosted change, secret read or instruction from untrusted content was performed.
