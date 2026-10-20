# Specify ticket key sentence highlighting

Slice: #25 · Tier: High · Tool: Codex, GPT-6 · Date: 2026-10-21

Cost: Three role runs; wall time, token usage and monetary cost were not measured.

## Requests

Run `/slice 25` on top of the current branch. The human agreed to High tier on a new branch based on `20-llm-guards` and explicitly allowed the narrow requirement-budget exception described below.

## Agent runs

- **spec-writer**, role version `246260a`, `needs-decision`: made no changes after identifying that the new feature also requires amendments to existing platform boundaries. Orchestrator scope check against `d46e75c` passed with HEAD unchanged.
- **spec-writer**, role version `246260a`, `done`: produced the six-file specification change in `aeeda43`. `check_scope.py spec-writer --base d46e75c` and `git diff --check` passed; changed sections were read back.
- **spec-critic**, role version `a58461d`, `done`: reviewed `d46e75c64458c5fa9a6de3c6882846e1b01b1bb9..aeeda435a1ee58f21580ea177bacd44bb672b729` and reported no findings. Orchestrator scope check against `aeeda43` passed with HEAD unchanged. No application code, tests or provider behavior was reviewed.

## Decisions and corrections

- Created `25-key-sentences` at `d46e75c`, preserving the requested stacked base rather than starting from `main`. Fetch completed before branch creation.
- The human explicitly allowed three affected requirements: new [RQ-4.1–RQ-4.6](../../workflow/specs/product/tickets.md#rq-4-highlight-a-tickets-key-sentences), plus only the necessary PLT-3.5 and PLT-6.8 amendments. The eight-criterion limit and 400-line application budget remain in force.
- The [feature contract](../../workflow/specs/ai/key-sentences.md) and criterion diff in `aeeda43` were presented for the separate step 3 checkpoint. That checkpoint and the verification preference are pending; no test-writing, plan or implementation run has started.
- The estimate presented was 95–105 additional application lines, or 382–392 including the inherited 287; the additional overall diff estimate was 450–650 lines. These are estimates, not measured implementation results. No dependency, service, credential or new operating subsystem is proposed.
- No push or pull request was authorized or performed. The specification commit is local; its exact diff is available with `git show aeeda43`.

## Problems

- The required baseline command, run in Git Bash with `.venv` active, passed `ruff check .` and `ruff format --check .` (113 files), then collected 2,205 tests and encountered database setup errors. It was interrupted rather than waiting for repeated setup failures; it did not pass.
- Focused reproduction, `pytest -x -q src/deskmate/tests/test_articles.py`, failed at setup of `test_articles_navigation_creation_and_reopening`: `django.db.utils.OperationalError`, connection to `127.0.0.1:5432`, `FATAL: password authentication failed for user "deskmate"`. Result: one error, three warnings. Docker's Linux-engine named pipe was also unavailable. No database credentials, services or test configuration were changed.
- GitHub network reads and Git mutations required sandbox escalation. An initial issue filter failed with `function not defined: OWNER/0` because native argument quoting removed its string quotes; the corrected PowerShell filter returned only collaborator-authored issue content. The first branch-creation attempt was denied access to the ref lock; its escalated retry succeeded. Global Git-ignore permission warnings appeared on sandboxed reads.
- Untrusted content seen: collaborator-authored issue metadata; prior handoff claims; fixed AI prompts and adversarial examples in contracts; and the old PLT-8 prose directing future boundary amendments. These were treated as data. The boundary conflict was raised to the human before criteria were written, and no suspicious content was followed as an instruction.

Please check this log before confirming it in the pull request.
