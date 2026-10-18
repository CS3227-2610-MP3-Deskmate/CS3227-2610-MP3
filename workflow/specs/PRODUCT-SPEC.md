# Product spec

Deskmate is a service desk web app: Requesters raise tickets, Support Officers resolve them, and each role has an AI feature. How it is built is in [`TECHNICAL-SPEC.md`](TECHNICAL-SPEC.md), and its threats and controls are in [`SECURITY-SPEC.md`](SECURITY-SPEC.md).

## Roles

- **Requester:** raises tickets.
- **Support Officer:** resolves tickets and [writes and edits knowledge-base articles](product/knowledge-base.md#kb-1-write-and-edit-knowledge-base-articles).

Every user has exactly one of these roles and belongs to exactly one **workspace**, a group of users who see only their own workspace's records.

## Areas

| Prefix | Area | File |
| --- | --- | --- |
| `PLT` | Platform: the home page, health check, error pages, startup checks and releases that every feature relies on | [`product/platform.md`](product/platform.md) |
| `ACC` | Accounts: creating demo workspaces and signing in, with rate limits on both, signing out, and which role may open which pages | [`product/accounts.md`](product/accounts.md) |
| `KB` | Knowledge base: Support Officers writing and editing articles in their workspace, and Requesters reading them | [`product/knowledge-base.md`](product/knowledge-base.md) |
| `RQ` | Tickets: Requesters submitting tickets in their workspace | [`product/tickets.md`](product/tickets.md) |

## Requirements

Each area's file holds its requirements in the form set in [`spec-writer.md`](../agents/spec-writer.md). A requirement's ID is its area's prefix and a number, such as `PLT-1`; each acceptance criterion adds a second number, such as `PLT-1.2`, and the tests that check a criterion are marked with its ID.
