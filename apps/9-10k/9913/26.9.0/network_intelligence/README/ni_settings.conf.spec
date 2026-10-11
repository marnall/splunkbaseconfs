[kvstore]
query_in_clause_chunk_size = <integer>
* Limits the number of parameters passed in a where clause. 
* Where conditions larger than this limit are automatically batched.

[topology]
default_hops = <integer>
* Default number of hops for GET /api/v1/graph/topology/l2.
* Must be positive and must not exceed max_hops.

max_hops = <integer>
* Maximum number of hops for GET /api/v1/graph/topology/l2.
* Must be positive.

[graph_configuration]
identifier_types = <string>
* A comma-separated list of identifier type descriptors.
* Identifier types should begin and end with a letter or number and may contain underscore characters.

[collection]
default_collection_interval_s = <integer>
* Global collection cadence for the cross-source Path-1 data-model searches, and
  the fallback for any data source in data_sources.conf that does not set its own
  collection_interval_s.
* Must be one of the fixed preset set: 60, 300, 900, 1800, 3600 (seconds). Any
  other value is rejected by the settings API and ignored (falls back to 300) by
  conf readers.
* Defaults to 300.

[alerts]
snapshot_ttl_seconds = <integer>
* Search job artifact TTL and the KV Store snapshot binding's expiry (seconds).

snapshot_create_wait_ms = <integer>
* Bounded poll ceiling (ms) after job creation before returning snapshot.state=running.

summary_create_wait_ms = <integer>
* Bounded poll ceiling (ms) for GET /api/v1/alerts/summary before the job is cancelled.

max_snapshot_rows = <integer>
* max_count passed to the search job; also the hard cap on total pageable rows.

default_limit = <integer>
* Default `limit` accepted on GET /api/v1/alerts.

max_limit = <integer>
* Maximum `limit` accepted on GET /api/v1/alerts.

search_max_time = <integer>
* max_time passed to the search job (seconds).
