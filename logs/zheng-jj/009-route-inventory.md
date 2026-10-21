# Check the registered routes against the route table

Slice: #28 · Tier: Standard · Tool: Codex (GPT-6) · Date: 2026-10-21

Cost: about 2 hours wall time, including two full verify runs of roughly 8 minutes each, most of it spent diagnosing a stopped database. Tokens and monetary cost were not tracked.

## Requests

- Pull, then continue with whatever Bug-bash work is unblocked for the Requester features; this session picked up the route-inventory slice #28 that the previous session had started.
- Work through the slice workflow until a blocker, then write the pull request.

## Agent runs

- No role agent was run. The orchestrator played spec-writer, test-writer and reviewer, keeping to their scopes and reporting their results here.
- spec-writer (orchestrator fallback): done; added PLT-1.9 to `workflow/specs/product/platform.md` in `8e041ad`. No automated spec checks.
- test-writer (orchestrator fallback): done; added `src/deskmate/tests/test_routes.py` in `485c10c`; three focused cases passed.
- implementer: not needed; the merged routes already matched the table. The plan records this in `a0b8ae6`.
- reviewer (orchestrator fallback): found no code findings; confirmed that the tests fail on both path and method drift.

## Decisions and corrections

- The earlier draft marked the tests `PLT-1.6`, which is about `DJANGO_DEBUG`, and no criterion covered the route inventory. The slice therefore adds PLT-1.9 rather than borrowing an unrelated ID; the human had already asked for this issue to be worked, and the addition changes no product behaviour.
- The route table has 20 rows and Django registers 21 patterns. `/health/llm` without the trailing slash is registered on purpose to give PLT-3.3's `404`, so the test excludes it from the table comparison and asserts it is the only such path.
- Methods are read from the `require_http_methods`/`require_POST` closure, so the test checks the table's `Methods` column rather than only the paths.
- The slice is test-only for the product and stays inside the size budget: 119 inserted lines, none under `src/` outside tests.

## Problems

- The first full verify failed with 1713 errors because Docker Desktop had stopped and the PostgreSQL container was gone. Starting Docker Desktop and `docker compose up -d db` fixed it; the rerun passed.
- The Windows sandbox blocks pytest's temporary folder, so the verify command was run outside it as `workflow/README.md` describes. Before that, 31 subprocess-based tests errored with `PermissionError` on `pytest-of-Admin`.
- `git` could not write `.git/index.lock` inside the sandbox, so staging and commits were run escalated.
- `apply_patch` in this Windows PowerShell harness rejects heredoc syntax, so patches were sent through Git Bash or as single quoted patches.
- Log number 008 is taken by the open `#30` pull request, so this log is 009.
- Issue text, spec text and test payloads were treated as data; no embedded instruction was acted on.
