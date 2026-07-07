#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_virtual_groups_admin.py"
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
import re
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

logger = setup_logger(
    "trackme.rest.virtual_groups_admin",
    "trackme_rest_api_virtual_groups_admin.log",
)


# import rest handler
import trackme_rest_handler

# import TrackMe libs
from trackme_libs import (
    trackme_audit_event,
    SPLUNKD_TIMEOUT_DEFAULT,
    trackme_parse_describe_flag,
)
from trackme_filter_engine import validate_filter

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerVirtualGroupsAdmin_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerVirtualGroupsAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_virtual_groups_admin(self, request_info, **kwargs):
        response = {
            "resource_group_name": "virtual_groups_admin",
            "resource_group_desc": "Endpoints related to Virtual Groups — read-only cross-tenant aggregation views (admin operations)",
        }
        return {"payload": response, "status": 200}

    def post_create_group(self, request_info, **kwargs):
        """
        Create a new Virtual Group.

        Required fields: group_id, group_alias
        Optional fields: group_description, tenants_scope (JSON), priority_filter (JSON), rbac_allowed_roles
        """

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            return {
                "payload": {"error": "Invalid request payload"},
                "status": 400,
            }

        describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": (
                    "This endpoint creates a new Virtual Group — a read-only "
                    "cross-tenant aggregation view that surfaces entities from "
                    "multiple tenants and components in a single card on the "
                    "Virtual Tenants grid. The group_id must be unique, "
                    "lowercase alphanumeric (with hyphens or underscores), and "
                    "max 40 characters. Each entry in tenants_scope must be "
                    '{"tenant_id": "<id>", "components": ["dsm", "dhm", ...]} '
                    "with components drawn from dsm, dhm, mhm, flx, fqm, wlk. "
                    "priority_filter, when non-empty, restricts the view to "
                    "entities at the listed priority levels. entity_filter is "
                    "an optional TrackMe filter expression evaluated against "
                    "entity records. rbac_allowed_roles controls visibility "
                    "to non-admin users."
                ),
                "resource_desc": "Create a new Virtual Group (read-only cross-tenant aggregation view)",
                "resource_spl_example": '| trackme url="/services/trackme/v2/virtual_groups/admin/create_group" mode="post" body="{\'group_id\': \'mygroup\', \'group_alias\': \'My Group\', \'tenants_scope\': [{\'tenant_id\': \'t1\', \'components\': [\'dsm\', \'dhm\']}], \'priority_filter\': [\'critical\', \'high\'], \'rbac_allowed_roles\': \'trackme_admin,trackme_power\'}"',
                "options": [
                    {
                        "group_id": "REQUIRED. Unique identifier — lowercase alphanumeric with hyphens/underscores, must start with a letter or digit, max 40 chars",
                        "group_alias": "REQUIRED. Human-readable display name shown on the group card",
                        "group_description": "OPTIONAL. Free-form description of the group's purpose",
                        "group_category": "OPTIONAL. Free-form category label used for grouping/filtering on the UI",
                        "tenants_scope": "OPTIONAL. JSON array of {tenant_id, components} entries that defines which tenants and components contribute entities to this group. Components must be drawn from dsm, dhm, mhm, flx, fqm, wlk; duplicates within an entry are deduplicated; duplicate tenant_id entries are rejected",
                        "priority_filter": "OPTIONAL. JSON array of priority levels to include — any subset of [\"critical\", \"high\", \"medium\", \"low\"]. Empty array means no priority filter",
                        "entity_filter": "OPTIONAL. TrackMe filter expression applied to entities at view time (e.g. 'priority=critical AND tag=production'). Validated for syntax on save",
                        "rbac_allowed_roles": "OPTIONAL. Comma-separated list of Splunk roles that can see this group. Defaults to 'trackme_admin,trackme_power,trackme_user'. Admin roles always have access regardless of this list",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        group_id = resp_dict.get("group_id")
        group_alias = resp_dict.get("group_alias")
        group_description = resp_dict.get("group_description", "")
        group_category = str(resp_dict.get("group_category", "") or "").strip()
        tenants_scope = resp_dict.get("tenants_scope", [])
        priority_filter = resp_dict.get("priority_filter", [])
        entity_filter = str(resp_dict.get("entity_filter", "") or "").strip()
        rbac_allowed_roles = resp_dict.get(
            "rbac_allowed_roles", "trackme_admin,trackme_power,trackme_user"
        )
        update_comment = resp_dict.get("update_comment") or "API update"

        # Validate required fields
        if not group_id:
            return {
                "payload": {"error": "group_id is required"},
                "status": 400,
            }

        if not group_alias:
            return {
                "payload": {"error": "group_alias is required"},
                "status": 400,
            }

        # Validate group_id format (lowercase, alphanumeric, hyphens, underscores, max 40 chars)
        if not re.match(r"^[a-z0-9][a-z0-9_-]{0,39}$", group_id):
            return {
                "payload": {
                    "error": (
                        "group_id must be lowercase alphanumeric with hyphens/underscores, "
                        "start with a letter or digit, and be max 40 characters"
                    )
                },
                "status": 400,
            }

        # Validate entity_filter syntax (if non-empty)
        if entity_filter:
            filter_error = validate_filter(entity_filter)
            if filter_error:
                return {
                    "payload": {"error": f"Invalid entity_filter: {filter_error}"},
                    "status": 400,
                }

        # Validate tenants_scope is a list of dicts
        if isinstance(tenants_scope, str):
            try:
                tenants_scope = json.loads(tenants_scope)
            except (json.JSONDecodeError, TypeError):
                return {
                    "payload": {"error": "tenants_scope must be a valid JSON array"},
                    "status": 400,
                }

        if not isinstance(tenants_scope, list):
            return {
                "payload": {"error": "tenants_scope must be a JSON array"},
                "status": 400,
            }

        seen_tenant_ids: set = set()
        for entry in tenants_scope:
            if not isinstance(entry, dict) or "tenant_id" not in entry or "components" not in entry:
                return {
                    "payload": {
                        "error": (
                            "Each tenants_scope entry must be a dict with 'tenant_id' and 'components' keys"
                        )
                    },
                    "status": 400,
                }
            if not isinstance(entry["components"], list):
                return {
                    "payload": {
                        "error": (
                            "'components' must be a list (e.g. [\"dsm\", \"dhm\"])"
                        )
                    },
                    "status": 400,
                }
            valid_components = {"dsm", "dhm", "mhm", "flx", "fqm", "wlk"}
            invalid = [c for c in entry["components"] if c not in valid_components]
            if invalid:
                return {
                    "payload": {
                        "error": (
                            f"Invalid component(s): {', '.join(invalid)}. "
                            f"Must be one of: {', '.join(sorted(valid_components))}"
                        )
                    },
                    "status": 400,
                }
            # Deduplicate components
            entry["components"] = list(dict.fromkeys(entry["components"]))
            tid = entry["tenant_id"]
            if tid in seen_tenant_ids:
                return {
                    "payload": {"error": f"Duplicate tenant_id '{tid}' in tenants_scope"},
                    "status": 400,
                }
            seen_tenant_ids.add(tid)

        # Validate priority_filter
        if isinstance(priority_filter, str):
            try:
                priority_filter = json.loads(priority_filter)
            except (json.JSONDecodeError, TypeError):
                return {
                    "payload": {"error": "priority_filter must be a valid JSON array"},
                    "status": 400,
                }

        valid_priorities = {"critical", "high", "medium", "low"}
        if not isinstance(priority_filter, list):
            return {
                "payload": {"error": "priority_filter must be a JSON array"},
                "status": 400,
            }
        for p in priority_filter:
            if p not in valid_priorities:
                return {
                    "payload": {
                        "error": f"Invalid priority filter value: '{p}'. Must be one of: {', '.join(sorted(valid_priorities))}"
                    },
                    "status": 400,
                }

        # Get Splunk service
        splunkd_port = request_info.server_rest_port
        service = client.connect(
            token=request_info.system_authtoken,
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            timeout=SPLUNKD_TIMEOUT_DEFAULT,
        )

        # Check for duplicate group_id
        collection_name = "kv_trackme_virtual_groups"
        try:
            collection = service.kvstore[collection_name]
            existing = collection.data.query(
                query=json.dumps({"group_id": group_id})
            )
            if existing:
                return {
                    "payload": {"error": f"Virtual Group '{group_id}' already exists"},
                    "status": 409,
                }
        except Exception as e:
            logger.error(
                f'function=post_create_group, group_id="{group_id}", '
                f'step="check_duplicate", exception="{str(e)}"'
            )
            return {"payload": {"error": str(e)}, "status": 500}

        # Create the record
        now = time.time()
        record = {
            "_key": hashlib.sha256(group_id.encode()).hexdigest(),
            "group_id": group_id,
            "group_alias": group_alias,
            "group_description": group_description,
            "group_category": group_category,
            "tenants_scope": json.dumps(tenants_scope),
            "priority_filter": json.dumps(priority_filter),
            "entity_filter": entity_filter,
            "rbac_allowed_roles": rbac_allowed_roles,
            "created_by": request_info.user,
            "created_time": now,
            "updated_by": request_info.user,
            "updated_time": now,
        }

        try:
            collection.data.insert(json.dumps(record))
        except Exception as e:
            logger.error(
                f'function=post_create_group, group_id="{group_id}", '
                f'step="insert", exception="{str(e)}"'
            )
            return {"payload": {"error": str(e)}, "status": 500}

        # Audit
        try:
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                "all",
                request_info.user,
                "success",
                "create virtual group",
                str(group_id),
                "virtual_group",
                json.dumps(record, indent=1),
                f'Virtual Group "{group_alias}" (id: {group_id}) was created by user="{request_info.user}"',
                str(update_comment),
            )
        except Exception as e:
            logger.warning(
                f'function=post_create_group, group_id="{group_id}", '
                f'step="audit", exception="{str(e)}"'
            )

        # Return the created record with parsed JSON fields
        record["tenants_scope"] = tenants_scope
        record["priority_filter"] = priority_filter

        return {"payload": record, "status": 201}

    def post_update_group(self, request_info, **kwargs):
        """
        Update an existing Virtual Group.

        Required: group_id
        Optional: group_alias, group_description, tenants_scope, priority_filter, rbac_allowed_roles
        """

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            return {
                "payload": {"error": "Invalid request payload"},
                "status": 400,
            }

        describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": (
                    "This endpoint updates an existing Virtual Group identified "
                    "by group_id. Only the fields supplied in the request body "
                    "are modified; omitted fields keep their current values. "
                    "group_id itself is immutable — supply the existing value "
                    "to identify the record. Validation rules match "
                    "create_group: tenants_scope entries must be "
                    '{"tenant_id", "components"} with components drawn from '
                    "dsm, dhm, mhm, flx, fqm, wlk; priority_filter values must "
                    "be in [critical, high, medium, low]; entity_filter is "
                    "syntax-checked when non-empty."
                ),
                "resource_desc": "Update an existing Virtual Group — only the fields supplied are modified",
                "resource_spl_example": '| trackme url="/services/trackme/v2/virtual_groups/admin/update_group" mode="post" body="{\'group_id\': \'mygroup\', \'group_alias\': \'New Display Name\', \'priority_filter\': [\'critical\']}"',
                "options": [
                    {
                        "group_id": "REQUIRED. Identifier of the Virtual Group to update (immutable — used as a lookup key)",
                        "group_alias": "OPTIONAL. New display name (cannot be empty if supplied)",
                        "group_description": "OPTIONAL. New free-form description",
                        "group_category": "OPTIONAL. New category label",
                        "tenants_scope": "OPTIONAL. Replacement JSON array of {tenant_id, components} entries — same validation as create_group",
                        "priority_filter": "OPTIONAL. Replacement JSON array of priority levels — values must be in [critical, high, medium, low]",
                        "entity_filter": "OPTIONAL. Replacement TrackMe filter expression. Pass an empty string to clear",
                        "rbac_allowed_roles": "OPTIONAL. Replacement comma-separated list of Splunk roles allowed to see this group",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        group_id = resp_dict.get("group_id")
        update_comment = resp_dict.get("update_comment") or "API update"

        if not group_id:
            return {
                "payload": {"error": "group_id is required"},
                "status": 400,
            }

        # Get Splunk service
        splunkd_port = request_info.server_rest_port
        service = client.connect(
            token=request_info.system_authtoken,
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            timeout=SPLUNKD_TIMEOUT_DEFAULT,
        )

        # Load existing record
        collection_name = "kv_trackme_virtual_groups"
        try:
            collection = service.kvstore[collection_name]
            existing = collection.data.query(
                query=json.dumps({"group_id": group_id})
            )
        except Exception as e:
            logger.error(
                f'function=post_update_group, group_id="{group_id}", '
                f'step="load", exception="{str(e)}"'
            )
            return {"payload": {"error": str(e)}, "status": 500}

        if not existing:
            return {
                "payload": {"error": f"Virtual Group '{group_id}' not found"},
                "status": 404,
            }

        record = existing[0]

        # Update fields if provided
        if "group_alias" in resp_dict:
            if not resp_dict["group_alias"] or not str(resp_dict["group_alias"]).strip():
                return {
                    "payload": {"error": "group_alias is required and cannot be empty"},
                    "status": 400,
                }
            record["group_alias"] = resp_dict["group_alias"]

        if "group_description" in resp_dict:
            record["group_description"] = resp_dict["group_description"]

        if "group_category" in resp_dict:
            record["group_category"] = str(resp_dict["group_category"] or "").strip()

        if "tenants_scope" in resp_dict:
            tenants_scope = resp_dict["tenants_scope"]
            if isinstance(tenants_scope, str):
                try:
                    tenants_scope = json.loads(tenants_scope)
                except (json.JSONDecodeError, TypeError):
                    return {
                        "payload": {"error": "tenants_scope must be a valid JSON array"},
                        "status": 400,
                    }
            if not isinstance(tenants_scope, list):
                return {
                    "payload": {"error": "tenants_scope must be a JSON array"},
                    "status": 400,
                }
            seen_update_tenant_ids: set = set()
            for entry in tenants_scope:
                if not isinstance(entry, dict) or "tenant_id" not in entry or "components" not in entry:
                    return {
                        "payload": {
                            "error": (
                                "Each tenants_scope entry must be a dict with 'tenant_id' and 'components' keys"
                            )
                        },
                        "status": 400,
                    }
                if not isinstance(entry["components"], list):
                    return {
                        "payload": {
                            "error": (
                                "'components' must be a list (e.g. [\"dsm\", \"dhm\"])"
                            )
                        },
                        "status": 400,
                    }
                valid_components = {"dsm", "dhm", "mhm", "flx", "fqm", "wlk"}
                invalid = [c for c in entry["components"] if c not in valid_components]
                if invalid:
                    return {
                        "payload": {
                            "error": (
                                f"Invalid component(s): {', '.join(invalid)}. "
                                f"Must be one of: {', '.join(sorted(valid_components))}"
                            )
                        },
                        "status": 400,
                    }
                # Deduplicate components
                entry["components"] = list(dict.fromkeys(entry["components"]))
                tid = entry["tenant_id"]
                if tid in seen_update_tenant_ids:
                    return {
                        "payload": {"error": f"Duplicate tenant_id '{tid}' in tenants_scope"},
                        "status": 400,
                    }
                seen_update_tenant_ids.add(tid)
            record["tenants_scope"] = json.dumps(tenants_scope)

        if "priority_filter" in resp_dict:
            priority_filter = resp_dict["priority_filter"]
            if isinstance(priority_filter, str):
                try:
                    priority_filter = json.loads(priority_filter)
                except (json.JSONDecodeError, TypeError):
                    return {
                        "payload": {"error": "priority_filter must be a valid JSON array"},
                        "status": 400,
                    }
            if not isinstance(priority_filter, list):
                return {
                    "payload": {"error": "priority_filter must be a JSON array"},
                    "status": 400,
                }
            valid_priorities = {"critical", "high", "medium", "low"}
            for p in priority_filter:
                if p not in valid_priorities:
                    return {
                        "payload": {
                            "error": f"Invalid priority filter value: '{p}'. Must be one of: {', '.join(sorted(valid_priorities))}"
                        },
                        "status": 400,
                    }
            record["priority_filter"] = json.dumps(priority_filter)

        if "entity_filter" in resp_dict:
            entity_filter_val = str(resp_dict["entity_filter"] or "").strip()
            if entity_filter_val:
                filter_error = validate_filter(entity_filter_val)
                if filter_error:
                    return {
                        "payload": {"error": f"Invalid entity_filter: {filter_error}"},
                        "status": 400,
                    }
            record["entity_filter"] = entity_filter_val

        if "rbac_allowed_roles" in resp_dict:
            record["rbac_allowed_roles"] = resp_dict["rbac_allowed_roles"]

        record["updated_by"] = request_info.user
        record["updated_time"] = time.time()

        # Save
        try:
            record_key = record["_key"]
            collection.data.update(record_key, json.dumps(record))
        except Exception as e:
            logger.error(
                f'function=post_update_group, group_id="{group_id}", '
                f'step="update", exception="{str(e)}"'
            )
            return {"payload": {"error": str(e)}, "status": 500}

        # Audit
        try:
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                "all",
                request_info.user,
                "success",
                "update virtual group",
                str(group_id),
                "virtual_group",
                json.dumps(record, indent=1, default=str),
                f'Virtual Group "{group_id}" was updated by user="{request_info.user}"',
                str(update_comment),
            )
        except Exception as e:
            logger.warning(
                f'function=post_update_group, group_id="{group_id}", '
                f'step="audit", exception="{str(e)}"'
            )

        # Parse JSON fields for response
        try:
            record["tenants_scope"] = json.loads(record.get("tenants_scope", "[]"))
        except (json.JSONDecodeError, TypeError):
            record["tenants_scope"] = []
        try:
            record["priority_filter"] = json.loads(record.get("priority_filter", "[]"))
        except (json.JSONDecodeError, TypeError):
            record["priority_filter"] = []
        record.setdefault("entity_filter", "")
        record.setdefault("group_category", "")

        return {"payload": record, "status": 200}

    def delete_delete_group(self, request_info, **kwargs):
        """
        Delete a Virtual Group by group_id.
        """

        group_id = None

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": (
                    "This endpoint permanently deletes a Virtual Group "
                    "identified by group_id. The deletion is recorded in the "
                    "audit log. Virtual Groups are read-only aggregation views "
                    "— deleting one does not affect the underlying tenants or "
                    "entities, only the cross-tenant card. group_id can be "
                    "passed in the JSON body or as a query-string parameter."
                ),
                "resource_desc": "Permanently delete a Virtual Group by group_id",
                "resource_spl_example": '| trackme url="/services/trackme/v2/virtual_groups/admin/delete_group" mode="delete" body="{\'group_id\': \'mygroup\'}"',
                "options": [
                    {
                        "group_id": "REQUIRED. Identifier of the Virtual Group to delete",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        update_comment = "API update"
        if resp_dict is not None:
            group_id = resp_dict.get("group_id")
            update_comment = resp_dict.get("update_comment") or "API update"

        # Try query string
        if not group_id:
            group_id = request_info.query.get("group_id")

        if not group_id:
            return {
                "payload": {"error": "group_id is required"},
                "status": 400,
            }

        # Get Splunk service
        splunkd_port = request_info.server_rest_port
        service = client.connect(
            token=request_info.system_authtoken,
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            timeout=SPLUNKD_TIMEOUT_DEFAULT,
        )

        # Find the record
        collection_name = "kv_trackme_virtual_groups"
        try:
            collection = service.kvstore[collection_name]
            existing = collection.data.query(
                query=json.dumps({"group_id": group_id})
            )
        except Exception as e:
            logger.error(
                f'function=delete_delete_group, group_id="{group_id}", '
                f'step="load", exception="{str(e)}"'
            )
            return {"payload": {"error": str(e)}, "status": 500}

        if not existing:
            return {
                "payload": {"error": f"Virtual Group '{group_id}' not found"},
                "status": 404,
            }

        record = existing[0]
        record_key = record["_key"]
        group_alias = record.get("group_alias", group_id)

        # Delete
        try:
            collection.data.delete_by_id(record_key)
        except Exception as e:
            logger.error(
                f'function=delete_delete_group, group_id="{group_id}", '
                f'step="delete", exception="{str(e)}"'
            )
            return {"payload": {"error": str(e)}, "status": 500}

        # Audit
        try:
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                "all",
                request_info.user,
                "success",
                "delete virtual group",
                str(group_id),
                "virtual_group",
                json.dumps(record, indent=1, default=str),
                f'Virtual Group "{group_alias}" (id: {group_id}) was deleted by user="{request_info.user}"',
                str(update_comment),
            )
        except Exception as e:
            logger.warning(
                f'function=delete_delete_group, group_id="{group_id}", '
                f'step="audit", exception="{str(e)}"'
            )

        return {
            "payload": {
                "message": f"Virtual Group '{group_alias}' (id: {group_id}) has been deleted",
                "group_id": group_id,
            },
            "status": 200,
        }

