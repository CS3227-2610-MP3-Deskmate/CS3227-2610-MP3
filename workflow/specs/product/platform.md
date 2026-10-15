# Platform

What every feature relies on: the app runs, reports its health, fails without exposing its internals, and starts only when it is safely configured.

### PLT-1 Run a safe placeholder site
Why: Developers and hosts need a running app whose health they can check, and no visitor may see its internals.
- PLT-1.1 (happy) Given the app is running, whether or not the database answers, when anyone requests `GET /`, then the response is `200` with an HTML page whose title and only heading are `Deskmate` and whose only other text is `Deskmate is under construction.`
- PLT-1.2 (happy) Given the database answers, when anyone requests `GET /health/`, then the response is `200` with content type `application/json` and a body that is exactly the JSON object `{"status": "ok"}`.
- PLT-1.3 (failure) Given the app is running and the database refuses connections, rejects the app's credentials, or accepts TCP connections but never replies, when anyone requests `GET /health/`, then within 5 seconds the response is `503` with content type `application/json` and a body that is exactly the JSON object `{"status": "error"}`.
- PLT-1.4 (failure) Given debug is off, when a request matches a row below, then the response has that row's status and an HTML page whose title and only heading are the row's title, and whose only other text is the row's text and a link `Go to the home page` to `/`, except that the `400` page has no links. No error page shows internal details (a traceback, an exception message, a file path, a setting's name or value, or the list of routes) or repeats the request's path, method or host.

  | Status | When | Title | Text |
  | --- | --- | --- | --- |
  | `400` | The app does not answer to the request's host (PLT-1.8) | `Bad request` | `Deskmate could not handle this request.` |
  | `404` | The path matches no [route](../TECHNICAL-SPEC.md#routes), even with a trailing slash added, such as `/admin` or `/%3Cscript%3Ealert(1)%3C/script%3E/` | `Page not found` | `There is no page at this address.` |
  | `405` | `/` or `/health/` is requested with a method other than `GET` or `HEAD`, such as `POST /` without a CSRF token or `OPTIONS /health/`; the response also has the header `Allow: GET, HEAD` | `Method not allowed` | `This address does not accept this kind of request.` |
  | `500` | The request causes an unexpected server error; the error and its traceback are written to standard error | `Something went wrong` | `Deskmate hit a problem. Please try again later.` |

  A `HEAD` request to `/` or `/health/` gets the status and headers that `GET` would, with no body, and a path that matches a route once a trailing slash is added, such as `/health`, gets a `301` redirect to that route.

- PLT-1.6 (ambiguous) Given `DJANGO_DEBUG` is unset or is anything other than exactly `true`, including `True`, `1`, `yes`, `true` with spaces around it and the empty string, when the app starts, then debug is off, so errors get the pages in PLT-1.4. Only `DJANGO_DEBUG=true` turns debug on.
- PLT-1.7 (failure) Given a variable that [Configuration](../TECHNICAL-SPEC.md#configuration) requires in the current debug mode is unset or has a value that table does not allow, when the web server or any management command starts, then it exits with a non-zero status without serving a request or running the command, and standard error contains `Deskmate cannot start: <NAME> is not set or is invalid.` for each such variable, but never any variable's value.
- PLT-1.8 (adversarial) Given debug is off and `DJANGO_ALLOWED_HOSTS` is `deskmate.example`, when a request's `Host` header names any other host, such as `attacker.example` or `deskmate.example.attacker.example`, then the response is the `400` page in PLT-1.4, even for a path such as `/health` that would otherwise redirect.

Out of scope: The Django admin site and any page other than `/` and `/health/`; styling; HTTPS settings and security headers; the image's production web server, publishing the image and deploying it.

Retired: PLT-1.5
