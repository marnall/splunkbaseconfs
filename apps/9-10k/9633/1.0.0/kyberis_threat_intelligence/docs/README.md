# Kyberis Threat Intelligence for Splunk — Documentation

Kyberis Threat Intelligence enriches indicators of compromise (IPs, domains,
URLs, hashes, emails) from Splunk search results and alerts with Kyberis
threat verdicts, scores, and context. It provides:

- the **`| kyberis`** streaming search command — batched enrichment of
  indicator fields, with CIM Threat Intelligence field mapping for
  Enterprise Security,
- the **Kyberis enrichment alert action** — a core Splunk alert action and
  ES 7 adaptive response action that enriches an alert's triggering results
  and indexes the verdicts,
- a **cross-search KV Store cache**, so repeated indicators cost zero API
  calls within a configurable TTL,
- the **`| kyberischeck`** diagnostic command and a setup page for managing
  named credential profiles in Splunk secure storage.

## Guides

| Document | Covers |
| --- | --- |
| [Installation](install.md) | Requirements, install/upgrade/uninstall, search head clusters, Splunk Cloud |
| [Credential setup](credentials.md) | The setup page, credential profiles, key rotation, `| kyberischeck` |
| [Permissions and roles](permissions.md) | Required capabilities, cache collection ACL, admin-only surfaces |
| [Network requirements](network.md) | Egress endpoints, TLS policy, timeouts/retries, what data is sent |
| [Data handling and privacy](privacy.md) | What leaves Splunk, what Kyberis retains, local persistence, controls |
| [`| kyberis` command reference](kyberis-command.md) | Syntax, options, output fields, caching, CIM mapping |
| [Alert action reference](alert-action.md) | Parameters, indexed event shape, adaptive response, failure policy |
| [Troubleshooting](troubleshooting.md) | Common errors, status fields, KV Store issues, logging |

## Compatibility matrix

| Component | Status |
| --- | --- |
| Splunk Enterprise 9.x (search heads) | Supported. Verified on Splunk Enterprise 9.4. |
| Splunk Cloud Platform | Expected to work: the app passes AppInspect cloud vetting and declares cloud support, but has not yet been run on a Splunk Cloud stack. |
| Search head clustering | Supported by packaging (custom conf replication is declared); replication has not yet been exercised on a live cluster. |
| Indexers / forwarders | Not used. The app is search-head only; commands run with `distributed=false` and the alert action runs on the search head. |
| Splunk Enterprise Security 7.x | Supported target for the adaptive response action and the Threat Intelligence data model mapping. The action uses the standard alert-action / Common Action Model mechanism; end-to-end verification on a live ES 7.x instance is still pending. |
| Splunk Enterprise Security 8.x | Untested. The alert-action mechanism is forward-compatible, but no ES 8 validation has been done. |
| CIM | Maps to the `Threat_Activity` dataset of the Threat Intelligence data model. Note this data model ships with Enterprise Security itself, not the CIM add-on — the mapping is inert without ES. |
| Python runtime | Runs on Python 3.9 (the Splunk 9.x runtime; verified 3.9.20) and declares Python 3.13 compatibility for future Splunk versions. |

The "verified" statements reflect the app's manual QA record; entries marked
pending or untested are honest gaps, not known incompatibilities.

## Support

Kyberis — <support@kyberis.ai>
