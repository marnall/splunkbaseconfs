#!/usr/bin/env python
# coding=utf-8

"""
Shared utility functions for TrackMe policy workflows (lookup and search based).

This module centralises helpers that are used identically across the
priority, SLA, and tag policy handlers (both power and user scopes).

Functions moved here from trackme_libs.py:
    - validate_lookup_name
    - load_lookup_content
    - match_entity_to_lookup_row

Search-based policy helpers:
    - validate_search_query
    - execute_search_content
    - get_search_fields

Functions extracted from the three user handlers:
    - list_available_transforms
    - get_lookup_fields
    - get_entity_fields
    - ENTITY_FIELDS_MAP

Resolver helpers (one per policy type):
    - resolve_lookup_priority
    - resolve_lookup_sla
    - resolve_lookup_tags
    - PRIORITY_DICT
"""

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"

import fnmatch
import json
import re

import splunklib.results as results


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Priority numerical ranking (higher = more critical)
PRIORITY_DICT = {"low": 1, "medium": 2, "high": 3, "critical": 4, "pending": 5}

#: Entity fields that may contain comma-separated multiple values (e.g. DHM
#: entities store all indexes/sourcetypes seen for a host as a CSV list).
MULTI_VALUE_FIELDS = {"data_index", "data_sourcetype"}

#: Entity fields available for lookup field mapping, per component
ENTITY_FIELDS_MAP = {
    "dsm": [
        {"field": "object", "description": "Full entity identifier (index:sourcetype)"},
        {"field": "alias", "description": "Entity alias"},
        {"field": "data_index", "description": "Splunk index name"},
        {"field": "data_sourcetype", "description": "Splunk sourcetype name"},
    ],
    "dhm": [
        {"field": "object", "description": "Full entity identifier"},
        {"field": "alias", "description": "Host name"},
        {"field": "data_index", "description": "Splunk index name (may contain multiple comma-separated values)"},
        {"field": "data_sourcetype", "description": "Splunk sourcetype name (may contain multiple comma-separated values)"},
    ],
    "mhm": [
        {"field": "object", "description": "Full entity identifier"},
        {"field": "alias", "description": "Host name"},
    ],
    "flx": [
        {"field": "object", "description": "Full entity identifier"},
        {"field": "alias", "description": "Entity alias"},
    ],
    "wlk": [
        {"field": "object", "description": "Full entity identifier"},
        {"field": "alias", "description": "Entity alias"},
    ],
    "fqm": [
        {"field": "object", "description": "Full entity identifier"},
        {"field": "alias", "description": "Entity alias"},
    ],
}


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def collect_all_fields(rows):
    """Return an ordered list of all field names across *rows*.

    Unlike ``list(rows[0].keys())``, this scans every row so that
    conditionally-populated fields (e.g. from a ``case()`` expression that
    only matches some rows) are still detected.
    """
    seen: dict[str, None] = {}
    for row in rows:
        for key in row:
            if key not in seen:
                seen[key] = None
    return list(seen)


# ---------------------------------------------------------------------------
# SPL search-based policy helpers
# ---------------------------------------------------------------------------

def validate_search_query(search_query):
    """
    Validate an SPL search query for use in search-based policies.

    Ensures the query is non-empty.  Splunk's own RBAC controls which
    commands a given user is allowed to run, so we do not restrict
    specific SPL commands here.

    Raises ``ValueError`` on invalid input.
    """
    if not search_query or not str(search_query).strip():
        raise ValueError("Search query must not be empty")


def execute_search_content(service, search_query, earliest="-5m", latest="now", max_rows=50000):
    """
    Execute an SPL search and return results as a list of dicts.

    This mirrors :func:`load_lookup_content` but accepts an arbitrary SPL
    query instead of a lookup transform name.  The result format is identical
    so that downstream helpers (``match_entity_to_lookup_row``, resolver
    functions) can be reused without changes.

    Args:
        service: A ``splunklib.client.Service`` instance.
        search_query: The SPL query string (may or may not start with ``|``).
        earliest: Earliest time bound (default ``"-5m"``).
        latest: Latest time bound (default ``"now"``).
        max_rows: Maximum number of rows to return (default 50 000).

    Returns:
        list[dict]: One dict per result row.
    """
    validate_search_query(search_query)

    query = str(search_query).strip()
    if not query.startswith("|"):
        # Avoid double-prefixing when the user already wrote "search …"
        if query.lower().startswith("search "):
            query = f"| {query}"
        else:
            query = f"| search {query}"
    query = f"{query} | head {int(max_rows)}"

    oneshot_results = service.jobs.oneshot(
        query,
        output_mode="json",
        count=0,
        earliest_time=str(earliest),
        latest_time=str(latest),
    )
    reader = results.JSONResultsReader(oneshot_results)
    return [row for row in reader if isinstance(row, dict)]


def get_search_fields(service, logger, search_query, earliest="-5m", latest="now"):
    """
    Execute an SPL search and return field names plus sample rows.

    This mirrors :func:`get_lookup_fields` and is called by the user-handler
    ``execute_search`` endpoint so the UI can preview results.

    Args:
        service: A ``splunklib.client.Service`` instance.
        logger: Logger instance for error reporting.
        search_query: The SPL query string.
        earliest: Earliest time bound (default ``"-5m"``).
        latest: Latest time bound (default ``"now"``).

    Returns:
        dict ready to be used as a REST response payload.
    """
    try:
        sample_rows = execute_search_content(service, search_query, earliest, latest, max_rows=100)
        fields = collect_all_fields(sample_rows)

        return {
            "payload": {
                "action": "success",
                "fields": fields,
                "sample_rows": sample_rows,
                "row_count": len(sample_rows),
            },
            "status": 200,
        }

    except ValueError as ve:
        return {
            "payload": {
                "action": "failure",
                "response": str(ve),
            },
            "status": 400,
        }
    except Exception as e:
        response = {
            "action": "failure",
            "response": f'an exception was encountered executing search, exception="{str(e)}"',
        }
        logger.error(json.dumps(response))
        return {"payload": response, "status": 500}


# ---------------------------------------------------------------------------
# Validation / lookup helpers  (moved from trackme_libs.py)
# ---------------------------------------------------------------------------


def validate_lookup_name(lookup_name):
    """
    Validate lookup name contains only safe characters to prevent SPL injection.
    Lookup transform names in Splunk are limited to alphanumeric, underscores, hyphens, and dots.
    """
    if not lookup_name or not re.match(r'^[\w.\-]+$', str(lookup_name)):
        raise ValueError(f'Invalid lookup name: "{lookup_name}"')


def load_lookup_content(service, lookup_name, max_rows=50000):
    """
    Load lookup content via SPL inputlookup search.
    Returns a list of dicts (one per row).
    Works for both CSV file lookups and KVstore lookups transparently.
    """
    validate_lookup_name(lookup_name)
    search_query = f"| inputlookup {lookup_name} | head {max_rows}"
    oneshot_results = service.jobs.oneshot(search_query, output_mode="json", count=0)
    reader = results.JSONResultsReader(oneshot_results)
    return [row for row in reader if isinstance(row, dict)]


def match_entity_to_lookup_row(entity_record, row, field_mappings, match_mode):
    """
    Check if an entity matches a lookup row based on field mappings.
    Returns True if all mapped fields match.

    For multi-value entity fields (see ``MULTI_VALUE_FIELDS``), the entity
    value is split on commas and a match against *any* individual value is
    considered a hit.  This is required for DHM entities where fields like
    ``data_index`` and ``data_sourcetype`` contain comma-separated lists.
    """
    for lookup_field, entity_field in field_mappings.items():
        lookup_val = str(row.get(lookup_field, "")).strip()
        entity_val = str(entity_record.get(entity_field, "")).strip()

        if not lookup_val or not entity_val:
            return False

        # Split multi-value fields into individual values for matching
        if entity_field in MULTI_VALUE_FIELDS:
            entity_values = [v.strip().lower() for v in entity_val.split(",") if v.strip()]
        else:
            entity_values = [entity_val.lower()]

        if match_mode == "wildcard":
            if not any(fnmatch.fnmatch(v, lookup_val.lower()) for v in entity_values):
                return False
        else:  # exact (case-insensitive)
            if not any(v == lookup_val.lower() for v in entity_values):
                return False

    return True


# ---------------------------------------------------------------------------
# Shared user-handler helpers  (extracted from the three *_user.py handlers)
# ---------------------------------------------------------------------------


def list_available_transforms(service, logger, name_filter=None):
    """
    List Splunk lookup transforms available for policy configuration.

    Args:
        service: A splunklib.client.Service instance.
        logger: Logger instance for error reporting.
        name_filter: Optional substring to filter transform names.

    Returns:
        dict ready to be used as a REST response payload.
    """
    try:
        transforms = service.confs["transforms"]
        result = []

        for stanza in transforms:
            name = stanza.name
            content = stanza.content

            # Skip internal TrackMe transforms and ML transforms
            if name.startswith("kv_trackme_") or name.startswith("__mlspl_"):
                continue

            # Determine lookup type
            filename = content.get("filename", None)
            collection = content.get("collection", None)

            if filename:
                lookup_type = "csv"
                target = filename
            elif collection:
                lookup_type = "kvstore"
                target = collection
            else:
                continue  # Not a lookup transform

            # Apply name filter if provided
            if name_filter and name_filter.lower() not in name.lower():
                continue

            result.append(
                {
                    "transform_name": name,
                    "type": lookup_type,
                    "filename_or_collection": target,
                }
            )

        # Sort by name
        result.sort(key=lambda x: x["transform_name"])

        return {
            "payload": {
                "action": "success",
                "transforms_count": len(result),
                "transforms": result,
            },
            "status": 200,
        }

    except Exception as e:
        response = {
            "action": "failure",
            "response": f'an exception was encountered listing transforms, exception="{str(e)}"',
        }
        logger.error(json.dumps(response))
        return {"payload": response, "status": 500}


def get_lookup_fields(service, logger, lookup_name):
    """
    Retrieve fields and sample data from a Splunk lookup transform.

    Args:
        service: A splunklib.client.Service instance.
        logger: Logger instance for error reporting.
        lookup_name: The Splunk lookup transform name to inspect.

    Returns:
        dict ready to be used as a REST response payload.
    """
    try:
        # Validate lookup name contains only safe characters (prevent SPL injection)
        if not re.match(r'^[\w.\-]+$', str(lookup_name)):
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Invalid lookup name: "{lookup_name}"',
                },
                "status": 400,
            }

        # Validate that the lookup transform exists
        try:
            transform = service.confs["transforms"][lookup_name]
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f'lookup transform "{lookup_name}" not found',
                },
                "status": 404,
            }

        # Determine lookup type
        filename = transform.content.get("filename", None)
        collection = transform.content.get("collection", None)

        if filename:
            lookup_type = "csv"
        elif collection:
            lookup_type = "kvstore"
        else:
            return {
                "payload": {
                    "action": "failure",
                    "response": f'"{lookup_name}" is not a lookup transform (no filename or collection defined)',
                },
                "status": 400,
            }

        # Load sample rows via inputlookup to get fields and preview data
        search_query = f"| inputlookup {lookup_name} | head 100"
        oneshot_results = service.jobs.oneshot(
            search_query, output_mode="json", count=0
        )
        reader = results.JSONResultsReader(oneshot_results)
        sample_rows = [row for row in reader if isinstance(row, dict)]

        fields = collect_all_fields(sample_rows)

        return {
            "payload": {
                "action": "success",
                "lookup_name": lookup_name,
                "lookup_type": lookup_type,
                "fields": fields,
                "sample_rows": sample_rows,
                "row_count": len(sample_rows),
            },
            "status": 200,
        }

    except Exception as e:
        response = {
            "action": "failure",
            "response": f'an exception was encountered retrieving lookup fields, exception="{str(e)}"',
        }
        logger.error(json.dumps(response))
        return {"payload": response, "status": 500}


def get_entity_fields(component):
    """
    Return available entity fields for lookup-based policy field mapping.

    Args:
        component: The component identifier (dsm/dhm/mhm/wlk/flx/fqm).

    Returns:
        dict ready to be used as a REST response payload.
    """
    fields = ENTITY_FIELDS_MAP.get(component, [])

    return {
        "payload": {
            "action": "success",
            "component": component,
            "fields": fields,
        },
        "status": 200,
    }


# ---------------------------------------------------------------------------
# Resolver helpers  (moved from the three *_power.py handlers)
# ---------------------------------------------------------------------------


def resolve_lookup_priority(raw_priority, priority_mappings):
    """
    Resolve a priority value from a lookup row, applying optional mappings.
    Returns the resolved priority string or None if invalid/empty.
    """
    if not raw_priority or not str(raw_priority).strip():
        return None

    raw_priority = str(raw_priority).strip().lower()

    if priority_mappings:
        # Try direct match (case-insensitive)
        mapped = None
        for mk, mv in priority_mappings.items():
            if mk.lower() == raw_priority:
                mapped = mv.lower() if isinstance(mv, str) else str(mv).lower()
                break
        if mapped:
            raw_priority = mapped

    # Validate against known priority values
    if raw_priority not in PRIORITY_DICT:
        return None

    return raw_priority


def resolve_lookup_sla(raw_sla, sla_mappings, valid_sla_classes):
    """
    Resolve SLA class from lookup value, applying optional mappings.
    Returns the resolved SLA class string or None if invalid/empty.
    """
    if not raw_sla or not str(raw_sla).strip():
        return None

    raw_sla = str(raw_sla).strip().lower()

    if sla_mappings:
        for mk, mv in sla_mappings.items():
            if mk.lower() == raw_sla:
                raw_sla = mv.lower() if isinstance(mv, str) else str(mv).lower()
                break

    # Validate against known SLA classes
    if raw_sla not in valid_sla_classes:
        return None

    return raw_sla


def resolve_lookup_tags(raw_tags, separator=","):
    """
    Extract tags from lookup field value, splitting by separator.
    Returns a list of lowercase tag strings.
    """
    if not raw_tags or not str(raw_tags).strip():
        return []
    # Guard against empty separator (str.split("") raises ValueError)
    if not separator:
        separator = ","
    return [t.strip().lower() for t in str(raw_tags).split(separator) if t.strip()]


# ---------------------------------------------------------------------------
# Remote account helpers
# ---------------------------------------------------------------------------


def resolve_service_for_account(service, request_info, account, logger):
    """
    Return the local service if account is None/empty/"local",
    otherwise establish a remote SDK service connection.

    Supports multi-URL remote accounts (comma-separated Splunk URLs)
    with HA/failover using the same ``select_url`` pattern as
    ``splunkremotesearch.py``.

    Args:
        service: The local ``splunklib.client.Service`` instance.
        request_info: The request_info dict from the REST handler.
        account: The account name (``"local"`` or a remote account name).
        logger: Logger instance for error reporting.

    Returns:
        A ``splunklib.client.Service`` targeting the appropriate deployment.

    Raises:
        Exception: If no reachable Splunk URL is found for the account.
    """
    if not account or str(account).strip().lower() in ("", "local"):
        return service

    import requests
    from trackme_libs import trackme_get_remote_account, establish_sdk_remote_service, select_url
    from urllib.parse import urlparse

    account_name = str(account).strip()
    account_info = trackme_get_remote_account(request_info, account_name)
    splunk_url = account_info["splunk_url"]
    bearer_token = account_info["token"]
    app_namespace = account_info.get("app_namespace", "search")
    timeout_search = int(account_info.get("timeout_search_check", 300))
    timeout_connect = int(account_info.get("timeout_connect_check", 15))

    # Build retry config from account settings (use string defaults to match
    # splunkremotesearch.py — is_reachable_with_retry handles type coercion)
    retry_config = {
        "retry_enabled": account_info.get("retry_enabled", "1"),
        "retry_max_total_time": account_info.get("retry_max_total_time", "30"),
        "retry_initial_delay": account_info.get("retry_initial_delay", "2"),
        "retry_backoff_multiplier": account_info.get("retry_backoff_multiplier", "2.0"),
        "retry_max_attempts": account_info.get("retry_max_attempts", "10"),
    }

    # Use select_url to handle multi-URL accounts with HA/failover
    with requests.Session() as session:
        selected_url, unreachable_errors = select_url(
            session, splunk_url, timeout=timeout_connect, retry_config=retry_config
        )

    if not selected_url:
        error_details = "; ".join(f"{url}: {err}" for url, err in unreachable_errors)
        raise Exception(
            f'No reachable Splunk URL found for remote account "{account_name}". '
            f"Unreachable URLs: {error_details}"
        )

    logger.info(
        f'Remote account "{account_name}": selected URL "{selected_url}" '
        f"from {len(splunk_url.split(','))} configured URL(s)"
    )

    parsed_url = urlparse(selected_url)
    remote_service = establish_sdk_remote_service(
        parsed_url, bearer_token, app_namespace, account_name, timeout=timeout_search
    )
    return remote_service


def preload_lookup_cache(
    lookup_policies, lookup_name_field, remote_services_cache,
    service, request_info, tenant_id, logger
):
    """
    Pre-load lookup contents once per unique (account, lookup_name) for batch policy application.

    Shared across priority, SLA, and tag policy _apply endpoints.
    Mutates remote_services_cache in-place to share connections with search cache.

    Returns:
        dict: lookup_cache keyed by (account, lookup_name) tuples
    """
    lookup_cache = {}
    for policy_record in lookup_policies:
        lk_name = policy_record.get(lookup_name_field, "")
        policy_account = policy_record.get("account", "local")
        cache_key = (policy_account, lk_name)
        if lk_name and cache_key not in lookup_cache:
            # Resolve remote service (cached, skip if previously failed)
            if policy_account not in remote_services_cache:
                try:
                    remote_services_cache[policy_account] = resolve_service_for_account(
                        service, request_info, policy_account, logger
                    )
                except Exception as e:
                    logger.error(
                        f'tenant_id="{tenant_id}", failed to connect to remote account "{policy_account}", exception="{str(e)}"'
                    )
                    remote_services_cache[policy_account] = None
            target_service = remote_services_cache[policy_account]
            if target_service is None:
                lookup_cache[cache_key] = []
            else:
                try:
                    lookup_cache[cache_key] = load_lookup_content(target_service, lk_name, max_rows=50000)
                    logger.info(
                        f'tenant_id="{tenant_id}", pre-loaded lookup "{lk_name}" (account="{policy_account}") with {len(lookup_cache[cache_key])} rows'
                    )
                except Exception as e:
                    logger.error(
                        f'tenant_id="{tenant_id}", failed to load lookup "{lk_name}" (account="{policy_account}"), exception="{str(e)}"'
                    )
                    lookup_cache[cache_key] = []
    return lookup_cache


def preload_search_cache(
    search_policies, query_field, earliest_field, latest_field,
    remote_services_cache, service, request_info, tenant_id, logger
):
    """
    Pre-execute search queries once per unique (account, query, earliest, latest) for batch policy application.

    Shared across priority, SLA, and tag policy _apply endpoints.
    Mutates remote_services_cache in-place to share connections with lookup cache.

    Returns:
        dict: search_cache keyed by (account, query, earliest, latest) tuples
    """
    search_cache = {}
    for sp in search_policies:
        sq = sp.get(query_field, "")
        se = sp.get(earliest_field, "-5m")
        sl = sp.get(latest_field, "now")
        policy_account = sp.get("account", "local")
        cache_key = (policy_account, sq, se, sl)
        if cache_key not in search_cache:
            # Resolve remote service (cached, skip if previously failed)
            if policy_account not in remote_services_cache:
                try:
                    remote_services_cache[policy_account] = resolve_service_for_account(
                        service, request_info, policy_account, logger
                    )
                except Exception as e:
                    logger.error(
                        f'tenant_id="{tenant_id}", failed to connect to remote account "{policy_account}", exception="{str(e)}"'
                    )
                    remote_services_cache[policy_account] = None
            target_service = remote_services_cache[policy_account]
            if target_service is None:
                search_cache[cache_key] = []
            else:
                try:
                    search_cache[cache_key] = execute_search_content(target_service, sq, se, sl)
                    logger.info(
                        f'tenant_id="{tenant_id}", pre-executed search query (account="{policy_account}") with {len(search_cache[cache_key])} rows'
                    )
                except Exception as e:
                    logger.error(
                        f'tenant_id="{tenant_id}", failed to execute search query (account="{policy_account}"), exception="{str(e)}"'
                    )
                    search_cache[cache_key] = []
    return search_cache
