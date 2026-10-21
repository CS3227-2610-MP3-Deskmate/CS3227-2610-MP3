# Correct key sentence authorization coverage

Slice: #27 · Tier: High (retained) · Tool: Codex (GPT-6) · Date: 2026-10-21

Cost: Three role-agent runs; wall time, tokens and monetary cost were not tracked.

## Requests

- Update the repository and determine whether PR #78 covers the route merged in PR #79.
- Correct PR #78's code to cover that route.
- Use GitHub CI for full verification; leave the existing local PostgreSQL service running.

## Agent runs

- test-writer (`3d65dbb`): done; corrected [the authorization matrix](../../src/deskmate/tests/test_authorization_matrix.py) in `70eae31`. Repository lint and formatting checks passed; the completeness assertion plus route-inventory tests passed; matrix collection and scope checks passed. Database tests were left to CI as requested.
- reviewer (`8d74e8e`): done; no findings in `3a690a2..70eae31`. Read-only GitHub inspection confirmed the correction; no commands run. Full CI was pending at review time.
- security-reviewer (`8d74e8e`): done; no findings in `3a690a2..70eae31`. Read-only review covered method, role and workspace denial before gateway invocation; no commands run. Its report covers this test correction only.

## Decisions and corrections

- Reused PR #78's branch and merged current main in `3a690a2`, without conflicts. Production code and acceptance criteria are unchanged.
- The correction exercises the merged route's existing [access contract](../../workflow/specs/product/tickets.md#rq-4-highlight-a-tickets-key-sentences), using real CSRF checks and a mocked gateway. The route-completeness test no longer needs a database fixture.
- The original completeness assertion was reproduced in an ignored temporary copy, with only its unused database marker removed. It failed specifically because the key-sentences route had no access decision.
- Full verification uses the unchanged `ruff check . && ruff format --check . && pytest` command in GitHub CI against PostgreSQL 18.6. The [CI run for `70eae31`](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39539081367) passed, as did the product-website check.
- Role scope checks passed. The PR diff has no application-code changes outside tests.

## Problems

- A plain pull initially failed because the merged key-sentences branch's upstream had been deleted; local main was fast-forwarded before the PR branch was updated.
- The initial local matrix run stopped with database setup errors: `FATAL: password authentication failed for user "deskmate"` on the existing PostgreSQL service. No local database tests are claimed as passing.
- Docker Desktop was started while checking the local environment, then stopped after the human chose GitHub CI. PostgreSQL 17 was left running.
- Fixed model instructions and escaped adversarial test payloads were treated as data; no embedded instruction was followed.
- The GitHub connector returned `403 Resource not accessible by integration` when updating the PR description; the existing GitHub CLI updated it successfully. A trailing blank line in this log was removed after the final whitespace check caught it.
