# Installation

## Requirements

- Splunk Enterprise 9.x (or Splunk Cloud Platform — see below). The app runs
  entirely on search heads; indexers need nothing installed.
- Outbound HTTPS from the search head to the Kyberis API
  (default `https://api.kyberis.ai`, port 443) — see
  [Network requirements](network.md).
- A Kyberis API key.
- An admin role for installation and credential setup.

## Install on a single instance

Via Splunk Web:

1. **Apps → Manage Apps → Install app from file**.
2. Upload `kyberis_threat_intelligence-<version>.tar.gz`.
3. Restart Splunk if prompted.

Or via the CLI:

```
$SPLUNK_HOME/bin/splunk install app kyberis_threat_intelligence-<version>.tar.gz
$SPLUNK_HOME/bin/splunk restart
```

After installation, opening the app redirects to its setup page until a
credential profile is saved — see [Credential setup](credentials.md). Verify
the configuration with:

```
| kyberischeck
```

## What the app installs

- Search commands `| kyberis` and `| kyberischeck` (search-bar help in
  `searchbnf.conf`).
- The **Kyberis enrichment** alert action (available on all alerts, and as an
  ES 7 adaptive response action).
- The `kyberis_ioc_cache` KV Store collection (enrichment cache, write access
  admin-only — see [Permissions](permissions.md)).
- The `kyberis:threat_activity` sourcetype plus an eventtype/tag pair that
  routes indexed enrichment events into the ES Threat Intelligence data
  model.
- A setup page for credential profiles. API keys are stored in Splunk secure
  storage, never in `.conf` files.

No scheduled searches, scripted inputs, or background jobs ship with the app.

## Search head clusters

Install through the deployer as usual for SHC (place the extracted app in
`$SPLUNK_HOME/etc/shcluster/apps/` on the deployer and push the bundle). The
app declares replication for its custom conf files (`kyberis.conf`,
`logging.conf`), and the KV Store cache lives in the cluster's KV Store.

SHC replication has not yet been exercised live for this app (see the
[compatibility matrix](README.md#compatibility-matrix)); treat cluster
deployments as early-adopter territory and verify credential resolution with
`| kyberischeck` on more than one member.

## Splunk Cloud

The app passes AppInspect cloud vetting and declares cloud support. Until it
is available on Splunkbase, it can be installed on Splunk Cloud as a private
app (self-service app install, or via a support ticket on stacks without
self-service). It has not yet been runtime-verified on Splunk Cloud.

## Upgrading

Install the new package over the existing app (same appid,
`kyberis_threat_intelligence`). Local configuration — credential profiles,
`local/kyberis.conf` overrides, and the KV Store cache — is preserved;
upgrades only replace the app's `default/` content and code.

## Uninstalling

Remove the app (Splunk Web, or delete
`$SPLUNK_HOME/etc/apps/kyberis_threat_intelligence` and restart). This also
removes the credential profiles stored under the app and the cached
enrichment results in the `kyberis_ioc_cache` collection. Events indexed by
the alert action remain in whatever index they were written to.
