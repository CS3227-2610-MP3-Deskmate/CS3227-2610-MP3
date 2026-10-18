Goal: Satisfy [PLT-1.1](../specs/product/platform.md#plt-1-run-a-safe-placeholder-site) by adding a `Sign in` link to `/sign-in/` on the home page, and keep production release verification aligned with the same page contract.

- [x] **implementer**: Add the link to `src/deskmate/templates/deskmate/home.html`. Makes `src/deskmate/tests/test_home.py` pass and changes no view, route or database access.
- [x] **implementer**: Update the home-page sentence in `docs/UserGuide.md` to describe the link. No new tests; run the full verify command again.
- [x] **test-writer**: Cover the production verifier's home-page check: exactly one `Sign in` link to `/sign-in/`, with the unchanged title, heading and construction sentence. The positive success case fails before the verifier update; the negative cases guard against regressions.
- [x] **implementer**: Update `src/deskmate/release.py` to parse the home-page link and enforce PLT-1.1's exact text and target. Makes the new release tests pass without weakening identity, TLS, timeout or redirect checks.
