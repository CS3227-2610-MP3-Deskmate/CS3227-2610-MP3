Goal: Lead home-page visitors to the existing sign-in page under [PLT-1.1](../specs/product/platform.md#plt-1-run-a-safe-placeholder-site).

- [x] **implementer**: Update `src/deskmate/templates/deskmate/home.html` and `src/deskmate/release.py`.
  - Add the ordinary **Sign in** link using the existing `sign-in` named URL and template pattern; preserve the title, heading, construction sentence and database-independent home rendering.
  - Extend the existing `_HomePage` parser and home smoke check to validate the anchor's text and exact target alongside the existing page content; retain current request, failure and deadline behavior.
  - Make every test in `src/deskmate/tests/test_home.py` pass: link navigation, healthy database, unavailable database and unavailable database with a session cookie (PLT-1.1).
  - Make `test_release_valid_identity_mapping_and_public_pages_succeed` and `test_release_missing_or_wrong_sign_in_link_fails_without_retry` in `src/deskmate/tests/test_release.py` pass; retain the full release suite, including wrong-content checks.
  - Make `test_production_wsgi_loaded_by_path_without_src_import_path_serves_home` in `src/deskmate/tests/test_production_settings.py` pass (PLT-1.1, PLT-2.7).
  - Run the full [verify command](../../AGENTS.md#commands) in Git Bash with `.venv` active; stop and report any conflict or confirmed scope/budget expansion without changing tests.
- [x] **implementer**: Update only `docs/UserGuide.md` after the application task passes.
  - Describe the built home-page **Sign in** link and replace the instruction that the home page does not link to `/sign-in/`; use the exact UI words and read the changed sections back.
  - No new tests; retain the application task's passing test mappings and rerun the full verify command before ticking this task.
