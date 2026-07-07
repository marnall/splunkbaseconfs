#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_variable_delay_admin.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import os
import sys
import json
import time

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test  # noqa: F401

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_variable_delay_admin",
    "trackme_rest_api_splk_variable_delay_admin.log",
)


# import rest handler
import trackme_rest_handler  # noqa: E402

# import trackme libs
from trackme_libs import (  # noqa: E402
    trackme_audit_event,
    trackme_getloglevel,
    trackme_parse_describe_flag,
)

# import Splunk libs
import splunklib.client as client  # noqa: E402


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

TEMPLATES_COLLECTION_FMT = "kv_trackme_common_variable_delay_templates_tenant_{tenant_id}"
VALID_COMPONENTS = ("dsm", "dhm")


def _normalize_component(component):
    """Accept 'dsm' / 'dhm' / 'splk-dsm' / 'splk-dhm' (any casing) and return
    'dsm' or 'dhm'.

    Order matters: lowercase BEFORE stripping the "splk-" prefix so that
    uppercase variants like "SPLK-DSM" or "Splk-dhm" get normalised
    correctly. The previous order ran replace on the raw string, which
    was case-sensitive and left uppercase inputs as "SPLK-DSM" →
    .lower() → "splk-dsm", failing the VALID_COMPONENTS check.
    """
    if not isinstance(component, str):
        return None
    comp = component.strip().lower().replace("splk-", "")
    if comp not in VALID_COMPONENTS:
        return None
    return comp


def _validate_template_payload(payload):
    """
    Shallow validation of a template record submitted from the UI.

    Returns (ok: bool, error_message: str | None, normalized: dict | None).
    Does not touch the KV store.
    """
    if not isinstance(payload, dict):
        return False, "template payload must be an object", None

    template_id = payload.get("template_id")
    if not isinstance(template_id, str) or not template_id.strip():
        return False, "template_id is required and must be a non-empty string", None

    label = payload.get("label", template_id)
    if not isinstance(label, str) or not label.strip():
        return False, "label is required and must be a non-empty string", None

    description = payload.get("description", "") or ""
    if not isinstance(description, str):
        return False, "description must be a string", None

    component = _normalize_component(payload.get("component"))
    if component is None:
        return False, f"component must be one of {VALID_COMPONENTS}", None

    raw_slots = payload.get("slots")
    if not isinstance(raw_slots, list) or len(raw_slots) == 0:
        return False, "slots must be a non-empty list", None

    validated_slots = []
    for idx, slot in enumerate(raw_slots):
        if not isinstance(slot, dict):
            return False, f"slots[{idx}] must be an object", None
        slot_name = slot.get("slot_name")
        if not isinstance(slot_name, str) or not slot_name.strip():
            return False, f"slots[{idx}].slot_name is required", None
        days = slot.get("days")
        # Must be a non-empty list of ints in [0, 6]. Note: `all(...)` on an
        # empty iterable returns True, so a plain membership check would
        # silently accept `days: []` — a slot with no days matches no day,
        # making the template useless. The frontend already rejects this;
        # enforce the same invariant here for direct API callers.
        if not isinstance(days, list):
            return False, f"slots[{idx}].days must be a list of integers 0-6", None
        if len(days) == 0:
            return False, f"slots[{idx}].days must not be empty", None
        if not all(isinstance(d, int) and 0 <= d <= 6 for d in days):
            return False, f"slots[{idx}].days must be a list of integers 0-6", None
        hours = slot.get("hours")
        if not isinstance(hours, list):
            return False, f"slots[{idx}].hours must be a list of integers 0-23", None
        if len(hours) == 0:
            return False, f"slots[{idx}].hours must not be empty", None
        if not all(isinstance(h, int) and 0 <= h <= 23 for h in hours):
            return False, f"slots[{idx}].hours must be a list of integers 0-23", None
        max_delay_allowed = slot.get("max_delay_allowed")
        try:
            max_delay_allowed_int = int(max_delay_allowed)
        except (TypeError, ValueError):
            return False, f"slots[{idx}].max_delay_allowed must be an integer", None
        if max_delay_allowed_int < 0:
            return False, f"slots[{idx}].max_delay_allowed must be >= 0", None
        validated_slots.append({
            "slot_name": slot_name.strip(),
            "days": sorted(set(days)),
            "hours": sorted(set(hours)),
            "max_delay_allowed": max_delay_allowed_int,
        })

    try:
        default_threshold = int(payload.get("default_threshold", 3600))
    except (TypeError, ValueError):
        return False, "default_threshold must be an integer", None
    if default_threshold < 0:
        return False, "default_threshold must be >= 0", None

    try:
        sort_order = int(payload.get("sort_order", 100))
    except (TypeError, ValueError):
        sort_order = 100

    normalized = {
        "template_id": template_id.strip(),
        "label": label.strip(),
        "description": description.strip(),
        "component": component,
        # slots and default_threshold are stored as JSON strings because the
        # KV Store accelerated_fields in collections_data.py are flat scalar
        # typed. This matches the existing pattern used elsewhere in TrackMe
        # (e.g. variable_delay_slots on the per-entity collection).
        "slots": json.dumps(validated_slots),
        "default_threshold": default_threshold,
        "sort_order": sort_order,
    }
    return True, None, normalized


# ---------------------------------------------------------------------------
# Handler class
# ---------------------------------------------------------------------------


class TrackMeHandlerSplkVariableDelayAdmin_v2(trackme_rest_handler.RESTHandler):
    """
    Admin-level REST handler for variable delay slot template management.

    Exposes three endpoints under /trackme/v2/splk_variable_delay/admin:
    - templates_save: upsert a template for a tenant + component
    - templates_reset: delete a single template by template_id
    - templates_reset_all: delete all custom templates for a tenant + component

    These endpoints do NOT mutate any per-entity variable delay config. They
    only manage the quick-template presets shown in the slot editor. Factory
    defaults remain in splunkui slotTemplates.ts and serve as the fallback
    when a tenant has no custom records — see issue #1056 for the full
    design rationale.
    """

    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkVariableDelayAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_variable_delay_admin(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_variable_delay/admin",
            "resource_group_desc": (
                "Admin endpoints for managing per-tenant variable delay slot template "
                "presets. These templates back the 'Quick templates' buttons in the "
                "variable delay editor (DSM/DHM) and the tenant creation wizard. "
                "Factory defaults ship with the app; admin customisations are "
                "stored in kv_trackme_common_variable_delay_templates_tenant_{tid} "
                "and override factory defaults per template_id."
            ),
        }
        return {"payload": response, "status": 200}

    # ------------------------------------------------------------------
    # POST /templates_save — upsert a template record
    # ------------------------------------------------------------------
    def post_templates_save(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_variable_delay/admin/templates_save" mode="post" body='{"tenant_id": "mytenant", "component": "dsm", "template": {...}}'
        """

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        describe = trackme_parse_describe_flag(request_info)

        if describe or resp_dict is None:
            response = {
                "describe": (
                    "Upsert a variable delay slot template record for a tenant + component. "
                    "Used by the 'Manage: Variable delay templates' admin modal to persist "
                    "custom template definitions that override (by matching template_id) "
                    "or extend the hardcoded factory defaults shipped in slotTemplates.ts."
                ),
                "resource_desc": "Create or update a variable delay template preset",
                "resource_spl_example": (
                    '| trackme url="/services/trackme/v2/splk_variable_delay/admin/templates_save" '
                    'mode="post" body=\'{"tenant_id":"mytenant","component":"dsm","template":'
                    '{"template_id":"business_hours","label":"Business hours vs. off-hours",'
                    '"slots":[...],"default_threshold":3600}}\''
                ),
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "MANDATORY — 'dsm' or 'dhm' (also accepts 'splk-dsm'/'splk-dhm')",
                        "template": "MANDATORY — template record (template_id, label, slots, default_threshold)",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        tenant_id = resp_dict.get("tenant_id")
        component = _normalize_component(resp_dict.get("component"))
        template_payload = resp_dict.get("template")
        update_comment = resp_dict.get("update_comment") or "API update"

        if not tenant_id:
            return {"payload": {"action": "failure", "response": "tenant_id is required"}, "status": 400}
        if component is None:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"component is required and must be one of {VALID_COMPONENTS}",
                },
                "status": 400,
            }
        # Ensure the component in the path matches (or sets) the component in the template body.
        if isinstance(template_payload, dict):
            template_payload.setdefault("component", component)

        ok, err, normalized = _validate_template_payload(template_payload)
        if not ok:
            return {"payload": {"action": "failure", "response": err}, "status": 400}
        if normalized["component"] != component:
            return {
                "payload": {
                    "action": "failure",
                    "response": "template.component does not match the top-level component",
                },
                "status": 400,
            }

        # set log level
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Connect as system so we can read/write the tenant collection
        # regardless of the caller's personal ACLs (the caller has already
        # been authenticated as a trackme_admin by the REST layer).
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        collection_name = TEMPLATES_COLLECTION_FMT.format(tenant_id=tenant_id)
        try:
            collection = service.kvstore[collection_name]
        except Exception as e:
            logger.error(
                f'post_templates_save: collection not found, tenant_id="{tenant_id}", '
                f'collection="{collection_name}", exception="{str(e)}"'
            )
            return {
                "payload": {
                    "action": "failure",
                    "response": f"Variable delay templates collection not found for tenant '{tenant_id}'",
                    "exception": str(e),
                },
                "status": 404,
            }

        now_epoch = time.time()
        username = request_info.user or "unknown"

        # Upsert strategy: query by (component, template_id) and either
        # insert a new record or update the existing one in place.
        query = {
            "component": normalized["component"],
            "template_id": normalized["template_id"],
        }
        try:
            existing = collection.data.query(query=json.dumps(query))
        except Exception as e:
            logger.error(
                f'post_templates_save: query failed, tenant_id="{tenant_id}", '
                f'query="{json.dumps(query)}", exception="{str(e)}"'
            )
            return {
                "payload": {"action": "failure", "response": "Failed to query existing templates", "exception": str(e)},
                "status": 500,
            }

        record = {
            "template_id": normalized["template_id"],
            "label": normalized["label"],
            "description": normalized["description"],
            "component": normalized["component"],
            "slots": normalized["slots"],
            "default_threshold": normalized["default_threshold"],
            "sort_order": normalized["sort_order"],
            "mtime": now_epoch,
            "author": username,
        }

        try:
            if existing and len(existing) > 0:
                existing_key = existing[0].get("_key")
                # preserve ctime of the original record
                record["ctime"] = existing[0].get("ctime", now_epoch)
                collection.data.update(existing_key, json.dumps(record))
                action_taken = "updated"
            else:
                record["ctime"] = now_epoch
                collection.data.insert(json.dumps(record))
                action_taken = "created"
        except Exception as e:
            logger.error(
                f'post_templates_save: upsert failed, tenant_id="{tenant_id}", '
                f'template_id="{normalized["template_id"]}", exception="{str(e)}"'
            )
            return {
                "payload": {"action": "failure", "response": "Failed to save template", "exception": str(e)},
                "status": 500,
            }

        logger.info(
            f'post_templates_save: action="{action_taken}", tenant_id="{tenant_id}", '
            f'component="{component}", template_id="{normalized["template_id"]}", author="{username}"'
        )

        # Audit
        try:
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                username,
                "success",
                f"variable delay template {action_taken}",
                str(normalized["template_id"]),
                f"splk-{component}",
                json.dumps(record, default=str),
                f'Variable delay template "{normalized["template_id"]}" was {action_taken} successfully',
                str(update_comment),
            )
        except Exception as audit_e:
            logger.warning(
                f'function=post_templates_save, tenant_id="{tenant_id}", '
                f'step="audit", exception="{str(audit_e)}"'
            )

        return {
            "payload": {
                "action": "success",
                "response": f"Template '{normalized['template_id']}' {action_taken}",
                "record": record,
            },
            "status": 200,
        }

    # ------------------------------------------------------------------
    # POST /templates_reset — delete a single custom template
    # ------------------------------------------------------------------
    def post_templates_reset(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_variable_delay/admin/templates_reset" mode="post" body='{"tenant_id": "mytenant", "component": "dsm", "template_id": "business_hours"}'
        """

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        describe = trackme_parse_describe_flag(request_info)

        if describe or resp_dict is None:
            response = {
                "describe": (
                    "Delete a single custom variable delay template for a tenant + component. "
                    "If the template_id also matches a hardcoded factory default, the UI will "
                    "transparently fall back to the factory version after the delete."
                ),
                "resource_desc": "Delete a custom variable delay template by template_id",
                "resource_spl_example": (
                    '| trackme url="/services/trackme/v2/splk_variable_delay/admin/templates_reset" '
                    'mode="post" body=\'{"tenant_id":"mytenant","component":"dsm","template_id":"business_hours"}\''
                ),
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "MANDATORY — 'dsm' or 'dhm'",
                        "template_id": "MANDATORY — template_id to delete",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        tenant_id = resp_dict.get("tenant_id")
        component = _normalize_component(resp_dict.get("component"))
        template_id = resp_dict.get("template_id")
        update_comment = resp_dict.get("update_comment") or "API update"

        if not tenant_id:
            return {"payload": {"action": "failure", "response": "tenant_id is required"}, "status": 400}
        if component is None:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"component is required and must be one of {VALID_COMPONENTS}",
                },
                "status": 400,
            }
        if not isinstance(template_id, str) or not template_id.strip():
            return {
                "payload": {"action": "failure", "response": "template_id is required"},
                "status": 400,
            }

        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        collection_name = TEMPLATES_COLLECTION_FMT.format(tenant_id=tenant_id)
        try:
            collection = service.kvstore[collection_name]
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"Variable delay templates collection not found for tenant '{tenant_id}'",
                    "exception": str(e),
                },
                "status": 404,
            }

        query = {"component": component, "template_id": template_id.strip()}
        try:
            existing = collection.data.query(query=json.dumps(query))
        except Exception as e:
            return {
                "payload": {"action": "failure", "response": "Failed to query existing templates", "exception": str(e)},
                "status": 500,
            }

        if not existing or len(existing) == 0:
            return {
                "payload": {
                    "action": "success",
                    "response": f"No custom template '{template_id}' found for component '{component}' — nothing to reset",
                    "deleted_count": 0,
                },
                "status": 200,
            }

        deleted = 0
        for rec in existing:
            try:
                collection.data.delete_by_id(rec.get("_key"))
                deleted += 1
            except Exception as e:
                logger.error(
                    f'post_templates_reset: failed to delete record, tenant_id="{tenant_id}", '
                    f'_key="{rec.get("_key")}", exception="{str(e)}"'
                )

        logger.info(
            f'post_templates_reset: tenant_id="{tenant_id}", component="{component}", '
            f'template_id="{template_id}", deleted_count={deleted}'
        )

        # Audit
        try:
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user or "unknown",
                "success",
                "variable delay template deleted",
                str(template_id),
                f"splk-{component}",
                json.dumps({"deleted_count": deleted}, default=str),
                f'Variable delay template "{template_id}" was deleted ({deleted} record(s))',
                str(update_comment),
            )
        except Exception as audit_e:
            logger.warning(
                f'function=post_templates_reset, tenant_id="{tenant_id}", '
                f'step="audit", exception="{str(audit_e)}"'
            )

        return {
            "payload": {
                "action": "success",
                "response": f"Deleted custom template '{template_id}' ({deleted} record(s))",
                "deleted_count": deleted,
            },
            "status": 200,
        }

    # ------------------------------------------------------------------
    # POST /templates_reset_all — wipe all custom templates for a tenant + component
    # ------------------------------------------------------------------
    def post_templates_reset_all(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_variable_delay/admin/templates_reset_all" mode="post" body='{"tenant_id": "mytenant", "component": "dsm"}'
        """

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        describe = trackme_parse_describe_flag(request_info)

        if describe or resp_dict is None:
            response = {
                "describe": (
                    "Delete ALL custom variable delay templates for a tenant + component, "
                    "reverting the Quick templates selection back to the factory defaults "
                    "hardcoded in slotTemplates.ts. Used by the 'Reset all to factory defaults' "
                    "button in the Manage Templates admin modal."
                ),
                "resource_desc": "Reset all custom variable delay templates to factory defaults",
                "resource_spl_example": (
                    '| trackme url="/services/trackme/v2/splk_variable_delay/admin/templates_reset_all" '
                    'mode="post" body=\'{"tenant_id":"mytenant","component":"dsm"}\''
                ),
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "MANDATORY — 'dsm' or 'dhm'",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        tenant_id = resp_dict.get("tenant_id")
        component = _normalize_component(resp_dict.get("component"))
        update_comment = resp_dict.get("update_comment") or "API update"

        if not tenant_id:
            return {"payload": {"action": "failure", "response": "tenant_id is required"}, "status": 400}
        if component is None:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"component is required and must be one of {VALID_COMPONENTS}",
                },
                "status": 400,
            }

        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        collection_name = TEMPLATES_COLLECTION_FMT.format(tenant_id=tenant_id)
        try:
            collection = service.kvstore[collection_name]
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"Variable delay templates collection not found for tenant '{tenant_id}'",
                    "exception": str(e),
                },
                "status": 404,
            }

        query = {"component": component}
        try:
            existing = collection.data.query(query=json.dumps(query))
        except Exception as e:
            return {
                "payload": {"action": "failure", "response": "Failed to query templates", "exception": str(e)},
                "status": 500,
            }

        deleted = 0
        for rec in existing:
            try:
                collection.data.delete_by_id(rec.get("_key"))
                deleted += 1
            except Exception as e:
                logger.error(
                    f'post_templates_reset_all: failed to delete record, tenant_id="{tenant_id}", '
                    f'_key="{rec.get("_key")}", exception="{str(e)}"'
                )

        logger.info(
            f'post_templates_reset_all: tenant_id="{tenant_id}", component="{component}", '
            f'deleted_count={deleted}'
        )

        # Audit
        try:
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user or "unknown",
                "success",
                "variable delay templates reset_all",
                "all",
                f"splk-{component}",
                json.dumps({"deleted_count": deleted}, default=str),
                f'All variable delay custom templates reset to factory defaults ({deleted} record(s))',
                str(update_comment),
            )
        except Exception as audit_e:
            logger.warning(
                f'function=post_templates_reset_all, tenant_id="{tenant_id}", '
                f'step="audit", exception="{str(audit_e)}"'
            )

        return {
            "payload": {
                "action": "success",
                "response": f"Reset {deleted} custom template(s) to factory defaults",
                "deleted_count": deleted,
            },
            "status": 200,
        }
