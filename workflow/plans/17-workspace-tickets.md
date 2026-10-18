# Workspace tickets

Implement [RQ-2](../specs/product/tickets.md#rq-2-read-workspace-tickets-as-a-support-officer) by reusing the ticket read views, templates and existing account controls.

- [x] implementer: Update `src/deskmate/tickets/views.py` and `src/deskmate/urls.py` to reuse the list/detail views with fixed server-defined route roles, defaulting to Requester; keep GET checks before access, current stored-role access before ticket lookup, workspace-scoped reads and `_ticket_id` validation. Reuse existing session, CSRF, response-header and generic-error handling.
  Update `src/deskmate/tickets/templates/tickets/list.html`, `src/deskmate/tickets/templates/tickets/detail.html` and `src/deskmate/accounts/templates/accounts/role_page.html` with role-specific route context and Support Officer navigation; retain escaped text, line breaks and stored status, and show creation navigation only to Requesters. Preserve existing Requester behavior.
  Make `src/deskmate/tests/test_support_tickets.py` pass and retain `src/deskmate/tests/test_tickets.py`; run both suites, then the [verify command](../../AGENTS.md#commands).
- [ ] implementer: Update `docs/UserGuide.md` after the application task for the built Support Officer ticket navigation and read-only pages, using the exact UI labels. Read the changed section back and run the [verify command](../../AGENTS.md#commands).
