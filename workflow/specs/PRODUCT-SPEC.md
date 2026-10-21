# Product spec

Deskmate is a service desk web app: Requesters raise tickets, Support Officers resolve them, and each role has an AI feature. How it is built is in [`TECHNICAL-SPEC.md`](TECHNICAL-SPEC.md), and its threats and controls are in [`SECURITY-SPEC.md`](SECURITY-SPEC.md).

## Roles

- **Requester:** raises tickets, [asks for suggested articles while writing one](product/tickets.md#rq-5-suggest-articles-while-writing-a-ticket) and reads their workspace's [saved resolution replies](product/tickets.md#rq-1-submit-a-ticket).
- **Support Officer:** [reads their workspace's tickets](product/tickets.md#rq-2-read-workspace-tickets-as-a-support-officer), [resolves tickets with a reply](product/tickets.md#rq-3-resolve-a-ticket-with-a-reply) and [writes and edits knowledge-base articles](product/knowledge-base.md#kb-1-write-and-edit-knowledge-base-articles).

Every user has exactly one of these roles and belongs to exactly one **workspace**, a group of users who see only their own workspace's records.

## Areas

| Prefix | Area | File |
| --- | --- | --- |
| `PLT` | Platform: the home page, health check, error pages, startup checks, releases, shared AI admission foundation, [internal AI-call audit recording](product/platform.md#plt-6-record-internal-ai-call-audit-metadata), the [internal AI gateway](product/platform.md#plt-8-guard-user-ai-calls-in-the-internal-gateway) and the [product website](product/platform.md#plt-7-publish-the-product-website) | [`product/platform.md`](product/platform.md) |
| `ACC` | Accounts: demo workspace creation, sign-in, sign-out, role access and [Requester password resets](product/accounts.md#acc-4-reset-a-requesters-password), with rate limits on creation, sign-in and resets | [`product/accounts.md`](product/accounts.md) |
| `KB` | Knowledge base: Support Officers writing and editing articles in their workspace | [`product/knowledge-base.md`](product/knowledge-base.md) |
| `RQ` | Tickets: Requesters submitting tickets and asking for suggested articles while writing one, Support Officers reading and resolving them with a reply, and both roles reading saved resolutions in their workspace | [`product/tickets.md`](product/tickets.md) |

AI feature contracts live under [`ai/`](ai/): [find a fix](ai/find-a-fix.md), the [SoC LLM production probe](ai/llm-health.md), and the [internal gateway](ai/llm-gateway.md) that every user AI call goes through.

## Requirements

Each area's file holds its requirements in the form set in [`spec-writer.md`](../agents/spec-writer.md). A requirement's ID is its area's prefix and a number, such as `PLT-1`; each acceptance criterion adds a second number, such as `PLT-1.2`, and the tests that check a criterion are marked with its ID.
