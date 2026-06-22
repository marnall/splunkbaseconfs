"""Batch-save threat intel records into Splunk ES KV Store collections.

Isolated from the rest of the pipeline so that the write path -- which
is the only component with a hard dependency on a live Splunk service --
can be tested, swapped, or mocked independently. The event-based
Cloud path (see ``whisper_threat_intel_input.format_intel_events``)
bypasses this module entirely; it exists for on-prem deployments that
populate ``whisper_ip_intel`` / ``whisper_domain_intel`` directly from
a modular input.
"""

from __future__ import annotations

import json
from typing import Any

from whisper_logging import get_logger

logger = get_logger("threat_intel_writer")

# KV Store batch size limit (Splunk ``batch_save`` maximum is 1000).
# Exceeding this silently truncates the batch on some Splunk versions,
# so we chunk here rather than relying on server-side enforcement.
BATCH_SAVE_SIZE = 1000


def populate_kvstore(
    collection: Any,
    records: list[dict[str, Any]],
) -> dict[str, int]:
    """Populate a KV Store collection with intel records using batch_save.

    Uses ``batch_save`` for efficient bulk upsert (up to 1000 records per
    batch) with ``_key``-based deduplication. Falls back to single-record
    inserts if a batch fails, to maximize the number of records saved.

    Args:
        collection: Splunk KV Store collection object (``service.kvstore[name]``
            or equivalent). Must expose ``data.batch_save(*records)`` and
            ``data.insert(json_str)``.
        records: List of intel records to insert.

    Returns:
        Dict with 'inserted' and 'errors' counts.
    """
    stats = {"inserted": 0, "errors": 0}
    if not records:
        return stats

    for batch_start in range(0, len(records), BATCH_SAVE_SIZE):
        batch = records[batch_start : batch_start + BATCH_SAVE_SIZE]
        try:
            collection.data.batch_save(*batch)
            stats["inserted"] += len(batch)
        except Exception:
            logger.warning(
                "action=batch_save status=error batch_start=%d batch_size=%d, falling back to single inserts",
                batch_start,
                len(batch),
            )
            # Fall back to single-record inserts for this batch so that a
            # single malformed record does not poison the entire batch.
            for record in batch:
                try:
                    collection.data.insert(json.dumps(record, default=str))
                    stats["inserted"] += 1
                except Exception:
                    logger.debug(
                        "Failed to insert intel record: %s",
                        record.get("_key", "unknown"),
                    )
                    stats["errors"] += 1

    return stats
