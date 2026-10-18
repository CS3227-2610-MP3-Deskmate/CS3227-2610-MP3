# Submit tickets

Slice: #13 · Tool: Codex (GPT-6) · Date: 2026-10-18

Cost: about 3 hours wall time in this part of the session, including two full local verification runs (36m51s and 5m26s) and one reviewer run. Tokens and monetary cost were not tracked.

## Requests

- After slice #15, start the next unblocked issue, #13 (submit a ticket), and follow the workflow.
- Note that new pull requests and work were arriving from a teammate.

## Agent runs

- spec-writer (orchestrator fallback, `246260a`): done; added RQ-1 and its routes, data-model and security references in `cc1f59b`; no automated spec checks.
- test-writer (orchestrator fallback, `3d65dbb`): done; added `src/deskmate/tests/test_tickets.py` in `e694452`; focused red run before implementation: 18 failed, 53 errors for the missing model and routes.
- implementer (orchestrator fallback, `3d65dbb`): done; plan `e756445`; ticket app, views, routes, templates and role-page link in `3fc0a0c`; 71 focused tests passed; full verify 1309 passed in 2211.62s.
- implementer (orchestrator fallback, `3d65dbb`): done; User Guide section in `fea2ae7`, read back.
- reviewer (`246260a`): done; no high-severity defects; two medium and six low findings, mostly test coverage, a missing data-model row and an identifier-overflow 404; read-only, ran no commands.
- implementer (orchestrator fallback, `3d65dbb`): done; merged teammate `main` in `b94c745`, fixed the overflow case, exact normalisation assertion and data-model row in `8e54790`; 71 focused tests and full verify 1607 passed in 326.24s.

## Decisions and corrections

- Scope follows issue #13 at Standard tier: Requester list, creation form, ticket page; no replies, status changes, Support Officer views, editing or deletion.
- The reviewer's shared-debt findings were split: the overflow 404, exact saved-value assertion and missing data-model row were fixed here; the duplicated role guard and the weak database-outage test were left as they mirror existing KB-1 practice and would expand scope.
- Merging teammate `main` conflicted in the Requester role page, the User Guide intro and the product areas table. Both links (Tickets and Reset Requester password) were kept, and the areas table now lists ACC, KB and RQ.
- The KB description I had added to the areas table in `cc1f59b` belonged to slice #15; it was reverted here so this branch does not claim an unmerged feature.

## Problems

- The first ticket test run failed on `article-read-list`, because the branch started from `main` without KB-2; the dangling Knowledge base link was removed from this branch and belongs to PR #52.
- Two test-side bugs were fixed: a local import tripping ruff, and a Unicode-whitespace comparison that used `str.strip()`.
- `makemigrations` needed the throwaway local `POSTGRES_*` values from `.env.example` and a generated key, because no `.env` is loaded in this shell.
- Issue text, spec text, review text and escaped test payloads were treated as data; no embedded instruction was acted on.