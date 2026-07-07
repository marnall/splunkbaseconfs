#!/usr/bin/env python
# coding=utf-8

"""
CMDB lookup helper for TrackMe alert actions.

Provides a shared function to perform CMDB lookups during stateful and notable
alert processing. The lookup is non-blocking: all errors are caught and logged,
returning None so that alert processing continues unimpeded.
"""

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import json
import logging
import re

from trackme_libs import run_splunk_search, trackme_vtenant_account_from_service

# Mapping from component code to global config key for CMDB search
COMPONENT_CMDB_KEYS = {
    "dsm": "splk_general_dsm_cmdb_search",
    "dhm": "splk_general_dhm_cmdb_search",
    "mhm": "splk_general_mhm_cmdb_search",
    "flx": "splk_general_flx_cmdb_search",
    "fqm": "splk_general_fqm_cmdb_search",
    "wlk": "splk_general_wlk_cmdb_search",
}

# OOTB default CMDB searches (non-functional placeholders from globalConfig.json).
# These exact values indicate the CMDB search has NOT been configured by the user.
OOTB_CMDB_DEFAULTS = {
    '| inputlookup my_cmdb where (index="$data_index$" AND sourcetype="$data_sourcetype$")',
    '| inputlookup my_cmdb where (host="$alias$")',
    '| inputlookup my_cmdb where (object="$object$")',
    '| inputlookup my_cmdb where (savedsearch_name="$savedsearch_name$")',
}


def replace_cmdb_placeholders(s, dictionary):
    """Replace $placeholder$ tokens in a string with values from a dictionary.

    Tokens not found in the dictionary are left as-is.

    Args:
        s: The string containing $placeholder$ tokens.
        dictionary: A dict mapping field names to replacement values.

    Returns:
        The string with placeholders replaced.
    """
    return re.sub(
        r"\$(\w+)\$", lambda m: str(dictionary.get(m.group(1), m.group(0))), s
    )


def resolve_cmdb_remote_service(service, account, logger_func=None):
    """Resolve a remote Splunk service for CMDB execution.

    Shared helper used by both the trackmesplkcmdb search command and
    the alert-action CMDB lookup to avoid duplicating remote account
    resolution logic.

    Args:
        service: A splunklib.client.Service (local) — used for account
                 credential lookup and as fallback.
        account: The account name ("local" or a remote account name).
        logger_func: Optional callable(level, msg) for logging. Receives
                     the log level ("info", "error", "warning") and message.
                     If None, uses the logging module directly.

    Returns:
        A splunklib.client.Service targeting the appropriate deployment.
        Falls back to the local service on any error.
    """
    if not account or str(account).strip().lower() == "local":
        return service

    def _log(level, msg):
        if logger_func:
            logger_func(level, msg)
        else:
            getattr(logging, level, logging.info)(msg)

    try:
        from trackme_libs import (
            trackme_get_remote_account,
            establish_sdk_remote_service,
            select_url,
        )
        from urllib.parse import urlparse
        import requests as req_lib

        # Build a request_info-like object for trackme_get_remote_account
        # Must provide: system_authtoken, server_rest_port (for SDK connect)
        # and server_rest_uri, session_key (for license check)
        class _ReqInfo:
            def __init__(self, svc):
                self.system_authtoken = svc.token
                self.session_key = svc.token
                self.server_rest_port = svc.port
                self.server_rest_uri = f"{svc.scheme}://{svc.host}:{svc.port}"

        req_info_adapter = _ReqInfo(service)
        account_info = trackme_get_remote_account(req_info_adapter, account)
        splunk_url = account_info["splunk_url"]
        bearer_token = account_info["token"]
        app_namespace = account_info.get("app_namespace", "search")
        timeout_search = int(account_info.get("timeout_search_check", 300))
        timeout_connect = int(account_info.get("timeout_connect_check", 15))

        retry_config = {
            "retry_enabled": account_info.get("retry_enabled", "1"),
            "retry_max_total_time": account_info.get("retry_max_total_time", "30"),
            "retry_initial_delay": account_info.get("retry_initial_delay", "2"),
            "retry_backoff_multiplier": account_info.get("retry_backoff_multiplier", "2.0"),
            "retry_max_attempts": account_info.get("retry_max_attempts", "10"),
        }

        with req_lib.Session() as session:
            selected_url, unreachable_errors = select_url(
                session, splunk_url, timeout=timeout_connect, retry_config=retry_config
            )

        if selected_url:
            parsed_url = urlparse(selected_url)
            remote_service = establish_sdk_remote_service(
                parsed_url, bearer_token, app_namespace, account, timeout=timeout_search
            )
            if remote_service is None:
                _log("error", f'establish_sdk_remote_service returned None for account "{account}", falling back to local')
                return service
            _log("info", f'CMDB using remote account "{account}", selected URL: {selected_url}')
            return remote_service
        else:
            error_details = "; ".join(f"{u}: {e}" for u, e in unreachable_errors)
            _log(
                "error",
                f'No reachable URL for CMDB account "{account}": {error_details}',
            )
            return service

    except Exception as e:
        _log("error", f'Failed to resolve remote service for CMDB account "{account}": {str(e)}')
        return service


def perform_cmdb_lookup(helper, service, reqinfo, tenant_id, component, event, vtenant_cache, cmdb_service_cache=None):
    """Perform a CMDB lookup for an entity during alert processing.

    This function replicates the CMDB search logic from trackmesplkcmdb.py but
    is designed for use within alert actions. It is fully non-blocking: any error
    is caught, logged, and None is returned.

    Args:
        helper: The alert helper object (used for logging).
        service: A splunklib.client.Service object.
        reqinfo: The reqinfo dict from trackme_reqinfo().
        tenant_id: The tenant identifier.
        component: The component code (dsm, dhm, mhm, flx, fqm, wlk).
        event: The event dict (must contain 'keyid' or 'object' for entity lookup).
        vtenant_cache: A mutable dict {tenant_id: vtenant_account} for caching.
        cmdb_service_cache: Optional mutable dict {cmdb_account: service} for caching
                           resolved remote services across entities. Avoids repeated
                           credential lookup, URL selection, and SDK connection per entity.

    Returns:
        - A dict if a single CMDB result is found.
        - A list of dicts if multiple CMDB results are found.
        - None if CMDB is not configured, no results, or on failure.
    """

    try:
        # Validate component
        if component not in COMPONENT_CMDB_KEYS:
            helper.log_debug(
                f"activity=cmdb_lookup, tenant_id={tenant_id}, "
                f"decision=skip, reason=unknown_component, component={component}"
            )
            return None

        # Get the global CMDB search for this component
        global_key = COMPONENT_CMDB_KEYS[component]
        cmdb_search = reqinfo.get("trackme_conf", {}).get("splk_general", {}).get(global_key, "")

        # Get vtenant account (cached)
        if tenant_id not in vtenant_cache:
            try:
                vtenant_cache[tenant_id] = trackme_vtenant_account_from_service(service, tenant_id)
            except Exception as e:
                helper.log_warn(
                    f"activity=cmdb_lookup, tenant_id={tenant_id}, "
                    f"decision=skip, reason=vtenant_account_load_failed, exception={str(e)}"
                )
                vtenant_cache[tenant_id] = {}

        vtenant_account = vtenant_cache[tenant_id]

        # Respect the tenant-level CMDB lookup toggle. The field defaults to 1
        # (enabled) in vtenant_account_default; a tenant that explicitly sets
        # it to 0 must NOT receive CMDB enrichment even if a search string is
        # configured.
        cmdb_lookup_toggle = vtenant_account.get("cmdb_lookup", 1)
        try:
            cmdb_lookup_enabled = int(str(cmdb_lookup_toggle)) == 1
        except (ValueError, TypeError):
            cmdb_lookup_enabled = True
        if not cmdb_lookup_enabled:
            helper.log_debug(
                f"activity=cmdb_lookup, tenant_id={tenant_id}, component={component}, "
                f"decision=skip, reason=cmdb_lookup_disabled_for_tenant"
            )
            return None

        # Check for tenant-level override
        tenant_override = vtenant_account.get(f"splk_{component}_cmdb_search", "")
        if tenant_override and tenant_override.strip():
            cmdb_search = tenant_override

        # Skip if still using OOTB default (not configured)
        if not cmdb_search or cmdb_search.strip() in OOTB_CMDB_DEFAULTS:
            helper.log_debug(
                f"activity=cmdb_lookup, tenant_id={tenant_id}, component={component}, "
                f"decision=skip, reason=cmdb_not_configured"
            )
            return None

        # Determine entity key for KV collection query
        collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
        keyid = event.get("keyid")

        if not keyid:
            # Fall back to object field
            object_name = event.get("object")
            if not object_name:
                helper.log_warn(
                    f"activity=cmdb_lookup, tenant_id={tenant_id}, component={component}, "
                    f"decision=skip, reason=no_keyid_or_object_in_event"
                )
                return None
            query_string = {"object": object_name}
        else:
            query_string = {"_key": keyid}

        # Query entity KV collection to get full record for placeholder replacement
        try:
            collection = service.kvstore[collection_name]
            kv_results = collection.data.query(query=json.dumps(query_string))
            if not kv_results:
                helper.log_debug(
                    f"activity=cmdb_lookup, tenant_id={tenant_id}, component={component}, "
                    f"decision=skip, reason=entity_not_found_in_kvstore, query={json.dumps(query_string)}"
                )
                return None
            kvrecord = kv_results[0]
        except Exception as e:
            helper.log_warn(
                f"activity=cmdb_lookup, tenant_id={tenant_id}, component={component}, "
                f"decision=skip, reason=kvstore_query_failed, exception={str(e)}"
            )
            return None

        # Replace placeholders in the CMDB search
        cmdb_search = replace_cmdb_placeholders(cmdb_search, kvrecord)

        # Resolve the service to use (local or remote)
        # Tenant-level cmdb_account takes precedence, then system-level, then "local"
        raw_cmdb_account = vtenant_account.get("cmdb_account", "")
        cmdb_account = str(raw_cmdb_account).strip() if raw_cmdb_account is not None else ""
        if not cmdb_account:
            # No tenant-level override — fall back to system-level default
            system_cmdb_account = reqinfo.get("trackme_conf", {}).get("splk_general", {}).get(
                "splk_general_cmdb_account", "local"
            )
            cmdb_account = system_cmdb_account.strip() if system_cmdb_account else "local"

        def _cmdb_log(level, msg):
            prefix = f"activity=cmdb_lookup, tenant_id={tenant_id}, component={component}, "
            log_method = getattr(helper, f"log_{level}", helper.log_info)
            log_method(prefix + msg)

        # Use cached service if available to avoid repeated remote resolution per entity
        if cmdb_service_cache is not None and cmdb_account in cmdb_service_cache:
            search_service = cmdb_service_cache[cmdb_account]
        else:
            search_service = resolve_cmdb_remote_service(
                service, cmdb_account, logger_func=_cmdb_log,
            )
            if cmdb_service_cache is not None:
                cmdb_service_cache[cmdb_account] = search_service

        # Execute the CMDB search with fast-fail parameters
        search_params = {
            "earliest_time": "-5m",
            "latest_time": "now",
            "count": 0,
            "output_mode": "json",
        }

        reader = run_splunk_search(
            search_service, cmdb_search, search_params, max_retries=3, sleep_time=2
        )

        # Collect results
        results = [item for item in reader if isinstance(item, dict)]

        if not results:
            helper.log_info(
                f"activity=cmdb_lookup, tenant_id={tenant_id}, component={component}, "
                f"decision=no_results, search=\"{cmdb_search}\""
            )
            return None

        helper.log_info(
            f"activity=cmdb_lookup, tenant_id={tenant_id}, component={component}, "
            f"decision=success, results_count={len(results)}, search=\"{cmdb_search}\""
        )

        # Single result → dict, multiple results → list
        if len(results) == 1:
            return results[0]
        return results

    except Exception as e:
        helper.log_error(
            f"activity=cmdb_lookup, tenant_id={tenant_id}, component={component}, "
            f"decision=error, reason=cmdb_lookup_failed, exception={str(e)}"
        )
        return None
