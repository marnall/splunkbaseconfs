#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_virtual_groups_user.py"
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

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.virtual_groups_user",
    "trackme_rest_api_virtual_groups_user.log",
)


# import rest handler
import trackme_rest_handler

# import TrackMe libs
from trackme_libs import SPLUNKD_TIMEOUT_DEFAULT, trackme_parse_describe_flag

# import Splunk libs
import splunklib.client as client

# import load utilities for RBAC and aggregation
from trackme_libs_load import (
    resolve_effective_roles_for_user,
    get_vtenants_accounts,
    compute_group_component_summary,
    load_group_shared_data,
)


def has_group_access(effective_roles, group_record):
    """
    Check if a user has access to a Virtual Group based on rbac_allowed_roles.
    Unlike tenants which have admin/power/user role splits, Virtual Groups
    have a single allowed_roles field since they are read-only views.
    """
    rbac_allowed_roles = group_record.get("rbac_allowed_roles", "")
    if isinstance(rbac_allowed_roles, list):
        allowed_roles = set(rbac_allowed_roles)
    else:
        allowed_roles = set(r.strip() for r in rbac_allowed_roles.split(",") if r.strip())

    # Always allow admin and sc_admin
    allowed_roles |= {"admin", "trackme_admin", "sc_admin"}

    return bool(effective_roles & allowed_roles)


class TrackMeHandlerVirtualGroupsRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerVirtualGroupsRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_virtual_groups(self, request_info, **kwargs):
        response = {
            "resource_group_name": "virtual_groups",
            "resource_group_desc": "Endpoints related to Virtual Groups — read-only cross-tenant aggregation views (user operations)",
        }
        return {"payload": response, "status": 200}

    def get_list_groups(self, request_info, **kwargs):
        """
        List all Virtual Groups accessible to the current user (RBAC-filtered).
        """

        describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": (
                    "This endpoint lists all Virtual Groups visible to the "
                    "calling user. Virtual Groups are read-only cross-tenant "
                    "aggregation views; visibility is filtered by the "
                    "rbac_allowed_roles field on each group against the "
                    "caller's effective Splunk roles. The response is sorted "
                    "by group_alias (case-insensitive). It requires a GET "
                    "call with no parameters."
                ),
                "resource_desc": "List all Virtual Groups visible to the calling user (RBAC-filtered)",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/virtual_groups/list_groups"',
            }
            return {"payload": response, "status": 200}

        # Get Splunk service
        splunkd_port = request_info.server_rest_port
        service = client.connect(
            token=request_info.system_authtoken,
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            timeout=SPLUNKD_TIMEOUT_DEFAULT,
        )

        # Get effective roles
        username = request_info.user
        effective_roles = resolve_effective_roles_for_user(service, username)

        # Load Virtual Groups from KV Store
        collection_name = "kv_trackme_virtual_groups"
        try:
            collection = service.kvstore[collection_name]
            records = collection.data.query()
        except Exception as e:
            logger.error(
                f'function=get_list_groups, exception="{str(e)}"'
            )
            return {"payload": {"error": str(e)}, "status": 500}

        # RBAC filter
        filtered_records = []
        for record in records:
            if (
                effective_roles is None  # splunk-system-user bypasses RBAC
                or has_group_access(effective_roles, record)
            ):
                # Parse JSON fields for the response
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
                filtered_records.append(record)

        # Sort by alias
        filtered_records.sort(key=lambda x: (x.get("group_alias") or x.get("group_id", "")).lower())

        return {"payload": filtered_records, "status": 200}

    def get_get_group(self, request_info, **kwargs):
        """
        Get a single Virtual Group definition by group_id.
        """

        group_id = None

        # Get from query args
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": (
                    "This endpoint returns the full definition of a single "
                    "Virtual Group identified by group_id, including its "
                    "tenants_scope, priority_filter, entity_filter and RBAC "
                    "settings. The caller must be in one of the group's "
                    "rbac_allowed_roles or hold an admin role; otherwise the "
                    "endpoint returns 404 to avoid leaking the existence of "
                    "groups the user cannot see. group_id can be passed in "
                    "the JSON body or as a query-string parameter."
                ),
                "resource_desc": "Return a single Virtual Group definition by group_id",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/virtual_groups/get_group" body="{\'group_id\': \'mygroup\'}"',
                "options": [
                    {
                        "group_id": "The Virtual Group identifier (lowercase, alphanumeric, hyphens/underscores, max 40 chars)",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        if resp_dict is not None:
            group_id = resp_dict.get("group_id")

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

        collection_name = "kv_trackme_virtual_groups"
        try:
            collection = service.kvstore[collection_name]
            records = collection.data.query(
                query=json.dumps({"group_id": group_id})
            )
        except Exception as e:
            logger.error(
                f'function=get_get_group, group_id="{group_id}", exception="{str(e)}"'
            )
            return {"payload": {"error": str(e)}, "status": 500}

        if not records:
            return {
                "payload": {"error": f"Virtual Group '{group_id}' not found"},
                "status": 404,
            }

        record = records[0]

        # RBAC check
        username = request_info.user
        effective_roles = resolve_effective_roles_for_user(service, username)
        if effective_roles is not None and not has_group_access(effective_roles, record):
            return {
                "payload": {"error": f"Virtual Group '{group_id}' not found"},
                "status": 404,
            }

        # Parse JSON fields
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

    def post_load_group_summary(self, request_info, **kwargs):
        """
        Load aggregated summary data for a Virtual Group.
        Returns per-component entity counts for card display.
        Skips deleted or disabled tenants.
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
                    "This endpoint returns aggregated summary data for a single "
                    "Virtual Group: per-component entity counts (green / orange "
                    "/ red / blue), the resolved component list, per-tenant "
                    "details for the cards, and the priority and entity "
                    "filters that were applied. Deleted or disabled tenants in "
                    "tenants_scope are skipped silently. RBAC is enforced "
                    "against the group's rbac_allowed_roles."
                ),
                "resource_desc": "Return aggregated per-component entity counts for a single Virtual Group",
                "resource_spl_example": '| trackme url="/services/trackme/v2/virtual_groups/load_group_summary" mode="post" body="{\'group_id\': \'mygroup\'}"',
                "options": [
                    {
                        "group_id": "The Virtual Group identifier",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        if resp_dict is not None:
            group_id = resp_dict.get("group_id")

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

        # Load group definition
        collection_name = "kv_trackme_virtual_groups"
        try:
            collection = service.kvstore[collection_name]
            records = collection.data.query(
                query=json.dumps({"group_id": group_id})
            )
        except Exception as e:
            logger.error(
                f'function=post_load_group_summary, group_id="{group_id}", '
                f'step="load_group", exception="{str(e)}"'
            )
            return {"payload": {"error": str(e)}, "status": 500}

        if not records:
            return {
                "payload": {"error": f"Virtual Group '{group_id}' not found"},
                "status": 404,
            }

        group_record = records[0]

        # RBAC check
        username = request_info.user
        effective_roles = resolve_effective_roles_for_user(service, username)
        if effective_roles is not None and not has_group_access(effective_roles, group_record):
            return {
                "payload": {"error": f"Virtual Group '{group_id}' not found"},
                "status": 404,
            }

        # Parse tenants_scope
        try:
            tenants_scope = json.loads(group_record.get("tenants_scope", "[]"))
        except (json.JSONDecodeError, TypeError):
            tenants_scope = []

        # Parse priority_filter
        try:
            priority_filter = json.loads(group_record.get("priority_filter", "[]"))
        except (json.JSONDecodeError, TypeError):
            priority_filter = []

        # Get vtenants accounts for aliases
        try:
            vtenants_account = get_vtenants_accounts(
                request_info.session_key,
                request_info.server_rest_uri,
            )
        except Exception:
            vtenants_account = {}

        component_summary, components_sorted, tenant_details = compute_group_component_summary(
            service, tenants_scope, vtenants_account, logger=logger
        )

        response = {
            "group_id": group_id,
            "group_alias": group_record.get("group_alias", group_id),
            "group_description": group_record.get("group_description", ""),
            "component_summary": component_summary,
            "components": components_sorted,
            "tenant_details": tenant_details,
            "priority_filter": priority_filter,
            "entity_filter": str(group_record.get("entity_filter", "") or ""),
        }

        return {"payload": response, "status": 200}

    def post_load_groups_summary(self, request_info, **kwargs):
        """
        Batch variant of post_load_group_summary.
        Accepts a list of group_ids and returns summaries for all of them in a single
        request, loading kv_trackme_virtual_tenants and kv_trackme_virtual_tenants_entities_summary
        only once regardless of how many groups are requested.

        Request body:
            {"group_ids": ["id1", "id2", ...]}

        Response:
            {"summaries": {"id1": {...}, "id2": {...}}}
        """

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": (
                    "Batch variant of load_group_summary. Accepts a list of "
                    "group_ids and returns the aggregated per-component entity "
                    "counts for every group in a single request, loading the "
                    "shared tenant and entity-summary KV collections only once "
                    "regardless of how many groups are requested. Groups the "
                    "caller cannot access (or that do not exist) are silently "
                    "skipped — the response only contains entries for groups "
                    "that resolved successfully."
                ),
                "resource_desc": "Return aggregated per-component entity counts for a batch of Virtual Groups in one call",
                "resource_spl_example": '| trackme url="/services/trackme/v2/virtual_groups/load_groups_summary" mode="post" body="{\'group_ids\': [\'group1\', \'group2\']}"',
                "options": [
                    {
                        "group_ids": "Non-empty list of Virtual Group identifiers to load summaries for (JSON array)",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        group_ids = resp_dict.get("group_ids", []) if resp_dict else []
        if not isinstance(group_ids, list) or not group_ids:
            return {"payload": {"error": "group_ids must be a non-empty list"}, "status": 400}

        splunkd_port = request_info.server_rest_port
        service = client.connect(
            token=request_info.system_authtoken,
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            timeout=SPLUNKD_TIMEOUT_DEFAULT,
        )

        # RBAC context — resolved once for all groups
        username = request_info.user
        effective_roles = resolve_effective_roles_for_user(service, username)

        # Load all group records in one KV query
        collection_name = "kv_trackme_virtual_groups"
        try:
            all_records = service.kvstore[collection_name].data.query()
        except Exception as e:
            logger.error(f'function=post_load_groups_summary step="load_groups" exception="{str(e)}"')
            return {"payload": {"error": str(e)}, "status": 500}

        group_map = {r["group_id"]: r for r in all_records if r.get("group_id") in group_ids}

        # vtenants_account for aliases
        try:
            vtenants_account = get_vtenants_accounts(
                request_info.session_key,
                request_info.server_rest_uri,
            )
        except Exception:
            vtenants_account = {}

        # Load the two shared KV collections once for all groups
        tenant_lookup, summary_by_tenant = load_group_shared_data(service, logger=logger)

        summaries = {}
        for group_id in group_ids:
            group_record = group_map.get(group_id)
            if not group_record:
                continue  # skip unknown groups silently

            if effective_roles is not None and not has_group_access(effective_roles, group_record):
                continue  # skip groups this user cannot access

            try:
                tenants_scope = json.loads(group_record.get("tenants_scope", "[]"))
            except (json.JSONDecodeError, TypeError):
                tenants_scope = []
            try:
                priority_filter = json.loads(group_record.get("priority_filter", "[]"))
            except (json.JSONDecodeError, TypeError):
                priority_filter = []

            component_summary, components_sorted, tenant_details = compute_group_component_summary(
                service, tenants_scope, vtenants_account, logger=logger,
                tenant_lookup=tenant_lookup, summary_by_tenant=summary_by_tenant,
            )

            summaries[group_id] = {
                "group_id": group_id,
                "group_alias": group_record.get("group_alias", group_id),
                "group_description": group_record.get("group_description", ""),
                "component_summary": component_summary,
                "components": components_sorted,
                "tenant_details": tenant_details,
                "priority_filter": priority_filter,
                "entity_filter": str(group_record.get("entity_filter", "") or ""),
            }

        return {"payload": {"summaries": summaries}, "status": 200}
