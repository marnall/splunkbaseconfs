#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_inject_expected_admin.py"
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
import re
import sys
import random

# Tenant IDs are restricted to alphanumeric characters, hyphens, and underscores.
# This matches the convention used across the TrackMe codebase (e.g.
# trackme_rest_handler_restricted_searches.py). Validating at handler entry
# prevents any possibility of SPL injection via tenant_id interpolation
# in the trackmepushdatasource pipeline built in post_inject_execute.
_TENANT_ID_RE = re.compile(r'^[a-zA-Z0-9_-]+$')

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_inject_expected_admin",
    "trackme_rest_api_splk_inject_expected_admin.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    run_splunk_search,
    trackme_audit_event,
    trackme_create_report,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_refresh_component_summary_async,
    trackme_reqinfo,
)
from trackme_libs_policies import (
    resolve_service_for_account,
    validate_lookup_name,
)
from trackme_libs_utils import (
    remove_leading_spaces,
    interpret_boolean,
    build_dhm_asset_index,
    dhm_host_matches_asset_index,
    dhm_reconcile_hosts,
    sanitize_spl_input,
    build_feed_comparison_key,
    reconcile_feed_keys,
)

# host / break-by field names are spliced unquoted into the composed SPL `by`
# clause, so they must be simple Splunk identifiers (same pattern the hybrid
# tracker wizard enforces).
_HOST_FIELD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")

# earliest/latest time specifiers are interpolated into the quoted args of the
# splunkremotesearch wrapper, so they are restricted to the characters that make
# up a Splunk time modifier (relative `-30d@d`, snap `@d`, `now`, epoch, ISO).
# This allowlist rejects quotes / backticks / `$` / whitespace that could escape
# the quoted-arg context.
_TIME_SPECIFIER_RE = re.compile(r"^[A-Za-z0-9_:@+\-./]+$")
from trackme_filter_engine import apply_filter, validate_filter

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkInjectExpectedAdmin_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkInjectExpectedAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_inject_expected(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_inject_expected/admin",
            "resource_group_desc": "Endpoints related to injecting expected sources and hosts (admin operations)",
        }

        return {"payload": response, "status": 200}

    def _read_lookup_rows(self, target_service, lookup_name, logger):
        """Read all rows from a lookup via inputlookup."""
        # Validate lookup name (raises ValueError on invalid names)
        validate_lookup_name(lookup_name)

        search_query = f"| inputlookup {lookup_name}"
        oneshot_results = target_service.jobs.oneshot(
            search_query, output_mode="json", count=0
        )
        raw = oneshot_results.read()
        data = json.loads(raw)
        rows = data.get("results", [])
        return rows

    def _apply_field_mappings(self, rows, field_mappings, component):
        """Apply field mappings to lookup rows and produce entity candidates."""
        entities = []
        errors = []

        # Characters that would break the SPL makeresults pipeline used by the
        # execute path. The `#` is used as a row delimiter, `"` and `\` would
        # break the JSON-like eval string. None of these are valid in Splunk
        # index/sourcetype/host values in practice, so we reject rows containing
        # them defensively.
        unsafe_chars = ('#', '"', '\\')

        for row_idx, row in enumerate(rows):
            entity = {}
            valid = True

            for mapping in field_mappings:
                lookup_field = mapping.get("lookupField", "")
                entity_field = mapping.get("entityField", "")

                if not lookup_field or not entity_field:
                    continue

                value = row.get(lookup_field, "")
                if value is None:
                    value = ""
                value_str = str(value).strip()

                # Reject values containing SPL-unsafe characters
                if any(c in value_str for c in unsafe_chars):
                    errors.append(
                        f"Row {row_idx + 1}: field '{entity_field}' value contains unsafe characters (#, \", or \\\\): {value_str!r}"
                    )
                    valid = False
                    break

                entity[entity_field] = value_str

            if not valid:
                continue

            # Validate required fields
            if component == "dsm":
                if not entity.get("index") or not entity.get("sourcetype"):
                    errors.append(f"Row {row_idx + 1}: missing required index or sourcetype")
                    valid = False
            elif component == "dhm":
                if not entity.get("host"):
                    errors.append(f"Row {row_idx + 1}: missing required host")
                    valid = False

            if valid:
                entities.append(entity)

        return entities, errors

    def _build_dsm_object_name(self, entity):
        """Build the DSM entity object name as index:sourcetype (matches trackmepushdatasource)."""
        index_val = entity.get("index", "").lower()
        sourcetype_val = entity.get("sourcetype", "").lower()
        return f"{index_val}:{sourcetype_val}"

    def _create_recurring_schedule(
        self,
        request_info,
        service,
        trackme_conf,
        tenant_id,
        component,
        lookup_name,
        field_mappings,
        account,
        custom_schedule_name,
        custom_cron_schedule,
        match_asset_field=True,
    ):
        """Create a recurring saved search that re-executes the injection.

        Returns a tuple of (schedule_created, schedule_name, schedule_error).
        """
        schedule_created = False
        schedule_error = None
        schedule_name = None

        try:
            # TrackMe sharing level
            trackme_default_sharing = trackme_conf["trackme_conf"]["trackme_general"][
                "trackme_default_sharing"
            ]

            # Retrieve the virtual tenant record for ACL
            collection_vtenants = service.kvstore["kv_trackme_virtual_tenants"]
            vtenant_record = collection_vtenants.data.query(
                query=json.dumps({"tenant_id": tenant_id})
            )[0]

            owner = vtenant_record.get("tenant_owner")

            component_label = "Sources" if component == "dsm" else "Hosts"
            schedule_prefix = f"TrackMe - Inject Expected {component_label} - {tenant_id} - "

            # Use custom schedule name or generate default
            # Enforce prefix so schedules remain manageable via list/delete endpoints
            # Use rstrip to avoid double-prefix when user name has minor spacing differences
            schedule_prefix_check = schedule_prefix.rstrip()
            if custom_schedule_name:
                if not custom_schedule_name.startswith(schedule_prefix_check):
                    schedule_name = schedule_prefix + custom_schedule_name
                else:
                    schedule_name = custom_schedule_name
            else:
                schedule_name = schedule_prefix + lookup_name

            # Build the REST call body for the recurring search
            inject_body = {
                "tenant_id": tenant_id,
                "component": component,
                "lookup_name": lookup_name,
                "field_mappings": field_mappings,
                "account": account,
            }
            # Persist the asset-recognition choice so scheduled runs honour it
            # (DHM only — DSM has no asset field).
            if component == "dhm":
                inject_body["match_asset_field"] = bool(match_asset_field)

            # Build the body string for the trackme command.
            # Keep the payload as *valid JSON* (so the trackme command parses it on
            # the json.loads fast-path) and escape it for embedding inside the
            # double-quoted SPL body="..." argument: backslashes first, then double
            # quotes. Splunk un-escapes \" -> " / \\ -> \ when it parses the saved
            # search, so the command receives the original JSON intact.
            #
            # The previous implementation did json.dumps(...).replace('"', "'"),
            # which produced a string that was neither valid JSON (single-quoted
            # keys) nor a valid Python literal (JSON booleans/null stay lowercase
            # `true`/`false`/`null`, which ast.literal_eval rejects). On DHM the
            # match_asset_field boolean made every scheduled run fail to parse.
            body_json = json.dumps(inject_body, ensure_ascii=True)
            body_str = body_json.replace("\\", "\\\\").replace('"', '\\"')
            report_search = (
                f'| trackme mode=post url="/services/trackme/v2/splk_inject_expected/admin/inject_execute" '
                f'body="{body_str}"'
            )

            # Use custom cron schedule or generate random nightly default
            if custom_cron_schedule:
                cron_schedule = custom_cron_schedule
            else:
                random_minute = random.randint(0, 59)
                random_hour = random.randint(1, 5)
                cron_schedule = f"{random_minute} {random_hour} * * *"

            report_properties = {
                "description": f"Recurring injection of expected {component_label.lower()} from lookup {lookup_name}",
                "is_scheduled": True,
                "schedule_window": "auto",
                "cron_schedule": cron_schedule,
                "dispatch.earliest_time": "-1h",
                "dispatch.latest_time": "now",
            }

            report_acl = {
                "owner": owner,
                "sharing": trackme_default_sharing,
                "perms.write": vtenant_record.get("tenant_roles_admin"),
                "perms.read": f"{vtenant_record.get('tenant_roles_user')},{vtenant_record.get('tenant_roles_power')}",
            }

            create_result = trackme_create_report(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                schedule_name,
                report_search,
                report_properties,
                report_acl,
            )

            # trackme_create_report returns a dict on cron validation failure
            # instead of raising, so check the result
            if isinstance(create_result, dict) and create_result.get("action") == "success":
                schedule_created = True
            elif isinstance(create_result, dict) and create_result.get("payload", {}).get("action") == "failure":
                schedule_error = create_result.get("payload", {}).get("response", "Unknown schedule creation error")
            else:
                schedule_error = "Unexpected response from schedule creation"

            if schedule_created:
                logger.info(
                    f'tenant_id="{tenant_id}", recurring schedule created successfully, schedule_name="{schedule_name}"'
                )
            else:
                logger.error(
                    f'tenant_id="{tenant_id}", recurring schedule creation failed, schedule_name="{schedule_name}", error="{schedule_error}"'
                )

        except Exception as e:
            schedule_error = str(e)
            logger.error(
                f'tenant_id="{tenant_id}", failed to create recurring schedule, exception="{schedule_error}"'
            )

        return schedule_created, schedule_name, schedule_error

    def _build_dhm_object_name(self, host_val):
        """Build the DHM object name from a raw hostname.
        DHM objects use the format key:host|{hostname} (lowercased)."""
        if host_val.lower().startswith("key:host|"):
            return host_val.lower()
        return f"key:host|{host_val}".lower()

    # Simulate injection (dry run)
    def post_inject_simulate(self, request_info, **kwargs):

        # Declare
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:

                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "tenant_id is required"},
                        "status": 500,
                    }

                # Validate tenant_id format to prevent any risk of SPL
                # injection via interpolation in the execute pipeline
                if not tenant_id or not _TENANT_ID_RE.match(str(tenant_id)):
                    return {
                        "payload": {"action": "failure", "response": f'Invalid tenant_id format: "{tenant_id}" (allowed: alphanumeric, underscores, hyphens)'},
                        "status": 400,
                    }

                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "component is required"},
                        "status": 500,
                    }

                if component not in ("dsm", "dhm"):
                    return {
                        "payload": {"action": "failure", "response": "component must be dsm or dhm"},
                        "status": 400,
                    }

                try:
                    lookup_name = resp_dict["lookup_name"]
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "lookup_name is required"},
                        "status": 500,
                    }

                try:
                    field_mappings = resp_dict["field_mappings"]
                    if isinstance(field_mappings, str):
                        field_mappings = json.loads(field_mappings)
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "field_mappings is required"},
                        "status": 500,
                    }

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint simulates injection of expected sources/hosts from a lookup, it requires a POST call with the following information:",
                "resource_desc": "Simulate expected sources/hosts injection",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_inject_expected/admin/inject_simulate" body="{\'tenant_id\': \'mytenant\', \'component\': \'dsm\', \'lookup_name\': \'example_expected_data_sources\', \'field_mappings\': [{\'lookupField\': \'index\', \'entityField\': \'index\'}, {\'lookupField\': \'sourcetype\', \'entityField\': \'sourcetype\'}]}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) dsm or dhm",
                        "lookup_name": "(required) Name of the lookup transform",
                        "field_mappings": "(required) Array of {lookupField, entityField} pairs",
                        "account": "(optional) Remote Splunk deployment account name, defaults to local",
                        "match_asset_field": "(optional, DHM only) Recognise already-known machines via the asset field (short<->FQDN variations), default true",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # optional account
        account = resp_dict.get("account", "local")

        # asset-based recognition toggle (DHM only) — ON by default. When on, an
        # incoming host is treated as already known if any of its variations
        # (short hostname / FQDN / key:host| form) matches an existing entity's
        # `asset` field, not just an exact `object` match.
        match_asset_field = interpret_boolean(resp_dict.get("match_asset_field", True))

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Resolve target service (local or remote) for lookup access
        try:
            target_service = resolve_service_for_account(service, request_info, account, logger)
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Failed to connect to remote account "{account}": {str(e)}',
                },
                "status": 503,
            }

        try:
            # Read lookup rows
            rows = self._read_lookup_rows(target_service, lookup_name, logger)

            # Apply field mappings
            entities, mapping_errors = self._apply_field_mappings(rows, field_mappings, component)

            # Check for existing entities
            entities_new = []
            entities_existing = []

            # Both DSM and DHM entities live in kv_trackme_{component}_tenant_{tid}
            collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            existing_records = []
            try:
                collection = service.kvstore[collection_name]
                existing_records = collection.data.query()
                # Lowercase for consistent case-insensitive comparison with built object names
                existing_objects = {str(r.get("object", "")).lower() for r in existing_records}
            except Exception as e:
                existing_objects = set()

            # Asset index for DHM asset-based recognition (built once). Empty for
            # DSM, or when the toggle is off, so the match short-circuits to False.
            asset_index = (
                build_dhm_asset_index(existing_records)
                if (component == "dhm" and match_asset_field)
                else set()
            )
            asset_match_count = 0

            if component == "dsm":
                for entity in entities:
                    obj_name = self._build_dsm_object_name(entity)
                    entity["_object_name"] = obj_name
                    if obj_name in existing_objects:
                        entities_existing.append(entity)
                    else:
                        entities_new.append(entity)
                        existing_objects.add(obj_name)

            elif component == "dhm":
                for entity in entities:
                    host_val = entity.get("host", "")
                    obj_name = self._build_dhm_object_name(host_val)
                    entity["_object_name"] = obj_name
                    entity["_host"] = host_val
                    if obj_name in existing_objects:
                        entities_existing.append(entity)
                    elif asset_index and dhm_host_matches_asset_index(
                        obj_name, host_val, asset_index
                    ):
                        # recognised via an asset variation (short <-> FQDN etc.)
                        entity["_matched_via"] = "asset"
                        entities_existing.append(entity)
                        asset_match_count += 1
                    else:
                        entities_new.append(entity)
                        existing_objects.add(obj_name)

            response = {
                "action": "success",
                "component": component,
                "lookup_name": lookup_name,
                "total_lookup_rows": len(rows),
                "total_valid_entities": len(entities),
                "total_new": len(entities_new),
                "total_existing": len(entities_existing),
                "total_existing_asset_match": asset_match_count,
                "match_asset_field": bool(component == "dhm" and match_asset_field),
                "entities_new": entities_new[:100],  # Limit preview to 100
                "entities_existing": entities_existing[:100],
                "mapping_errors": mapping_errors[:20],
            }

            return {"payload": response, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Host coverage gap analysis (DHM): reconcile a lookup (e.g. a CMDB) against
    # the hosts TrackMe tracks, in both directions. Read-only.
    def post_coverage_gaps(self, request_info, **kwargs):

        # Declare
        describe = False

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception:
                    return {
                        "payload": {"action": "failure", "response": "tenant_id is required"},
                        "status": 500,
                    }

                # Validate tenant_id format (defence in depth, mirrors the other endpoints)
                if not tenant_id or not _TENANT_ID_RE.match(str(tenant_id)):
                    return {
                        "payload": {"action": "failure", "response": f'Invalid tenant_id format: "{tenant_id}" (allowed: alphanumeric, underscores, hyphens)'},
                        "status": 400,
                    }

                # comparison source: "lookup" (default) or "search"
                source_type = str(resp_dict.get("source_type", "lookup") or "lookup").lower()
                if source_type not in ("lookup", "search"):
                    return {
                        "payload": {"action": "failure", "response": "source_type must be 'lookup' or 'search'"},
                        "status": 400,
                    }

                lookup_name = None
                field_mappings = None
                if source_type == "lookup":
                    try:
                        lookup_name = resp_dict["lookup_name"]
                    except Exception:
                        return {
                            "payload": {"action": "failure", "response": "lookup_name is required"},
                            "status": 500,
                        }
                    try:
                        field_mappings = resp_dict["field_mappings"]
                        if isinstance(field_mappings, str):
                            field_mappings = json.loads(field_mappings)
                    except Exception:
                        return {
                            "payload": {"action": "failure", "response": "field_mappings is required"},
                            "status": 500,
                        }
                else:  # search
                    if not str(resp_dict.get("root_constraint", "") or "").strip():
                        return {
                            "payload": {"action": "failure", "response": "root_constraint is required for source_type=search"},
                            "status": 400,
                        }
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint performs a Host coverage gap analysis for DHM: it reconciles a lookup (e.g. a CMDB) against the hosts tracked by TrackMe and returns the hosts only in the lookup, only in TrackMe, and in both. It requires a POST call with the following information:",
                "resource_desc": "Host coverage gap analysis (DHM)",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_inject_expected/admin/coverage_gaps" body="{\'tenant_id\': \'mytenant\', \'lookup_name\': \'my_cmdb_lookup\', \'field_mappings\': [{\'lookupField\': \'ci_name\', \'entityField\': \'host\'}]}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "source_type": "(optional) 'lookup' (default) or 'search' — where the reference host list comes from",
                        "lookup_name": "(required for source_type=lookup) Name of the lookup transform (the reference inventory)",
                        "field_mappings": "(required for source_type=lookup) Array of {lookupField, entityField} pairs mapping a lookup field to host",
                        "search_mode": "(source_type=search) 'tstats' (default) or 'raw'",
                        "root_constraint": "(required for source_type=search) base SPL constraint, e.g. index=firewalls",
                        "host_field": "(source_type=search) host metadata field, default 'host'",
                        "earliest_time": "(source_type=search) defaults to -30d (tstats) / -24h (raw)",
                        "latest_time": "(source_type=search) defaults to now",
                        "account": "(optional) Remote Splunk deployment account name, defaults to local",
                        "filter_expression": "(optional, source_type=lookup) TrackMe filter DSL applied to the lookup rows before comparison",
                        "match_asset_field": "(optional) Recognise short<->FQDN variations via the asset field, default true",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Host coverage gaps are DHM-only (the asset field is DHM-specific)
        component = "dhm"

        # optional parameters
        account = resp_dict.get("account", "local")
        filter_expression = resp_dict.get("filter_expression", "") or ""
        match_asset_field = interpret_boolean(resp_dict.get("match_asset_field", True))
        # Hard safety cap on rows returned per bucket (full lists feed the CSV
        # export). Realistic inventories are well under this; truncation is flagged.
        max_rows = 100000

        # search-source parameters (only used when source_type == "search").
        # root_constraint is SPL by design — control-char sanitised only, like the
        # hybrid tracker wizard. host_field is spliced unquoted into the `by` clause,
        # so it is validated as a simple identifier.
        search_mode = str(resp_dict.get("search_mode", "tstats") or "tstats").lower()
        if search_mode not in ("tstats", "raw"):
            return {
                "payload": {"action": "failure", "response": "search_mode must be 'tstats' or 'raw'"},
                "status": 400,
            }
        root_constraint = sanitize_spl_input(str(resp_dict.get("root_constraint", "") or "")).strip()
        host_field = str(resp_dict.get("host_field", "host") or "host").strip()
        if source_type == "search" and not _HOST_FIELD_RE.match(host_field):
            return {
                "payload": {"action": "failure", "response": f'invalid host_field "{host_field}" (must be a simple field identifier)'},
                "status": 400,
            }
        default_earliest = "-30d" if search_mode == "tstats" else "-24h"
        search_earliest = str(resp_dict.get("earliest_time") or default_earliest)
        search_latest = str(resp_dict.get("latest_time") or "now")
        # Validate the time specifiers — they are interpolated into the quoted
        # splunkremotesearch args, so reject anything that isn't a Splunk time
        # modifier (prevents breaking out of the quoted-arg context).
        if source_type == "search":
            for _label, _value in (("earliest_time", search_earliest), ("latest_time", search_latest)):
                if not _TIME_SPECIFIER_RE.match(_value):
                    return {
                        "payload": {"action": "failure", "response": f'invalid {_label} "{_value}" (must be a Splunk time specifier, e.g. -30d, @d, now)'},
                        "status": 400,
                    }

        # Validate the filter expression up-front for a clean error
        if filter_expression:
            filter_error = validate_filter(filter_expression)
            if filter_error:
                return {
                    "payload": {"action": "failure", "response": f"invalid filter_expression: {filter_error}"},
                    "status": 400,
                }

        # Get splunkd port + service
        splunkd_port = request_info.server_rest_port
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Resolve target service (local or remote) for lookup access
        try:
            target_service = resolve_service_for_account(service, request_info, account, logger)
        except Exception as e:
            return {
                "payload": {"action": "failure", "response": f'Failed to connect to remote account "{account}": {str(e)}'},
                "status": 503,
            }

        try:
            if source_type == "search":
                # Compose the comparison search from the root constraint + host field.
                if search_mode == "tstats":
                    base_search = f"| tstats count where {root_constraint} by {host_field}"
                else:  # raw
                    base_search = f"{root_constraint} | stats count by {host_field}"

                # Run on the selected remote account when one is chosen (mirrors the
                # hybrid tracker remote pattern); otherwise run locally.
                if account and account != "local":
                    escaped = base_search.replace('"', '\\"')
                    search_query = (
                        f'| splunkremotesearch account="{account}" search="{escaped}" '
                        f'earliest="{search_earliest}" latest="{search_latest}" | fields - _raw'
                    )
                else:
                    search_query = base_search

                kwargs_search = {
                    "app": "trackme",
                    "earliest_time": search_earliest,
                    "latest_time": search_latest,
                    "output_mode": "json",
                    "count": 0,
                }
                logger.info(
                    f'tenant_id="{tenant_id}", coverage gap analysis search source, '
                    f'search_mode="{search_mode}", account="{account}", host_field="{host_field}"'
                )
                reader = run_splunk_search(service, search_query, kwargs_search, 24, 5)
                source_rows = [item for item in reader if isinstance(item, dict)]
                total_lookup_rows = len(source_rows)
                mapping_errors = []

                lookup_entries = []
                for row in source_rows:
                    host_val = str(row.get(host_field, "") or "").strip()
                    if not host_val:
                        continue
                    if host_val.lower().startswith("key:host|"):
                        host_val = host_val[len("key:host|"):]
                    obj_name = self._build_dhm_object_name(host_val)
                    lookup_entries.append(
                        {"host": host_val, "object": obj_name, "count": row.get("count", "")}
                    )
                total_valid = len(lookup_entries)
            else:
                # Read lookup rows from the (local or remote) reference inventory
                rows = self._read_lookup_rows(target_service, lookup_name, logger)
                total_lookup_rows = len(rows)

                # Apply the optional filter DSL to the lookup rows (fail-closed on
                # an unparseable expression — already validated above)
                if filter_expression:
                    rows = apply_filter(rows, filter_expression)

                # Map a lookup field -> host
                entities, mapping_errors = self._apply_field_mappings(rows, field_mappings, component)

                # Normalise lookup entries to {object, host, ...original columns}
                lookup_entries = []
                for entity in entities:
                    host_val = entity.get("host", "")
                    if host_val.lower().startswith("key:host|"):
                        host_val = host_val[len("key:host|"):]
                    obj_name = self._build_dhm_object_name(host_val)
                    # pass through the mapped columns (drop internal markers)
                    passthrough = {k: v for k, v in entity.items() if not str(k).startswith("_")}
                    passthrough["host"] = host_val
                    passthrough["object"] = obj_name
                    lookup_entries.append(passthrough)
                total_valid = len(entities)

            # Load tracked DHM entities
            collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            try:
                collection = service.kvstore[collection_name]
                existing_records = collection.data.query()
            except Exception as e:
                logger.warning(
                    f'tenant_id="{tenant_id}", could not load tracked entities for coverage gap analysis, '
                    f'exception="{str(e)}"'
                )
                existing_records = []

            # Reconcile the two referentials
            result = dhm_reconcile_hosts(
                existing_records, lookup_entries, match_asset_field=match_asset_field
            )

            buckets = {}
            truncated = {}
            counts = {}
            for key in ("only_in_lookup", "in_both", "only_in_trackme"):
                full = result.get(key, [])
                counts[key] = len(full)
                truncated[key] = len(full) > max_rows
                buckets[key] = full[:max_rows]

            response = {
                "action": "success",
                "component": component,
                "source_type": source_type,
                "lookup_name": lookup_name,
                "search_mode": search_mode if source_type == "search" else None,
                "total_lookup_rows": total_lookup_rows,
                "total_lookup_after_filter": total_valid,
                "total_tracked_entities": len(existing_records),
                "match_asset_field": match_asset_field,
                "filter_expression": filter_expression,
                "counts": counts,
                "truncated": truncated,
                "rows": buckets,
                "mapping_errors": mapping_errors[:20],
            }
            return {"payload": response, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Feeds coverage gap analysis (DSM): reconcile a reference (lookup or Splunk
    # search) against the feed entities TrackMe tracks, at a configurable break-by
    # grain (default index, sourcetype). Read-only.
    def post_feeds_coverage_gaps(self, request_info, **kwargs):

        # Declare
        describe = False

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception:
                    return {
                        "payload": {"action": "failure", "response": "tenant_id is required"},
                        "status": 500,
                    }

                if not tenant_id or not _TENANT_ID_RE.match(str(tenant_id)):
                    return {
                        "payload": {"action": "failure", "response": f'Invalid tenant_id format: "{tenant_id}" (allowed: alphanumeric, underscores, hyphens)'},
                        "status": 400,
                    }

                source_type = str(resp_dict.get("source_type", "lookup") or "lookup").lower()
                if source_type not in ("lookup", "search"):
                    return {
                        "payload": {"action": "failure", "response": "source_type must be 'lookup' or 'search'"},
                        "status": 400,
                    }

                field_mappings = None
                if source_type == "lookup":
                    try:
                        lookup_name = resp_dict["lookup_name"]
                    except Exception:
                        return {
                            "payload": {"action": "failure", "response": "lookup_name is required"},
                            "status": 500,
                        }
                    try:
                        field_mappings = resp_dict["field_mappings"]
                        if isinstance(field_mappings, str):
                            field_mappings = json.loads(field_mappings)
                    except Exception:
                        return {
                            "payload": {"action": "failure", "response": "field_mappings is required"},
                            "status": 500,
                        }
                else:  # search
                    lookup_name = None
                    if not str(resp_dict.get("root_constraint", "") or "").strip():
                        return {
                            "payload": {"action": "failure", "response": "root_constraint is required for source_type=search"},
                            "status": 400,
                        }
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint performs a Feeds coverage gap analysis for DSM: it reconciles a reference (a lookup or a Splunk search) against the DSM feed entities tracked by TrackMe, at a configurable break-by grain, and returns the feeds only in the reference, only in TrackMe, and in both.",
                "resource_desc": "Feeds coverage gap analysis (DSM)",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_inject_expected/admin/feeds_coverage_gaps" body="{\'tenant_id\': \'mytenant\', \'breakby_sequence\': \'index, sourcetype\', \'lookup_name\': \'my_feeds_lookup\', \'field_mappings\': [{\'lookupField\': \'idx\', \'entityField\': \'index\'}, {\'lookupField\': \'st\', \'entityField\': \'sourcetype\'}]}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "breakby_sequence": "(optional) comma-separated break-by fields, default 'index, sourcetype' (the comparison grain)",
                        "source_type": "(optional) 'lookup' (default) or 'search'",
                        "lookup_name": "(required for source_type=lookup) Name of the lookup transform",
                        "field_mappings": "(required for source_type=lookup) Array of {lookupField, entityField} — one per break-by field",
                        "search_mode": "(source_type=search) 'tstats' (default) or 'raw'",
                        "root_constraint": "(required for source_type=search) base SPL constraint, e.g. index=siem-*",
                        "earliest_time": "(source_type=search) defaults -30d (tstats) / -24h (raw)",
                        "latest_time": "(source_type=search) defaults now",
                        "account": "(optional) Remote Splunk deployment account name, defaults to local",
                        "filter_expression": "(optional, source_type=lookup) TrackMe filter DSL applied to the lookup rows",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        component = "dsm"

        # break-by sequence (the comparison grain). Each field is spliced unquoted
        # into the SPL `by` clause, so it must be a simple identifier.
        breakby_raw = str(resp_dict.get("breakby_sequence", "index, sourcetype") or "index, sourcetype")
        breakby_fields = [f.strip() for f in breakby_raw.split(",") if f.strip()]
        if not breakby_fields:
            return {
                "payload": {"action": "failure", "response": "breakby_sequence must contain at least one field"},
                "status": 400,
            }
        if len(breakby_fields) > 8:
            return {
                "payload": {"action": "failure", "response": "breakby_sequence is limited to 8 fields"},
                "status": 400,
            }
        for _f in breakby_fields:
            if not _HOST_FIELD_RE.match(_f):
                return {
                    "payload": {"action": "failure", "response": f'invalid break-by field "{_f}" (must be a simple field identifier)'},
                    "status": 400,
                }

        # optional parameters
        account = resp_dict.get("account", "local")
        filter_expression = resp_dict.get("filter_expression", "") or ""
        max_rows = 100000

        # search-source parameters
        search_mode = str(resp_dict.get("search_mode", "tstats") or "tstats").lower()
        if search_mode not in ("tstats", "raw"):
            return {
                "payload": {"action": "failure", "response": "search_mode must be 'tstats' or 'raw'"},
                "status": 400,
            }
        root_constraint = sanitize_spl_input(str(resp_dict.get("root_constraint", "") or "")).strip()
        default_earliest = "-30d" if search_mode == "tstats" else "-24h"
        search_earliest = str(resp_dict.get("earliest_time") or default_earliest)
        search_latest = str(resp_dict.get("latest_time") or "now")
        if source_type == "search":
            for _label, _value in (("earliest_time", search_earliest), ("latest_time", search_latest)):
                if not _TIME_SPECIFIER_RE.match(_value):
                    return {
                        "payload": {"action": "failure", "response": f'invalid {_label} "{_value}" (must be a Splunk time specifier, e.g. -30d, @d, now)'},
                        "status": 400,
                    }

        if filter_expression:
            filter_error = validate_filter(filter_expression)
            if filter_error:
                return {
                    "payload": {"action": "failure", "response": f"invalid filter_expression: {filter_error}"},
                    "status": 400,
                }

        splunkd_port = request_info.server_rest_port
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            target_service = resolve_service_for_account(service, request_info, account, logger)
        except Exception as e:
            return {
                "payload": {"action": "failure", "response": f'Failed to connect to remote account "{account}": {str(e)}'},
                "status": 503,
            }

        try:
            reference_entries = []
            mapping_errors = []

            if source_type == "search":
                by_clause = ", ".join(breakby_fields)
                if search_mode == "tstats":
                    base_search = f"| tstats count where {root_constraint} by {by_clause}"
                else:  # raw
                    base_search = f"{root_constraint} | stats count by {by_clause}"

                if account and account != "local":
                    escaped = base_search.replace('"', '\\"')
                    search_query = (
                        f'| splunkremotesearch account="{account}" search="{escaped}" '
                        f'earliest="{search_earliest}" latest="{search_latest}" | fields - _raw'
                    )
                else:
                    search_query = base_search

                kwargs_search = {
                    "app": "trackme",
                    "earliest_time": search_earliest,
                    "latest_time": search_latest,
                    "output_mode": "json",
                    "count": 0,
                }
                logger.info(
                    f'tenant_id="{tenant_id}", feeds coverage gap analysis search source, '
                    f'search_mode="{search_mode}", account="{account}", breakby="{by_clause}"'
                )
                reader = run_splunk_search(service, search_query, kwargs_search, 24, 5)
                source_rows = [item for item in reader if isinstance(item, dict)]
                total_source_rows = len(source_rows)

                for row in source_rows:
                    values = [row.get(f, "") for f in breakby_fields]
                    cmp_key = build_feed_comparison_key(values)
                    if not cmp_key:
                        continue
                    entry = {f: row.get(f, "") for f in breakby_fields}
                    entry["_cmp_key"] = cmp_key
                    reference_entries.append(entry)
            else:
                rows = self._read_lookup_rows(target_service, lookup_name, logger)
                total_source_rows = len(rows)

                if filter_expression:
                    rows = apply_filter(rows, filter_expression)

                # build the lookupField -> entityField map; every break-by field
                # must be mapped to a lookup column
                mapping = {}
                for fm in field_mappings or []:
                    if isinstance(fm, dict) and fm.get("lookupField") and fm.get("entityField"):
                        mapping[str(fm["entityField"])] = str(fm["lookupField"])
                unmapped = [f for f in breakby_fields if f not in mapping]
                if unmapped:
                    return {
                        "payload": {"action": "failure", "response": f'every break-by field must be mapped to a lookup column; missing: {", ".join(unmapped)}'},
                        "status": 400,
                    }

                for row in rows:
                    values = [row.get(mapping[f], "") for f in breakby_fields]
                    cmp_key = build_feed_comparison_key(values)
                    if not cmp_key:
                        mapping_errors.append("row with empty break-by values skipped")
                        continue
                    entry = {f: row.get(mapping[f], "") for f in breakby_fields}
                    entry["_cmp_key"] = cmp_key
                    reference_entries.append(entry)

            total_valid = len(reference_entries)

            # Load tracked DSM entities and reduce each to the break-by grain.
            collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            try:
                collection = service.kvstore[collection_name]
                existing_records = collection.data.query()
            except Exception as e:
                logger.warning(
                    f'tenant_id="{tenant_id}", could not load tracked feeds for coverage gap analysis, '
                    f'exception="{str(e)}"'
                )
                existing_records = []

            def _resolve_feed_field(record, field):
                # index/sourcetype are stored as data_index/data_sourcetype;
                # any other break-by field is read directly when present.
                if field == "index":
                    return record.get("data_index")
                if field == "sourcetype":
                    return record.get("data_sourcetype")
                return record.get(field)

            trackme_entries = []
            for record in existing_records:
                if not isinstance(record, dict):
                    continue
                values = [_resolve_feed_field(record, f) for f in breakby_fields]
                cmp_key = build_feed_comparison_key(values)
                if not cmp_key:
                    continue
                trackme_entries.append(
                    {
                        "_cmp_key": cmp_key,
                        "object": record.get("object"),
                        "data_index": record.get("data_index"),
                        "data_sourcetype": record.get("data_sourcetype"),
                    }
                )

            result = reconcile_feed_keys(trackme_entries, reference_entries)

            buckets = {}
            truncated = {}
            counts = {}
            for key in ("only_in_lookup", "in_both", "only_in_trackme"):
                full = result.get(key, [])
                counts[key] = len(full)
                truncated[key] = len(full) > max_rows
                buckets[key] = full[:max_rows]

            response = {
                "action": "success",
                "component": component,
                "source_type": source_type,
                "lookup_name": lookup_name,
                "search_mode": search_mode if source_type == "search" else None,
                "breakby_sequence": breakby_fields,
                "total_lookup_rows": total_source_rows,
                "total_lookup_after_filter": total_valid,
                "total_tracked_entities": len(existing_records),
                "filter_expression": filter_expression,
                "counts": counts,
                "truncated": truncated,
                "rows": buckets,
                "mapping_errors": mapping_errors[:20],
            }
            return {"payload": response, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Execute injection
    def post_inject_execute(self, request_info, **kwargs):

        # Declare
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:

                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "tenant_id is required"},
                        "status": 500,
                    }

                # Validate tenant_id format to prevent any risk of SPL
                # injection via interpolation in the execute pipeline
                if not tenant_id or not _TENANT_ID_RE.match(str(tenant_id)):
                    return {
                        "payload": {"action": "failure", "response": f'Invalid tenant_id format: "{tenant_id}" (allowed: alphanumeric, underscores, hyphens)'},
                        "status": 400,
                    }

                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "component is required"},
                        "status": 500,
                    }

                if component not in ("dsm", "dhm"):
                    return {
                        "payload": {"action": "failure", "response": "component must be dsm or dhm"},
                        "status": 400,
                    }

                try:
                    lookup_name = resp_dict["lookup_name"]
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "lookup_name is required"},
                        "status": 500,
                    }

                try:
                    field_mappings = resp_dict["field_mappings"]
                    if isinstance(field_mappings, str):
                        field_mappings = json.loads(field_mappings)
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "field_mappings is required"},
                        "status": 500,
                    }

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint executes injection of expected sources/hosts from a lookup, it requires a POST call with the following information:",
                "resource_desc": "Execute expected sources/hosts injection",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_inject_expected/admin/inject_execute" body="{\'tenant_id\': \'mytenant\', \'component\': \'dsm\', \'lookup_name\': \'example_expected_data_sources\', \'field_mappings\': [{\'lookupField\': \'index\', \'entityField\': \'index\'}, {\'lookupField\': \'sourcetype\', \'entityField\': \'sourcetype\'}]}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) dsm or dhm",
                        "lookup_name": "(required) Name of the lookup transform",
                        "field_mappings": "(required) Array of {lookupField, entityField} pairs",
                        "account": "(optional) Remote Splunk deployment account name, defaults to local",
                        "match_asset_field": "(optional, DHM only) Recognise already-known machines via the asset field (short<->FQDN variations), default true",
                        "create_schedule": "(optional) If true, create a recurring saved search for this injection",
                        "update_comment": "(optional) Comment for the audit record",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # optional parameters
        account = resp_dict.get("account", "local")
        create_schedule = resp_dict.get("create_schedule", False)
        if isinstance(create_schedule, str):
            create_schedule = create_schedule.lower() in ("true", "1", "yes")
        update_comment = resp_dict.get("update_comment", "Inject expected sources/hosts from lookup")
        custom_schedule_name = resp_dict.get("schedule_name", None)
        custom_cron_schedule = resp_dict.get("cron_schedule", None)
        # asset-based recognition toggle (DHM only) — ON by default; see simulate
        match_asset_field = interpret_boolean(resp_dict.get("match_asset_field", True))

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # get TrackMe conf
        trackme_conf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )

        # Resolve target service (local or remote) for lookup access
        try:
            target_service = resolve_service_for_account(service, request_info, account, logger)
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Failed to connect to remote account "{account}": {str(e)}',
                },
                "status": 503,
            }

        try:
            # Read lookup rows
            rows = self._read_lookup_rows(target_service, lookup_name, logger)

            # Apply field mappings
            entities, mapping_errors = self._apply_field_mappings(rows, field_mappings, component)

            if len(entities) == 0:
                return {
                    "payload": {
                        "action": "failure",
                        "response": "No valid entities found after applying field mappings",
                        "mapping_errors": mapping_errors[:20],
                    },
                    "status": 400,
                }

            entities_created = 0
            entities_skipped = 0

            # Pre-filter entities against existing KV store records to avoid
            # sending entities that already exist through the trackmepushdatasource
            # pipeline. This is especially important for recurring schedule runs
            # where the lookup may contain thousands of entities but only a few
            # (or none) are actually new. trackmepushdatasource would also skip
            # existing entities on its side, but pre-filtering avoids running
            # unnecessary SPL searches entirely when nothing needs to be injected.
            main_collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            existing_records = []
            try:
                main_collection = service.kvstore[main_collection_name]
                existing_records = main_collection.data.query()
                existing_objects_set = {
                    str(r.get("object", "")).lower() for r in existing_records
                }
            except Exception as e:
                logger.warning(
                    f'tenant_id="{tenant_id}", could not load existing objects for pre-filter, '
                    f'will rely on trackmepushdatasource dedup only, exception="{str(e)}"'
                )
                existing_objects_set = set()

            # Asset-based recognition index (DHM only, toggle ON). Empty otherwise,
            # so the asset match short-circuits to False and behaviour is unchanged.
            asset_index = (
                build_dhm_asset_index(existing_records)
                if (component == "dhm" and match_asset_field)
                else set()
            )
            entities_skipped_asset_match = 0

            # Build synthetic records for trackmepushdatasource for entities that
            # are NOT already in the KV store. We cannot insert directly into the
            # KV store because the decision maker expects many stub fields to be
            # properly initialized (delay/latency stats, timestamps, etc).
            # trackmepushdatasource handles this via the
            # trackme_{component}_tracker_abstract macro.
            #
            # For DHM, we strip any leading "key:host|" prefix from the raw host
            # value so trackmepushdatasource can normalize it consistently (it
            # only lowercases when it adds the prefix itself; preserving the raw
            # hostname ensures simulate and execute both end up with the same
            # lowercased object name).
            data_strings = []
            for entity in entities:
                if component == "dsm":
                    index_val = entity.get("index", "")
                    sourcetype_val = entity.get("sourcetype", "")
                    obj_name = self._build_dsm_object_name(entity)
                    if obj_name in existing_objects_set:
                        entities_skipped += 1
                        continue
                    existing_objects_set.add(obj_name)  # dedup within this run
                    data_strings.append(
                        f'"index": "{index_val}", "sourcetype": "{sourcetype_val}"'
                    )
                elif component == "dhm":
                    host_val = entity.get("host", "")
                    # Strip any existing key:host| prefix so trackmepushdatasource
                    # applies its own normalization (add prefix + lowercase)
                    if host_val.lower().startswith("key:host|"):
                        host_val = host_val[len("key:host|"):]
                    obj_name = self._build_dhm_object_name(host_val)
                    if obj_name in existing_objects_set:
                        entities_skipped += 1
                        continue
                    # asset-based recognition: skip if a known variation of this
                    # host (short <-> FQDN etc.) already exists on a tracked entity
                    if asset_index and dhm_host_matches_asset_index(
                        obj_name, host_val, asset_index
                    ):
                        entities_skipped += 1
                        entities_skipped_asset_match += 1
                        continue
                    existing_objects_set.add(obj_name)  # dedup within this run
                    data_strings.append(
                        f'"host": "{host_val}"'
                    )

            # Log when nothing new to inject — the for loop below will skip entirely
            # and we'll skip the audit event further down to avoid log pollution
            # on recurring runs that find no new entities
            if len(data_strings) == 0:
                logger.info(
                    f'tenant_id="{tenant_id}", nothing new to inject, all {entities_skipped} '
                    f'entities already exist in the KV store'
                )

            # Escape double quotes for SPL string embedding
            data_strings = [ds.replace('"', '\\"') for ds in data_strings]

            # Batch entities to avoid SPL query length limits (~100K chars).
            # Each entity contributes ~50-70 escaped chars, so batch conservatively
            # at 500 entities per search (~30-35KB per query, well under the limit).
            batch_size = 500
            search_kwargs = {
                "earliest_time": "-5m",
                "latest_time": "now",
                "count": 0,
                "output_mode": "json",
            }

            # Track partial batch failures so that entities already written by
            # earlier successful batches are still reported to the caller and
            # recorded in the audit trail (see "Partial batch failure" fix).
            batch_error = None
            failed_batch_index = None

            for batch_start in range(0, len(data_strings), batch_size):
                batch = data_strings[batch_start:batch_start + batch_size]

                # Build the SPL pipeline for this batch
                search_query = remove_leading_spaces(
                    f"""
                    | makeresults
                    | eval data = "{'#'.join(batch)}"
                    | eval data = split(data, "#")
                    | mvexpand data
                    | eval data = "{{" . data . "}}"
                    | fields - _time
                    | spath input=data
                    | fields - data
                    | trackmepushdatasource tenant_id={tenant_id} component={component} search_type=tstats
                    """
                ).strip()

                logger.debug(
                    f'inject_execute batch {batch_start // batch_size + 1}, '
                    f'size={len(batch)}, search_query_len={len(search_query)}'
                )

                try:
                    reader = run_splunk_search(
                        service,
                        search_query,
                        search_kwargs,
                        24,  # max_retries
                        5,  # retry_delay
                    )

                    # Parse the summary yielded by trackmepushdatasource for this batch.
                    # We already tracked entities_skipped via pre-filter, so only accumulate
                    # new_records_added here. Any existing_records reported by trackmepushdatasource
                    # would indicate race conditions (entity created between pre-filter and insert)
                    # which we count as skipped as well.
                    for item in reader:
                        if isinstance(item, dict):
                            if "error" in item:
                                raise Exception(f"trackmepushdatasource error: {item['error']}")
                            entities_created += int(item.get("new_records_added", 0))
                            entities_skipped += int(item.get("existing_records", 0))

                except Exception as e:
                    batch_error = str(e)
                    failed_batch_index = batch_start // batch_size + 1
                    logger.error(
                        f'tenant_id="{tenant_id}", failed to execute trackmepushdatasource on '
                        f'batch {failed_batch_index}, entities_created_so_far={entities_created}, '
                        f'exception="{batch_error}"'
                    )
                    # Stop processing further batches but still fall through
                    # to record the audit event and return the partial counts
                    break

            # Record audit event only when something actually changed — avoids
            # polluting the audit log with no-op entries from recurring scheduled
            # runs that find no new entities in the lookup. We log even on
            # partial failures so the audit trail reflects what was actually
            # written to the KV store before the failing batch.
            if entities_created > 0:
                audit_status = "failure" if batch_error else "success"
                audit_message = (
                    f"Injected {entities_created} new entities from lookup {lookup_name}, "
                    f"skipped {entities_skipped} existing"
                )
                if batch_error:
                    audit_message += (
                        f" (partial failure: batch {failed_batch_index} failed, "
                        f"remaining entities not processed)"
                    )
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    request_info.user,
                    audit_status,
                    f"inject expected {component}",
                    lookup_name,
                    "inject_expected",
                    json.dumps({
                        "entities_created": entities_created,
                        "entities_skipped": entities_skipped,
                        "entities_skipped_asset_match": entities_skipped_asset_match,
                        "lookup_name": lookup_name,
                        "component": component,
                        "partial_failure": bool(batch_error),
                        "failed_batch_index": failed_batch_index,
                        "batch_error": batch_error,
                    }),
                    audit_message,
                    str(update_comment),
                )

            # If all batches failed (no entities were created) and we have an
            # error, return a hard failure to the caller.
            if batch_error and entities_created == 0:
                return {
                    "payload": {
                        "action": "failure",
                        "response": f'Failed to inject entities via trackmepushdatasource: {batch_error}',
                    },
                    "status": 500,
                }

            # Create recurring schedule if requested. Skip schedule creation on
            # partial batch failure — the user should re-run after diagnosing.
            schedule_created = False
            schedule_error = None
            schedule_name = None

            if create_schedule and not batch_error:
                schedule_created, schedule_name, schedule_error = self._create_recurring_schedule(
                    request_info,
                    service,
                    trackme_conf,
                    tenant_id,
                    component,
                    lookup_name,
                    field_mappings,
                    account,
                    custom_schedule_name,
                    custom_cron_schedule,
                    match_asset_field=match_asset_field,
                )

            response = {
                "action": "partial_success" if batch_error else "success",
                "component": component,
                "lookup_name": lookup_name,
                "entities_created": entities_created,
                "entities_skipped": entities_skipped,
                "entities_skipped_asset_match": entities_skipped_asset_match,
                "match_asset_field": bool(component == "dhm" and match_asset_field),
                "total_lookup_rows": len(rows),
                "schedule_created": schedule_created,
                "schedule_name": schedule_name,
            }

            if batch_error:
                response["batch_error"] = batch_error
                response["failed_batch_index"] = failed_batch_index

            if create_schedule and not schedule_created:
                response["schedule_error"] = (
                    schedule_error
                    or "Schedule creation skipped due to partial batch failure"
                )

            if entities_created > 0:
                # Refresh tenant component summary cache (drives the
                # Single Value cards on Tenant Home). Inject-execute
                # creates new DSM/DHM entities. Daemon thread, fail-open.
                trackme_refresh_component_summary_async(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    component,
                    logger_=logger,
                )

            return {"payload": response, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Create a recurring injection schedule without running the injection
    # Used when the user enables the recurring import toggle after the initial execution
    def post_inject_create_schedule(self, request_info, **kwargs):

        # Declare
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "tenant_id is required"},
                        "status": 500,
                    }

                # Validate tenant_id format to prevent any risk of SPL
                # injection via interpolation in the execute pipeline
                if not tenant_id or not _TENANT_ID_RE.match(str(tenant_id)):
                    return {
                        "payload": {"action": "failure", "response": f'Invalid tenant_id format: "{tenant_id}" (allowed: alphanumeric, underscores, hyphens)'},
                        "status": 400,
                    }

                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "component is required"},
                        "status": 500,
                    }

                if component not in ("dsm", "dhm"):
                    return {
                        "payload": {"action": "failure", "response": "component must be dsm or dhm"},
                        "status": 400,
                    }

                try:
                    lookup_name = resp_dict["lookup_name"]
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "lookup_name is required"},
                        "status": 500,
                    }

                try:
                    field_mappings = resp_dict["field_mappings"]
                    if isinstance(field_mappings, str):
                        field_mappings = json.loads(field_mappings)
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "field_mappings is required"},
                        "status": 500,
                    }

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint creates a recurring injection schedule without running the injection. Used when the user enables the recurring import toggle after the initial execution",
                "resource_desc": "Create injection schedule",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_inject_expected/admin/inject_create_schedule" body="{\'tenant_id\': \'mytenant\', \'component\': \'dsm\', \'lookup_name\': \'example_expected_data_sources\', \'field_mappings\': [{\'lookupField\': \'index\', \'entityField\': \'index\'}, {\'lookupField\': \'sourcetype\', \'entityField\': \'sourcetype\'}]}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) dsm or dhm",
                        "lookup_name": "(required) Name of the lookup transform",
                        "field_mappings": "(required) Array of {lookupField, entityField} pairs",
                        "account": "(optional) Remote Splunk deployment account name, defaults to local",
                        "match_asset_field": "(optional, DHM only) Recognise already-known machines via the asset field (short<->FQDN variations), default true",
                        "schedule_name": "(optional) Custom schedule name",
                        "cron_schedule": "(optional) Custom cron expression",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # optional parameters
        account = resp_dict.get("account", "local")
        custom_schedule_name = resp_dict.get("schedule_name", None)
        custom_cron_schedule = resp_dict.get("cron_schedule", None)
        # asset-based recognition toggle (DHM only) — ON by default; see simulate
        match_asset_field = interpret_boolean(resp_dict.get("match_asset_field", True))

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # get TrackMe conf
        trackme_conf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )

        schedule_created, schedule_name, schedule_error = self._create_recurring_schedule(
            request_info,
            service,
            trackme_conf,
            tenant_id,
            component,
            lookup_name,
            field_mappings,
            account,
            custom_schedule_name,
            custom_cron_schedule,
            match_asset_field=match_asset_field,
        )

        if schedule_created:
            return {
                "payload": {
                    "action": "success",
                    "schedule_created": True,
                    "schedule_name": schedule_name,
                },
                "status": 200,
            }
        else:
            return {
                "payload": {
                    "action": "failure",
                    "schedule_created": False,
                    "schedule_name": schedule_name,
                    "schedule_error": schedule_error or "Unknown error",
                },
                "status": 500,
            }

    # List recurring injection schedules
    def post_inject_list_schedules(self, request_info, **kwargs):

        # Declare
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "tenant_id is required"},
                        "status": 500,
                    }

                # Validate tenant_id format to prevent any risk of SPL
                # injection via interpolation in the execute pipeline
                if not tenant_id or not _TENANT_ID_RE.match(str(tenant_id)):
                    return {
                        "payload": {"action": "failure", "response": f'Invalid tenant_id format: "{tenant_id}" (allowed: alphanumeric, underscores, hyphens)'},
                        "status": 400,
                    }

                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "component is required"},
                        "status": 500,
                    }

                if component not in ("dsm", "dhm"):
                    return {
                        "payload": {"action": "failure", "response": "component must be dsm or dhm"},
                        "status": 400,
                    }

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint lists recurring injection schedules for a tenant and component",
                "resource_desc": "List injection schedules",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_inject_expected/admin/inject_list_schedules" body="{\'tenant_id\': \'mytenant\', \'component\': \'dsm\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) dsm or dhm",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            component_label = "Sources" if component == "dsm" else "Hosts"
            pattern = f"TrackMe - Inject Expected {component_label} - {tenant_id} -"

            schedules = []
            for ss in service.saved_searches:
                if ss.name.startswith(pattern):
                    schedules.append({
                        "name": ss.name,
                        "cron_schedule": ss.content.get("cron_schedule", ""),
                        "is_scheduled": ss.content.get("is_scheduled", "0"),
                        "disabled": ss.content.get("disabled", "0"),
                    })

            return {
                "payload": {
                    "action": "success",
                    "schedules": schedules,
                    "count": len(schedules),
                },
                "status": 200,
            }

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Delete a recurring injection schedule
    def delete_inject_delete_schedule(self, request_info, **kwargs):

        # Declare
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "tenant_id is required"},
                        "status": 500,
                    }

                # Validate tenant_id format to prevent any risk of SPL
                # injection via interpolation in the execute pipeline
                if not tenant_id or not _TENANT_ID_RE.match(str(tenant_id)):
                    return {
                        "payload": {"action": "failure", "response": f'Invalid tenant_id format: "{tenant_id}" (allowed: alphanumeric, underscores, hyphens)'},
                        "status": 400,
                    }

                try:
                    schedule_name = resp_dict["schedule_name"]
                except Exception as e:
                    return {
                        "payload": {"action": "failure", "response": "schedule_name is required"},
                        "status": 500,
                    }

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes a recurring injection schedule",
                "resource_desc": "Delete injection schedule",
                "resource_spl_example": '| trackme mode=delete url="/services/trackme/v2/splk_inject_expected/admin/inject_delete_schedule" body="{\'tenant_id\': \'mytenant\', \'schedule_name\': \'TrackMe - Inject Expected Sources - mytenant - my_lookup\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "schedule_name": "(required) Name of the saved search to delete",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            # Validate the schedule name matches the expected pattern and belongs to this tenant
            if not schedule_name.startswith("TrackMe - Inject Expected"):
                return {
                    "payload": {"action": "failure", "response": "Invalid schedule name, must be a TrackMe inject expected schedule"},
                    "status": 400,
                }
            if f"- {tenant_id} -" not in schedule_name:
                return {
                    "payload": {"action": "failure", "response": f"Schedule does not belong to tenant {tenant_id}"},
                    "status": 403,
                }

            service.saved_searches.delete(schedule_name)

            # Record audit event
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user,
                "success",
                "delete inject expected schedule",
                schedule_name,
                "inject_expected",
                json.dumps({"schedule_name": schedule_name}),
                f"Deleted recurring injection schedule: {schedule_name}",
                "Schedule deleted by user",
            )

            return {
                "payload": {
                    "action": "success",
                    "response": f'Schedule "{schedule_name}" deleted successfully',
                },
                "status": 200,
            }

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}
