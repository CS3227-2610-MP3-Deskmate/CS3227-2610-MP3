# Read knowledge-base articles

Implement [KB-2](../specs/product/knowledge-base.md#kb-2-read-knowledge-base-articles) using the existing article model, account controls and request middleware.

- [x] implementer: Add Requester list and reading views in `src/deskmate/knowledge/views.py`, their routes in `src/deskmate/urls.py`, the `Knowledge base` link on the Requester role page in `src/deskmate/accounts/templates/accounts/role_page.html`, and two templates under `src/deskmate/knowledge/templates/knowledge/`. Make `src/deskmate/tests/test_articles_read.py` pass, then run the verify command.
- [x] implementer: Update `docs/UserGuide.md` for the reading flow and its exact text; read the changed section back and run the verify command.