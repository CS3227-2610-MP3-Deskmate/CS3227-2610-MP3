# Specify ticket key sentence highlighting

Slice: #25 · Tier: High · Tool: Codex, GPT-6 · Date: 2026-10-21

Cost: Ten role turns, including resumed spec-writing and test-writing work; wall time, token usage and monetary cost were not measured.

## Requests

Run `/slice 25` on top of the current branch. The human agreed to High tier on a new branch based on `20-llm-guards`, confirmed the scope checkpoint, and explicitly allowed the requirement and size exceptions below.

## Agent runs

- **spec-writer**, role version `246260a`, `needs-decision`: made no changes after identifying that the new feature also requires amendments to existing platform boundaries. Orchestrator scope check against `d46e75c` passed with HEAD unchanged.
- **spec-writer**, role version `246260a`, `done`: produced the six-file specification change in `aeeda43`. `check_scope.py spec-writer --base d46e75c` and `git diff --check` passed; changed sections were read back.
- **spec-critic**, role version `a58461d`, `done`: reviewed `d46e75c64458c5fa9a6de3c6882846e1b01b1bb9..aeeda435a1ee58f21580ea177bacd44bb672b729` and reported no findings. Orchestrator scope check against `aeeda43` passed with HEAD unchanged. No application code, tests or provider behavior was reviewed.
- **test-writer**, role version `3d65dbb`, `needs-decision`: left an unfinished test draft when its formatted size showed the initial overall estimate would be exceeded; scope check against `4967d5a` passed, HEAD unchanged. Fifteen routing tests failed with the expected missing-route `404`; integration setup hit the database blocker. Draft lint errors were reported, not treated as completion.
- **test-writer**, role version `3d65dbb`, `done` after confirmation: finalized `287d2a3`, mapping all eight changed criteria to tests and updating only the necessary existing form assertion. Scope check against `4967d5a`, repository lint and format checks passed; routing tests remained expected red, while database-backed coverage remained unverified.
- **implementer**, role version `3d65dbb`, `done`: wrote the two-task [plan](../../workflow/plans/25-key-sentences.md) in `d3f1a69`; scope check against `e161dc6` and diff check passed, HEAD unchanged.
- **implementer**, role version `3d65dbb`, `blocked` on verification: prepared `41e56d1`; scope check against `d3f1a69`, diff check, repository lint/format and all fifteen new routing cases passed. Exact full verification hit repeated database setup errors and was interrupted. Task checkbox stayed pending.
- **implementer**, role version `3d65dbb`, `blocked` on verification: updated the User Guide in `4046e83`; scope check against `41e56d1`, section read-back and diff check passed. Exact verification passed Ruff then repeated the database blocker; checkbox stayed pending.
- **reviewer**, role version `8d74e8e`, `done`: static review of `9c6d68b9742c184e6a8fade6adb9b4af4edd61ad..4046e83b2fdd1772b4e64813d7d79df0c75aee35` found no issues. Scope check against `4046e83` passed; no commands or edits by the reviewer. Database-backed behavior was not verified.
- **security-reviewer**, role version `8d74e8e`, `done`: static review of `9c6d68b9742c184e6a8fade6adb9b4af4edd61ad..4046e83b2fdd1772b4e64813d7d79df0c75aee35` found no concrete issues or missing attack classes. Scope check against `4046e83` passed; no commands or edits by the reviewer. Fake-provider attack execution and real-model behavior were not verified.
- **test-writer**, role version `3d65dbb`, `done`: `d407edb` corrected the two assertions CI reported, and the CI job on that commit passed. A later `reviewer` round found that the expired-session case could pass without the 8-hour sign-in rule, because Django's stored expiry also ended the session at the same moment; a second `test-writer` run renews the session just before the boundary. Ruff check and format passed; pytest could not run locally, and CI on that follow-up commit is pending.
- **reviewer**, role version `8d74e8e`, `done`: reviewed `4046e83..d407edb` and the follow-up test change. It found one Low (the expired-session case above), one Low log-accuracy finding fixed here, and no correctness, escaping, source-selection or access-order defect. The first-round corrections strengthen assertions rather than weaken them. Read-only; no commands or edits.

## Decisions and corrections

- Created `25-key-sentences` at `d46e75c`, preserving the requested stacked base rather than starting from `main`. Fetch completed before branch creation.
- The human explicitly allowed three affected requirements: new [RQ-4.1–RQ-4.6](../../workflow/specs/product/tickets.md#rq-4-highlight-a-tickets-key-sentences), plus only the necessary PLT-3.5 and PLT-6.8 amendments. The eight-criterion limit and 400-line application budget remain in force.
- The human confirmed the [feature contract](../../workflow/specs/ai/key-sentences.md), criteria in `aeeda43` and estimates with `approve go`, completing the separate step 3 checkpoint.
- The initial overall estimate of 450–650 lines was too low for readable tests. Work paused before implementation; the human explicitly selected an allowance of up to 800 overall changed lines while retaining the 400-line application cap. No capability, dependency, service, credential or operating subsystem was added by that exception.
- Parent PR #75 merged into `main` at `9c6d68b`; `e161dc6` integrated it without conflicts, preserving the requested ancestry. The inherited gateway no longer appears in this slice's diff against `main`; application changes measure 96 lines, within the original 95–105 estimate.
- The orchestrator reproduced 27 passing explicit test nodes on `4046e83`: fifteen new routing cases and twelve existing probe cases. The remaining 68 new database-backed cases are unverified. Both plan boxes stay pending until full verification passes.
- Both static reviews inspected baseline files through the read-only GitHub connector and received unpublished changes as fenced data; shared tool-store values were not visible across agents. No reviewer ran shell commands. This log, the test corrections and the draft PR description are the only changes after the first reviewed head.
- The draft PR description is prepared from the repository template with criterion mappings, unverified results and unticked human checkboxes. No push or PR creation has been authorized or performed; publishing for CI remains the next permission decision.

## Problems

- The required baseline command, run in Git Bash with `.venv` active, passed `ruff check .` and `ruff format --check .` (113 files), then collected 2,205 tests and encountered database setup errors. It was interrupted rather than waiting for repeated setup failures; it did not pass.
- Focused reproduction, `pytest -x -q src/deskmate/tests/test_articles.py`, failed at setup of `test_articles_navigation_creation_and_reopening`: `django.db.utils.OperationalError`, connection to `127.0.0.1:5432`, `FATAL: password authentication failed for user "deskmate"`. Result: one error, three warnings. Docker's Linux-engine named pipe was also unavailable. No database credentials, services or test configuration were changed.
- Final exact verification passed `ruff check .` and `ruff format --check .` (114 files), then collected 2,288 tests and repeated that setup failure. It was interrupted, including a second interrupt during traceback printing; there is no full-suite pass. Focused new integration execution failed at setup for the same reason; no real provider was contacted.
- An initial combined test selection used `-k no_session`, which also filtered out the requested probe nodes. The corrected explicit-node command ran all 27 selected cases successfully. Pytest reported a cache-path warning; no application behavior was skipped or changed to avoid the database failure.
- GitHub network reads and Git mutations required sandbox escalation. An initial issue filter failed with `function not defined: OWNER/0` because native argument quoting removed its string quotes; the corrected PowerShell filter returned only collaborator-authored issue content. The first branch-creation attempt was denied access to the ref lock; its escalated retry succeeded. Global Git-ignore permission warnings appeared on sandboxed reads.
- Untrusted content seen: collaborator-authored issue metadata; prior handoff claims; fixed AI prompts and adversarial examples in contracts; and the old PLT-8 prose directing future boundary amendments. These were treated as data. The boundary conflict was raised to the human before criteria were written, and no suspicious content was followed as an instruction.

Please check this log before confirming it in the pull request.
