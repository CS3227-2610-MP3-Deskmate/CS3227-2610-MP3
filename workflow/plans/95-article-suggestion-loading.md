Goal: Implement [RQ-5.7](../specs/product/tickets.md#rq-5-suggest-articles-while-writing-a-ticket) within [PLT-4's inline-script exception](../specs/product/platform.md#plt-4-present-every-page-consistently) and the [Find a fix controls](../specs/SECURITY-SPEC.md#find-a-fix).

- [x] **implementer**: Update `src/deskmate/tickets/templates/tickets/form.html` (30–60 changed application lines), reusing `detail.html`'s inert pending template and fixed inline submit-handler convention.
  Use the submit event's submitter to apply only RQ-5.7's prescribed changes to an accepted `Suggest articles` submission, preserving native validation, the normal POST target and all existing content; keep all user and provider values outside the script.
  Make `src/deskmate/tests/test_find_a_fix.py` and `src/deskmate/tests/test_styling.py` pass, retaining the existing ticket, gateway, admission, audit and adversarial regressions through full CI verification.
  Add no dependency, service, credential, route, gateway change, extra request, retry, timeout or recovery subsystem.
- [x] **implementer**: Update `docs/UserGuide.md` after the application task (about 4–8 changed lines) with the built pending caption and paragraph, available `Submit ticket` action, retained content, response reset and scripting-unavailable behavior; use exact UI text and read the section back against the template.
  Add no prose tests; retain the application task's full CI checks.

Verification: use existing GitHub CI on draft PR #96 for `ruff check . && ruff format --check . && pytest` with PostgreSQL; start no local Docker and run no local database tests.
Application verification: [CI run 39702246138](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39702246138) at `2de022a2152dd8a2573c7788d2f93cdafb049c59` passed the full verification command on PostgreSQL.
User Guide verification: [CI run 39702809901](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39702809901) at `0ec2ccd90466861e19ac9bcacfddc4e9c5a6184c` passed the same automated checks.
Keep task boxes pending until successful CI verifies their implementation commits; the orchestrator may commit provisionally and finalize checkboxes in a later plan-only commit.
Browser execution checks remain unrun because the browser runtime is unavailable; disclose this in the PR for pending feedback, browser validation, ordinary ticket submission, retained results/errors/messages, scripting unavailable and response reset.
Budget: retain the confirmed 30–60 changed application lines, roughly 200–350 total changed lines across the slice and default 400-line application cap; stop and report any required scope expansion.
