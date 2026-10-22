Goal: Show [PLT-1.1](../specs/product/platform.md#plt-1-run-a-safe-placeholder-site)'s service-desk sentence on the home page and in the release smoke test, so v1.0 can be released to production.

- [ ] **implementer**: Update `src/deskmate/templates/deskmate/home.html` and the expected `other` text in `src/deskmate/release.py`'s `verify_release` together in one commit (about 2–6 changed application lines), so `main` never deploys a home page its own release check rejects.
  Replace only `Deskmate is under construction.` with `Deskmate is a service desk: Requesters raise tickets and Support Officers resolve them.`; keep the page's title, heading, `Sign in` link and markup otherwise unchanged.
  In `src/deskmate/views.py`, reword the module and `home` docstrings' "placeholder home page" to "home page", since they become wrong; change no other docstring or code.
  Make `src/deskmate/tests/test_home.py`, `test_production_settings.py` and `test_release.py` pass, retaining `test_styling.py` and the rest of the suite, then run the verify command.
  Add no route, setting, dependency, workflow change or new release check.
- [ ] **implementer**: Update `docs/UserGuide.md` after the application task (about 2–4 changed lines).
  Replace the quoted home-page sentence near the top with the built sentence, read back against `home.html`.
  Bring the opening summary up to date with what is built: Requesters can press **Suggest articles** while writing a ticket to see suggested knowledge-base articles ([RQ-5](../specs/product/tickets.md#rq-5-suggest-articles-while-writing-a-ticket)), and Support Officers see the **Possible manipulation** marker on tickets whose text may try to steer Deskmate's AI features ([RQ-6](../specs/product/tickets.md#rq-6-flag-tickets-with-possible-manipulation)); use the UI text and the wording of the guide's own **Tickets** section, and add nothing planned. Read the changed lines back for duplication with that section and rerun the verify command.

Not in this plan: the orchestrator separately updates the product website landing page `docs/index.md`, which is outside implementer scope, to mention the built AI features, without changing [PLT-7](../specs/product/platform.md#plt-7-publish-the-product-website)'s criteria.
Verification: run `source .venv/bin/activate && ruff check . && ruff format --check . && pytest` locally against the local PostgreSQL. On this Mac, 17 tests in `test_migration.py` fail on main as well, because macOS cannot bind the 127.0.0.1 alias 127.0.0.2; they are environment-only, must be reported as such and need GitHub CI on the pull request to confirm them. Any other failure blocks the task.
Budget: a few changed lines under `src/` outside tests, hard cap 400; stop and report any required scope expansion.
