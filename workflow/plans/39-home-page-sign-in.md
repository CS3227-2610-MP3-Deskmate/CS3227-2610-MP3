Goal: Satisfy [PLT-1.1](../specs/product/platform.md#plt-1-run-a-safe-placeholder-site) by adding a `Sign in` link to `/sign-in/` on the home page without changing its other text.

- [ ] **implementer**: Add the link to `src/deskmate/templates/deskmate/home.html`. Makes `src/deskmate/tests/test_home.py` pass and changes no view, route or database access.
- [ ] **implementer**: Update the home-page sentence in `docs/UserGuide.md` to describe the link. No new tests; run the full verify command again.