# Submit a ticket

Implement [RQ-1](../specs/product/tickets.md#rq-1-submit-a-ticket) using the existing account controls and article patterns.

- [x] implementer: Add `src/deskmate/tickets/` with the ticket record, additive migration, validated form, workspace-scoped Requester views and templates; register it in `src/deskmate/settings.py` and `src/deskmate/urls.py`, and link it from `src/deskmate/accounts/templates/accounts/role_page.html`. Make `src/deskmate/tests/test_tickets.py` pass, then run the verify command.
- [x] implementer: Update `docs/UserGuide.md` for the ticket flow and its exact messages; read the changed section back and run the verify command.