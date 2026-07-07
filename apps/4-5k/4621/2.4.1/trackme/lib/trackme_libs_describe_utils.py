#!/usr/bin/env python
# coding=utf-8

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
from trackme_libs_logging import get_effective_logger
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch_endpoint_describe(session_key, splunkd_uri, method, endpoint_url):
    """
    Fetch the describe response from a TrackMe REST endpoint.

    Args:
        session_key: Splunk authentication token
        splunkd_uri: Splunk REST URI (e.g., https://localhost:8089)
        method: HTTP method (get, post, delete)
        endpoint_url: Endpoint path relative to /services/trackme/v2/
                      (e.g., "backup_and_restore/backup")

    Returns:
        dict: The describe response with added metadata (http_method, endpoint_path),
              or None on failure.
    """

    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    url = "%s/services/trackme/v2/%s" % (splunkd_uri, endpoint_url)
    request_data = json.dumps({"describe": "true"}, indent=0)

    try:
        if method == "get":
            response = requests.get(
                url,
                headers=header,
                data=request_data,
                verify=False,
                timeout=30,
            )
        elif method == "post":
            response = requests.post(
                url,
                headers=header,
                data=request_data,
                verify=False,
                timeout=30,
            )
        elif method == "delete":
            response = requests.delete(
                url,
                headers=header,
                data=request_data,
                verify=False,
                timeout=30,
            )
        else:
            get_effective_logger().error(
                f'function=fetch_endpoint_describe, '
                f'step="invalid_method", '
                f'method="{method}", '
                f'endpoint_url="{endpoint_url}"'
            )
            return None

        if response.status_code not in (200, 201, 204):
            get_effective_logger().error(
                f'function=fetch_endpoint_describe, '
                f'step="http_error", '
                f'endpoint_url="{endpoint_url}", '
                f'status_code="{response.status_code}"'
            )
            return None

        result = json.loads(response.text)

        # Add metadata for context
        result["http_method"] = method.upper()
        result["endpoint_path"] = "/services/trackme/v2/%s" % endpoint_url

        return result

    except Exception as e:
        get_effective_logger().error(
            f'function=fetch_endpoint_describe, '
            f'step="exception", '
            f'endpoint_url="{endpoint_url}", '
            f'exception="{str(e)}"'
        )
        return None


def fetch_resource_group_describe(session_key, splunkd_uri, resource_group, desc_suffix):
    """
    Fetch the resource group description from a TrackMe REST handler.

    Args:
        session_key: Splunk authentication token
        splunkd_uri: Splunk REST URI (e.g., https://localhost:8089)
        resource_group: Resource group path (e.g., "backup_and_restore")
        desc_suffix: The suffix for the resource_group_desc method
                     (e.g., "backup_and_restore")

    Returns:
        dict: {"resource_group_name": "...", "resource_group_desc": "..."},
              or None on failure.
    """

    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    url = "%s/services/trackme/v2/%s/resource_group_desc_%s" % (
        splunkd_uri,
        resource_group,
        desc_suffix,
    )

    try:
        response = requests.get(
            url,
            headers=header,
            data=json.dumps({"describe": "true"}, indent=0),
            verify=False,
            timeout=30,
        )

        if response.status_code not in (200, 201, 204):
            get_effective_logger().error(
                f'function=fetch_resource_group_describe, '
                f'step="http_error", '
                f'resource_group="{resource_group}", '
                f'status_code="{response.status_code}"'
            )
            return None

        return json.loads(response.text)

    except Exception as e:
        get_effective_logger().error(
            f'function=fetch_resource_group_describe, '
            f'step="exception", '
            f'resource_group="{resource_group}", '
            f'exception="{str(e)}"'
        )
        return None


def fetch_all_endpoint_describes(session_key, splunkd_uri, endpoint_definitions):
    """
    Fetch describe responses for a list of endpoint definitions.

    Args:
        session_key: Splunk authentication token
        splunkd_uri: Splunk REST URI
        endpoint_definitions: List of dicts with "method" and "url" keys

    Returns:
        list: List of describe response dicts (None entries filtered out)
    """

    results = []
    for ep in endpoint_definitions:
        result = fetch_endpoint_describe(
            session_key, splunkd_uri, ep["method"], ep["url"]
        )
        if result is not None:
            results.append(result)

    return results
