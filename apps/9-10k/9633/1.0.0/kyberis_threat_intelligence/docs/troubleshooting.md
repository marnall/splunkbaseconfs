# Troubleshooting

## Configuration and credential errors

These fail the search (or alert action) with an actionable message rather
than annotating events.

**"No API key is stored for Kyberis credential profile …"**
Two distinct causes, called out in the message itself:

1. The profile genuinely has no stored key — add it on the setup page
   (**Apps → Kyberis Threat Intelligence → Set up**).
2. A key exists, but the role running the search lacks the
   `list_storage_passwords` capability — grant it
   ([Permissions](permissions.md)).

A third cause on hand-edited systems: `default_profile` in `kyberis.conf`
points at a profile that was deleted. The setup page reassigns the default
automatically when a profile is removed, but manual conf edits can still
leave it dangling — point `default_profile` at an existing profile.

**"base_url … uses http://, which would send the API key … unencrypted"**
`base_url` must be `https://` except for local development targets
([Network requirements](network.md#transport-policy)). Fix the URL in
`kyberis.conf`.

**"The Kyberis API rejected the configured credentials (HTTP 401/403)"**
The key stored for the profile is wrong, revoked, or truncated. Re-save the
profile with a valid key and re-run `| kyberischeck`.

## Per-event status fields

When the search succeeds but individual indicators carry a non-`ok`
`kyberis_status`, see the
[status reference](kyberis-command.md#kyberis_status-values). In short:

- `transport_error` — the API was unreachable; the search also shows a
  warning banner. Check egress/firewall/DNS from the search head, then
  re-run: these results are never cached, so the next search retries them.
- `plan_limit` — the Kyberis plan ran out mid-search; partial results are
  kept and the remainder retried next search.
- `error` — the API answered but could not assess that indicator;
  `kyberis_message` says why.

## Only the first field of `field=a,b` gets enriched

An unquoted comma ends an SPL option value, so `field=src_ip,dest_ip`
passes only `src_ip` to the command. Quote the list:
`field="src_ip,dest_ip"`.

## Cache issues

**Warm searches still call the API.** Check in order: `cache=false` on the
search? `cache_ttl_seconds = 0` (cache disabled)? Was the earlier result not
`ok` (only `ok` verdicts are cached)? Did `base_url` change (entries are
scoped to it)? Finally, check the per-search cache stats line in
`search.log` (`kyberis cache: N hit(s), …`).

**"KV Store … degraded" warnings / zero cache hits and writes.** The cache
fails soft, so searches keep working uncached. If the KV Store itself is
down (`Settings → KV Store status`, or
`| rest /services/kvstore/status`): note that splunkd does **not**
auto-restart a dead KV Store (mongod) process — a Splunk restart is
required to bring it back.

**Non-admin users never write the cache.** Expected: collection write access
is admin-only as a security property
([Permissions](permissions.md#the-cache-collection-acl--do-not-broaden-it)).
Their searches still read the cache and return full results.

## Search cancellation semantics

Finalizing or cancelling a `| kyberis` search does not abort instantly: the
chunk currently in flight (at most 50 indicators, one API call) drains
before the command exits. Fetched results are kept and cached; no further
calls are made.

## Logging

- **Search commands** log to the search's own `search.log`
  (Job Inspector → search.log). The app ships `default/logging.conf` so its
  operational lines are visible; format can be customized via
  `local/logging.conf`.
- **Verbosity** is controlled by `log_level` in `kyberis.conf`
  (DEBUG/INFO/WARNING/ERROR, default INFO) for both the commands and the
  alert action. `local/logging.conf` only affects search-command formatting
  and handlers — the alert action does not read it.
- Credential material (API keys, Authorization headers, session keys) is
  redacted from all log output at every level, including tracebacks.

### Reading alert action logs

Alert action output goes to `splunkd.log`, component `sendmodalert`:

```
index=_internal sourcetype=splunkd component=sendmodalert action="kyberis_enrichment"
```

`| sendalert kyberis_enrichment` invocations from the search bar log into
that search's `search.log` instead.

## Alert action does not fire

- Dispatching a saved search via REST with `trigger_actions=1` has been
  observed not to fire alert actions on Splunk 9.4. Test with
  `| sendalert kyberis_enrichment` or let the scheduler trigger the alert.
- Exit codes and failure policy:
  [Alert action reference](alert-action.md#failure-policy).

## Setup page shows raw REST errors on Save

The user is not an admin. Profile setup writes `storage/passwords` and
`kyberis.conf`, which needs admin capabilities — there is no friendlier
gate for non-admins ([Credential setup](credentials.md)).
