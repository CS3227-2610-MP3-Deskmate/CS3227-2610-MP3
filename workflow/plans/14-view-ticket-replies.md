# View ticket replies as a Requester

Implement the Requester-facing part of [RQ-1.3](../specs/product/tickets.md#rq-1-submit-a-ticket) and [RQ-3.7](../specs/product/tickets.md#rq-3-resolve-a-ticket-with-a-reply), preserving the existing ticket and resolution behaviour.

- [x] test-writer: Add focused Requester regression tests in `src/deskmate/tests/test_ticket_replies.py` for a saved reply shown under `Reply` with its line breaks, an empty reply with no heading or placeholder, no reply or resolution controls, no mutation when the page is refreshed, and another workspace's ticket returning the generic `404` without its text. Run the focused suite and the verify command.
