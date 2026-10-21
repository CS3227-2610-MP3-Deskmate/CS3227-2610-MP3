# Key sentences

The AI contract for [RQ-4](../product/tickets.md#rq-4-highlight-a-tickets-key-sentences); its action and access order are in [Routes](../TECHNICAL-SPEC.md#routes), and its controls are in [Security](../SECURITY-SPEC.md#key-sentences).

## Inputs and authorship

After the route's current stored Support Officer/workspace authorization and ticket lookup succeed, the action makes exactly one [gateway call](llm-gateway.md) outside a database transaction:

| Input | Written by | Value |
| --- | --- | --- |
| `user` | The stored account loaded by authentication | The authenticated Support Officer |
| `feature` | Developers | Exactly `key_sentences` |
| `instructions` | Developers | The fixed text below, with no trailing line break |
| `schema` | Developers | The fixed bounded schema below |
| `text` | The ticket's Requester, or developers for a demo workspace's [sample tickets](../product/accounts.md#acc-2-create-a-demo-workspace) | The entire saved description, unchanged |

The title, resolution reply, articles, identities, workspace values and request fields are not AI input. The feature does not clean, truncate or split the description. The gateway's [input guard](llm-gateway.md#input-guard) applies unchanged, including its length check before removal: a description over 4,000 code points gets its existing `error` result without a provider request if admitted, and an admission refusal still takes precedence. Existing admission and audit behavior, provider transport, model and limits remain the gateway's responsibility.

## Fixed instructions and schema

The task instructions are exactly this single line:

```text
Extract up to three key sentences from the ticket description in untrusted_text. Copy each selected sentence exactly, without rewriting, trimming or adding characters. Each quotation must contain 1 to 1000 Unicode code points. Return exactly one JSON object with only the field "sentences", an array of the quoted strings. Return {"sentences": []} if no suitable sentence is available. Return no explanation or markup.
```

The schema uses the gateway's existing [schema forms](llm-gateway.md#output-schema):

```json
{
  "type": "object",
  "fields": {
    "sentences": {
      "type": "array",
      "items": {"type": "string", "max_length": 1000},
      "max_items": 3
    }
  }
}
```

## Output and source selection

The gateway checks the reply under its existing output contract. On `ok`, the feature accepts the selection only if every string is nonempty and occurs as an exact, case-sensitive substring of the original saved description, comparing code points without normalization, whitespace trimming or cleaning. An empty string or one unmatched quotation rejects the entire selection; no partial selection is displayed. The schema's maximum is inclusive; an empty array is valid. Whitespace is not trimmed from a quotation, and a nonempty whitespace-only quotation is subject to the same exact-match rule.

The source is the original description, not the gateway-cleaned text. If removal of invisible or control characters means a returned quotation no longer occurs there, the selection fails; there is no cleaned-to-original offset mapping or recovery. If the same exact quotation occurs elsewhere in the original, those exact occurrences remain eligible.

Duplicate quotations have no additional effect. Scan the original description from left to right: at each position with an eligible quotation, select the longest quotation beginning there, then continue at its end; otherwise continue at the next code point. Thus all occurrences not skipped by that deterministic overlap rule are selected, independently of array order. Highlight each selected occurrence in its original position, preserving every source character and line break; do not append a quotations list or display generated content. Empty selections and failures use [RQ-4.3 and RQ-4.4's fixed messages](../product/tickets.md#rq-4-highlight-a-tickets-key-sentences).

The model's extraction and judgment of importance are best effort. The feature adds no sentence tokenizer or semantic check: a source-matching fragment can pass even if it is not a whole sentence or is misleading in context.

## Failures and privacy

A gateway `error`, a gateway `refused` result and a source-validation failure have exactly [RQ-4.4's response behavior](../product/tickets.md#rq-4-highlight-a-tickets-key-sentences). No automatic retry, fallback request or additional admission/audit call follows. Source validation happens after the gateway has recorded its outcome: a source mismatch after `ok` leaves the gateway's `success` event unchanged, because that event describes its validation, not source matching or relevance.

The feature retains no description, quotations or result beyond the current response, and writes none of them or provider details to logs, standard output or standard error. It uses only the gateway's existing metadata records and credential handling. User-visible fragments come from escaped original source; provider output is never trusted as markup or instructions. SoC LLM receives the guarded description under the gateway's existing [privacy boundary](llm-gateway.md#privacy-and-logs).
