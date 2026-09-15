# Credential setup

## Where credentials live

Kyberis API keys are stored in Splunk secure storage (`storage/passwords`,
realm `kyberis`), encrypted at rest by Splunk. Each key is saved under a
**named credential profile**; the profile name is the storage username. Keys
never appear in `.conf` files, dashboards, saved searches, search results, or
logs (log output is scrubbed of credential material as a hard guarantee).

Non-secret settings — API base URL, timeouts, cache TTL, the default profile
name, per-profile descriptions — live in `kyberis.conf`
(see `README/kyberis.conf.spec` in the app for every key).

## Setting up a profile

Setup is an **admin task**: saving a profile writes to `storage/passwords`
and `kyberis.conf`, which requires admin capabilities. Non-admin users who
open the setup page and hit Save will see raw REST permission errors rather
than a friendly gate.

1. Open the app in Splunk Web. Unconfigured installs redirect to the setup
   page automatically; it is also at **Apps → Kyberis Threat Intelligence →
   Set up**.
2. Enter a profile name (e.g. `default` or `soc_team`), the Kyberis API key,
   and an optional description. Profile names start with a letter or digit
   and may contain letters, digits, dot, underscore, and hyphen (max 64
   characters).
3. Check **use as default** to make this the profile searches use when none
   is named. The first profile saved is preselected as default.
4. Save, then verify:

```
| kyberischeck profile=<name>
```

Paste the API key exactly as issued by Kyberis (the `key_id:secret` form).
The app picks the right HTTP authentication scheme from the key's shape.

## Credential profiles

Profiles exist for usage attribution: teams (or individual heavy users) can
each get their own key, so Kyberis-side usage is attributable per profile.
All profiles talk to the same `base_url` and share the enrichment cache —
verdicts fetched under one profile are served from cache to the others by
design.

Which profile a given enrichment uses:

1. `profile=` on the `| kyberis` / `| kyberischeck` command, or the
   **Credential profile** parameter on the alert action, if set;
2. otherwise `default_profile` from `kyberis.conf`;
3. otherwise the profile literally named `default`.

## Rotating a key

Save the profile again with the new key — same profile name, new key value.
The stored key is overwritten in place; no search or alert configuration
changes.

## Removing a profile

Remove profiles from the table on the setup page. If the removed profile was
the default, the setup page reassigns `default_profile` to the first
remaining profile (alphabetically) and says so; if no profiles remain, the
default is cleared and searches will fail with an actionable error until a
profile is added.

If `kyberis.conf` is edited by hand instead, `default_profile` can be left
pointing at a profile with no stored key — searches then fail with the
missing-key error described in [Troubleshooting](troubleshooting.md).

## Verifying with `| kyberischeck`

`| kyberischeck [profile=<name>]` resolves a profile exactly the way
`| kyberis` would and reports one result row with the effective settings:
`profile`, `base_url`, `api_prefix`, `timeout_seconds`, `max_retries`,
`cache_ttl_seconds`, `cim_min_threat`, `log_level`, `api_key_present`, and
`client_ready`. The key itself is never emitted. On a configuration problem
it reports the same admin-actionable error message a search would show.

Note `| kyberischeck` validates configuration and credential resolution; it
does not call the Kyberis API. The first `| kyberis` search (or a bad-key
401 from it) is the end-to-end check.
