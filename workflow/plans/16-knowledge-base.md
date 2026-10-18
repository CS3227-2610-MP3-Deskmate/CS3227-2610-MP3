# Write and edit knowledge-base articles

Implement [KB-1](../specs/product/knowledge-base.md#kb-1-write-and-edit-knowledge-base-articles) using the existing account and request controls.

- [ ] implementer: Add `src/deskmate/knowledge/` with the article record, additive migration, validated form, workspace-scoped authoring views and templates; register it in `src/deskmate/settings.py` and `src/deskmate/urls.py`, and link it from `src/deskmate/accounts/templates/accounts/role_page.html`. Make `src/deskmate/tests/test_articles.py` pass, then run the verify command.
- [ ] implementer: Update `docs/UserGuide.md` for the built authoring flow and its exact messages; read the changed section back and run the verify command.
