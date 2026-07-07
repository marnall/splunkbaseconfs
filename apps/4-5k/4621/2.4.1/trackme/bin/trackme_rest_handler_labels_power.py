#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_labels_power.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Built-in libraries
import hashlib
import json
import os
import sys
import time
import threading

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger("trackme.rest.labels_power", "trackme_rest_api_labels_power.log")


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    trackme_audit_event,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_resolve_entity_object_name,
    trackme_vtenant_account_from_service,
)
from trackme_libs_shadow import patch_shadow_records

# import Splunk libs
import splunklib.client as client

# Import default labels from single source of truth
from collections_data import default_labels as DEFAULT_LABELS


def _resolve_label_names(labels_collection, label_ids):
    """Resolve a list of label _key values to their display names. Missing
    labels keep the raw _key as their name. Never raises.
    """
    names = []
    for lid in label_ids or []:
        try:
            label_def = labels_collection.data.query_by_id(lid)
            if label_def and label_def.get("label_name"):
                names.append(label_def["label_name"])
            else:
                names.append(str(lid))
        except Exception:
            names.append(str(lid))
    return names


# Default colour and description applied to labels auto-created by
# ``post_assign_labels`` when callers pass ``label_names`` and a name
# isn't already in the tenant's catalog.  Neutral grey so these
# labels are visually distinguishable from the curated 8-default
# palette (each of which has a meaning-bearing colour).
_AUTO_CREATED_LABEL_COLOR = "#9e9e9e"
_AUTO_CREATED_LABEL_DESCRIPTION = "Auto-created via assign_labels"


def _deterministic_label_key_for_auto_create(label_name):
    """
    Deterministic ``_key`` for auto-created labels, derived from the
    lowercase / trimmed name.

    Splunk KV Store enforces uniqueness ONLY on ``_key``; it has no
    unique constraint on the ``label_name`` field.  The naive race
    fix ("catch the unique-constraint exception and re-read")
    therefore doesn't work for auto-create with an auto-generated
    ``_key`` — two concurrent callers both succeed and silently
    duplicate the catalog (Bugbot caught this on PR #1510 cycle 2,
    Medium severity).

    Using a deterministic ``_key`` derived from the canonical (lower-
    cased, whitespace-trimmed) form of the name forces concurrent
    inserts to actually collide on the only field KV Store DOES
    enforce — so the recovery path is real, not aspirational.

    24 hex chars matches the visual format Splunk uses for its
    auto-generated keys (MongoDB-style ObjectID), and 96 bits of
    SHA-256 prefix is more than enough collision resistance for
    label-name space (a tenant has dozens, not millions, of
    distinct labels).

    The deterministic-key convention only applies to labels created
    via THIS auto-create path. Labels created via the UI / explicit
    ``post_create_label`` retain Splunk's auto-generated ``_key`` —
    the lookup-by-name path at the top of
    ``_resolve_or_create_labels_by_name`` finds them first and short-
    circuits before the auto-create branch is reached, so the two
    key conventions never need to interoperate at create time.
    """
    canonical = str(label_name or "").strip().lower()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def _resolve_or_create_labels_by_name(
    labels_collection,
    label_names,
    request_info,
    tenant_id,
    audit_uri,
    audit_token,
    update_comment,
):
    """
    Resolve a list of label *names* to the catalog's ``_key`` values,
    auto-creating any name that isn't already in the catalog so that
    callers (notably the Concierge AI Assistant — which builds REST
    requests from natural-language input and doesn't pre-resolve IDs
    the way the UI does) can pass human-readable names directly.

    Behaviour:
      * Names are matched case-insensitively against the catalog's
        existing ``label_name`` field.
      * Whitespace is trimmed; empty strings are dropped.
      * Duplicate-by-name input is silently deduped (so passing
        ``["Blocked", "blocked"]`` resolves to one assignment).
      * For names that don't match the catalog, a new label is
        inserted with a deterministic ``_key`` derived from the
        lowercase name (see
        ``_deterministic_label_key_for_auto_create``) plus
        ``_AUTO_CREATED_LABEL_COLOR`` /
        ``_AUTO_CREATED_LABEL_DESCRIPTION``, and audit-trailed via
        ``trackme_audit_event``.
      * Race-safe under concurrency: two callers both attempting to
        auto-create the same name will collide on ``_key`` (the only
        field Splunk KV Store enforces uniquely); the loser catches
        the insert exception, fetches the existing record by the
        same deterministic ``_key``, and reuses it. The audit event
        is emitted only by the actual winner.

    Returns:
        (resolved_keys, created_records, errors)
        * resolved_keys: list of ``_key`` strings, one per surviving
          input name (post-dedup).
        * created_records: list of full label records for any names
          that were auto-created during this call. Useful for the
          response payload so the caller knows what was added to
          the catalog.
        * errors: list of ``{name, reason}`` dicts for names that
          could not be resolved or created. Caller decides whether
          to fail the whole request or proceed with the partial
          ``resolved_keys``.
    """
    if not label_names:
        return ([], [], [])

    # Normalise input: trim, drop empties, dedupe case-insensitively
    # while preserving the first-seen casing for display in the
    # auto-created record.
    seen_lower = set()
    cleaned_names = []
    for raw in label_names:
        text = str(raw or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen_lower:
            continue
        seen_lower.add(key)
        cleaned_names.append(text)

    if not cleaned_names:
        return ([], [], [])

    # Build the catalog index (case-insensitive name → _key).
    try:
        catalog = list(labels_collection.data.query())
    except Exception as e:
        # Catalog read failure is fatal for any caller passing names —
        # we cannot tell what exists vs. needs creating.
        return ([], [], [{"name": n, "reason": f"catalog_read_failed: {e}"} for n in cleaned_names])

    name_to_key = {}
    for lbl in catalog:
        nm = lbl.get("label_name", "")
        k = lbl.get("_key")
        if nm and k:
            name_to_key[str(nm).strip().lower()] = k

    resolved_keys = []
    created_records = []
    errors = []
    user = request_info.user

    for display_name in cleaned_names:
        lower = display_name.lower()
        existing_key = name_to_key.get(lower)
        if existing_key:
            resolved_keys.append(existing_key)
            continue

        # Auto-create with a deterministic ``_key`` derived from the
        # canonical (lowercase / trimmed) form of the name. This is
        # what makes the race-recovery path actually work: Splunk KV
        # Store enforces uniqueness only on ``_key``, not on
        # ``label_name``, so without this two concurrent callers
        # would both succeed and silently duplicate the catalog
        # (Bugbot caught this on PR #1510 cycle 2 — the original
        # docstring's "race-safe" claim was wrong for this storage
        # backend). With a deterministic ``_key`` the loser hits a
        # real unique-constraint exception and the recovery branch
        # below picks up the existing record.
        deterministic_key = _deterministic_label_key_for_auto_create(display_name)
        now = time.time()
        new_record = {
            "_key": deterministic_key,
            "label_name": display_name,
            "label_color": _AUTO_CREATED_LABEL_COLOR,
            "label_description": _AUTO_CREATED_LABEL_DESCRIPTION,
            "label_order": "999",
            "is_default": "0",
            "created_by": user,
            "ctime": now,
            "mtime": now,
        }
        try:
            insert_result = labels_collection.data.insert(json.dumps(new_record))
            # Splunk echoes the inserted ``_key`` back; we already
            # know it (deterministic) but cross-check for safety.
            returned_key = (
                insert_result.get("_key")
                if isinstance(insert_result, dict)
                else None
            )
            new_key = returned_key or deterministic_key
            new_record["_key"] = new_key
            resolved_keys.append(new_key)
            name_to_key[lower] = new_key  # update index in case the same name appears later
            created_records.append(new_record)

            # Audit the auto-create separately from the assignment
            # — mirrors the explicit create_label endpoint so the
            # audit timeline shows exactly when each label entered
            # the catalog and via which path. Only the WINNER of a
            # concurrent race emits this event (the loser falls into
            # the except branch below and reuses the existing key
            # without re-auditing).
            try:
                trackme_audit_event(
                    audit_token,
                    audit_uri,
                    tenant_id,
                    user,
                    "success",
                    "create label",
                    display_name,
                    "labels",
                    new_record,
                    "Label auto-created during assign_labels",
                    str(update_comment),
                )
            except Exception as audit_e:
                # Non-fatal — the label was created; we just couldn't
                # log the audit event. Log locally so operators can
                # reconcile if needed.
                logger.warning(
                    f'tenant_id="{tenant_id}", auto-created label "{display_name}" '
                    f'but audit event failed: {audit_e}'
                )
        except Exception as e:
            # Two real cases land here:
            #   1. ``_key`` collision — another caller just won the
            #      race and inserted the same deterministic key. The
            #      existing record is the one we want to use.
            #   2. Genuine backend error (KV unavailable, etc.) —
            #      no record exists at the deterministic key and we
            #      cannot proceed.
            # Distinguish via a direct ``query_by_id`` against the
            # deterministic key: it's an O(1) lookup (vs. the O(N)
            # scan the previous code did) and unambiguous about which
            # case we're in.
            try:
                existing = labels_collection.data.query_by_id(deterministic_key)
            except Exception:
                existing = None
            if existing:
                resolved_keys.append(deterministic_key)
                name_to_key[lower] = deterministic_key
                # Do NOT append to ``created_records`` — the other
                # caller is the one that actually created it; from
                # this caller's perspective the label was already
                # there at the time of assignment.
            else:
                errors.append({"name": display_name, "reason": f"create_failed: {e}"})

    return (resolved_keys, created_records, errors)


class TrackMeHandlerLabelsWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerLabelsWrite_v2, self).__init__(command_line, command_arg, logger)

    def get_resource_group_desc_labels(self, request_info, **kwargs):
        response = {
            "resource_group_name": "labels",
            "resource_group_desc": "Labels allow users to tag entities with colored badges for lifecycle tracking (write operations)",
        }

        return {"payload": response, "status": 200}

    def post_create_label(self, request_info, **kwargs):

        describe = False
        tenant_id = None
        label_name = None
        label_color = None
        update_comment = "API update"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict.get("tenant_id", None)
                if tenant_id is None:
                    error_msg = f'tenant_id="{tenant_id}", tenant_id is required'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                label_name = resp_dict.get("label_name", None)
                if label_name is None or str(label_name).strip() == "":
                    error_msg = f'tenant_id="{tenant_id}", label_name is required and cannot be empty'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                label_color = resp_dict.get("label_color", None)
                if label_color is None or str(label_color).strip() == "":
                    error_msg = f'tenant_id="{tenant_id}", label_color is required and cannot be empty'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                update_comment = resp_dict.get("update_comment") or "API update"

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint creates a new label definition. It requires a POST call with the following information:",
                "resource_desc": "Create a label definition",
                "resource_spl_example": '| trackme url="/services/trackme/v2/labels/write/create_label" mode="post" body="{\'tenant_id\': \'mytenant\', \'label_name\': \'blocked\', \'label_color\': \'#dc4e41\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "label_name": "The label name (must be unique per tenant, case-insensitive)",
                        "label_color": "The label hex color (e.g. #dc4e41)",
                        "label_description": "(optional) A description of the label",
                        "label_order": "(optional) Sort order integer, defaults to 999",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        label_name = str(label_name).strip()
        label_color = str(label_color).strip()
        label_description = str(resp_dict.get("label_description", "")).strip()
        label_order_raw = str(resp_dict.get("label_order", "999")).strip()
        try:
            label_order = str(int(label_order_raw))
        except (ValueError, TypeError):
            label_order = "999"
        created_by = request_info.user

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        collection_name = f"kv_trackme_labels_tenant_{tenant_id}"

        try:
            collection = service.kvstore[collection_name]

            # Check name uniqueness (case-insensitive)
            existing = list(collection.data.query())
            for label in existing:
                if label.get("label_name", "").lower() == label_name.lower():
                    error_msg = f'tenant_id="{tenant_id}", label_name="{label_name}" already exists (case-insensitive match)'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 400}

            now = time.time()
            label_record = {
                "label_name": label_name,
                "label_color": label_color,
                "label_description": label_description,
                "label_order": label_order,
                "is_default": "0",
                "created_by": created_by,
                "ctime": now,
                "mtime": now,
            }

            result = collection.data.insert(json.dumps(label_record))
            label_record["_key"] = result["_key"]

            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                created_by,
                "success",
                "create label",
                label_name,
                "labels",
                label_record,
                "Label created successfully",
                str(update_comment),
            )

            return {
                "payload": {"action": "success", "result": "Label created successfully", "label": label_record},
                "status": 200,
            }

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", label_name="{label_name}", failed to create label, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

    def post_update_label(self, request_info, **kwargs):

        describe = False
        tenant_id = None
        label_key = None
        update_comment = "API update"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict.get("tenant_id", None)
                if tenant_id is None:
                    error_msg = f'tenant_id="{tenant_id}", tenant_id is required'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                label_key = resp_dict.get("label_key", None)
                if label_key is None:
                    error_msg = f'tenant_id="{tenant_id}", label_key is required'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                update_comment = resp_dict.get("update_comment") or "API update"

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint updates a label definition. It requires a POST call with the following information:",
                "resource_desc": "Update a label definition (partial update)",
                "resource_spl_example": '| trackme url="/services/trackme/v2/labels/write/update_label" mode="post" body="{\'tenant_id\': \'mytenant\', \'label_key\': \'abc123\', \'label_color\': \'#ff0000\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "label_key": "The _key of the label to update",
                        "label_name": "(optional) New label name",
                        "label_color": "(optional) New hex color",
                        "label_description": "(optional) New description",
                        "label_order": "(optional) New sort order",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        user = request_info.user
        splunkd_port = request_info.server_rest_port

        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        collection_name = f"kv_trackme_labels_tenant_{tenant_id}"

        try:
            collection = service.kvstore[collection_name]

            # Get existing record
            try:
                existing_record = collection.data.query_by_id(label_key)
            except Exception:
                error_msg = f'tenant_id="{tenant_id}", label_key="{label_key}" not found'
                logger.error(error_msg)
                return {"payload": {"action": "failure", "result": error_msg}, "status": 404}

            # Check name uniqueness if name is being changed
            new_name = resp_dict.get("label_name", None)
            if new_name is not None:
                new_name = str(new_name).strip()
                if new_name.lower() != existing_record.get("label_name", "").lower():
                    all_labels = list(collection.data.query())
                    for label in all_labels:
                        if label.get("_key") != label_key and label.get("label_name", "").lower() == new_name.lower():
                            error_msg = f'tenant_id="{tenant_id}", label_name="{new_name}" already exists'
                            logger.error(error_msg)
                            return {"payload": {"action": "failure", "result": error_msg}, "status": 400}
                existing_record["label_name"] = new_name

            # Apply partial updates
            if resp_dict.get("label_color") is not None:
                existing_record["label_color"] = str(resp_dict["label_color"]).strip()
            if resp_dict.get("label_description") is not None:
                existing_record["label_description"] = str(resp_dict["label_description"]).strip()
            if resp_dict.get("label_order") is not None:
                try:
                    existing_record["label_order"] = str(int(str(resp_dict["label_order"]).strip()))
                except (ValueError, TypeError):
                    existing_record["label_order"] = "999"

            existing_record["mtime"] = time.time()

            # Update
            collection.data.update(label_key, json.dumps(existing_record))

            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                user,
                "success",
                "update label",
                existing_record.get("label_name", label_key),
                "labels",
                existing_record,
                "Label updated successfully",
                str(update_comment),
            )

            return {
                "payload": {"action": "success", "result": "Label updated successfully", "label": existing_record},
                "status": 200,
            }

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", label_key="{label_key}", failed to update label, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

    def post_delete_label(self, request_info, **kwargs):

        describe = False
        tenant_id = None
        label_key = None
        update_comment = "API update"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict.get("tenant_id", None)
                if tenant_id is None:
                    error_msg = f'tenant_id="{tenant_id}", tenant_id is required'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                label_key = resp_dict.get("label_key", None)
                if label_key is None:
                    error_msg = f'tenant_id="{tenant_id}", label_key is required'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                update_comment = resp_dict.get("update_comment") or "API update"

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes a label definition and removes it from all entity assignments (cascade). It requires a POST call with the following information:",
                "resource_desc": "Delete a label definition (with cascade removal from assignments)",
                "resource_spl_example": '| trackme url="/services/trackme/v2/labels/write/delete_label" mode="post" body="{\'tenant_id\': \'mytenant\', \'label_key\': \'abc123\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "label_key": "The _key of the label to delete",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        user = request_info.user
        splunkd_port = request_info.server_rest_port

        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        labels_collection_name = f"kv_trackme_labels_tenant_{tenant_id}"
        assignments_collection_name = f"kv_trackme_label_assignments_tenant_{tenant_id}"

        try:
            labels_collection = service.kvstore[labels_collection_name]
            assignments_collection = service.kvstore[assignments_collection_name]

            # Get label name for audit before deletion
            label_name = label_key
            try:
                label_record = labels_collection.data.query_by_id(label_key)
                label_name = label_record.get("label_name", label_key)
            except Exception:
                pass

            # Delete the label definition
            labels_collection.data.delete(json.dumps({"_key": label_key}))

            # Cascade: remove label_key from all assignment records
            cascade_count = 0
            cascaded_entities = []
            try:
                all_assignments = list(assignments_collection.data.query())
                for assignment in all_assignments:
                    previous_label_ids = json.loads(assignment.get("label_ids", "[]"))
                    if label_key in previous_label_ids:
                        new_label_ids = [lid for lid in previous_label_ids if lid != label_key]
                        if new_label_ids:
                            assignment["label_ids"] = json.dumps(new_label_ids)
                            assignment["mtime"] = time.time()
                            assignments_collection.data.update(assignment["_key"], json.dumps(assignment))
                        else:
                            # No labels left, remove the assignment record
                            assignments_collection.data.delete(json.dumps({"_key": assignment["_key"]}))
                        cascade_count += 1
                        cascaded_entities.append({
                            "object_id": assignment.get("object_id"),
                            "component": assignment.get("component"),
                            "previous_label_ids": previous_label_ids,
                            "new_label_ids": new_label_ids,
                        })
            except Exception as cascade_e:
                logger.warning(f'tenant_id="{tenant_id}", cascade removal partial failure: {str(cascade_e)}')

            # Emit per-entity audit events so the cascaded removal is visible in
            # each affected entity's "Audit changes" tab (filters on
            # object_category=splk-<component>).
            for entry in cascaded_entities:
                entity_component = entry.get("component")
                entity_object_id = entry.get("object_id")
                if not entity_component or not entity_object_id:
                    continue
                try:
                    entity_object_name = trackme_resolve_entity_object_name(
                        service, entity_component, tenant_id, entity_object_id
                    )
                    previous_names = _resolve_label_names(labels_collection, entry["previous_label_ids"])
                    # labels_collection no longer contains the deleted label, so
                    # resolve it manually from the name we captured earlier.
                    previous_names_patched = [
                        label_name if lid == label_key else name
                        for lid, name in zip(entry["previous_label_ids"], previous_names)
                    ]
                    new_names = _resolve_label_names(labels_collection, entry["new_label_ids"])
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        user,
                        "success",
                        "remove label from object",
                        entity_object_name,
                        f"splk-{entity_component}",
                        {
                            "field": "labels",
                            "reason": "cascade: label deleted",
                            "removed_label": label_name,
                            "removed_label_id": label_key,
                            "old_value": previous_names_patched,
                            "new_value": new_names,
                            "old_label_ids": entry["previous_label_ids"],
                            "new_label_ids": entry["new_label_ids"],
                        },
                        "Label removed from entity successfully (cascade from label deletion)",
                        f"{update_comment} (cascade)",
                        object_id=entity_object_id,
                    )
                except Exception as audit_e:
                    logger.warning(
                        f'tenant_id="{tenant_id}", cascade audit skipped for '
                        f'entity_object_id="{entity_object_id}", component="{entity_component}": {str(audit_e)}'
                    )

            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                user,
                "success",
                "delete label",
                label_name,
                "labels",
                {"label_key": label_key, "cascade_assignments_updated": cascade_count},
                f"Label deleted successfully, {cascade_count} assignment(s) updated",
                str(update_comment),
            )

            return {
                "payload": {
                    "action": "success",
                    "result": f"Label deleted successfully, {cascade_count} assignment(s) updated",
                },
                "status": 200,
            }

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", label_key="{label_key}", failed to delete label, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

    def post_assign_labels(self, request_info, **kwargs):

        describe = False
        tenant_id = None
        object_id = None
        component = None
        label_ids = None
        label_names = None
        update_comment = "API update"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict.get("tenant_id", None)
                if tenant_id is None:
                    error_msg = f'tenant_id="{tenant_id}", tenant_id is required'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                object_id = resp_dict.get("object_id", None)
                if object_id is None:
                    error_msg = f'tenant_id="{tenant_id}", object_id is required'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                component = resp_dict.get("component", None)
                if component is None:
                    error_msg = f'tenant_id="{tenant_id}", component is required'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                # ``label_ids`` and ``label_names`` are both optional
                # individually but at least one must be provided.
                # ``label_names`` is the AI-Assistant / Concierge friendly
                # path: callers pass human-readable names and the server
                # resolves them to ``_key`` values, auto-creating any
                # name that isn't yet in the catalog.  ``label_ids``
                # remains the canonical UI path (existing UI code is
                # unchanged).  Passing both is allowed; the resolved
                # results are merged and deduped.
                label_ids = resp_dict.get("label_ids", None)
                label_names = resp_dict.get("label_names", None)
                if label_ids is None and label_names is None:
                    error_msg = (
                        f'tenant_id="{tenant_id}", at least one of '
                        f'``label_ids`` (JSON array of label _key values) '
                        f'or ``label_names`` (JSON array of label names — '
                        f'unknown names are auto-created with default '
                        f'colour) is required'
                    )
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                update_comment = resp_dict.get("update_comment") or "API update"

        else:
            describe = True

        if describe:
            response = {
                "describe": (
                    "This endpoint assigns labels to an entity. It accepts label "
                    "_key values (``label_ids``) and/or label names (``label_names`` — "
                    "names not in the catalog are auto-created with a neutral grey "
                    "default colour). Pass at least one of the two; both can be "
                    "combined and the resolved set is deduplicated. The full set "
                    "REPLACES the entity's current assignments — pass an empty "
                    "``label_ids`` to clear all labels."
                ),
                "resource_desc": "Assign labels to an entity (replaces current assignments). Accepts label _key values and/or label names; unknown names are auto-created.",
                "resource_spl_example": '| trackme url="/services/trackme/v2/labels/write/assign_labels" mode="post" body="{\'tenant_id\': \'mytenant\', \'object_id\': \'myentity\', \'component\': \'dsm\', \'label_names\': [\'business\']}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_id": "The object_id (entity keyid)",
                        "component": "The component type (dsm, dhm, mhm, flx, fqm, wlk)",
                        "label_ids": "OPTIONAL (required if label_names not provided). JSON array of label _key values to assign — typically obtained from ``/trackme/v2/labels/get_labels``. Use this path when you already have the catalog _key.",
                        "label_names": "OPTIONAL (required if label_ids not provided). JSON array of human-readable label names — case-insensitive match against the tenant's catalog. Names not yet in the catalog are auto-created with a neutral grey colour and a placeholder description (caller can rename / recolour later via ``post_update_label``). This is the AI-Assistant / Concierge friendly path: the LLM can pass natural-language names without a separate name→_key resolution round-trip.",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        user = request_info.user
        splunkd_port = request_info.server_rest_port

        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Parse label_ids if string (JSON-encoded array) — backwards
        # compatible with callers that JSON-stringify the field.
        if isinstance(label_ids, str):
            try:
                label_ids = json.loads(label_ids)
            except Exception:
                error_msg = f'tenant_id="{tenant_id}", label_ids must be a valid JSON array'
                logger.error(error_msg)
                return {"payload": {"action": "failure", "result": error_msg}, "status": 400}

        # Same forgiveness for label_names — Concierge body templates may
        # round-trip JSON twice depending on how the LLM emits the body.
        if isinstance(label_names, str):
            try:
                label_names = json.loads(label_names)
            except Exception:
                error_msg = f'tenant_id="{tenant_id}", label_names must be a valid JSON array'
                logger.error(error_msg)
                return {"payload": {"action": "failure", "result": error_msg}, "status": 400}

        # Defensive: tolerate ``None`` (means "this field wasn't passed").
        if label_ids is None:
            label_ids = []
        if label_names is None:
            label_names = []

        # Hard type check — both fields MUST be lists by this point.
        # Bugbot caught a destructive failure mode on PR #1510 cycle 1
        # (Medium): if the LLM double-encodes ``label_names`` (e.g.
        # emits ``"label_names": "\"business\""``), the
        # ``json.loads()`` above unwraps to a Python *string*, not a
        # list.  Without this guard the downstream resolver would
        # iterate the string character-by-character and auto-create a
        # junk single-character label per character — a real
        # destructive side effect on the catalog (and the audit
        # trail).  ``label_ids`` doesn't have the same blast radius
        # (its validation rejects each character harmlessly), but the
        # type check is uniform on principle.
        if not isinstance(label_ids, list):
            error_msg = (
                f'tenant_id="{tenant_id}", label_ids must be a JSON '
                f'array of label _key values, got '
                f'{type(label_ids).__name__}'
            )
            logger.error(error_msg)
            return {"payload": {"action": "failure", "result": error_msg}, "status": 400}
        if not isinstance(label_names, list):
            error_msg = (
                f'tenant_id="{tenant_id}", label_names must be a JSON '
                f'array of label name strings, got '
                f'{type(label_names).__name__}'
            )
            logger.error(error_msg)
            return {"payload": {"action": "failure", "result": error_msg}, "status": 400}

        labels_collection_name = f"kv_trackme_labels_tenant_{tenant_id}"
        assignments_collection_name = f"kv_trackme_label_assignments_tenant_{tenant_id}"

        # Track auto-created labels so the response can surface them
        # back to the caller (the Concierge UI displays them so the
        # user knows the catalog grew).
        auto_created_labels = []

        try:
            labels_collection = service.kvstore[labels_collection_name]
            assignments_collection = service.kvstore[assignments_collection_name]

            # Resolve label_names → _key values, auto-creating missing
            # names. Done BEFORE the existing label_ids validation so
            # that a request mixing names + IDs gets a single coherent
            # validation pass.
            if label_names:
                resolved_keys, created_records, name_errors = _resolve_or_create_labels_by_name(
                    labels_collection,
                    label_names,
                    request_info,
                    tenant_id,
                    request_info.server_rest_uri,
                    request_info.system_authtoken,
                    update_comment,
                )
                if name_errors:
                    # Hard failure on any name we couldn't resolve or
                    # create — partial success would leave the entity
                    # in a state the caller didn't ask for.
                    error_msg = (
                        f'tenant_id="{tenant_id}", failed to resolve / create '
                        f'label name(s): {name_errors}'
                    )
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}
                auto_created_labels = created_records
                # Merge resolved keys into label_ids; dedupe while
                # preserving the caller-provided order (existing IDs
                # first, newly-resolved names after).
                if resolved_keys:
                    seen = set(label_ids)
                    for k in resolved_keys:
                        if k not in seen:
                            label_ids.append(k)
                            seen.add(k)

            # Validate all label_ids exist (after name resolution —
            # auto-created keys are guaranteed to exist, so this only
            # catches caller-supplied stale / typoed IDs).
            if label_ids:
                existing_labels = {l["_key"] for l in labels_collection.data.query()}
                invalid_ids = [lid for lid in label_ids if lid not in existing_labels]
                if invalid_ids:
                    error_msg = f'tenant_id="{tenant_id}", invalid label_ids: {invalid_ids}'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 400}

            # Deterministic key for upsert
            assignment_key = f"{component}:{object_id}"
            now = time.time()

            # Capture previous label_ids for audit diff
            previous_label_ids = []
            try:
                existing_assignment = assignments_collection.data.query_by_id(assignment_key)
                if existing_assignment:
                    previous_label_ids = json.loads(existing_assignment.get("label_ids", "[]"))
            except Exception:
                previous_label_ids = []

            if label_ids:
                assignment_record = {
                    "_key": assignment_key,
                    "object_id": object_id,
                    "component": component,
                    "label_ids": json.dumps(label_ids),
                    "updated_by": user,
                    "mtime": now,
                }

                # Upsert: try update first, then insert
                try:
                    assignments_collection.data.update(assignment_key, json.dumps(assignment_record))
                except Exception:
                    assignments_collection.data.insert(json.dumps(assignment_record))
            else:
                # Empty label_ids means remove the assignment
                try:
                    assignments_collection.data.delete(json.dumps({"_key": assignment_key}))
                except Exception:
                    pass  # Already doesn't exist

            # Resolve labels and patch shadow record (non-blocking)
            # Labels are enriched at read-time by dynamic_labels_lookup, but shadow
            # records cache the enriched output, so we must patch them immediately.
            #
            # NOTE: this local list was previously called ``label_names``
            # — same name as the request-body parameter.  Renamed to
            # ``resolved_label_names`` on PR #1510 cycle 1 (Bugbot
            # Low) to avoid silently overwriting the caller's input;
            # a future change adding label-name-aware code below this
            # block would otherwise see an empty list rather than the
            # original request.  The two concepts are distinct: the
            # request-body parameter (untrusted, may contain
            # auto-create candidates) vs. the post-write display
            # names resolved from the catalog (trusted, used for
            # audit + shadow patching).
            resolved_labels = []
            resolved_label_names = []
            if label_ids:
                for lid in label_ids:
                    try:
                        label_def = labels_collection.data.query_by_id(lid)
                        if label_def:
                            name = label_def.get("label_name", "")
                            resolved_labels.append({
                                "label_id": lid,
                                "label_name": name,
                                "label_color": label_def.get("label_color", "#9e9e9e"),
                                "label_description": label_def.get("label_description", ""),
                            })
                            if name:
                                resolved_label_names.append(name)
                    except Exception:
                        pass

            labels_list = sorted(resolved_label_names)

            try:
                vtenant_conf = trackme_vtenant_account_from_service(service, tenant_id)
                shadow_enabled = int(vtenant_conf.get("shadow_enabled", 0))
            except Exception:
                shadow_enabled = None

            def _patch_shadow():
                try:
                    service_system = client.connect(
                        token=request_info.system_authtoken,
                        owner="nobody",
                        app="trackme",
                        port=splunkd_port,
                        timeout=120,
                    )
                    patch_shadow_records(
                        service_system,
                        tenant_id,
                        component,
                        [{"_key": object_id}],
                        {"labels_objects": resolved_labels, "labels": labels_list},
                        shadow_enabled=shadow_enabled,
                    )
                except Exception as e:
                    logger.debug(
                        f'Shadow patch skipped after label assignment: {e}, '
                        f'component="{component}", tenant_id="{tenant_id}", object_id="{object_id}"'
                    )

            shadow_thread = threading.Thread(target=_patch_shadow, daemon=True)
            shadow_thread.start()

            # Audit as an entity-level change so the event is visible in the
            # per-entity "Audit changes" tab (filters on object_category=splk-<component>).
            # Use _resolve_label_names so old and new sides share the same
            # resolution semantics and preserve index alignment with their id lists.
            object_name = trackme_resolve_entity_object_name(service, component, tenant_id, object_id)
            previous_label_names = _resolve_label_names(labels_collection, previous_label_ids)
            new_label_names = _resolve_label_names(labels_collection, label_ids)
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                user,
                "success",
                "assign labels",
                object_name,
                f"splk-{component}",
                {
                    "field": "labels",
                    "old_value": previous_label_names,
                    "new_value": new_label_names,
                    "old_label_ids": previous_label_ids,
                    "new_label_ids": label_ids,
                },
                f"Labels assigned successfully ({len(label_ids)} label(s))",
                str(update_comment),
                object_id=object_id,
            )

            # Build a richer success payload so callers (notably the
            # Concierge UI consent card) can show whether any labels
            # were auto-created during this assignment — important
            # because auto-creation extends the catalog and the user
            # may want to recolour / rename the new labels afterwards.
            success_payload = {
                "action": "success",
                "result": f"Labels assigned successfully ({len(label_ids)} label(s))",
                "label_ids": label_ids,
            }
            if auto_created_labels:
                success_payload["auto_created_labels"] = [
                    {
                        "_key": lbl.get("_key"),
                        "label_name": lbl.get("label_name"),
                        "label_color": lbl.get("label_color"),
                        "label_description": lbl.get("label_description"),
                    }
                    for lbl in auto_created_labels
                ]
            return {
                "payload": success_payload,
                "status": 200,
            }

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", object_id="{object_id}", failed to assign labels, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

    def post_remove_label_from_object(self, request_info, **kwargs):

        describe = False
        tenant_id = None
        object_id = None
        component = None
        label_key = None
        update_comment = "API update"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict.get("tenant_id", None)
                if tenant_id is None:
                    error_msg = f'tenant_id="{tenant_id}", tenant_id is required'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                object_id = resp_dict.get("object_id", None)
                if object_id is None:
                    error_msg = f'tenant_id="{tenant_id}", object_id is required'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                component = resp_dict.get("component", None)
                if component is None:
                    error_msg = f'tenant_id="{tenant_id}", component is required'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                label_key = resp_dict.get("label_key", None)
                if label_key is None:
                    error_msg = f'tenant_id="{tenant_id}", label_key is required'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                update_comment = resp_dict.get("update_comment") or "API update"

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint removes a single label from an entity. It requires a POST call with the following information:",
                "resource_desc": "Remove a label from an entity",
                "resource_spl_example": '| trackme url="/services/trackme/v2/labels/write/remove_label_from_object" mode="post" body="{\'tenant_id\': \'mytenant\', \'object_id\': \'myentity\', \'component\': \'dsm\', \'label_key\': \'abc123\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_id": "The object_id (entity keyid)",
                        "component": "The component type (dsm, dhm, mhm, flx, fqm, wlk)",
                        "label_key": "The _key of the label to remove",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        user = request_info.user
        splunkd_port = request_info.server_rest_port

        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        labels_collection_name = f"kv_trackme_labels_tenant_{tenant_id}"
        assignments_collection_name = f"kv_trackme_label_assignments_tenant_{tenant_id}"

        try:
            labels_collection = service.kvstore[labels_collection_name]
            assignments_collection = service.kvstore[assignments_collection_name]

            assignment_key = f"{component}:{object_id}"

            try:
                assignment = assignments_collection.data.query_by_id(assignment_key)
            except Exception:
                return {
                    "payload": {"action": "success", "result": "No labels assigned to this entity"},
                    "status": 200,
                }

            previous_label_ids = json.loads(assignment.get("label_ids", "[]"))
            label_ids = list(previous_label_ids)
            if label_key in label_ids:
                label_ids.remove(label_key)

            if label_ids:
                assignment["label_ids"] = json.dumps(label_ids)
                assignment["mtime"] = time.time()
                assignment["updated_by"] = user
                assignments_collection.data.update(assignment_key, json.dumps(assignment))
            else:
                assignments_collection.data.delete(json.dumps({"_key": assignment_key}))

            # Audit as an entity-level change so the event is visible in the
            # per-entity "Audit changes" tab (filters on object_category=splk-<component>).
            object_name = trackme_resolve_entity_object_name(service, component, tenant_id, object_id)
            previous_label_names = _resolve_label_names(labels_collection, previous_label_ids)
            new_label_names = _resolve_label_names(labels_collection, label_ids)
            removed_label_name = _resolve_label_names(labels_collection, [label_key])[0]
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                user,
                "success",
                "remove label from object",
                object_name,
                f"splk-{component}",
                {
                    "field": "labels",
                    "removed_label": removed_label_name,
                    "removed_label_id": label_key,
                    "old_value": previous_label_names,
                    "new_value": new_label_names,
                    "old_label_ids": previous_label_ids,
                    "new_label_ids": label_ids,
                },
                "Label removed from entity successfully",
                str(update_comment),
                object_id=object_id,
            )

            return {
                "payload": {"action": "success", "result": "Label removed from entity successfully"},
                "status": 200,
            }

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", object_id="{object_id}", failed to remove label, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

    def post_seed_default_labels(self, request_info, **kwargs):

        describe = False
        tenant_id = None
        update_comment = "API update"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict.get("tenant_id", None)
                if tenant_id is None:
                    error_msg = f'tenant_id="{tenant_id}", tenant_id is required'
                    logger.error(error_msg)
                    return {"payload": {"action": "failure", "result": error_msg}, "status": 500}

                update_comment = resp_dict.get("update_comment") or "API update"

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint seeds default label definitions for a tenant if they don't already exist. It requires a POST call with the following information:",
                "resource_desc": "Seed default labels for a tenant",
                "resource_spl_example": '| trackme url="/services/trackme/v2/labels/write/seed_default_labels" mode="post" body="{\'tenant_id\': \'mytenant\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        user = request_info.user
        splunkd_port = request_info.server_rest_port

        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        collection_name = f"kv_trackme_labels_tenant_{tenant_id}"

        try:
            collection = service.kvstore[collection_name]

            # Get existing labels
            existing = list(collection.data.query())
            existing_names = {l.get("label_name", "").lower() for l in existing}

            created_count = 0
            now = time.time()

            for default_label in DEFAULT_LABELS:
                if default_label["label_name"].lower() not in existing_names:
                    label_record = {
                        "label_name": default_label["label_name"],
                        "label_color": default_label["label_color"],
                        "label_description": default_label["label_description"],
                        "label_order": default_label["label_order"],
                        "is_default": "1",
                        "created_by": "system",
                        "ctime": now,
                        "mtime": now,
                    }
                    collection.data.insert(json.dumps(label_record))
                    created_count += 1

            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                user,
                "success",
                "seed default labels",
                tenant_id,
                "labels",
                {"created_count": created_count},
                f"Default labels seeded successfully ({created_count} created)",
                str(update_comment),
            )

            return {
                "payload": {"action": "success", "result": f"Default labels seeded successfully ({created_count} created)"},
                "status": 200,
            }

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failed to seed default labels, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"action": "failure", "result": error_msg}, "status": 500}
