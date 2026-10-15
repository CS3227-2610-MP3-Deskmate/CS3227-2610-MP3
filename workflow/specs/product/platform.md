# Platform

What every feature relies on: the app runs, reports its health, fails without exposing its internals, and starts only when it is safely configured.

### PLT-1 Run a safe placeholder site
Why: Developers and hosts need a running app whose health they can check, and no visitor may see its internals.
- PLT-1.1 (happy) Given the app is running, whether or not the database answers, when anyone requests `GET /`, then the response is `200` with an HTML page whose title and only heading are `Deskmate` and whose only other text is `Deskmate is under construction.`
- PLT-1.2 (happy) Given the database answers, when anyone requests `GET /health/`, then the response is `200` with content type `application/json` and a body that is exactly the JSON object `{"status": "ok"}`.
- PLT-1.3 (failure) Given the app is running and the database refuses connections or rejects the app's credentials, when anyone requests `GET /health/`, then the response is `503` with content type `application/json` and a body that is exactly the JSON object `{"status": "error"}`.
- PLT-1.4 (failure) Given debug is off, when a request's path matches no [route](../TECHNICAL-SPEC.md#routes), even with a trailing slash added, such as `/admin` or `/%3Cscript%3Ealert(1)%3C/script%3E/`, then the response is `404`, and when a request causes an unexpected server error, then the response is `500` and the error and its traceback are written to standard error. Neither response shows internal details: a traceback, an exception message, a file path, a setting's name or value, or the list of routes.
- PLT-1.6 (ambiguous) Given `DJANGO_DEBUG` is unset or is anything other than exactly `true`, including `True`, `1`, `yes`, `true` with spaces around it and the empty string, when the app starts, then debug is off, so errors get the responses in PLT-1.4. Only `DJANGO_DEBUG=true` turns debug on.
- PLT-1.7 (failure) Given a variable that [Configuration](../TECHNICAL-SPEC.md#configuration) requires in the current debug mode is unset or has a value that table does not allow, when the web server or any management command starts, then it exits with a non-zero status without serving a request or running the command, and standard error contains `Deskmate cannot start: <NAME> is not set or is invalid.` for each such variable, but never any variable's value.

Out of scope: The Django admin site and any page other than `/` and `/health/`; custom error pages; styling; HTTPS settings and security headers; the image's production web server, publishing the image and deploying it.

Retired: PLT-1.5, PLT-1.8
