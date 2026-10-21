# Find a fix

The AI contract for [RQ-5](../product/tickets.md#rq-5-suggest-articles-while-writing-a-ticket); its route and access order are in [Routes](../TECHNICAL-SPEC.md#routes), and its controls are in [Security](../SECURITY-SPEC.md#find-a-fix).

## Inputs and authorship

After the New ticket form is submitted to the suggestion route and the current stored Requester/workspace authorization succeeds, the action validates both fields by RQ-1.4 and makes exactly one [gateway call](llm-gateway.md) outside a database transaction when they pass:

| Input | Written by | Value |
| --- | --- | --- |
| `user` | The stored account loaded by authentication | The authenticated Requester |
| `feature` | Developers | Exactly `find_a_fix` |
| `instructions` | Developers | The fixed text below, with no trailing line break |
| `schema` | Developers | The fixed bounded schema below |
| `text` | The Requester | RQ-1.4's normalised title, then two `LF` characters, then RQ-1.4's normalised description |

The value of `text` is exactly the title normalised for a would-be ticket, two line feeds, and the description normalised for a would-be ticket, as RQ-1.4 defines that normalisation. No submitted or stored article text, identity, workspace value, other form field, query parameter or header is AI input. The feature does not clean, truncate or split the text and sends no article content; only the Requester's own draft leaves the app.

The gateway's [input guard](llm-gateway.md#input-guard) applies unchanged, including its length check before character removal. A `text` of more than 4,000 Unicode code points gets its existing `error` result with no provider request after admission, and a `refused` admission takes precedence. The joined draft can exceed that cap even when each field passes RQ-1.4, because a title of up to 200 code points, two separators and a description of up to 10,000 code points can total up to 10,202; that is RQ-5.4's unavailable outcome, not a validation error. Existing admission and audit behavior, provider transport, model and limits remain the gateway's responsibility.

## Fixed instructions and schema

The task instructions are exactly this single line:

```text
Suggest up to three short search phrases that could find knowledge-base articles relevant to the support request described in untrusted_text. Base each phrase only on that request. Each phrase must be from 1 to 100 Unicode code points. Return exactly one JSON object with only the field "phrases", an array of the phrases. Return {"phrases": []} if no useful phrase is available. Return no explanation or markup.
```

The schema uses the gateway's existing [schema forms](llm-gateway.md#output-schema):

```json
{
  "type": "object",
  "fields": {
    "phrases": {
      "type": "array",
      "items": {"type": "string", "max_length": 100},
      "max_items": 3
    }
  }
}
```

## Output and source matching

The gateway checks the reply under its existing output contract. On `ok`, validation happens before any matching: if any string in `phrases` is empty, reject the entire selection and use RQ-5.4's unavailable response, with no partial selection displayed. The schema's maximums are inclusive; an empty array is valid and shows `No matching articles found.`.

Matching is local and deterministic. Each non-empty phrase is used exactly as returned, without trimming, cleaning or Unicode normalisation. Casefold each phrase and each article's saved title and saved body independently with Python's standard-library `str.casefold()`. A non-empty phrase whose folded result is empty never matches any article. An article matches when any folded phrase occurs as a substring of its folded saved title or its folded saved body; a match in either includes that article once. An article appears at most once regardless of duplicate phrases or repeated occurrences. The provider's reply is never used as a search query, a URL, a template or an instruction.

Consider only articles in the Requester's current stored workspace. Select the earliest three matching articles by stored identity ascending, where identity is the integer primary key, never by title, query order or phrase order, so which three appear is deterministic when more than three match. After RQ-5's `suggestion form`, show either an `<h2>` heading `Suggested articles` followed by a `<ul>` with exactly one `<li>` per shown article and nothing else and exactly one link per `<li>`, whose text is that article's escaped saved title and whose target is exactly `/requester/articles/<id>/` with that article's stored identity; or, when the phrase array is empty or no article matches, a single `<p>` reading `No matching articles found.`, with no heading and no links. The `200` form remains above this results area. Do not show an article body, a generated phrase or any other provider output.

The model's choice of search phrases and its judgment of relevance are best effort. The feature adds no ranking, relevance score, synonym expansion, stemming or fuzzy matching, so a matched article is only one whose escaped saved title or body contains the phrase under this rule; it is not verified as a solution.

## Failures and privacy

A gateway `error`, including when `SOC_LLM_API_KEY` is unset or empty, in which case no provider request is sent, or a rejected phrase list has exactly [RQ-5.4's unavailable response](../product/tickets.md#rq-5-suggest-articles-while-writing-a-ticket): the `suggestion form` followed by a single `<p>` reading `Article suggestions are unavailable. Try again later.`, with no `Suggested articles` heading, list, item or article link. A gateway `refused` result uses the same form and results placement with `AI limit reached. Try again later.` No automatic retry, fallback request or additional admission/audit call follows. The complete form, both buttons and its submitted values stay usable in every case. No provider detail, status, error message, phrase or user identity appears in the response.

Source matching happens after the gateway has recorded its outcome: a rejected phrase list after `ok` leaves the gateway's `success` event unchanged, because that event describes the gateway's own validation, not source matching or relevance. Every gateway result uses only the existing [privacy boundary](llm-gateway.md#privacy-and-logs) and credential handling.

The feature stores no draft, phrase, suggestion or result in a session, cookie, cache, database record or elsewhere, and writes none of them or any provider detail to logs, standard output or standard error. Only the gateway's existing admission and audit records change. User-visible article titles come from escaped stored text; provider output is never treated as HTML, Markdown or instructions. SoC LLM receives the guarded draft under the gateway's existing privacy boundary, and the feature sends it no article text.
