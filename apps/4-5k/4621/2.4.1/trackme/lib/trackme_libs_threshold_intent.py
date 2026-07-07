"""
Delay/Latency Threshold Intent Lock — shared helpers (DSM + DHM).

Background
----------
The mechanical delay auto-writers (adaptive delay, variable-delay auto-review)
and the static lagging-class override can silently rewrite an entity's
``data_max_delay_allowed`` / ``data_max_lag_allowed`` during routine scheduled
runs, reverting a value an operator set by hand. This module implements the
countermeasure: an operator can *pin* (lock) an entity's thresholds, which

  1. sets the persistent on-record flags ``data_max_delay_allowed_locked`` /
     ``data_max_lag_allowed_locked`` (preserved across decision-maker cycles by
     ``persistent_fields_{dsm,dhm}``), so every auto-writer SKIPS the entity at
     source (zero extra round-trips — the flag rides on the already-loaded
     record / SPL candidate lookup), and

  2. records the requested values in an independent per-tenant ledger collection
     ``kv_trackme_{component}_threshold_intent_tenant_<tid>``, which the
     reconcile task (in the health tracker) verifies and restores on drift,
     leaving an audit + Configuration Guardian trace.

Cost
----
The ledger is keyed off the *pinned subset*, never the full entity collection.
Capture is one small write per manual edit; reconcile reads the whole (small)
ledger and ``batch_find``s only the pinned live entities. Both scale with the
number of pinned entities, independent of total entity count (safe at 100k+).
"""

import json
import time

from trackme_libs_logging import get_effective_logger
from trackme_libs_get_data import (
    batch_find_records_by_object,
    batch_find_records_by_key,
    get_full_kv_collection,
)

# Persistent on-record lock flags (mirror collections_data persistent_fields).
LOCK_FIELD_DELAY = "data_max_delay_allowed_locked"
LOCK_FIELD_LAG = "data_max_lag_allowed_locked"

# vtenant_account master toggle. Enabled-when-absent for forward-compat with
# tenants that predate the field (same convention as ``enable_ai_assistant``).
VTENANT_TOGGLE = "delay_threshold_lock_enabled"

SUPPORTED_COMPONENTS = ("dsm", "dhm")


def _truthy(value):
    return str(value).strip().lower() == "true"


def is_delay_threshold_locked(record):
    """True when the entity's delay threshold is pinned by the operator."""
    return _truthy((record or {}).get(LOCK_FIELD_DELAY, "false"))


def is_lag_threshold_locked(record):
    """True when the entity's lag threshold is pinned by the operator."""
    return _truthy((record or {}).get(LOCK_FIELD_LAG, "false"))


def threshold_lock_enabled(vtenant_account):
    """
    Master per-tenant toggle. Enabled-when-absent so existing tenants keep the
    safety net on through an upgrade; only an explicit falsy value disables it.
    """
    if not vtenant_account:
        return True
    value = vtenant_account.get(VTENANT_TOGGLE, 1)
    return str(value).strip().lower() not in ("0", "false", "no", "")


def ledger_collection_name(tenant_id, component):
    return f"kv_trackme_{component}_threshold_intent_tenant_{tenant_id}"


def get_ledger_collection(service, tenant_id, component):
    return service.kvstore[ledger_collection_name(tenant_id, component)]


def _resolve_entities(entity_collection, object_list, keys_list):
    """Resolve the affected entity records (pre-update) by object or _key."""
    if object_list:
        _, entities = batch_find_records_by_object(entity_collection, object_list)
    elif keys_list:
        _, entities = batch_find_records_by_key(entity_collection, keys_list)
    else:
        entities = []
    return entities


def _coalesce(provided, fallback):
    """Use the just-provided value, else fall back to the entity's current one."""
    if provided is not None and str(provided) != "":
        return str(provided)
    if fallback is not None and str(fallback) != "":
        return str(fallback)
    return ""


def variable_delay_collection_name(tenant_id, component):
    return f"kv_trackme_{component}_variable_delay_tenant_{tenant_id}"


def _fetch_variable_delay_dict(service, tenant_id, component, keys):
    """
    Best-effort {entity_key: variable_delay_record} for the given entity keys.

    The variable-delay slots live in their own per-tenant collection, separate
    from the main entity record. The lock must pin the SLOTS for a variable-policy
    entity (the slots ARE the operator's delay configuration), so capture/reconcile
    snapshot them here. Returns {} on any error (the static scalars still pin).
    """
    if not keys:
        return {}
    try:
        coll = service.kvstore[variable_delay_collection_name(tenant_id, component)]
        found, _ = batch_find_records_by_key(coll, list(keys))
        return found or {}
    except Exception:
        return {}


def _is_variable_policy(entity):
    return str((entity or {}).get("variable_delay_policy", "static")).strip().lower() == "variable"


def _slots_equal(a, b):
    """Compare two variable_delay_slots JSON strings structurally (order-tolerant)."""
    try:
        return json.loads(a or "{}") == json.loads(b or "{}")
    except Exception:
        return (a or "") == (b or "")


def _build_ledger_record(
    entity,
    component,
    tenant_id,
    requested_delay,
    requested_lag,
    requested_by,
    now,
    variable_delay_record=None,
):
    # Variable-delay slot snapshot. For a variable-policy entity the pinned
    # "delay threshold" is the slot schedule (stored in the variable-delay
    # collection), NOT the static scalar — data_max_delay_allowed merely tracks
    # the active slot at runtime. Snapshot the slots + default so reconcile can
    # restore slot drift; the static scalar is captured too but reconcile ignores
    # it for variable entities (see reconcile_threshold_intent).
    vd = variable_delay_record or {}
    return {
        "_key": entity.get("_key"),
        "object": entity.get("object"),
        "object_category": entity.get("object_category", ""),
        "tenant_id": tenant_id,
        "component": component,
        "requested_delay_allowed": _coalesce(
            requested_delay, entity.get("data_max_delay_allowed")
        ),
        "requested_lag_allowed": _coalesce(
            requested_lag, entity.get("data_max_lag_allowed")
        ),
        "requested_variable_delay_policy": str(
            entity.get("variable_delay_policy", "static")
        ),
        "requested_variable_delay_slots": vd.get("variable_delay_slots", "") or "",
        "requested_variable_delay_default": str(vd.get("variable_delay_default", "")),
        "locked": "true",
        "requested_by": requested_by or "",
        "requested_ctime": str(int(now)),
        "last_reconcile_time": "",
        "last_reconcile_status": "",
        "mtime": str(int(now)),
    }


def apply_threshold_intent_on_manual_update(
    service,
    tenant_id,
    component,
    entity_collection,
    object_list,
    keys_list,
    lock_threshold,
    requested_delay,
    requested_lag,
    requested_by="manual",
    logger=None,
):
    """
    Maintain the threshold-intent ledger on a manual lag-policy update and
    return the on-record lock flags to merge into the same entity update.

    Semantics
    ---------
    ``lock_threshold == "true"``  -> pin: set ``*_locked=true`` on the entity
        (returned in ``lock_update_fields``) and upsert one ledger record per
        affected entity capturing the requested delay+lag.
    ``lock_threshold == "false"`` -> unpin: set ``*_locked=false`` and delete the
        ledger records.
    ``lock_threshold is None``    -> preserve lock state (no entity-flag change);
        if a threshold value changed on an *already-locked* entity, refresh that
        entity's ledger requested value so reconcile honours the latest manual
        intent. Non-locking callers (adaptive delay write-back, bulk edits) thus
        never toggle a lock by accident.

    Returns ``(lock_update_fields, counts)``. ``lock_update_fields`` is an empty
    dict for the preserve path. Fail-soft: any ledger error is logged and
    swallowed so it never blocks the underlying threshold update.

    Note: the time module's epoch is read once here; callers in restricted
    contexts (workflow scripts) never reach this path.
    """
    log = logger or get_effective_logger()
    counts = {"locked": 0, "unlocked": 0, "refreshed": 0}
    lock_update_fields = {}

    if component not in SUPPORTED_COMPONENTS:
        return lock_update_fields, counts

    # Normalise the tri-state lock intent.
    lock_intent = None
    if lock_threshold is not None:
        lock_intent = str(lock_threshold).strip().lower()
        if lock_intent not in ("true", "false"):
            lock_intent = None

    # Compute the on-record lock flags from the intent BEFORE any ledger I/O.
    # The persistent *_locked flags are the PRIMARY protection (every auto-writer
    # gate honours them); the ledger is only the SECONDARY safety net. So the
    # source-side lock must still be set/cleared even if the ledger collection is
    # missing or temporarily unavailable (e.g. a partially-upgraded tenant) — the
    # outer fail-soft except must never silently drop the flag.
    if lock_intent == "true":
        lock_update_fields = {LOCK_FIELD_DELAY: "true", LOCK_FIELD_LAG: "true"}
    elif lock_intent == "false":
        lock_update_fields = {LOCK_FIELD_DELAY: "false", LOCK_FIELD_LAG: "false"}

    try:
        ledger = get_ledger_collection(service, tenant_id, component)
        now = time.time()

        entities = _resolve_entities(entity_collection, object_list, keys_list)
        if not entities:
            return lock_update_fields, counts

        # Snapshot source for variable-delay slots (one batch read of the
        # variable-delay collection for the affected pinned subset). Used by
        # _build_ledger_record so a locked variable-policy entity pins its slot
        # schedule, not just the static scalar.
        vd_dict = _fetch_variable_delay_dict(
            service,
            tenant_id,
            component,
            [e.get("_key") for e in entities if e.get("_key")],
        )

        if lock_intent == "true":
            records = [
                _build_ledger_record(
                    e,
                    component,
                    tenant_id,
                    requested_delay,
                    requested_lag,
                    requested_by,
                    now,
                    variable_delay_record=vd_dict.get(e.get("_key")),
                )
                for e in entities
                if e.get("_key")
            ]
            if records:
                ledger.data.batch_save(*records)
                counts["locked"] = len(records)
                log.info(
                    f'threshold_intent pinned, tenant_id="{tenant_id}", '
                    f'component="{component}", count={len(records)}, '
                    f'requested_by="{requested_by}"'
                )

        elif lock_intent == "false":
            # The unpin is authoritative the moment the caller clears the entity
            # *_locked flags (returned above, independent of this I/O). Deleting
            # the ledger row is best-effort cleanup: if it fails, reconcile sees
            # the entity is no longer locked and drops the stale row as
            # `stale_cleared` rather than resurrecting the lock — so a failed
            # delete cannot silently re-pin. Log failures for visibility instead
            # of swallowing them.
            keys = [e.get("_key") for e in entities if e.get("_key")]
            if keys:
                deleted = False
                try:
                    ledger.data.delete(query=json.dumps({"_key": {"$in": keys}}))
                    deleted = True
                except Exception:
                    for key in keys:
                        try:
                            ledger.data.delete_by_id(key)
                        except Exception as delete_error:
                            log.warning(
                                f'threshold_intent unpin ledger delete failed '
                                f'(reconcile will clean up the stale row), '
                                f'tenant_id="{tenant_id}", component="{component}", '
                                f'key="{key}", exception="{str(delete_error)}"'
                            )
                counts["unlocked"] = len(keys)
                log.info(
                    f'threshold_intent unpinned, tenant_id="{tenant_id}", '
                    f'component="{component}", count={len(keys)}, '
                    f'ledger_rows_deleted="{deleted}"'
                )

        else:
            # Preserve: only refresh the ledger for entities already locked, so a
            # value edit on a pinned entity updates the pinned value rather than
            # being reverted by reconcile.
            locked_entities = [
                e
                for e in entities
                if e.get("_key")
                and (is_delay_threshold_locked(e) or is_lag_threshold_locked(e))
            ]
            records = [
                _build_ledger_record(
                    e,
                    component,
                    tenant_id,
                    requested_delay,
                    requested_lag,
                    requested_by,
                    now,
                    variable_delay_record=vd_dict.get(e.get("_key")),
                )
                for e in locked_entities
            ]
            if records:
                # CRITICAL: a swallowed preserve-refresh would leave the ledger
                # holding the OLD requested value while the caller persists the
                # operator's NEW threshold — reconcile would then revert the edit
                # to the stale pin. Catch the refresh failure HERE (not the outer
                # fail-soft except) and surface it via counts so the caller can
                # reject the edit and keep entity+ledger consistent.
                try:
                    ledger.data.batch_save(*records)
                    counts["refreshed"] = len(records)
                    log.info(
                        f'threshold_intent refreshed for locked entities, '
                        f'tenant_id="{tenant_id}", component="{component}", '
                        f'count={len(records)}'
                    )
                except Exception as refresh_error:
                    counts["preserve_refresh_failed"] = True
                    log.error(
                        f'threshold_intent preserve-path ledger refresh FAILED — '
                        f'caller must reject the edit to avoid a reconcile revert, '
                        f'tenant_id="{tenant_id}", component="{component}", '
                        f'count={len(records)}, exception="{str(refresh_error)}"'
                    )

    except Exception as e:
        # Fail-soft: never block the threshold update on a ledger error.
        log.error(
            f'threshold_intent ledger maintenance failed (non-blocking), '
            f'tenant_id="{tenant_id}", component="{component}", '
            f'exception="{str(e)}"'
        )

    return lock_update_fields, counts


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_seconds_note(value):
    """Render a seconds value as ``"8000s (~2h 13m)"`` for the Markdown note.

    Falls back to the raw string for non-numeric input.
    """
    f = _as_float(value)
    if f is None:
        return str(value)
    secs = int(round(f))
    if secs < 60:
        return f"{secs}s"
    mins, _ = divmod(secs, 60)
    hrs, m = divmod(mins, 60)
    days, h = divmod(hrs, 24)
    parts = []
    if days:
        parts.append(f"{days}d")
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    human = " ".join(parts) if parts else f"{secs}s"
    return f"{secs}s (~{human})"


def _build_reconcile_note_markdown(entity, component, restored, is_var, persisted=True):
    """Compose the Markdown body of the threshold-lock reconcile note.

    ``restored`` maps facet -> {"from": <drifted value>, "to": <restored value>}
    for "delay" / "lag", and a presence marker for "slots".

    ``persisted`` selects the variant:
      * True  — the restore was written back successfully ("restored" note).
      * False — drift was detected but the KV write-back FAILED, so the values
        were NOT actually repaired ("restore did not persist" warning note). The
        success note must never be shown for a correction that never landed.
    """
    entity_name = entity.get("object", "")
    comp = str(component).upper()
    if persisted:
        title = "### 🔒 Threshold lock — pinned value automatically restored"
        intro = (
            f"This **{comp}** entity (**{entity_name}**) is **threshold-locked**, "
            f"but one or more values had drifted from the pinned configuration. "
            f"TrackMe restored them:"
        )
    else:
        title = (
            "### ⚠️ Threshold lock — drift detected, automatic restore did NOT persist"
        )
        intro = (
            f"This **{comp}** entity (**{entity_name}**) is **threshold-locked** and "
            f"one or more values had drifted from the pinned configuration. TrackMe "
            f"attempted to restore them but the KV write-back **failed**, so the "
            f"drift may still be present:"
        )

    lines = [
        title,
        "",
        (
            "_Generated automatically by the TrackMe threshold-lock reconcile "
            "routine (the per-tenant health-tracker safety net)._"
        ),
        "",
        intro,
        "",
    ]
    if "delay" in restored:
        d = restored["delay"]
        if persisted:
            lines.append(
                f"- **Delay threshold:** `{_format_seconds_note(d.get('from'))}` "
                f"→ restored to **`{_format_seconds_note(d.get('to'))}`** (the locked value)"
            )
        else:
            lines.append(
                f"- **Delay threshold:** drifted to `{_format_seconds_note(d.get('from'))}` "
                f"— could not be restored to the locked **`{_format_seconds_note(d.get('to'))}`**"
            )
    if "lag" in restored:
        lg = restored["lag"]
        if persisted:
            lines.append(
                f"- **Latency threshold:** `{_format_seconds_note(lg.get('from'))}` "
                f"→ restored to **`{_format_seconds_note(lg.get('to'))}`** (the locked value)"
            )
        else:
            lines.append(
                f"- **Latency threshold:** drifted to `{_format_seconds_note(lg.get('from'))}` "
                f"— could not be restored to the locked **`{_format_seconds_note(lg.get('to'))}`**"
            )
    if "slots" in restored:
        if persisted:
            lines.append(
                "- **Variable-delay slots:** the time-slot schedule had drifted and "
                "was restored to the locked schedule."
            )
        else:
            lines.append(
                "- **Variable-delay slots:** the time-slot schedule had drifted and "
                "could not be restored to the locked schedule."
            )
    lines.append("")
    if persisted:
        lines.extend(
            [
                (
                    "**Why did this happen?** A locked entity is never changed by "
                    "TrackMe's own automation — adaptive delay, variable-delay review "
                    "and lagging-class overrides all skip locked entities. A restored "
                    "drift therefore means a change reached this entity **outside** "
                    "those gates (e.g. a direct KV edit, a downgrade/upgrade, or a "
                    "writer that did not honour the lock)."
                ),
                "",
                (
                    "**What to check:** review this entity's **Audit changes** "
                    "timeline to find what changed the value, and the "
                    "`delay_threshold_drift_corrected` Configuration Guardian alert "
                    "for the running history. If the drift keeps recurring, fix the "
                    "underlying writer rather than relying on this safety net."
                ),
            ]
        )
    else:
        lines.append(
            "**Action required:** the automatic safety net could not repair this "
            "entity — the KV Store write-back failed (see `trackme_tracker_health.log` "
            "for the error). Verify the KV Store is healthy; the next reconcile cycle "
            "will retry, but if the drift persists, re-apply the locked thresholds "
            "manually."
        )
    return "\n".join(lines)


def _create_reconcile_note(
    service,
    tenant_id,
    component,
    entity,
    restored,
    is_var,
    session_key=None,
    splunkd_uri=None,
    logger=None,
    persisted=True,
):
    """Best-effort Markdown note on an entity whose pinned threshold the reconcile
    routine just restored (``persisted=True``) — or attempted to restore but the
    KV write-back failed (``persisted=False``). Never raises — a note failure must
    not affect the reconcile outcome. Mirrors the adaptive-delay framework's
    summary-note pattern (``kv_trackme_notes_tenant_<tid>``)."""
    log = logger or get_effective_logger()
    if not restored:
        return
    object_id = entity.get("_key")
    if not object_id:
        return
    note_kind = "restored" if persisted else "restore_failed"

    try:
        note_md = _build_reconcile_note_markdown(
            entity, component, restored, is_var, persisted=persisted
        )
        collection = service.kvstore[f"kv_trackme_notes_tenant_{tenant_id}"]
        collection.data.insert(
            json.dumps(
                {
                    "object_id": object_id,
                    "note": note_md,
                    "created_by": "trackme_threshold_reconcile",
                    "mtime": time.time(),
                }
            )
        )
        log.info(
            f'threshold_intent reconcile note created, tenant_id="{tenant_id}", '
            f'component="{component}", object="{entity.get("object")}", '
            f'kind="{note_kind}", facets="{",".join(sorted(restored.keys()))}"'
        )
    except Exception as e:
        log.warning(
            f'threshold_intent reconcile note creation failed (non-blocking), '
            f'tenant_id="{tenant_id}", component="{component}", '
            f'object_id="{object_id}", kind="{note_kind}", exception="{str(e)}"'
        )
        return

    # Best-effort audit event so the note shows in the per-entity Audit changes
    # tab. Requires session_key + splunkd_uri (passed from the health tracker);
    # skip silently when unavailable (e.g. unit tests). change_type="create note"
    # keeps it distinct from the threshold restore in the audit timeline.
    if not session_key or not splunkd_uri:
        return
    try:
        from trackme_libs import trackme_audit_event

        trackme_audit_event(
            session_key,
            splunkd_uri,
            tenant_id,
            "trackme_threshold_reconcile",
            "success",
            "create note",
            entity.get("object"),
            f"splk-{component}",
            {
                "object_id": object_id,
                "created_by": "trackme_threshold_reconcile",
                "kind": note_kind,
                "facets": sorted(restored.keys()),
            },
            "Note created successfully",
            (
                "threshold-lock reconcile summary note"
                if persisted
                else "threshold-lock reconcile FAILURE note (restore did not persist)"
            ),
            object_id=object_id,
        )
    except Exception as audit_e:
        log.warning(
            f'threshold_intent reconcile note audit failed (non-blocking), '
            f'tenant_id="{tenant_id}", component="{component}", '
            f'object_id="{object_id}", exception="{str(audit_e)}"'
        )


def reconcile_threshold_intent(
    service, tenant_id, component, logger=None, session_key=None, splunkd_uri=None
):
    """
    Independent safety net: verify every pinned entity's live threshold against
    the ledger and RESTORE any drift, leaving an audit trace. Runs periodically
    in the health tracker — the source gates are the real-time protection, this
    catches anything that slips past (direct KV pokes, a downgrade/upgrade, a
    bug in a future auto-writer).

    Cost: reads the whole (small) ledger once, then ``batch_find``s ONLY the
    pinned live entities — never a full scan of the entity collection. Writes
    back only drifted records. Scales with the pinned subset, not total entity
    count (safe at 100k+).

    Returns a summary dict:
        {component, checked, drift_corrected, drifted_objects[], orphans_cleared,
         errors}
    The ``drifted_objects`` list feeds the Configuration Guardian drift check.
    """
    log = logger or get_effective_logger()
    summary = {
        "component": component,
        "checked": 0,
        "drift_corrected": 0,
        "drifted_objects": [],
        "orphans_cleared": 0,
        "stale_cleared": 0,
        "errors": 0,
        # Set when the KV write-back of restored values FAILED — the corrections
        # did NOT land. drift_corrected/drifted_objects are then zeroed (so the
        # Guardian doesn't claim a correction that never persisted) and the
        # affected objects are reported here instead.
        "restore_persist_failed": False,
        "restore_failed_objects": [],
    }

    if component not in SUPPORTED_COMPONENTS:
        return summary

    try:
        ledger = get_ledger_collection(service, tenant_id, component)
        ledger_records, _, _ = get_full_kv_collection(
            ledger, ledger_collection_name(tenant_id, component)
        )
    except Exception as e:
        summary["errors"] += 1
        log.error(
            f'threshold_intent reconcile failed to read ledger, '
            f'tenant_id="{tenant_id}", component="{component}", '
            f'exception="{str(e)}"'
        )
        return summary

    locked_records = [
        r for r in ledger_records if str(r.get("locked", "")).strip().lower() == "true"
    ]
    if not locked_records:
        return summary

    keys = [r.get("_key") for r in locked_records if r.get("_key")]
    try:
        # The kvstore[...] subscript itself raises if the collection is missing,
        # so keep it INSIDE the fail-soft try (a missing/unavailable entity
        # collection must yield a logged error summary, not an unhandled throw).
        entity_collection = service.kvstore[
            f"kv_trackme_{component}_tenant_{tenant_id}"
        ]
        entity_dict, _ = batch_find_records_by_key(entity_collection, keys)
    except Exception as e:
        summary["errors"] += 1
        log.error(
            f'threshold_intent reconcile failed to read entities, '
            f'tenant_id="{tenant_id}", component="{component}", '
            f'exception="{str(e)}"'
        )
        return summary

    # Variable-delay slot snapshots for the same pinned subset (best effort). A
    # read failure only disables slot-drift checking this cycle; the static
    # scalar + lag reconcile still run.
    vd_collection = None
    vd_dict = {}
    try:
        vd_collection = service.kvstore[
            variable_delay_collection_name(tenant_id, component)
        ]
        vd_dict, _ = batch_find_records_by_key(vd_collection, keys)
    except Exception as e:
        log.warning(
            f'threshold_intent reconcile could not read variable-delay slots '
            f'(slot drift unchecked this cycle), tenant_id="{tenant_id}", '
            f'component="{component}", exception="{str(e)}"'
        )

    now = time.time()
    entity_updates = []
    ledger_updates = []
    vd_updates = []
    orphan_keys = []
    note_tasks = []  # (entity, restored_facets, is_variable) per corrected entity

    for lr in locked_records:
        key = lr.get("_key")
        entity = entity_dict.get(key)
        summary["checked"] += 1

        if entity is None:
            # Entity no longer exists (deleted) — drop the orphan ledger record.
            orphan_keys.append(key)
            summary["orphans_cleared"] += 1
            continue

        # The entity's on-record lock flag is the AUTHORITY on whether the
        # threshold is pinned (it is the field the auto-writer gates honour and
        # that persistent_fields preserves). The ledger only stores the values
        # to restore *while* pinned. If the operator unpinned the entity (flag
        # cleared) but this ledger row still reads locked="true" — e.g. the
        # capture path's best-effort delete failed — the entity is NO LONGER
        # pinned: drop the stale row and DO NOT restore or re-assert. Re-locking
        # here would silently undo the operator's unpin (CodeRabbit). Restoring
        # is gated per field on the entity's own delay/lag lock flag.
        delay_locked = is_delay_threshold_locked(entity)
        lag_locked = is_lag_threshold_locked(entity)
        if not delay_locked and not lag_locked:
            orphan_keys.append(key)
            summary["stale_cleared"] += 1
            continue

        entity_changed = False
        slot_changed = False
        req_delay = lr.get("requested_delay_allowed", "")
        req_lag = lr.get("requested_lag_allowed", "")
        is_var = _is_variable_policy(entity)
        # What was restored, for the operator-facing Markdown note. Keyed by
        # facet -> {"from": <live drifted value>, "to": <restored pinned value>}.
        restored = {}

        if delay_locked and is_var:
            # Variable-policy: the pinned delay config is the SLOT schedule, not
            # the static scalar — data_max_delay_allowed legitimately tracks the
            # active slot every cycle, so restoring it would fight the decision
            # maker. Restore SLOT drift from the snapshot instead (lag is still
            # static and handled below).
            req_slots = lr.get("requested_variable_delay_slots", "")
            req_default = str(lr.get("requested_variable_delay_default", ""))
            vd = vd_dict.get(key)
            if vd is not None and req_slots:
                live_slots = vd.get("variable_delay_slots", "")
                live_default = str(vd.get("variable_delay_default", ""))
                if (not _slots_equal(live_slots, req_slots)) or (
                    req_default and req_default != live_default
                ):
                    vd["variable_delay_slots"] = req_slots
                    if req_default:
                        vd["variable_delay_default"] = req_default
                    vd["variable_delay_updated_by"] = "trackme_threshold_reconcile"
                    vd["variable_delay_mtime"] = str(int(now))
                    vd_updates.append(vd)
                    slot_changed = True
                    restored["slots"] = {"from": "drifted schedule", "to": "locked schedule"}
        elif delay_locked:
            req_delay_f = _as_float(req_delay)
            if req_delay_f is not None:
                live_delay = entity.get("data_max_delay_allowed")
                live_delay_f = _as_float(live_delay)
                if live_delay_f is None or abs(live_delay_f - req_delay_f) >= 1:
                    entity["data_max_delay_allowed"] = req_delay
                    entity["data_max_delay_allowed_updated_by"] = (
                        "trackme_threshold_reconcile"
                    )
                    entity["data_max_delay_allowed_mtime"] = str(int(now))
                    entity_changed = True
                    restored["delay"] = {"from": live_delay, "to": req_delay}

        # Lag is always a static scalar, even for variable-delay entities.
        req_lag_f = _as_float(req_lag)
        if lag_locked and req_lag_f is not None:
            live_lag = entity.get("data_max_lag_allowed")
            live_lag_f = _as_float(live_lag)
            if live_lag_f is None or abs(live_lag_f - req_lag_f) >= 1:
                entity["data_max_lag_allowed"] = req_lag
                entity_changed = True
                restored["lag"] = {"from": live_lag, "to": req_lag}

        drift = entity_changed or slot_changed
        status = "ok"
        if entity_changed:
            entity_updates.append(entity)
        if drift:
            summary["drift_corrected"] += 1
            summary["drifted_objects"].append(entity.get("object"))
            status = "drift_corrected"
            note_tasks.append((entity, dict(restored), is_var))
            log.info(
                f'threshold_intent reconcile restored pinned threshold, '
                f'tenant_id="{tenant_id}", component="{component}", '
                f'object="{entity.get("object")}", '
                f'policy="{"variable" if is_var else "static"}", '
                f'slot_restored="{slot_changed}"'
            )

        lr["last_reconcile_time"] = str(int(now))
        lr["last_reconcile_status"] = status
        lr["mtime"] = str(int(now))
        ledger_updates.append(lr)

    # Persist the restored values (entity + variable-delay records). This is the
    # part that actually repairs the drift — tracked separately from the ledger
    # bookkeeping so the note and summary tell the truth about what landed.
    restore_persisted = True
    try:
        if entity_updates:
            entity_collection.data.batch_save(*entity_updates)
        if vd_updates and vd_collection is not None:
            vd_collection.data.batch_save(*vd_updates)
    except Exception as e:
        restore_persisted = False
        summary["errors"] += 1
        log.error(
            f'threshold_intent reconcile failed to persist restored values, '
            f'tenant_id="{tenant_id}", component="{component}", '
            f'exception="{str(e)}"'
        )

    # Ledger bookkeeping + orphan cleanup. A failure here does NOT invalidate a
    # restore that already landed on the entity/vd record above.
    try:
        if ledger_updates:
            ledger.data.batch_save(*ledger_updates)
        if orphan_keys:
            try:
                ledger.data.delete(query=json.dumps({"_key": {"$in": orphan_keys}}))
            except Exception:
                for key in orphan_keys:
                    try:
                        ledger.data.delete_by_id(key)
                    except Exception as delete_error:
                        # Don't overstate cleanup success — surface the failing
                        # key so recurring stale-row churn is diagnosable.
                        summary["errors"] += 1
                        log.warning(
                            f'threshold_intent reconcile failed to delete stale '
                            f'ledger row, tenant_id="{tenant_id}", '
                            f'component="{component}", key="{key}", '
                            f'exception="{str(delete_error)}"'
                        )
    except Exception as e:
        summary["errors"] += 1
        log.error(
            f'threshold_intent reconcile failed to update ledger bookkeeping, '
            f'tenant_id="{tenant_id}", component="{component}", '
            f'exception="{str(e)}"'
        )

    # If the restore did NOT persist, do not let the summary claim a correction
    # that never landed: relocate the optimistic accounting so the Guardian drift
    # check (which reads drift_corrected/drifted_objects) does not raise a false
    # "corrected" alert, and surface the affected objects under a distinct key.
    if not restore_persisted and summary["drifted_objects"]:
        summary["restore_persist_failed"] = True
        summary["restore_failed_objects"] = list(summary["drifted_objects"])
        summary["drift_corrected"] = 0
        summary["drifted_objects"] = []

    # Operator-facing Markdown notes — one per corrected entity. On success a
    # "restored" note; if the restore did NOT persist, a "restore failed" warning
    # note instead — never a success note for a change that never landed. Written
    # AFTER the write-back so the note reflects reality. Best-effort and fully
    # isolated: a note failure never affects the reconcile outcome.
    for note_entity, note_restored, note_is_var in note_tasks:
        _create_reconcile_note(
            service,
            tenant_id,
            component,
            note_entity,
            note_restored,
            note_is_var,
            session_key=session_key,
            splunkd_uri=splunkd_uri,
            logger=log,
            persisted=restore_persisted,
        )

    if (
        summary["drift_corrected"]
        or summary["orphans_cleared"]
        or summary["stale_cleared"]
        or summary["restore_persist_failed"]
    ):
        log.info(
            f'threshold_intent reconcile summary, tenant_id="{tenant_id}", '
            f'component="{component}", checked={summary["checked"]}, '
            f'drift_corrected={summary["drift_corrected"]}, '
            f'orphans_cleared={summary["orphans_cleared"]}, '
            f'stale_cleared={summary["stale_cleared"]}, '
            f'restore_persist_failed={summary["restore_persist_failed"]}, '
            f'restore_failed_objects={len(summary["restore_failed_objects"])}'
        )

    return summary
