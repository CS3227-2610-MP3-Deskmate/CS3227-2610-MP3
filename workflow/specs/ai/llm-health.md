# SoC LLM production probe

The contract for the operator-only call that proves the deployed app can reach SoC LLM. The observable behaviour is [PLT-3](../product/platform.md#plt-3-call-soc-llm-from-production); this file holds the request, output and failure contract.

## Request

- The app sends exactly one `POST` to `https://soclaas-api.comp.nus.edu.sg/v1/chat/completions` per probe request. It sends no other provider request and does not retry.
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

- The app sets `Authorization: Bearer <SOC_LLM_API_KEY>`, `Content-Type: application/json` and `Accept: application/json`. The HTTP transport may add its own standard headers. No cookie, user data, workspace, ticket, article or other application header is sent to the provider.
- The connection uses the system CA store with hostname verification, follows no redirect, uses no proxy and gives up after 10 seconds in total. It reads at most 65,536 bytes of the response body and treats a larger body as a failure.

## Authorship and prompt injection

All prompt text is fixed in the app and written by the developers. The probe accepts no user input: query parameters, form fields, cookies, other headers and the request body cannot change the URL, model, messages, token, key or limits. There is therefore no untrusted text in the prompt to separate from instructions. Any future AI feature that adds user or workspace text needs its own contract with its own separation and validation rules.

## Output

The app accepts only a `200` response whose body is UTF-8 JSON with this shape: an object with a `choices` list that is not empty, whose first item is an object with a `message` object whose `content` is a string containing at least one non-whitespace character. The app does not read, display, store or log that content. Any other status, invalid UTF-8 or JSON, a body over the limit, or a shape that does not match is a failure.

The client response is only `{"status": "ok"}` with `200` on success or `{"status": "error"}` with `503` on failure. It never includes the provider's status, headers, body, error message or model text.

## Limits and failure

- One provider request per probe request; no retry, fallback, cache, queue or background work.
- A network or TLS failure, timeout, non-`200` status, oversized body, invalid UTF-8 or JSON, or invalid shape is a failure. It returns `503` and leaves every other route usable.
- A missing, empty or invalid `SOC_LLM_API_KEY` makes the probe return `503` without contacting the provider. A missing or invalid `SOC_LLM_PROBE_TOKEN` makes the route return the generic `404` without contacting the provider.
- The app starts and serves every other route whether or not either variable is set.

## Privacy and logs

The API key appears only in the provider request's `Authorization` header. Neither the key nor the provider's response body, headers or error text appears in the client response, standard output, standard error or logs. The probe writes no database record.
