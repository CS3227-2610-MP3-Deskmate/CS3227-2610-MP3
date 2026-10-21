# Build article suggestions while writing a ticket

Slice: #24 · Tier: High · Tool: Codex · Date: 2026-10-21

Cost: One session with eleven role runs (spec-writer twice, spec-critic, test-writer five times, implementer twice, reviewer twice, security-reviewer once). Wall time, tokens and monetary cost were not measured.

## Requests

- "if u can work on #24 now", after an earlier instruction to check for blocked issues and update every open pull request.
- Two corrections on #24's state: "issue 24 should also be blocked", then "no it should be unblocked".

## Agent runs

- **spec-writer** (`246260a`), `done`: `118b1e8` and `b9203ea` add and refine RQ-5 and the find-a-fix contract after the critic's findings. Scope and whitespace checks passed.
- **spec-critic** (`a58461d`), `done`: reviewed `9c6d68b..118b1e8`, reported ten findings (stale PLT-8 text, an undefined post-suggestion form, empty-phrase order, the three-article tie-break, generic-error bodies). None were for the human.
- **test-writer** (`3d65dbb`), five runs, `done`: `e6f0304` adds 24 RQ-5 cases (101 failing at that point, for the missing route and button, which CI confirmed). `128100a` adds the route to the authorization matrix. `9694ab9`, `054960a`, `21e3a69` and `415075d` fix test-side defects CI exposed (label keys instead of field names, a missing fixture parameter, colliding fixture text, a shared workspace). Each run's scope check passed; `test_find_a_fix.py` was never weakened.
- **implementer** (`3d65dbb`), two runs, `done`: `e75ddcd` writes the two-task plan; `05c375b` adds the route, view, matching helper and two-button form (95 application lines). Ruff and the compile check passed; pytest could not run locally.
- **implementer** (orchestrator fallback, `3d65dbb`), `done`: `942b57c` documents the feature in the User Guide and ticks the plan; `1070153` corrects the guide's absolute "nothing is saved" claim.
- **reviewer** (`8d74e8e`), two rounds, `done`: round one (`origin/main..942b57c`) found one Low (a valid draft let the role-order case pass) plus guide wording; round two (`942b57c..1070153`) found the new adversarial test's wrong expected values and conflated draft/reply assertion, both fixed in `9927362` and `23f7b58`, and a criterion marker and jargon wording, fixed in `1ccb89e`.
- **security-reviewer** (`8d74e8e`), `done`: no High; one Medium (loading the whole workspace's articles before admission) and one Low (missing feature-level attack cases, added in `957578a`). Read-only.

## Decisions and corrections

- The human's "work on #24 now" was taken as the checkpoint go-ahead, with option A from the earlier discussion: build the feature so the registered route exists and PLT-1.9 stays intact, instead of exempting a specified-but-unbuilt row.
- The provider never receives article text: the model returns up to three search phrases and matching against the workspace's saved titles and bodies happens locally. `find_a_fix` was already a reserved gateway identifier, so no gateway capability was added.
- CI, not a local run, verified the slice: there is no PostgreSQL, `.venv` or Docker on this machine. Every claim of passing below is a CI result.
- CI totals, in order: 101 failed / 2,296 passed (red for the missing feature), 65 / 2,332, 4 / 2,393, 1 / 2,396, 0 / 2,397 at `415075d`, then 5 failed at `1070153` from the new adversarial test's own assertions, and finally 2,402 passed at `1ccb89e`.
- Size: 95 application lines, far under the 400-line cap; 14 files and about 1,400 changed lines including tests, spec, plan, guide and log.

## Problems

- The first CI red run was useful: it confirmed the new tests failed on the missing button and 404, not on test errors.
- Four later red runs were test defects, not feature defects: `send()` posted `Title`/`Description` instead of `title`/`description`; two tests used the module-level `provider` without the fixture; fixture text repeated as both a title and a body; and `make_account` shares one workspace per test. The adversarial test then asserted the absence of text that RQ-5.6 requires to be redisplayed.
- One self-inflicted process error: I read a Product website success as the CI job and briefly reported a green build that was red. The CI job was then read directly.
- The repository head moved twice during the session (PR #81 merged; a teammate opened #86). #24's branch merges cleanly into current `main`.
- Untrusted content seen: issue text, agent handoffs and test attack payloads. They were treated as data.
