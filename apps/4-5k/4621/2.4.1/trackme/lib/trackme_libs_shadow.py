#!/usr/bin/env python
# coding=utf-8

"""
Shadow Copy Collections for Instant UI Entity Loading.

Implements a CQRS-like pattern where pre-computed, fully-enriched entity records
are stored in dedicated shadow KV collections. The UI reads from the shadow
(~7 seconds for 100k records via inputlookup) instead of re-running the full
decision maker enrichment (~102+ seconds).

Write-behind pattern:
  - Shadow is populated AFTER load_component_data completes enrichment
  - Single-entity updates happen after power endpoint writes
  - Shadow starts empty; first full load populates it

Shadow collections: kv_trackme_{component}_shadow_tenant_{tenant_id}
Fields: _key (entity key), record (JSON string of enriched entity), shadow_mtime (epoch)
"""

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import os
import sys
import time
import logging
import json

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))
from trackme_libs_logging import get_effective_logger

from trackme_libs_kvstore_batch import batch_update_worker
from trackme_libs import run_splunk_search


# Valid component names for shadow collections
_VALID_COMPONENTS = {"dsm", "dhm", "mhm", "flx", "fqm", "wlk"}


def _get_shadow_collection_name(component):
    """Return the KV collection name for a component's shadow."""
    if component not in _VALID_COMPONENTS:
        raise ValueError(f"Invalid component for shadow: {component}")
    return f"trackme_{component}_shadow"


def _get_shadow_collection(service, tenant_id, component):
    """
    Get the Splunk KV Store collection object for the shadow.
    Returns (collection, collection_name) tuple.
    """
    base_name = _get_shadow_collection_name(component)
    collection_name = f"kv_{base_name}_tenant_{tenant_id}"
    return service.kvstore[collection_name], collection_name


def _get_shadow_keys(shadow_collection):
    """
    Fetch all _key values from a shadow collection via SDK pagination.

    Uses fields="_key" to return minimal payloads (no record JSON blobs).
    Pure REST/SDK call — no search slot consumed.

    Returns:
        set of _key strings currently in the shadow collection.
    """
    keys = set()
    chunk_size = 5000
    skip = 0
    try:
        while True:
            rows = shadow_collection.data.query(
                fields="_key", limit=chunk_size, skip=skip
            )
            if not rows:
                break
            for row in rows:
                k = row.get("_key")
                if k:
                    keys.add(k)
            # Advance by the actual count returned; stop only on an empty page.
            # A byte-capped short page does not mean end-of-collection.
            skip += len(rows)
    except Exception:
        # Collection may not exist yet (first write) — return empty set
        pass
    return keys


def _purge_stale_shadow_keys(shadow_collection, stale_keys):
    """
    Delete stale keys from shadow collection using chunked $or queries.

    Args:
        shadow_collection: KV Store collection object
        stale_keys: set of _key values to remove

    Returns:
        Tuple of (purged_count, failed_count) for observability.
    """
    CHUNK_SIZE = 250
    stale_list = list(stale_keys)
    purged = 0
    failed = 0
    for i in range(0, len(stale_list), CHUNK_SIZE):
        chunk = stale_list[i : i + CHUNK_SIZE]
        try:
            shadow_collection.data.delete(
                json.dumps({"$or": [{"_key": k} for k in chunk]})
            )
            purged += len(chunk)
        except Exception as e:
            failed += len(chunk)
            get_effective_logger().warning(
                f'task="_purge_stale_shadow_keys", '
                f'chunk delete failed: {e}, chunk_size={len(chunk)}'
            )
    return purged, failed


def write_shadow_records(
    service,
    tenant_id,
    component,
    enriched_records,
    instance_id,
    max_workers=16,
    requester=None,
    shadow_enabled=None,
):
    """
    Write fully-enriched entity records to the shadow collection.

    Called after load_component_data completes enrichment for unfiltered
    batch requests above the shadow threshold.

    Args:
        service: Splunk service object
        tenant_id: Virtual tenant ID
        component: Component type (dsm, dhm, mhm, flx, fqm, wlk)
        enriched_records: List of enriched entity dicts from decision maker
        instance_id: Parent instance ID for logging
        max_workers: Max parallel threads for batch write
        requester: Optional identifier of the caller (e.g. health_tracker, hybrid_tracker_executor)
        shadow_enabled: Master switch from tenant config. When 0, all shadow writes are disabled.

    Non-fatal: all exceptions are caught and logged, never blocks caller.
    """
    # If shadow is explicitly disabled for this tenant, skip all writes
    if shadow_enabled is not None and int(shadow_enabled) == 0:
        get_effective_logger().debug(
            f'task="write_shadow_records", tenant_id="{tenant_id}", component="{component}", '
            f'shadow disabled (shadow_enabled=0), skipping'
        )
        return
    task_instance_id = str(time.time())
    requester_str = f', requester="{requester}"' if requester else ""

    try:
        shadow_collection, collection_name = _get_shadow_collection(
            service, tenant_id, component
        )

        # Build shadow records and upstream key set
        now = str(time.time())
        shadow_records = []
        upstream_keys = set()
        for record in enriched_records:
            key = record.get("_key")
            if not key:
                continue
            upstream_keys.add(key)
            shadow_records.append(
                {
                    "_key": key,
                    "record": json.dumps(record),
                    "shadow_mtime": now,
                }
            )

        # Diff-based reconciliation: instead of a full collection wipe (which
        # locks the collection and creates replication/compaction pressure),
        # fetch existing shadow keys via lightweight SDK calls and only purge
        # records that no longer exist upstream (deleted, blocklisted, etc.).
        shadow_keys = _get_shadow_keys(shadow_collection)
        stale_keys = shadow_keys - upstream_keys
        purged = 0
        purge_failed = 0

        if stale_keys:
            # If more than 50% of the shadow is stale, a single atomic wipe
            # is cheaper than many chunked $or deletes.

            if shadow_keys and len(stale_keys) > len(shadow_keys) * 0.5:
                purge_mode = "wipe"
                try:
                    shadow_collection.data.delete()
                    purged = len(stale_keys)
                except Exception as e:
                    purge_failed = len(stale_keys)
                    get_effective_logger().warning(
                        f'instance_id={instance_id}, task="write_shadow_records", '
                        f'task_instance_id={task_instance_id}, '
                        f'failed to wipe shadow collection: {e}, '
                        f'component="{component}", tenant_id="{tenant_id}"{requester_str}'
                    )
            else:
                purge_mode = "selective"
                purged, purge_failed = _purge_stale_shadow_keys(shadow_collection, stale_keys)

            log_level = logging.INFO
            purge_detail = f'count="{len(stale_keys)}", mode="{purge_mode}"'
            if purge_failed > 0:
                purge_detail += f', purged="{purged}", failed="{purge_failed}"'
                if purged == 0:
                    log_level = logging.WARNING

            logging.log(
                log_level,
                f'instance_id={instance_id}, task="write_shadow_records", '
                f'task_instance_id={task_instance_id}, '
                f'purged stale shadow records, {purge_detail}, '
                f'component="{component}", tenant_id="{tenant_id}"{requester_str}'
            )

        if not shadow_records:
            if shadow_keys and not upstream_keys:
                # All records removed upstream — shadow was purged above
                get_effective_logger().info(
                    f'instance_id={instance_id}, task="write_shadow_records", '
                    f'task_instance_id={task_instance_id}, '
                    f'shadow cleared, no records to write, component="{component}", '
                    f'tenant_id="{tenant_id}"{requester_str}'
                )
            return

        # Upsert current records via batch_update_worker (500-record chunks, multi-threaded)
        # batch_save is an upsert — handles both inserts and updates in one pass
        batch_update_worker(
            collection_name=collection_name,
            collection_object=shadow_collection,
            inputs_dict_or_list=shadow_records,
            parent_instance_id=instance_id,
            task_instance_id=task_instance_id,
            task_name="write_shadow_records",
            max_multi_thread_workers=max_workers,
        )

        get_effective_logger().info(
            f'instance_id={instance_id}, task="write_shadow_records", '
            f'task_instance_id={task_instance_id}, '
            f'shadow write completed, records="{len(shadow_records)}", '
            f'stale_purged="{purged}", '
            f'component="{component}", tenant_id="{tenant_id}"{requester_str}'
        )

    except Exception as e:
        get_effective_logger().error(
            f'instance_id={instance_id}, task="write_shadow_records", '
            f'task_instance_id={task_instance_id}, '
            f'shadow write failed: {e}, '
            f'component="{component}", tenant_id="{tenant_id}"{requester_str}'
        )


def read_shadow_records(service, transform_name, instance_id):
    """
    Read pre-computed enriched entity records from a shadow collection
    using | inputlookup via run_splunk_search (export + JSONResultsReader).

    Args:
        service: Splunk service object
        transform_name: The shadow transform/lookup name
            (e.g. "trackme_dhm_shadow_tenant_xxx")
        instance_id: Instance ID for logging

    Returns:
        List of enriched entity dicts, or empty list on failure.
    """
    try:
        import time as _time
        t0 = _time.time()

        # Use | inputlookup for bulk read — export bypasses the 50k maxresultrows limit
        search_query = f"| inputlookup {transform_name} | fields record"
        kwargs_search = {
            "earliest_time": "-1s",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
            "preview": False,
        }

        reader = run_splunk_search(
            service,
            search_query,
            kwargs_search,
            3,  # max_retries
            5,  # sleep_time
        )

        t1 = _time.time()

        # Parse the "record" JSON field from each shadow row
        records = []
        parse_errors = 0
        for item in reader:
            if isinstance(item, dict):
                try:
                    record_str = item.get("record", "{}")
                    records.append(json.loads(record_str))
                except (json.JSONDecodeError, TypeError):
                    parse_errors += 1

        t2 = _time.time()

        if parse_errors > 0:
            get_effective_logger().warning(
                f'instance_id={instance_id}, task="read_shadow_records", '
                f'parse errors={parse_errors}, transform="{transform_name}"'
            )

        get_effective_logger().info(
            f'instance_id={instance_id}, task="read_shadow_records", '
            f'shadow read completed, records="{len(records)}", '
            f'transform="{transform_name}", '
            f'inputlookup_time={round(t1 - t0, 3)}s, '
            f'parse_time={round(t2 - t1, 3)}s'
        )

        return records

    except Exception as e:
        get_effective_logger().error(
            f'instance_id={instance_id}, task="read_shadow_records", '
            f'shadow read failed: {e}, transform="{transform_name}"'
        )
        return []


def update_shadow_record(service, tenant_id, component, entity_key, enriched_record, shadow_enabled=None):
    """
    Upsert a single entity's shadow record.

    Called after power endpoints modify an entity (priority change, tag update, etc.)
    to keep the shadow in sync without waiting for the next full refresh.

    Args:
        service: Splunk service object
        tenant_id: Virtual tenant ID
        component: Component type (dsm, dhm, mhm, flx, fqm, wlk)
        entity_key: The entity's _key
        enriched_record: The enriched entity dict
        shadow_enabled: Master switch from tenant config. When 0, all shadow writes are disabled.

    Non-fatal: all exceptions are caught and logged.
    """
    if shadow_enabled is not None and int(shadow_enabled) == 0:
        return
    try:
        shadow_collection, collection_name = _get_shadow_collection(
            service, tenant_id, component
        )

        shadow_record = {
            "_key": entity_key,
            "record": json.dumps(enriched_record),
            "shadow_mtime": str(time.time()),
        }

        # batch_save with a single record acts as upsert
        shadow_collection.data.batch_save(shadow_record)

        get_effective_logger().debug(
            f'task="update_shadow_record", '
            f'entity="{entity_key}", component="{component}", '
            f'tenant_id="{tenant_id}"'
        )

    except Exception:
        # Non-fatal: shadow may not exist for small tenants below threshold
        pass


def delete_shadow_records(service, tenant_id, component, entity_keys, shadow_enabled=None):
    """
    Remove shadow records for deleted entities.

    Called after bulk or single entity deletion to keep the shadow in sync.
    Uses chunked $or queries for efficient batch deletion.

    Args:
        service: Splunk service object
        tenant_id: Virtual tenant ID
        component: Component type (dsm, dhm, mhm, flx, fqm, wlk)
        entity_keys: List of entity _key values to remove from the shadow
        shadow_enabled: Master switch from tenant config. When 0, all shadow writes are disabled.

    Non-fatal: all exceptions are caught and logged, never blocks caller.
    """
    if not entity_keys:
        return
    if shadow_enabled is not None and int(shadow_enabled) == 0:
        return

    CHUNK_SIZE = 250

    try:
        shadow_collection, collection_name = _get_shadow_collection(
            service, tenant_id, component
        )

        for i in range(0, len(entity_keys), CHUNK_SIZE):
            chunk = entity_keys[i : i + CHUNK_SIZE]
            try:
                shadow_collection.data.delete(
                    json.dumps({"$or": [{"_key": k} for k in chunk]})
                )
            except Exception:
                # Individual chunk failure — may not have shadow records
                pass

        get_effective_logger().debug(
            f'task="delete_shadow_records", '
            f'count="{len(entity_keys)}", component="{component}", '
            f'tenant_id="{tenant_id}"'
        )

    except Exception:
        # Non-fatal: shadow may not exist for small tenants below threshold
        pass


def patch_shadow_records(service, tenant_id, component, updated_records, update_fields, shadow_enabled=None):
    """
    Selectively patch shadow records after power endpoint writes (bulk edit, priority change, etc.).

    Instead of rewriting the entire shadow collection (100k records), this reads only the
    affected shadow entries, merges the changed fields into the stored enriched JSON,
    and writes them back. This preserves all decision maker enrichment (object_state,
    scores, status_message, etc.) while reflecting the user's changes immediately.

    Args:
        service: Splunk service object (system-level auth)
        tenant_id: Virtual tenant ID
        component: Component type (dsm, dhm, mhm, flx, fqm, wlk)
        updated_records: List of updated KV records from generic_batch_update
            (used to extract _key and any fields not in update_fields like mtime)
        update_fields: Dict of {field: value} that were changed (e.g., {"priority": "critical"})

    Non-fatal: all exceptions are caught and logged, never blocks caller.
    """
    if not updated_records or not update_fields:
        return
    if shadow_enabled is not None and int(shadow_enabled) == 0:
        return

    try:
        shadow_collection, collection_name = _get_shadow_collection(
            service, tenant_id, component
        )

        now = str(time.time())
        patched_count = 0
        skipped_count = 0
        shadow_batch = []

        for record in updated_records:
            entity_key = record.get("_key")
            if not entity_key:
                continue

            try:
                # Read the existing shadow record for this entity
                existing_shadow = shadow_collection.data.query_by_id(entity_key)

                if not existing_shadow:
                    skipped_count += 1
                    continue

                # Parse the enriched record JSON stored in shadow
                enriched_record = json.loads(
                    existing_shadow.get("record", "{}")
                )

                # Merge updated fields into the enriched record
                enriched_record.update(update_fields)

                # Also sync mtime from the updated KV record
                if "mtime" in record:
                    enriched_record["mtime"] = record["mtime"]

                shadow_batch.append(
                    {
                        "_key": entity_key,
                        "record": json.dumps(enriched_record),
                        "shadow_mtime": now,
                    }
                )

            except Exception:
                # Record not found in shadow or parse error — skip
                skipped_count += 1
                continue

        # Batch write all patched shadow records
        if shadow_batch:
            # Write in chunks of 500 (KV store batch_save limit)
            for i in range(0, len(shadow_batch), 500):
                chunk = shadow_batch[i : i + 500]
                shadow_collection.data.batch_save(*chunk)

            patched_count = len(shadow_batch)

        get_effective_logger().info(
            f'task="patch_shadow_records", '
            f'patched="{patched_count}", skipped="{skipped_count}", '
            f'fields="{list(update_fields.keys())}", '
            f'component="{component}", tenant_id="{tenant_id}"'
        )

    except Exception as e:
        # Non-fatal: shadow may not exist for small tenants below threshold
        get_effective_logger().debug(
            f'task="patch_shadow_records" skipped or failed: {e}, '
            f'component="{component}", tenant_id="{tenant_id}"'
        )


def patch_shadow_records_full(service, tenant_id, component, updated_records, shadow_enabled=None):
    """
    Selectively patch shadow records using full updated KV records.

    Used by post_bulk_edit where each record may have different fields changed.
    Reads existing shadow entries, merges ALL fields from the updated KV record
    into the stored enriched JSON, and writes back.

    This preserves decision maker enrichment fields (object_state, scores, etc.)
    that are NOT present in the KV record, while updating all fields that ARE.

    Args:
        service: Splunk service object (system-level auth)
        tenant_id: Virtual tenant ID
        component: Component type (dsm, dhm, mhm, flx, fqm, wlk)
        updated_records: List of full KV records after bulk edit

    Non-fatal: all exceptions are caught and logged, never blocks caller.
    """
    if not updated_records:
        return
    if shadow_enabled is not None and int(shadow_enabled) == 0:
        return

    try:
        shadow_collection, collection_name = _get_shadow_collection(
            service, tenant_id, component
        )

        now = str(time.time())
        patched_count = 0
        skipped_count = 0
        shadow_batch = []

        for record in updated_records:
            entity_key = record.get("_key")
            if not entity_key:
                continue

            try:
                # Read the existing shadow record for this entity
                existing_shadow = shadow_collection.data.query_by_id(entity_key)

                if not existing_shadow:
                    skipped_count += 1
                    continue

                # Parse the enriched record JSON stored in shadow
                enriched_record = json.loads(
                    existing_shadow.get("record", "{}")
                )

                # Merge all fields from the updated KV record into enriched
                # This preserves enrichment-only fields (object_state, scores, etc.)
                # while updating all KV-level fields (priority, tags, lags, etc.)
                enriched_record.update(record)

                shadow_batch.append(
                    {
                        "_key": entity_key,
                        "record": json.dumps(enriched_record),
                        "shadow_mtime": now,
                    }
                )

            except Exception:
                # Record not found in shadow or parse error — skip
                skipped_count += 1
                continue

        # Batch write all patched shadow records
        if shadow_batch:
            for i in range(0, len(shadow_batch), 500):
                chunk = shadow_batch[i : i + 500]
                shadow_collection.data.batch_save(*chunk)

            patched_count = len(shadow_batch)

        get_effective_logger().info(
            f'task="patch_shadow_records_full", '
            f'patched="{patched_count}", skipped="{skipped_count}", '
            f'component="{component}", tenant_id="{tenant_id}"'
        )

    except Exception as e:
        # Non-fatal: shadow may not exist for small tenants below threshold
        get_effective_logger().debug(
            f'task="patch_shadow_records_full" skipped or failed: {e}, '
            f'component="{component}", tenant_id="{tenant_id}"'
        )


def refresh_shadow_after_score_change(
    service, server_rest_uri, system_authtoken, tenant_id, component, object_id,
    splunkd_timeout=300, shadow_enabled=None, splunkd_port=None,
):
    """
    Refresh a single entity's shadow record after a score change (false positive,
    manual score influence, outlier false positive).

    These operations write scoring metrics but do NOT update KV store records.
    The shadow must be refreshed by re-fetching the entity through the
    in-process DecisionMakerEngine (which re-runs the decision maker) and
    patching the shadow with the updated enriched record.

    Previously this function did an HTTP loopback to
    /trackme/v2/component/load_component_data. The engine produces the
    same enriched record via the same library code (set_*_status /
    scoring helpers / threshold lookups) but in-process — no HTTP
    round-trip, no JSON serialization, no second REST stack pass.

    Designed to run in a daemon thread — non-fatal, never blocks caller.

    Args:
        service: Splunk service object (system-level auth)
        server_rest_uri: Splunk REST URI (e.g. https://localhost:8089)
        system_authtoken: System auth token for REST calls
        tenant_id: Virtual tenant ID
        component: Component type (dsm, dhm, mhm, flx, fqm, wlk)
        object_id: Entity key (_key) to refresh
        splunkd_timeout: legacy REST timeout (ignored by the engine path,
            kept for caller signature compatibility)
        shadow_enabled: When 0, skip the refresh entirely
        splunkd_port: Splunkd REST port — used by the engine to open its
            system-level service connection. Required; caller must pass
            request_info.server_rest_port. The engine does NOT invent a
            fallback host or port.
    """
    # If shadow is explicitly disabled for this tenant, skip
    if shadow_enabled is not None and int(shadow_enabled) == 0:
        return

    if not splunkd_port:
        get_effective_logger().warning(
            f'task="refresh_shadow_after_score_change" missing splunkd_port; '
            f'cannot construct DecisionMakerEngine, skipping refresh. '
            f'object_id="{object_id}", component="{component}", tenant_id="{tenant_id}"'
        )
        return

    try:
        # Re-fetch the entity with updated score from the decision maker.
        # Reuse the caller's existing splunklib service for KV reads; the
        # engine builds its own service_system internally for conf reads.
        from trackme_libs_decisionmaker_engine import DecisionMakerEngine

        engine = DecisionMakerEngine(
            session_key=system_authtoken,
            splunkd_uri=server_rest_uri,
            tenant_id=tenant_id,
            component=component,
            system_authtoken=system_authtoken,
            splunkd_port=splunkd_port,
            service=service,
            logger=logging.getLogger("trackme.shadow.refresh_after_score_change"),
        )
        engine.load()
        enriched_record = engine.evaluate_object_full(object_id, lookup_field="_key")

        if enriched_record is None:
            get_effective_logger().debug(
                f'task="refresh_shadow_after_score_change" no data returned, '
                f'object_id="{object_id}", component="{component}", tenant_id="{tenant_id}"'
            )
            return

        # Reuse the existing shadow-write helper (full replacement, not merge)
        update_shadow_record(service, tenant_id, component, object_id, enriched_record, shadow_enabled=shadow_enabled)

        get_effective_logger().info(
            f'task="refresh_shadow_after_score_change", '
            f'object_id="{object_id}", component="{component}", tenant_id="{tenant_id}"'
        )

    except Exception as e:
        get_effective_logger().debug(
            f'task="refresh_shadow_after_score_change" failed: {e}, '
            f'object_id="{object_id}", component="{component}", tenant_id="{tenant_id}"'
        )


def should_use_shadow(service, tenant_id, component, shadow_threshold, has_filters, shadow_enabled=0):
    """
    Determine whether to read from the shadow collection instead of
    running full enrichment.

    Args:
        service: Splunk service object
        tenant_id: Virtual tenant ID
        component: Component type (dsm, dhm, mhm, flx, fqm, wlk)
        shadow_threshold: Minimum entity count to use shadow (e.g. 5000)
        has_filters: True if request has entity-level filters (filter_key, filter_object, etc.)
        shadow_enabled: Master switch from tenant config (1=enabled, 0=disabled)

    Returns:
        True if shadow should be used, False otherwise.
    """
    # Disabled when master switch is off, threshold is 0, or when request has entity-level filters
    if int(shadow_enabled) == 0 or shadow_threshold <= 0 or has_filters:
        return False

    try:
        # Use | inputlookup with stats count to check if shadow has enough data
        # This is safe for any collection size and avoids direct KV store SDK queries
        shadow_base = _get_shadow_collection_name(component)
        transform_name = f"{shadow_base}_tenant_{tenant_id}"

        search_query = f"| inputlookup {transform_name} | head 1 | stats count"
        kwargs_search = {
            "earliest_time": "-1s",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }

        reader = run_splunk_search(
            service,
            search_query,
            kwargs_search,
            1,  # max_retries — keep fast, this is a gate check
            1,  # sleep_time
        )

        shadow_has_data = False
        for item in reader:
            if isinstance(item, dict):
                if int(item.get("count", 0)) > 0:
                    shadow_has_data = True

        return shadow_has_data

    except Exception:
        # Any error means we can't use shadow — fall back to direct path
        return False
