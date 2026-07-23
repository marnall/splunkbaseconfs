REST Profiler for Splunk
========================

Author : majid ershadi
Website: https://mj.github.io
License: Apache License 2.0

REST Profiler lets you define reusable REST API request profiles and execute
them as Splunk alert actions, ad-hoc searches, or one-off tests.

A profile describes a complete HTTP request: URL, method, custom headers,
content type, body, request timeout, retry policy with exponential backoff,
optional proxy (HTTP/HTTPS/SOCKS5 with separate proxy authentication),
response validation (expected status codes and body content), rate limiting,
SSL verification, and endpoint authentication (none, HTTP Basic, token/bearer,
or mutual TLS via client certificate). All secrets - passwords, tokens,
certificates, key passphrases - are stored encrypted in Splunk secure storage
(passwords.conf) and are masked in previews and logs.

Highlights
----------
- Profiles: create, edit, clone, delete; per-row Preview (exact masked request)
  and live Test send.
- Alert action "REST Profiler: Send request": run a profile when an alert
  fires; optionally send the triggering result rows, one request per row, as a
  JSON / XML / form-urlencoded body, URL query parameters, or a custom
  $field$ template in the body and URL.
- Search command: | restprofilersend profile="<name>" mode=preview|send
- Monitoring dashboard, configurable log level, and a Search view.

Compatibility
-------------
Designed for Splunk Enterprise 10.x. Using earlier versions is not
recommended (Python runtime differences).

1.0.0
-----
- First stable release.
