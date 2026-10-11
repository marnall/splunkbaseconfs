#   Version 1.0
#
############################################################################
# OVERVIEW
############################################################################
# data_sources.conf declares the enable/disable, index scope, and collection
# interval for each of NI's OOTB data sources.
#
# Writing this conf directly does not, on its own, recompute ni_indexes or
# the affected adapters/bindings/saved searches — that recomputation is
# transactional orchestration performed by the settings API and CLI
# (PUT /api/v1/settings/data_sources/<source_system>, ni_data_sources_cli.py).
# Hand-editing local/data_sources.conf and reloading leaves ni_indexes and
# the per-source searches stale until the next orchestrated change.
#
############################################################################
# STANZA
############################################################################

[<source_system>]
* One stanza per OOTB data source: meraki, catalyst_center, thousandeyes.
* Ships with all three sources present, disabled, and no indexes configured.

indexes = <comma-separated string>
* Required to enable this source.
* When enabling this source, every listed index must correspond to a real
  Splunk index; the settings API validates this server-side against the
  indexes REST endpoint using a system-level token, independent of the
  calling user's own visibility. This check does not run when disabling a
  source, so a source whose index was later deleted or renamed can still be
  disabled without first clearing its indexes.
* Enabled sources' indexes are combined (OR) into the ni_indexes macro
  (macros.conf). Disabling every source removes the ni_indexes override in
  local/macros.conf entirely, rather than leaving an empty or index=* value.

collection_interval_s = <integer>
* Optional. One of the fixed preset set: 60, 300, 900, 1800, 3600 (seconds).
* Blank/absent means this source inherits ni_settings.conf [collection]
  default_collection_interval_s.
* Governs this source's Path-2 graph-adapter and capability-binding saved
  searches. Does not affect the cross-source Path-1 data-model searches,
  which always follow the global default.

disabled = <boolean>
* Standard Splunk conf toggle. Use 0 to enable, 1 to disable. Defaults to 1.
* Enabling requires indexes to be non-empty.
* Toggling this source's adapters, bindings, and their saved searches, and
  recomputing ni_indexes and dependent rollup/Path-1 state, per the
  transaction described in the OVERVIEW.
