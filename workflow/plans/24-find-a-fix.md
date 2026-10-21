# Find a fix

Goal: Implement [RQ-5](../specs/product/tickets.md#rq-5-suggest-articles-while-writing-a-ticket) under the [find-a-fix AI contract](../specs/ai/find-a-fix.md), reusing the [RQ-1.2](../specs/product/tickets.md#rq-1-submit-a-ticket) creation form and [RQ-1.4](../specs/product/tickets.md#rq-1-submit-a-ticket) validation.

- [x] **implementer**: Update `src/deskmate/tickets/views.py`, `src/deskmate/urls.py` and `src/deskmate/tickets/templates/tickets/form.html` (about 120–180 changed application lines; hard cap 400 outside tests and migrations) with the fixed `find_a_fix` instructions and schema, the POST-only Requester action at `/requester/tickets/new/suggest-articles/`, the two-button New ticket form and the results area.
  Reuse `_ticket_role` with `@require_POST` outside it, `TicketForm` and `redisplay()`; validate with the existing form before AI work and render that same form on rejection, with no identifier, no ticket write and no duplicated validation rules.
  After validation, make exactly one `deskmate.llm_gateway.call(...)` outside a transaction with `feature="find_a_fix"` and text = normalised title + two LFs + normalised description; casefold phrases and article titles/bodies locally, search only the current stored workspace, keep the earliest three by stored identity, and show RQ-5.3/RQ-5.4's exact messages (`No matching articles found.`, `Article suggestions are unavailable. Try again later.`, `AI limit reached. Try again later.`) with no provider detail and no stored draft, phrase, suggestion or result.
  Make `src/deskmate/tests/test_find_a_fix.py` and `src/deskmate/tests/test_routes.py` pass; retain the existing ticket, gateway, audit and limit tests; use the existing cache/framing middleware and add no dependency, setting, table, migration or credential.
- [x] **implementer**: Update `docs/UserGuide.md` (about 8–10 changed lines) with the built **Suggest articles** control, form and results placement, exact fixed messages, local workspace-only matching, best-effort guidance, temporary results and the SoC LLM draft exposure; read the section back and rerun the verification command.

Verification: `ruff check . && ruff format --check . && pytest`

Estimated total: about 128–190 changed lines (application plus User Guide).
