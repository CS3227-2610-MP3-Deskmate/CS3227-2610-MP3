# SoC LLM production probe

The contract for the operator-only call that proves the deployed app can reach SoC LLM. The observable behaviour is [PLT-3](../product/platform.md#plt-3-call-soc-llm-from-production); this file holds the request, output and failure contract.

## Request

- The app sends exactly one `POST` to `https://soclaas-api.comp.nus.edu.sg/v1/chat/completions` per probe request. It sends no other provider request and does not retry. A request whose path is `/health/llm`, without the trailing slash, never reaches the provider; it gets PLT-3.3's `404`.
- The body is exactly this JSON object, with no other fields:

  ```json
  {
    "model": "llama3.1:8b",
    "messages": [
      {"role": "system", "content": "You are a health check. Reply with exactly OK."},
      {"role": "user", "content": "Reply with OK."}
    ],
    "max_tokens": 8,
    "temperature": 0,
    "stream": false
  }
  ```

- The provider request carries exactly these headers: `Authorization: Bearer <SOC_LLM_API_KEY>`, `Content-Type: application/json` and `Accept: application/json`, plus only the transport's `Host`, `Content-Length`, `Connection` and `Accept-Encoding`. It carries no `User-Agent` and no other header. No header from the probe request is copied to the provider, and no cookie, user data, workspace, ticket, article or other application header is sent.
- The sent body parses as JSON to a value equal to the fixed object above: the same fields with the same strings, numbers and booleans, and the same `messages` order, with no other field. Whitespace between tokens and the order of an object's fields do not matter, and a test checks this equality on the bytes actually sent.
- The connection uses the system CA store with hostname verification, follows no redirect, uses no proxy and gives up after 10 seconds in total. It reads at most 65,536 bytes of the response body and treats a larger body as a failure.

## Operator token

`SOC_LLM_PROBE_TOKEN` is at least 32 printable ASCII characters (`U+0020`–`U+007E`), with no carriage return or line feed. The operator generates it with a cryptographically secure random source and rotates it on any suspected leak; it is never committed, logged or placed in a fixture. A request passes the gate only when it carries exactly one `Authorization` header whose value is exactly `Bearer <SOC_LLM_PROBE_TOKEN>`: one space, a case-sensitive `Bearer`, and the token byte for byte. The app compares the supplied token with `SOC_LLM_PROBE_TOKEN` using `hmac.compare_digest`, so the comparison does not reveal where the values differ. A missing, empty, invalid or duplicated header, or any other scheme or spacing, is refused with the generic `404` of PLT-3.3 before the key is read.

## Authorship and prompt injection

All prompt text is fixed in the app and written by the developers. The probe accepts no user input: query parameters, form fields, cookies, other headers and the request body cannot change the URL, model, messages, token, key or limits. There is therefore no untrusted text in the prompt to separate from instructions. Any future AI feature that adds user or workspace text needs its own contract with its own separation and validation rules.

## Output

The app accepts only a provider `200` whose body is UTF-8 JSON with this shape: an object with a `choices` list that is not empty, whose first item is an object with a `message` object whose `content` is a string that, after removing leading and trailing whitespace as Python's `str.strip()` does, is not empty. The content need not be exactly `OK`: any content that is non-empty after that strip passes. The app does not check the provider's `Content-Type` header: only the status and body shape matter. It does not read, display, store or log the content beyond that check. Any other status, invalid UTF-8 or JSON, a body over the limit, or a shape that does not match is a failure. The provider's response is untrusted data and is used only for this shape check: it never changes the app's behaviour, is never passed to a template, shell, database or log, and is never used as an instruction.

The client response body is only `{"status": "ok"}` with `200` on success or `{"status": "error"}` with `503` on failure. It never includes the provider's status, headers, body, error message or model text.

## Limits and failure

- One provider request per probe request; no retry, fallback, cache, queue or background work.
- A network or TLS failure, timeout, non-`200` status, oversized body, invalid UTF-8 or JSON, or invalid shape is a failure. It returns `503` and leaves every other route usable.
- A missing, empty or invalid `SOC_LLM_API_KEY` makes the probe return `503` without contacting the provider. A missing or invalid `SOC_LLM_PROBE_TOKEN` makes a `GET` return the generic `404` without contacting the provider.
- The app starts and serves every other route whether or not either variable is set.

## Privacy and logs

The API key appears only in the provider request's `Authorization` header. Neither the key nor the provider's response body, headers or error text appears in the client response, standard output, standard error or logs. The probe writes no database record.
