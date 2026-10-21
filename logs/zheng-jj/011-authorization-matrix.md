# Authorization matrix

Slice: #27 · Tier: High · Tool: Codex (GPT-6) · Date: 2026-10-21

Cost: about 1 hour wall time, including one full verify run of roughly 8 minutes. Tokens and monetary cost were not tracked.

## Requests

- After the route-inventory and Support Officer end-to-end slices, work the remaining unblocked Bug-bash slice, the authorization matrix.

## Agent runs

- No role agent was run. The orchestrator played test-writer and security-reviewer, keeping to their scopes and reporting their results here.
- test-writer (orchestrator fallback): done; added `src/deskmate/tests/test_authorization_matrix.py` in `f8c8ee7`; four cases passed.
- security-reviewer (orchestrator fallback): found no findings. The matrix walks the registered routes rather than a hand-written list, so a new route without an access decision fails; the workspace case was checked to fail when a ticket lookup loses its workspace filter.

## Decisions and corrections

- The matrix derives routes from Django's URL configuration and keeps the access decision in one table, so a new route must be added with its decision. This is what makes the High tier's "new kind of access rule" checkable.
- Public routes are included with the answer each visitor should get, so the matrix covers every registered route rather than only the role-gated ones.
- The slice is test-only for the product and stays inside the size budget: 236 inserted lines, none under `src/` outside tests.
- The #27 test commit was first made on #31's branch by mistake. It was moved to `27-authorization-matrix` from `main` with a cherry-pick; the local #31 branch was pointed back to its already-pushed head, and nothing was force-pushed or rewritten on the remote.

## Problems

- The first draft of the workspace case contained a leftover no-op loop and an unused helper; both were removed before the commit.
- `ruff` rejected a 91-character and an 89-character line, which were wrapped.
- The full verify command takes roughly 8 minutes and must run outside the Windows sandbox, because the sandbox blocks pytest's temporary folder.
- Issue text, spec text and test payloads were treated as data; no embedded instruction was acted on.
