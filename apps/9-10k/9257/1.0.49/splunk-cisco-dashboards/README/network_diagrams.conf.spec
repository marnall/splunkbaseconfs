# network_diagrams.conf — schema for Network Diagram persistence
#
# One stanza per saved diagram. Stanza names are the human-friendly
# diagram names shown in the page header dropdown (e.g. "Splunk Cloud
# Deployment Architecture", "Customer DR Plan").
#
# This file replaces the deprecated `network_diagrams.csv` lookup
# (Build 108). Diagrams shipped in `default/` are inherited by every
# install; operator saves are written to `local/` so a factory-reset
# is a single `rm local/network_diagrams.conf`.
#
# Schema versions
#   v1 (Build 115.3) — only `updated_at`, `updated_by`, `payload_json`.
#                      All other metadata lived inside the JSON blob.
#   v2 (Build 115.5) — hybrid: metadata fields below are promoted to
#                      first-class conf keys so `btool` / `splunk show
#                      config` / SPL can answer questions about
#                      diagrams without parsing JSON. The body still
#                      lives in `payload_json`. Older v1 stanzas are
#                      tolerated on read; the next save promotes them.
#
# See also: app.conf [triggers] for hot-reload semantics.

[<diagram-name>]

## Schema metadata

schema_version = <integer>
* On-disk schema version for this stanza.
* 2 = "hybrid" (current). Metadata fields are first-class conf keys;
*     `payload_json` carries the canvas body.
* 1 = legacy (Build 115.3). Only `updated_at` / `updated_by` /
*     `payload_json` set; runtime derives metadata from the body.
*     The next save upgrades the stanza to schema 2.
* Defaults to 1 when absent (treated as legacy).

## String fields

title = <string>
* On-canvas diagram title shown at the top of the canvas. Distinct
*   from the stanza name, which is the picker key.
* Empty string is allowed (operator hasn't added an on-canvas title).
* No default.

description = <string>
* Free-form description rendered in the diagram-picker tooltip / list
*   view. Reserved for operator-supplied prose; OOB seeds ship with
*   an empty value.
* No default.

updated_at = <string>
* ISO-8601 UTC timestamp of the last save.
* Format: 2026-05-15T16:28:01Z (no fractional seconds).
* For OOB seed diagrams, the canonical seed timestamp.
* No default.

updated_by = <string>
* Splunk username of the operator who saved this diagram.
* `oob-seed` for diagrams shipped in `default/`.
* `unknown` if the persistence layer couldn't resolve $C.USERNAME.
* No default.

asset_bindings = <string>
* Comma-separated list of asset_inventory `device_name` values
*   referenced by bound shapes inside the diagram. Lets operators
*   grep "which diagrams reference host X?" without parsing the
*   JSON body.
* Empty string when no shapes are bound to real assets.
* No default.

payload_json = <string>
* JSON-encoded `SavedDiagramPayload` produced by the React canvas.
* Single-line; the React bundle is the only consumer — SPL never
*   parses it. The schema is documented in
*   `packages/splunk-cisco-dashboards/src/main/webapp/common/services/diagramPersistenceService.ts`.
* Hard cap: 256 KiB. The persistence layer rejects oversize payloads
*   with a friendly error before dispatching the REST write.
* No default.

## Integer fields (denormalised counts from payload_json)

node_count = <integer>
* Number of device-shape nodes in the diagram body. Denormalised on
*   save so SPL / btool can answer "how big is this diagram?" without
*   parsing the JSON payload.
* Recomputed from `payload_json` on every save; no manual edits.
* No default.

edge_count = <integer>
* Number of connector edges in the diagram body. Same rationale as
*   `node_count`.
* No default.

group_count = <integer>
* Number of region/group container shapes in the diagram body. Same
*   rationale as `node_count`.
* No default.
