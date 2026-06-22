[es_checkpoint_store]
field.stanza_name = <string> The modular input stanza name (primary key).
field.last_bookmark = <string> ISO 8601 timestamp of last successful data collection.
field.scroll_state = <string> JSON-encoded scroll context for crash recovery.
field.updated_at = <string> ISO 8601 timestamp of last update to this record.

[es_seen_ids_store]
field.stanza_name = <string> The modular input stanza name (primary key).
field.seen_ids = <string> JSON-encoded array of recently seen Elasticsearch document IDs for deduplication.
field.count = <number> Number of IDs currently stored in the seen_ids array.
field.updated_at = <string> ISO 8601 timestamp of last update to this record.
