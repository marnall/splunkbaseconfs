# Network requirements

## Egress

The app makes outbound HTTPS requests from **search heads only** (indexers
and forwarders make no connections):

| Destination | Port | Purpose |
| --- | --- | --- |
| `api.kyberis.ai` (or your configured `base_url`) | 443 | Batched enrichment calls: `POST <base_url><api_prefix>/assessments/batch` |

Allow this destination in any egress firewall/proxy policy that applies to
your search heads. Requests are batched — up to 50 indicators per call —
never one call per event.

The app has no proxy configuration; requests go directly from the search
head to the API endpoint.

## Transport policy

- `base_url` **must be `https://`**. Requests carry the API key and
  indicator values, so plaintext `http://` is rejected with an error. The
  only exception is local development targets that never leave the machine:
  `localhost`, `*.localhost`, literal loopback IPs (`127.0.0.0/8`, `::1`),
  and `host.docker.internal`.
- TLS certificates are always verified using Python's default certificate
  handling. There is deliberately no option to disable verification. If your
  network intercepts TLS, the intercepting CA must be trusted by the
  certificate store Splunk's Python runtime uses.

## Timeouts and retries

Configured in `kyberis.conf` (see `README/kyberis.conf.spec`):

- `timeout_seconds` (default 20) — per-request timeout.
- `max_retries` (default 2) — retries for transient failures: connection
  errors and HTTP 429/5xx responses, with a short backoff.

When the API stays unreachable, affected events are annotated with
`kyberis_status=transport_error` and the search shows a warning; after two
consecutive failed batches the command stops calling the API for the rest of
the search rather than adding retry latency to every remaining batch. See
[Troubleshooting](troubleshooting.md).

## What data leaves Splunk

This is the transport-level summary; for the full statement — including
what Kyberis retains server-side and the controls you have — see
[Data handling and privacy](privacy.md).

Each enrichment request contains:

- the **indicator values** being enriched (the contents of the fields you
  point `| kyberis field=` or the alert action at) — nothing else from the
  events;
- a static **agent context**: an objective string (a fixed default, or the
  `objective=` override typed by the user), a fixed requested-outcome and
  workflow-stage string, the Splunk search id as `run_id`, and a batch
  counter as `step_id`;
- the `Authorization` header with the profile's API key.

The raw SPL of the running search is **never** sent. This is runtime-enforced,
not just policy: every outgoing payload is checked against the running
search's SPL text, and a request that would contain it is blocked before
sending (the search fails with an explicit privacy error asking you to
report the bug).

Data the app keeps locally: successful verdicts are cached in the customer's
own KV Store (`kyberis_ioc_cache`, indicator + verdict fields + fetch
timestamp, expiring after `cache_ttl_seconds`), and the alert action indexes
verdict events into a customer-chosen index. Neither leaves the Splunk
environment.
