# Resolve a ticket

Implement [RQ-3](../specs/product/tickets.md#rq-3-resolve-a-ticket-with-a-reply), preserving RQ-1 and RQ-2 and following the existing [model/routes](../specs/TECHNICAL-SPEC.md) and [controls](../specs/SECURITY-SPEC.md#tickets).

- [x] implementer: Own `src/deskmate/tickets/models.py`, `src/deskmate/tickets/forms.py`, `src/deskmate/tickets/views.py`, `src/deskmate/urls.py`, `src/deskmate/tickets/templates/tickets/detail.html`, and new `src/deskmate/tickets/migrations/0002_ticket_reply.py` and `src/deskmate/tickets/templates/tickets/resolve.html`; implement the specified schema, form, resolution operation and shared detail display.
  Reuse the ticket multiline normalization, validation and safe redisplay code, role and identifier helpers, navigation and template patterns; preserve existing behavior and error handling.
  Make `src/deskmate/tests/test_ticket_resolution.py` pass, including migration preservation, overlapping submissions and rejected writes; retain `src/deskmate/tests/test_support_tickets.py` and `src/deskmate/tests/test_tickets.py`.
  Run those three suites, then `ruff check . && ruff format --check . && pytest` in the [required environment](../../AGENTS.md#commands).
- [ ] implementer: Own `docs/UserGuide.md`; update its introduction and Tickets section after the app task for the built resolution flow and both roles' saved replies, using exact UI labels and validation text.
  Read the changed sections back, compare labels with the templates, and run `ruff check . && ruff format --check . && pytest` in the [required environment](../../AGENTS.md#commands), supplying final pre-review verification.
