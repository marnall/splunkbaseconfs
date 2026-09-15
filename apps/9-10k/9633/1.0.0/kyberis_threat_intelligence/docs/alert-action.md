# Kyberis enrichment alert action

The **Kyberis enrichment** alert action enriches indicator values from an
alert's triggering results and indexes one JSON event per unique indicator
as sourcetype `kyberis:threat_activity`. It is available on every core
Splunk alert, and — via its Common Action Model metadata — as an adaptive
response action in Enterprise Security 7.x incident review.

It reuses the same enrichment core and KV Store cache as `| kyberis`:
alert-triggered enrichments and interactive searches warm each other's
cache.

## Parameters

Configured per alert (defaults from `default/alert_actions.conf`):

| Parameter | Default | Meaning |
| --- | --- | --- |
| Indicator fields | `src,dest,src_ip,dest_ip,domain,url,file_hash` | Comma-separated result fields to read indicator values from. Fields a result row does not have are skipped; multivalue fields are handled. |
| Credential profile | *(empty)* | Named credential profile; empty uses `default_profile` from `kyberis.conf`. |
| Destination index | `main` | Index the enrichment events are written to. Must already exist — the action fails (with a clear error) rather than auto-creating indexes. |
| Max indicators | `100` | Cap on unique indicators enriched per invocation — a cost guard for wide alerts. `0` removes the cap. When the cap trims the list, a warning is logged. |

The role that owns the alert needs `list_storage_passwords` and write access
to the destination index ([Permissions](permissions.md)).

## Indexed event shape

One event per unique indicator (a value seen in several fields/rows keeps
its first occurrence):

```json
{
  "indicator": "malicious-domain.example",
  "indicator_field": "domain",
  "orig_sid": "scheduler__admin__search__RMD5...at_1753692000_42",
  "orig_rid": 0,
  "search_name": "Suspicious outbound traffic",
  "kyberis_status": "ok",
  "kyberis_urgency": "today",
  "kyberis_score": 87,
  "kyberis_threat": "high",
  "...": "remaining kyberis_* fields",
  "threat_match_field": "domain",
  "threat_match_value": "malicious-domain.example",
  "threat_key": "kyberis",
  "threat_collection": "kyberis",
  "threat_collection_key": "<sha256 of the indicator>"
}
```

- `orig_sid` / `orig_rid` / `search_name` link the event back to the
  triggering search and result row — the linkage ES incident review
  correlates on.
- The full `kyberis_*` field set is the same as the
  [`| kyberis` output](kyberis-command.md#output-fields).
- The CIM `threat_*` fields appear only when the verdict meets
  `cim_min_threat`, exactly as at search time.
- Events have no embedded timestamp; the index time is the enrichment time
  (`DATETIME_CONFIG = CURRENT`).

**Every** verdict is indexed, benign ones included, so analysts see the
answer for each indicator. Data model membership is narrower on purpose: the
app's eventtype requires `threat_match_value=*`, so only events that
qualified as threat matches are tagged `threat` and enter the ES Threat
Intelligence data model. Benign verdicts stay searchable
(`sourcetype=kyberis:threat_activity`) but out of the data model.

## Failure policy

The action is designed to degrade rather than lose work:

- A **mid-run plan limit** (HTTP 402) is not a failure: already-enriched
  indicators are indexed with their verdicts, the remainder are indexed with
  `kyberis_status=plan_limit`, a warning is logged, and the action exits 0.
- A **transport failure** annotates affected indicators with
  `kyberis_status=transport_error` (indexed, retried by later runs since
  they are never cached) and logs a warning.
- Configuration, credential, or missing-index problems exit non-zero with an
  actionable message and index nothing.

Exit codes, for reference: `0` success (including partial plan-limit runs
and "no indicators found"); `2` bad invocation payload or splunkd connection
failure; `3` settings problem or missing destination index; `4` credentials
rejected or privacy guard tripped; `5` indexing failed mid-write.

Action output lands in `splunkd.log`, component `sendmodalert`
([Troubleshooting](troubleshooting.md#reading-alert-action-logs)).

## Adaptive response (ES 7)

In ES 7.x incident review, the action appears under adaptive response
actions (category *Information Gathering*). It runs ad hoc from a notable
event or as part of a correlation search's response actions. The mechanism
is the standard alert-action / Common Action Model one — forward-compatible
with ES 8, where it is currently untested (see the
[compatibility matrix](README.md#compatibility-matrix)).

## Testing an alert action configuration

Trigger it inline with `sendalert` on any search results:

```
index=_internal | head 5 | eval domain="malicious-domain.example"
| sendalert kyberis_enrichment param.index="main"
```

Note that dispatching a saved search over REST with `trigger_actions=1` has
been observed **not** to fire alert actions on Splunk 9.4; use `| sendalert`
or a genuinely scheduled/triggered alert to test.
