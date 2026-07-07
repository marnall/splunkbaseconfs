#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_notes.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Built-in libraries
import json
import os
import sys
import time

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger("trackme.rest.notes_power", "trackme_rest_api_notes_power.log")


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    trackme_audit_event,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_resolve_entity_object_name,
)

# import Splunk libs
import splunklib.client as client


_SUPPORTED_COMPONENTS = ("dsm", "dhm", "mhm", "flx", "fqm", "wlk")


def _normalize_component(component):
    """Return a lower-cased component name if it is one of the supported
    entity components, or None otherwise. Used to decide whether to scope the
    audit event under splk-<component> (visible in the per-entity Audit
    changes tab) or fall back to the legacy "notes" object_category.
    """
    if not component:
        return None
    c = str(component).strip().lower()
    if c in _SUPPORTED_COMPONENTS:
        return c
    return None


class TrackMeHandlerNotesWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerNotesWrite_v2, self).__init__(command_line, command_arg, logger)

    def get_resource_group_desc_notes(self, request_info, **kwargs):
        response = {
            "resource_group_name": "notes",
            "resource_group_desc": "Notes allow users to publish notes associated with entities (write operations)",
        }

        return {"payload": response, "status": 200}

    def post_create_note(self, request_info, **kwargs):

        describe = False
        tenant_id = None
        object_id = None
        note = None
        component = None
        update_comment = "API update"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                # tenant_id is required
                tenant_id = resp_dict.get("tenant_id", None)
                if tenant_id is None:
                    error_msg = f'tenant_id="{tenant_id}", tenant_id is required'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

                # object_id is required
                object_id = resp_dict.get("object_id", None)
                if object_id is None:
                    error_msg = f'tenant_id="{tenant_id}", object_id="{object_id}", object_id is required'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

                # note is required
                note = resp_dict.get("note", None)
                if note is None or note.strip() == "":
                    error_msg = f'tenant_id="{tenant_id}", object_id="{object_id}", note is required and cannot be empty'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

                # component is optional — when provided, the audit event is
                # scoped under object_category=splk-<component> so it is
                # visible in the per-entity Audit changes tab. Older callers
                # that omit it keep the legacy global "notes" audit scope.
                component = _normalize_component(resp_dict.get("component"))

                update_comment = resp_dict.get("update_comment") or "API update"

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint creates a new note for a given object_id. It requires a POST call with the following information:",
                "resource_desc": "Create a note for an entity",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/notes/write/create_note\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'object_id': 'netscreen:netscreen:firewall', 'component': 'dsm', 'note': 'This is a note'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_id": "The object_id (entity keyid) to create a note for",
                        "component": "Optional component type (dsm, dhm, mhm, flx, fqm, wlk). When provided, the audit event is scoped under object_category=splk-<component> so it appears in the per-entity Audit changes tab.",
                        "note": "The note content (supports Markdown format)",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get current user from session
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

        collection_name = f"kv_trackme_notes_tenant_{tenant_id}"
        
        try:
            collection = service.kvstore[collection_name]
            
            # Create note record
            note_record = {
                "object_id": object_id,
                "note": note.strip(),
                "created_by": created_by,
                "mtime": time.time(),
            }
            
            # Insert the note
            result = collection.data.insert(json.dumps(note_record))

            # Get the created record with _key
            note_record["_key"] = result["_key"]

            # Audit event — scope under splk-<component> when we know the
            # component so the event is visible in the per-entity Audit
            # changes tab. Otherwise fall back to the legacy global scope.
            if component:
                object_name = trackme_resolve_entity_object_name(service, component, tenant_id, object_id)
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    created_by,
                    "success",
                    "create note",
                    object_name,
                    f"splk-{component}",
                    note_record,
                    "Note created successfully",
                    str(update_comment),
                    object_id=object_id,
                )
            else:
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    created_by,
                    "success",
                    "create note",
                    str(object_id),
                    "notes",
                    note_record,
                    "Note created successfully",
                    str(update_comment),
                )

            return {
                "payload": {"action": "success", "result": "Note created successfully", "note": note_record},
                "status": 200,
            }

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", object_id="{object_id}", failed to create note in KVstore collection, exception="{str(e)}"'
            logger.error(error_msg)

            # Audit event for failure — same entity-scoping logic as success.
            try:
                if component:
                    object_name = trackme_resolve_entity_object_name(service, component, tenant_id, object_id)
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        created_by,
                        "failure",
                        "create note",
                        object_name,
                        f"splk-{component}",
                        {"note": note[:100] if note else ""},  # Truncate for audit
                        f"Note creation failed: {str(e)}",
                        str(update_comment),
                        object_id=object_id,
                    )
                else:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        created_by,
                        "failure",
                        "create note",
                        str(object_id),
                        "notes",
                        {"note": note[:100] if note else ""},  # Truncate for audit
                        f"Note creation failed: {str(e)}",
                        str(update_comment),
                    )
            except Exception as audit_e:
                logger.error(f"Failed to create audit event: {str(audit_e)}")

            return {
                "payload": {"action": "failure", "result": error_msg},
                "status": 500,
            }

    def post_clone_note(self, request_info, **kwargs):

        describe = False
        tenant_id = None
        note = None
        target_object_ids = None
        component = None
        update_comment = "API update"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                # tenant_id is required
                tenant_id = resp_dict.get("tenant_id", None)
                if tenant_id is None:
                    error_msg = f'tenant_id="{tenant_id}", tenant_id is required'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

                # note content is required (must be a non-empty string; this
                # mirrors post_create_note's validation exactly so callers get
                # the same error semantics, and guarantees note.strip() later
                # in this method will not raise AttributeError).
                note = resp_dict.get("note", None)
                if not isinstance(note, str) or note.strip() == "":
                    error_msg = f'tenant_id="{tenant_id}", note is required and must be a non-empty string'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

                # target_object_ids is required (non-empty list of entity keyids)
                target_object_ids = resp_dict.get("target_object_ids", None)
                if not isinstance(target_object_ids, list) or len(target_object_ids) == 0:
                    error_msg = f'tenant_id="{tenant_id}", target_object_ids is required and must be a non-empty list'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

                # component is optional — when provided, a per-target entity
                # audit event is emitted (one per cloned entity) so each
                # target entity records the addition in its own Audit changes
                # tab. All clone targets are assumed to be within the same
                # component scope, which matches the frontend (cloneable
                # entities come from the current tenant+component view).
                component = _normalize_component(resp_dict.get("component"))

                update_comment = resp_dict.get("update_comment") or "API update"

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint clones a note (by content) to a list of target entities. It requires a POST call with the following information:",
                "resource_desc": "Clone a note to one or more entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/notes/write/clone_note\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'note': 'Cloned note content', 'target_object_ids': ['key1', 'key2'], 'component': 'dsm'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "note": "The note content to clone (supports Markdown format)",
                        "target_object_ids": "List of entity keyids (object_id values) to clone the note to",
                        "component": "Optional component type (dsm, dhm, mhm, flx, fqm, wlk) shared by all target entities. When provided, a per-target audit event is emitted under object_category=splk-<component> so each target entity records the addition in its own Audit changes tab.",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # De-duplicate targets while preserving order
        seen = set()
        unique_targets = []
        for oid in target_object_ids:
            if oid is None:
                continue
            s = str(oid)
            if s and s not in seen:
                seen.add(s)
                unique_targets.append(s)

        if not unique_targets:
            error_msg = f'tenant_id="{tenant_id}", target_object_ids contains no valid entries'
            logger.error(error_msg)
            return {
                "payload": {"action": "failure", "result": error_msg},
                "status": 500,
            }

        # Get current user from session
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

        collection_name = f"kv_trackme_notes_tenant_{tenant_id}"

        cloned = []
        failed = []

        try:
            collection = service.kvstore[collection_name]

            note_text = note.strip()

            for target_object_id in unique_targets:
                try:
                    note_record = {
                        "object_id": target_object_id,
                        "note": note_text,
                        "created_by": created_by,
                        "mtime": time.time(),
                    }
                    result = collection.data.insert(json.dumps(note_record))
                    note_record["_key"] = result["_key"]
                    cloned.append(note_record)
                except Exception as e:
                    logger.error(
                        f'tenant_id="{tenant_id}", target_object_id="{target_object_id}", failed to clone note, exception="{str(e)}"'
                    )
                    failed.append({"object_id": target_object_id, "error": str(e)})

            # Derive the outcome:
            #   - success: all targets cloned, none failed
            #   - partial: some cloned AND some failed
            #   - failure: nothing cloned (every target failed)
            if failed and not cloned:
                outcome = "failure"
            elif failed:
                outcome = "partial"
            else:
                outcome = "success"

            # Audit event — when component is provided, emit one per-target
            # audit so each affected entity records the addition in its own
            # per-entity Audit changes tab. Also keep the summary audit under
            # the legacy "notes" scope for backward compatibility with any
            # dashboards that aggregate clone operations across tenants.
            if component:
                cloned_ids = {c.get("object_id") for c in cloned}
                failed_ids = {f.get("object_id") for f in failed}
                for target_object_id in unique_targets:
                    if target_object_id in cloned_ids:
                        per_target_action = "success"
                        per_target_result = "Note cloned to entity successfully"
                    elif target_object_id in failed_ids:
                        per_target_action = "failure"
                        per_target_result = "Note clone to entity failed"
                    else:
                        continue
                    try:
                        object_name = trackme_resolve_entity_object_name(
                            service, component, tenant_id, target_object_id
                        )
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            created_by,
                            per_target_action,
                            "clone note",
                            object_name,
                            f"splk-{component}",
                            {
                                "note": note_text[:100],
                                "source": "clone_note",
                            },
                            per_target_result,
                            f"{update_comment} (clone)",
                            object_id=target_object_id,
                        )
                    except Exception as audit_e:
                        logger.error(
                            f'Failed to create per-target audit event, '
                            f'target_object_id="{target_object_id}": {str(audit_e)}'
                        )

            try:
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    created_by,
                    outcome,
                    "clone note",
                    ",".join(unique_targets),
                    "notes",
                    {
                        "targets": unique_targets,
                        "cloned_count": len(cloned),
                        "failed_count": len(failed),
                    },
                    f"Note cloned to {len(cloned)} entities, {len(failed)} failed",
                    str(update_comment),
                )
            except Exception as audit_e:
                logger.error(f"Failed to create audit event: {str(audit_e)}")

            # Always return 200 so the structured payload (cloned/failed
            # arrays, per-target errors) reaches the frontend. The frontend
            # must distinguish the outcome via the `action` field:
            # "success", "partial" or "failure".
            return {
                "payload": {
                    "action": outcome,
                    "result": f"Cloned note to {len(cloned)} entities, {len(failed)} failed",
                    "cloned": cloned,
                    "failed": failed,
                },
                "status": 200,
            }

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failed to clone note in KVstore collection, exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {"action": "failure", "result": error_msg},
                "status": 500,
            }

    def post_delete_note(self, request_info, **kwargs):

        describe = False
        tenant_id = None
        note_key = None
        component = None
        update_comment = "API update"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                # tenant_id is required
                tenant_id = resp_dict.get("tenant_id", None)
                if tenant_id is None:
                    error_msg = f'tenant_id="{tenant_id}", tenant_id is required'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

                # note_key is required
                note_key = resp_dict.get("note_key", None)
                if note_key is None:
                    error_msg = f'tenant_id="{tenant_id}", note_key="{note_key}", note_key is required'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

                # component is optional — when provided, the audit event is
                # scoped under object_category=splk-<component> so it appears
                # in the per-entity Audit changes tab.
                component = _normalize_component(resp_dict.get("component"))

                update_comment = resp_dict.get("update_comment") or "API update"

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes a note by its _key. It requires a POST call with the following information:",
                "resource_desc": "Delete a note",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/notes/write/delete_note\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'note_key': 'abc123', 'component': 'dsm'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "note_key": "The _key of the note to delete",
                        "component": "Optional component type (dsm, dhm, mhm, flx, fqm, wlk). When provided, the audit event is scoped under object_category=splk-<component> so it appears in the per-entity Audit changes tab.",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get current user from session
        user = request_info.user

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

        collection_name = f"kv_trackme_notes_tenant_{tenant_id}"
        
        try:
            collection = service.kvstore[collection_name]
            
            # First, get the note to retrieve object_id for audit
            try:
                note_record = collection.data.query_by_id(note_key)
                object_id = note_record.get("object_id", "unknown")
            except Exception as e:
                object_id = "unknown"
                logger.warning(f'Could not retrieve note before deletion, note_key="{note_key}", exception="{str(e)}"')

            # Delete the note - KVstore delete requires JSON format with _key
            collection.data.delete(json.dumps({"_key": note_key}))

            # Audit event — scope under splk-<component> when we know the
            # component so the event is visible in the per-entity Audit
            # changes tab. Skip entity-scoping when object_id could not be
            # resolved, since there is no real entity to attach the audit to.
            if component and object_id and object_id != "unknown":
                object_name = trackme_resolve_entity_object_name(service, component, tenant_id, object_id)
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    user,
                    "success",
                    "delete note",
                    object_name,
                    f"splk-{component}",
                    {"note_key": note_key},
                    "Note deleted successfully",
                    str(update_comment),
                    object_id=object_id,
                )
            else:
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    user,
                    "success",
                    "delete note",
                    str(object_id),
                    "notes",
                    {"note_key": note_key},
                    "Note deleted successfully",
                    str(update_comment),
                )

            return {
                "payload": {"action": "success", "result": "Note deleted successfully"},
                "status": 200,
            }

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", note_key="{note_key}", failed to delete note from KVstore collection, exception="{str(e)}"'
            logger.error(error_msg)

            # Audit event for failure — same entity-scoping logic as success.
            try:
                resolved_object_id = object_id if 'object_id' in locals() else "unknown"
                if component and resolved_object_id and resolved_object_id != "unknown":
                    object_name = trackme_resolve_entity_object_name(service, component, tenant_id, resolved_object_id)
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        user,
                        "failure",
                        "delete note",
                        object_name,
                        f"splk-{component}",
                        {"note_key": note_key},
                        f"Note deletion failed: {str(e)}",
                        str(update_comment),
                        object_id=resolved_object_id,
                    )
                else:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        user,
                        "failure",
                        "delete note",
                        str(resolved_object_id),
                        "notes",
                        {"note_key": note_key},
                        f"Note deletion failed: {str(e)}",
                        str(update_comment),
                    )
            except Exception as audit_e:
                logger.error(f"Failed to create audit event: {str(audit_e)}")

            return {
                "payload": {"action": "failure", "result": error_msg},
                "status": 500,
            }

