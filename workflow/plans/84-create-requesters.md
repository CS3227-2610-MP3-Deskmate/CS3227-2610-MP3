Implement [ACC-5.1–ACC-5.7 and ACC-1.2](../specs/product/accounts.md) within the confirmed two-requirement exception, preserving the workspace code.

Budget: estimated 250–345 changed source lines, with a hard maximum of 400 against `main`; reuse existing records, dependencies, settings, middleware and `Kind.CREATION`.

- [x] implementer: Own `src/deskmate/accounts/{membership,creations,views}.py`, `src/deskmate/accounts/templatetags/workspace_labels.py`, `src/deskmate/urls.py`, and `src/deskmate/accounts/templates/accounts/{create_requester,role_page}.html`.
  - Extract one canonical membership resolver shared by the workspace-label tag and creation; retain stored-workspace access snapshots and propagate database failures.
  - Serialize creation by locking the existing Workspace row inside the insertion transaction; recheck the Requester count and membership together, applying the fixed quota before canonical-membership rejection and generating nothing for either rejection.
  - Reuse `demo.random_password`, Django's salted hasher and the existing database-error sanitization pattern; insert only the next numbered account, never retry a collision, and commit before rendering the one-time credentials.
  - Register the GET/POST route, add the Support Officer link and exact form/success/error wording, and reuse the authorized layout plus global cache/framing middleware.
  - Apply existing method, session and stored-role checks before the shared creation limiter; commit admission before membership checks or hashing, with the specified route-specific refusal message and no new rate kind or capacity.
  - Make `test_requester_creations.py`, `test_requester_creation_failures.py`, `test_requester_creation_limits.py`, `test_workspace_labels.py`, `test_authorization_matrix.py` and `test_routes.py` pass while preserving the existing account, reset and limiter suites; never edit tests.
- [ ] implementer: Own `docs/UserGuide.md`; after the app is built, document its exact link, button, success and rejection wording, one-time password handling, fixed workspace quota including the initial accounts, preserved workspace line, repeat/lost-response behavior and shared creation allowance; link to the criteria for full rules.
  - Read the changed guide sections back against the built templates; retain task 1's CI regression checks, with no new tests for this prose change.

Verification: use the existing GitHub Actions CI on draft PR #87 for `ruff check . && ruff format --check . && pytest`; run no local tests. Static lint, format and implementer scope checks remain allowed.
