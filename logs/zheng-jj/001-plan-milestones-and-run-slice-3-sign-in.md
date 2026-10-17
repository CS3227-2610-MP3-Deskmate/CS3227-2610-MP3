# Plan milestones and run slice 3 sign-in

Slice: #3 · Tool: Claude Code in VS Code (Claude Opus 5.5) · Date: 2026-10-16 to 2026-10-17

Cost: about 20 hours of wall time. The first milestone was created at 20:52 SGT on 16 Oct, and the log was written at 12:30 SGT on 17 Oct. That span includes an overnight gap and waits for the human. There were 15 role-agent runs and 2 resumes, using about 1.88M subagent tokens. The orchestrator's own tokens are not counted.

## Requests

- Asked which agents the project has. Claude listed the seven role agents in `workflow/agents/` and the built-in ones.
- Asked for GitHub milestones and high-level issues for the project, from the team's one-pager and the assignment brief. Claude was to note the open pull request and the 23 Oct 2pm SGT deadline, and leave exact implementation details to development.
- During that work, said the teammate had settled deployment and DevOps, and asked Claude to start on issues #3 and #4 once the planning was done.
- At the #3 checkpoint, replied "yea do it". Claude took this as accepting every recommendation it had listed and approving the local setup.
- After shell commands began failing, said "just work in a docker container then".

## Agent runs

- **Planning (orchestrator, no role agent):**
  - Created milestones Core workflows (17 Oct), AI features (18 Oct, feature freeze), Bug bash (20 Oct) and Release v1.0 (22 Oct, with the 23 Oct 2pm SGT cut-off in its description).
  - Created labels `requester`, `support-officer` and `team`, and added `team` to #2–#5.
  - Created issues #11–#37 from the Slice template, holding only titles, `Spec: new` and proposed tiers, with owners unassigned. During #3 it added #38 (rate limits) and #39 (home page link to sign-in).
  - GitHub first shifted the due dates a day earlier. Setting the time to 12:00 UTC fixed it.
- **spec-writer** (`a58461d`), 3 runs and 1 resume, all within scope:
  - ACC-1 with 8 criteria, a Data model section, the routes and the sign-in security controls: `eb2cfad`.
  - The spec-critic's findings: `504517c`.
  - The checkpoint changes, plus a `Gap:` line for `http://` origins: `5e1cd2d`.
- **spec-critic** (`a58461d`): 10 findings on `eb2cfad`, including the rule order, Origin checks behind HTTPS, database outages and username matching.
- **test-writer** (`3d65dbb`), 2 runs, both within scope:
  - Tests for ACC-1.1–1.8: `a402efe`. Before the build, 224 failed for want of a user model or routes, and 221 passed. The agent also checked them against a scratch reference implementation, which was never committed: 445 passed, and each of 30 injected defects was caught.
  - The review round's tests: `b8cbea1`. With these, 511 passed. A deliberately broken copy (`|safe`, or no sign-in time middleware) failed as it should.
- **implementer** (`3d65dbb`), 5 runs and 1 resume, all within scope:
  - Plan: `86e9793`. The resume applied Claude's two answers.
  - Task 1, the accounts app, sign-in, sign-out and role pages: `22afaed`. The size command gave 189 lines.
  - Task 2, the CSRF page and the framing and caching headers: `52cfbea`. 445 passed, at 223 lines.
  - Task 3, the User Guide: `d3aaefa`.
  - Review fixes: `b94d703`. 445 passed, at 343 of 400 lines.
- **reviewer** (`a58461d`), 2 rounds:
  - Round 1: three must-fix findings (the username field's mobile attributes, no test of markup in role-page usernames, and the browser-close wording) and eleven nice-to-have.
  - Round 2: nothing must-fix. Open: no test pins `required` and `maxlength` being off, the 405 lists are incomplete, and two `sessions.py` branches are untested.
- **security-reviewer** (`3d65dbb`), 2 rounds:
  - Round 1: nothing must-fix in code. Two Medium decisions (unthrottled sign-in using up the CPU quota, and the missing production schema), Lows 3–8, and missing attack tests.
  - Round 2: nothing must-fix. Three Lows remain: `sign_in_limit` relies on middleware order, the async and missing-time branches have no tests, and no test fails if the 600-character guard is removed.
- **Orchestrator commits:**
  - `5cf5a73`: the Developer Guide's `migrate` and local-account steps. Claude ran them in the container against the local database: sign-in redirected to `/requester/`, that page returned 200, and `/support/` returned 403.
  - `6b01780`: merged `main` (#8's automatic releases and the scope-confirmation rule). 511 passed after the merge.

## Decisions and corrections

- **Planning:**
  - Skipped the stretch AI features, because the one-pager's own gate (core passing by 15 Oct) had passed.
  - Left the overdue Skeleton milestone unchanged, since the teammate created it.
  - Flagged that Vercel builds from the repository, which is the one-pager's open question 2.
  - Owners stay unassigned until the team confirms who owns which role.
- **The #3 checkpoint ("yea do it"):**
  - All of Claude's proposals were accepted: paths and wording, the single error message, 302/403/405, ignoring `next`, the 8-hour session, Django's username defaults, the security headers, and a narrow database-down rule.
  - The CSRF check was widened to every method except GET, HEAD, OPTIONS and TRACE.
  - The `Origin: http://<host>` refusal was dropped, and recorded as a gap.
  - The slice stays at 8 criteria, the size cap.
- **Claude's answers to the implementer, not the human's:**
  - The sign-in fields have no `required` attribute, following ACC-1.3.
  - A site-wide `no_store` middleware was used, so that ACC-1.8 would not need narrowing. It also covers `/` and `/health/`.
- **Review fixes chosen by Claude:**
  - The `sign_in_limit` middleware, which enforces the 8-hour limit lazily, so that `/` and `/health/` work with the database down.
  - The 600-character guard before NFKC.
  - Trusted origins built only from plain host names.
  - The shared Forbidden page and CSRF view moved into the `deskmate` package.
- **Left for the human:**
  - Softening ACC-1.6's "the browser drops it when it closes".
  - A missing Origin, or an Origin with a port.
  - How `*` and leading-dot hosts become trusted origins.
  - C0 controls around usernames.
  - `__Host-` cookie names.
  - Whether to run a third review round.

## Problems

- **Python:**
  - Git Bash on this machine has no `python3`, so the pre-edit scope hook fails open. Claude ran `check_scope.py` by hand with `python` after every role agent.
  - Only Python 3.13 was installed, and there was no `.venv`. With the human's approval, Claude created one and installed the existing pins.
- **The shell:**
  - The first verify run on the host printed only Ruff's output, then exited with code 4. This was not diagnosed.
  - After that, every shell command failed with exit code 107, even `echo`. Claude tried once with the sandbox disabled. Auto mode denied that, and then plain commands too, until the human answered.
- **The dev container:**
  - Verify now runs in a `python:3.14.2-slim-trixie` container (pinned by digest) named `deskmate-dev`.
  - Sharing the database container's network made PostgreSQL trust local connections, which broke the PLT-1.3 bad-credentials test. A socat forward replaced it.
  - The Windows bind mount shows every file as executable, which trips Ruff's EXE002. So the `verify` helper copies the tree into `/work` with Git's file modes.
  - `check_scope.py` run inside the container flagged almost every file, so it is run on the host only.
- **Prototypes outside the repository:** test-writer and implementer built throwaway prototypes in the scratchpad and the container, none committed.
- **Production:** merging #3 deploys automatically. Production has no tables until #11, so sign-in will return 500 there until migrations run.
- **Untrusted content:** none. The only payloads seen were the escaped red-team data in the tests.
