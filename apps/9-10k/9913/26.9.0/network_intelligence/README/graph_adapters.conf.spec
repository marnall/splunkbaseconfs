#   Version 1.0
#
############################################################################
# OVERVIEW
############################################################################
# graph_adapters.conf declares NI graph adapters: source-specific
# definitions of how one raw sourcetype produces one canonical NI graph
# target (a vertex or an edge).
#
# Each stanza describes, declaratively, the search a compiler would
# generate to materialize that target into the matching ni_* KV Store
# collection (ni_vertices plus ni_vertex_mappings for vertex:* targets,
# ni_edges for edge:* targets). Until a compiler exists, the hand-written
# equivalent search lives in savedsearches.conf and must stay in sync
# with the adapter stanza it implements.
#
# Full contract: docs/graph_topology/reference/graph-adapters-contract.md
# Worked examples: docs/graph_topology/reference/graph-adapters-examples.md
#
# One adapter stanza emits exactly one target output. A vertex:* stanza's
# ni_vertex_mappings rows are derived from that same stanza's identifier.*
# declarations (see IDENTIFIER, PARENT, AND SITE DECLARATIONS below), not
# from a separate mapping stanza. A source event that produces several
# distinct graph facts (for example: an interface vertex and a physical
# connected_to edge) uses several adapter stanzas that cover the same
# source event.
#
############################################################################
# STANZA
############################################################################

[<source_system>.<source_slug>.<adapter_name>]
* One stanza per adapter. The stanza name is a free-form, stable adapter
  id — it is not parsed into parts by NI, but the "<source_system>.
  <source_slug>.<adapter_name>" convention keeps related adapters for the
  same source and sourcetype grouped together, for example:
  [meraki.switchportsbyswitch.interface_vertex]
* adapter_id defaults to the stanza name and must be stable and unique.

############################################################################
# IDENTITY AND DESCRIPTION
############################################################################

source_system = <string>
* Required.
* Stable, lower-case source namespace, such as "meraki", "catalyst_center",
  or "thousandeyes".

source_sourcetype = <string>
* Optional.
* Source sourcetype, recorded for validation, documentation, and
  debugging. Does not affect base_search matching on its own.

title = <string>
* Optional.
* Human-readable title, echoed into the generated saved search name.

description = <string>
* Optional.
* Human-readable description of what the adapter materializes.

############################################################################
# SOURCE SEARCH
############################################################################

base_search = <SPL string>
* Required.
* Bounded raw-evidence search used by the generated materializer. Should
  include an index macro (or explicit index) and enough source
  constraints, such as sourcetype, to select the intended raw evidence.
* Must not contain write, destructive, alerting, or side-effecting
  commands such as collect, outputlookup, delete, sendemail, or map.

pre_transform_spl = <pipe-prefixed SPL fragment>
* Optional.
* Runs immediately after base_search and before expansion_step.<n>.
* Last-resort escape hatch for event-level normalization that cannot be
  expressed by any structured adapter declaration (for example, a
  "where" filter that drops events before expansion). Always prefer
  expansion_step.*, let.*, target fields, identifier declarations, and
  property declarations when they can express the operation. Must be
  pipe-prefixed and must not contain write, destructive, alerting, or
  side-effecting commands.
* Do NOT use this for field aliasing (renaming a raw field to a
  contract-facing name). Field aliasing belongs in an expansion step's
  "fields" map, or is unnecessary if the target/let/field expressions can
  reference the raw field name directly.
* Do NOT use this to reproduce supported expansion, field extraction, or
  target mapping behavior.

observed_time_expr = <SPL eval expression>
* Required.
* Expression assigned to observed_ts via eval (observed_ts=<observed_time_expr>),
  producing the source observation epoch seconds. Almost always just the
  field name "_time" (the event's indexed time), not a computed
  expression.

############################################################################
# ROW EXPANSION
############################################################################

expansion_step.<n> = <JSON object>
* Optional, one key per step, numbered from 1 and executed in numeric
  order. Omit all expansion_step.* keys when one source event already
  represents one target row.
* JSON shape:
    {"path": "<spath_path>", "output": "<field_name>",
     "input": "<field_name>", "fields": {"<src_field>": "<dst_field>", ...}}
* path (required): spath array path to expand, for example "ports{}".
* output (required): field name to hold the raw item JSON before field
  extraction.
* input (optional): extract "path" from this field instead of the event
  root. Used for nested/child arrays (parent -> child containment) or to
  chain a later step off an earlier step's "output".
* fields (optional): explicit per-field extraction with aliasing. If
  omitted, a broad "spath input=<output>" extraction is used, which is
  only safe when no event-level field names collide with item fields.
  Use fields whenever item field names collide with event-level fields,
  or when only a subset of item fields is needed. Splunk encodes JSON
  null as the literal string "null"; when fields is present, the compiler
  emits a matching nullif() eval for every destination field so downstream
  coalesce()/non-null checks are not fooled by that literal string. When
  fields is omitted (broad extraction), stanza authors must apply
  nullif() explicitly in any let.* or field.* expression that reads a
  field which may be JSON null.
* Two steps without "input" produce a Cartesian product of two
  independent sibling arrays — use only when that cross product is
  semantically correct.

############################################################################
# TARGET SELECTOR
############################################################################

target = <target_class>:<target_type>
* Required.
* Exactly one target class and one target type, separated by ":".
* vertex:<entity_type> — target_type is the graph vertex entity_type,
  such as device, interface, tunnel, synthetic_agent, or synthetic_test. Writes
  ni_vertices. nigraphmaterialize also derives and writes the vertex's
  own ni_vertex_mappings rows from its identifier.* declarations (see
  IDENTIFIER, PARENT, AND SITE DECLARATIONS below) — no separate
  mapping:<label> stanza is needed or supported.
* edge:<edge_type> — target_type is the graph edge_type. The current
  materialized graph supports connected_to and runs_test and writes ni_edges.
* One adapter stanza must emit only one target class and one target type.


############################################################################
# HELPER AND TARGET EXPRESSIONS
############################################################################

let.<name> = <SPL eval expression>
* Optional, any number of keys.
* Reusable helper eval expression, evaluated after expansion_step.* and
  before target expressions. Creates a helper field named <name>.
* Must not depend on another let.<name> helper. Repeat the source
  expression inline instead of chaining lets — this keeps helper
  evaluation order compiler-independent.

key.canonical = <SPL eval expression>
* NOT USED. canonical_key is derived entirely in Python, not declared per
  adapter: for target = vertex:*, VertexMaterializer.build_canonical_key
  (graph/materializer.py) computes it from entity_type plus the
  identifier.*/parent.* values nigraphmaterialize resolves at runtime;
  for target = edge:*, the transition materializer derives it as
  described under EDGE TARGET EXPRESSIONS below. No adapter stanza sets
  key.canonical.

field.<name> = <SPL eval expression>
* Optional, any number of keys. Valid for vertex:* and edge:* targets.
* Target field expression rendered into the graph KV row's matching
  column (for example field.display_name, field.status, or
  field.site_vertex_id).

identity.<name> = <SPL eval expression>
* Optional, any number of keys. Only valid for target = vertex:*.
* Contributes one key to the vertex's rendered identity JSON field.

property.<name> = <SPL eval expression>
* Optional, any number of keys. Valid for vertex:* and edge:* targets.
* Contributes one key to the vertex or edge's rendered properties JSON
  field.

############################################################################
# IDENTIFIER, PARENT, AND SITE DECLARATIONS (target = vertex:*)
############################################################################

identifier.<id_type> = <SPL eval expression>
identifier.<id_type>.id_namespace = <SPL eval expression>
* Optional, any number of keys. Only valid for target = vertex:*.
* Declares the vertex's own identity. nigraphmaterialize resolves and
  writes one ni_vertex_mappings row per non-null identifier.* entry —
  there is no separate mapping:<label> stanza; this replaces that
  pattern entirely.
* id_type is restricted to the controlled vocabulary documented in
  docs/graph_topology/reference/kvstore-graph-schema.md under
  "Identifier-kind (id_type) vocabulary" (for example mac_address,
  serial_number, internal_identifier, or ifindex).
* identifier.<id_type>.id_namespace is optional and only meaningful
  alongside a matching identifier.<id_type> expression. When omitted,
  nigraphmaterialize derives id_namespace itself (see
  docs/graph_topology/reference/graph-adapters-contract.md's Identifier
  Declarations section for the exact derivation per id_type).

parent.mac_address = <SPL eval expression>
parent.serial_number = <SPL eval expression>
parent.internal_identifier = <SPL eval expression>
* Optional. Only valid for target = vertex:* entity types that need a
  parent (currently interface).
* Declares the parent's identifying value. nigraphmaterialize tries
  parent.mac_address, then parent.serial_number, then
  parent.internal_identifier against ni_vertex_mappings, in that fixed
  order — the resolution order is not configurable per adapter. Full
  contract: docs/graph_topology/reference/graph-adapters-contract.md.

site.<id_type> = <SPL eval expression>
site.<id_type>.id_namespace = <SPL eval expression>
* Optional. Declares which identifier the adapter derives for resolving this vertex's
  site_vertex_id against ni_vertex_mappings (entity_type=site).
* The adapter's saved search must pass site_id, site_id_type, and
  site_id_namespace through to nigraphmaterialize. The command performs
  the exact namespaced lookup and assigns a unique result to site_vertex_id;
  missing or ambiguous matches leave that optional field unresolved. See
  docs/graph_topology/reference/graph-adapters-contract.md's Site Declaration
  section.


############################################################################
# EDGE TARGET EXPRESSIONS (target = edge:<edge_type>)
############################################################################

edge.directionality = "directed" | "bidirectional"
* Required for target = edge:*.
* Defines traversal semantics independently of the currently implemented
  edge vocabulary. An edge type must have one consistent directionality
  across all adapters. connected_to is bidirectional; runs_test is directed.

edge.src_id_namespace = <SPL field or eval expression>
edge.src_id_type = <SPL field or eval expression>
edge.src_id_value = <SPL field or eval expression>
edge.dst_id_namespace = <SPL field or eval expression>
edge.dst_id_type = <SPL field or eval expression>
edge.dst_id_value = <SPL field or eval expression>
* Required for target = edge:* except that either endpoint namespace may
  evaluate to blank when the source cannot determine it.
* Declares normalized source and destination endpoint identifier tuples.
  nigraphmaterialize resolves these tuples to existing vertices. A supplied
  namespace is authoritative; namespace-free resolution is used only when
  the namespace evaluates to blank.
* The selected edge-type policy constrains which vertex entity types may
  satisfy each endpoint. connected_to permits device and discovered_neighbor
  at either end; runs_test requires synthetic_agent then synthetic_test.

edge.src_interface_id_namespace = <SPL field or eval expression>
edge.src_interface_id_type = <SPL field or eval expression>
edge.src_interface_id_value = <SPL field or eval expression>
edge.dst_interface_id_namespace = <SPL field or eval expression>
edge.dst_interface_id_type = <SPL field or eval expression>
edge.dst_interface_id_value = <SPL field or eval expression>
* Optional interface qualifier tuples. Type and value must be supplied
  together. An explicit namespace is authoritative. When namespace is blank,
  nigraphmaterialize uses the corresponding resolved endpoint vertex's full
  canonical_key verbatim as the parent-scoped interface namespace.
* Interface qualifiers must resolve to interface vertices owned by their
  corresponding endpoint. Failure to resolve a qualifier does not suppress
  otherwise valid endpoint adjacency.
* nigraphmaterialize derives edge identity from resolved endpoint IDs. A
  complete interface pair participates in identity so parallel links remain
  distinct; a missing or one-sided pair falls back to endpoint-only identity.
  Bidirectional policies canonicalize endpoint order and move qualifiers with
  their endpoints. Source link IDs are evidence, not graph identity.


############################################################################
# EVIDENCE AND VALIDATION
############################################################################

evidence_ref_template = <JSON object as a string>
* Required.
* Describes raw source evidence provenance, not derived graph KV rows.
  Must include "index", "sourcetype", "source", "host", and a non-empty
  "keys" object. Template placeholders (for example "{serial}",
  "{canonical_key}") may reference any field available after expansion
  and expression evaluation. Rendered into the graph row's evidence_ref
  as JSON.

############################################################################
# LIFECYCLE
############################################################################

adapter_status = draft | validated | active | disabled | error | deprecated
* Optional.
* Defaults to "active" when omitted, but shipped conf should set it
  explicitly. Generated MVP materializers process only adapters with
  adapter_status = active and disabled = 0. Draft and error adapters must
  not ship in default conf.

disabled = <boolean>
* Optional.
* Standard Splunk conf toggle. Use 0 for active, 1 for disabled. Defaults
  to 0.
* An adapter is commonly disabled (with a comment above the stanza
  explaining why) when another already-active adapter writes the same
  canonical key and enabling both would cause the target ni_*_lookup to
  flap between writers on every schedule cycle.

version = <number>
* Optional.
* Adapter version. Should increment when the source key, expansion, or
  target semantics change, so downstream consumers can detect a
  materialization contract change.
