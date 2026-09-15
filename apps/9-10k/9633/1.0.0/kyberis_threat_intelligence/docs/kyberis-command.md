# `| kyberis` command reference

```
... | kyberis field=<fields> [profile=<name>] [objective=<text>] [cache=<bool>] [cim=<bool>]
```

Streaming command that reads indicator values (IPs, domains, URLs, hashes,
emails) from the named event field(s), deduplicates them, enriches them in
batched Kyberis API calls (up to 50 indicators per call, never one call per
event), and appends `kyberis_*` verdict fields to each event. Events whose
target fields are empty pass through untouched. Runs on the search head
only, so credentials and outbound traffic stay off the indexers.

Running it requires the `list_storage_passwords` capability
([Permissions](permissions.md)).

## Options

| Option | Required | Default | Meaning |
| --- | --- | --- | --- |
| `field` | yes | — | Comma-separated event field(s) holding indicator values. **Quote multi-field lists**: `field="src_ip,dest_ip"`. An unquoted comma ends the option value, so `field=src_ip,dest_ip` silently enriches only `src_ip`. Multivalue fields are supported. |
| `profile` | no | `default_profile` from `kyberis.conf` | Named credential profile ([Credential setup](credentials.md)). |
| `objective` | no | a static app-defined objective | Overrides the enrichment objective reported to the Kyberis API. 8–280 characters. Must never contain search text — see [Network requirements](network.md). |
| `cache` | no | `true` | `cache=false` bypasses the cross-search KV Store cache for this search (fresh verdicts, e.g. during an active investigation). |
| `cim` | no | `true` | `cim=false` suppresses the CIM `threat_*` fields for this search. |

Examples:

```
... | kyberis field=src_ip
... | kyberis field="src_ip,dest_ip" profile=soc_team
... | kyberis field=file_hash cache=false
... | kyberis field=src_ip | where isnotnull(threat_match_value)
```

## Output fields

Every processed indicator produces `kyberis_ioc` plus:

| Field | Values / meaning |
| --- | --- |
| `kyberis_status` | `ok`, `error`, `plan_limit`, or `transport_error` — see below |
| `kyberis_message` | Human-readable explanation when status is not `ok` |
| `kyberis_urgency` | Decision urgency: `today`, `this_week`, `monitor`, `ignore` |
| `kyberis_score` | Numeric ranking score |
| `kyberis_threat` | Environment threat level: `high`, `medium`, `low` |
| `kyberis_action_confidence` | `high`, `medium`, `low`, `insufficient` |
| `kyberis_confidence` | Overall verdict confidence |
| `kyberis_resolution` | Entity resolution status |
| `kyberis_entity` | Resolved canonical entity (actor, malware family, campaign) |
| `kyberis_entity_type` | `actor`, `campaign`, `cve`, `domain`, `email`, `hash`, `ip`, `malware`, `url` |
| `kyberis_actions` | Recommended actions (multivalue) |
| `kyberis_caveats` | Caveats on the verdict (multivalue) |
| `kyberis_degraded_reasons` | Present when the verdict was computed degraded |

Verdict fields are omitted when the API did not provide them. When one event
contains several distinct indicators (multiple fields, or multivalue
fields), `kyberis_ioc` and every result field become multivalue, aligned by
index.

### `kyberis_status` values

- **`ok`** — a verdict was returned; the fields above are populated.
- **`error`** — the API answered but could not assess this indicator;
  `kyberis_message` carries the reason. Not cached; retried next search.
- **`plan_limit`** — the Kyberis plan limit was hit mid-search (HTTP 402).
  Already-enriched events keep their results; remaining events get this
  status, and the search shows a warning. Not cached; retried next search.
- **`transport_error`** — the API was unreachable (connection failure or
  timeout after retries). The search shows a warning; after two consecutive
  failed batches no further API calls are made for the rest of the search.
  Not cached; retried next search.

A configuration or credential problem (missing key, invalid `base_url`,
rejected credentials) fails the search with an actionable error instead of
annotating events — see [Troubleshooting](troubleshooting.md).

## Caching

Successful (`kyberis_status=ok`) results are cached in the
`kyberis_ioc_cache` KV Store collection and shared across searches, users,
profiles, and the alert action. Within `cache_ttl_seconds` (`kyberis.conf`,
default 86400 = 24 h) a repeated indicator costs zero API calls.

- Verdicts can therefore be up to `cache_ttl_seconds` stale. Use
  `cache=false` when freshness matters more than quota, or lower the TTL.
- `cache_ttl_seconds = 0` disables the cache entirely.
- Expiry is lazy: expired entries are ignored on read and swept
  opportunistically during searches. No background jobs.
- Cache entries are scoped to the `base_url` they were fetched from;
  re-pointing environments refetches rather than serving foreign verdicts.
- The cache **fails soft** in every direction: a missing collection, no
  write access, or a down KV Store degrades to uncached enrichment with a
  search-log warning — never a failed search.

Per-search cache statistics (`kyberis cache: N hit(s), M miss(es), K
write(s)`) are logged to the search's `search.log`.

## CIM Threat Intelligence mapping

Qualifying verdicts additionally gain the field names of the
`Threat_Activity` dataset of the Threat Intelligence data model (which ships
with Enterprise Security, not the CIM add-on):

| CIM field | Value |
| --- | --- |
| `threat_match_field` | the event field the indicator came from |
| `threat_match_value` | the indicator value |
| `threat_key` | `kyberis` |
| `threat_collection` | `kyberis` (results come from the Kyberis API, not an ES intel KV collection, so no ES collection name like `ip_intel` is claimed) |
| `threat_collection_key` | `sha256(indicator)` — also the `_key` of the matching `kyberis_ioc_cache` document |
| `threat_group` | `kyberis_entity`, when resolved |
| `threat_category` | `kyberis_entity_type`, when resolved |

In ES semantics an event carrying `threat_*` fields **is a threat match**,
so benign verdicts must not produce them: mapping requires
`kyberis_status=ok` and `kyberis_threat` at or above `cim_min_threat`
(`kyberis.conf`, default `medium`; set `low` to map every successful
verdict). `cim=false` suppresses the mapping for one search. The `kyberis_*`
fields are always present regardless of gating.

Search-time fields cannot carry tags, so piped `| kyberis` output does not
itself populate the data model — only indexed events do. The
[alert action](alert-action.md) writes indexed events that qualify.

## Cancellation

The command enriches in bounded chunks. Finalizing or cancelling a search
lets the chunk in flight (at most 50 indicators) drain before the command
exits; results already fetched are kept (and cached), and no further API
calls are made.

## `| kyberischeck`

```
| kyberischeck [profile=<name>]
```

Generating command that resolves a credential profile into a ready API
client and reports the effective configuration in one result row, without
calling the Kyberis API and without ever emitting the key. See
[Credential setup](credentials.md#verifying-with--kyberischeck) for the
output fields.
