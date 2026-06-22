# 💾 Cache controls (PhishIQPlus Splunk Add-on)

This add-on includes a **local in-process cache** to reduce repeat API calls for the same URL(s).

---

## Configuration knobs

| Setting | Meaning | Default |
|--------|---------|---------|
| `cache_enabled` | Enable/disable cache | true |
| `cache_ttl_seconds` | How long a cached result stays valid | 86400 (24h) |
| `cache_max_entries` | Maximum number of cached entries | 10000 |
| `cache_clear_on_start` | Clear cache at the start of each run (troubleshooting) | false |

---

## What is cached

- The add-on caches the **API response** per URL (keyed by a hash of the URL string).
- Cache is **local to the modular input process**. It is not shared across hosts.

---

## Edge cases (important for production)

### Stale results

- If a URL changes classification over time, a cached result can be stale until TTL expires.
- For operational troubleshooting, set `cache_clear_on_start=true` for a short period.

### Cache misses

- A miss means the URL was not in cache (or the entry expired). The add-on will call the API normally.

### Cache poisoning

- The cache stores results returned by the PhishIQ API.
- The cache does **not** execute content. However, to reduce risk:
  - Keep **SSL verify enabled** in production.
  - Do not disable TLS verification except during controlled tests.

### URL normalization

- Cache keys are based on the URL string as provided.
- If your environment produces equivalent URLs in different string forms (e.g. trailing slashes, uppercase, different URL encodings), you may see lower hit rates.
  - If needed, introduce a URL normalization policy (future enhancement) and document it so customers understand caching behaviour.

---

## Observability

Internal telemetry events (`event_type=run_summary`) include:

- `cache_hits`
- cache configuration (`ttl_seconds`, `max_entries`, `cleared_on_start`)
- cache runtime stats (`entries`, `max_entries`, `ttl_seconds`)

These power the **PhishIQ - Cache** dashboard.

