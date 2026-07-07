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
import time
import logging
from trackme_libs_logging import get_effective_logger
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from trackme_libs_describe_concierge import build_concierge_knowledge
from trackme_libs_describe_utils import (
    fetch_resource_group_describe,
    fetch_all_endpoint_describes,
)

# Endpoint registry for License resource groups
LICENSE_ENDPOINTS = [
    {"method": "get", "url": "licensing/license_status"},
    {"method": "post", "url": "licensing/admin/license_key"},
    {"method": "post", "url": "licensing/admin/upload_license_file"},
    {"method": "post", "url": "licensing/admin/start_trial"},
    {"method": "post", "url": "licensing/admin/enable_developer_license"},
    {"method": "post", "url": "licensing/admin/reset_license"},
]


def _build_knowledge_reference(api_endpoints=None, resource_group_info=None):
    """
    Build a knowledge reference section that provides the AI assistant
    with comprehensive understanding of TrackMe licensing concepts, editions,
    states, and workflows.

    Args:
        api_endpoints: List of dynamically fetched endpoint describe responses.
                       If None, a fallback note is included.
        resource_group_info: Resource group description dict from the handler.
    """
    ref = {
        "license_editions": {
            "foundation": (
                "Entry-level edition. Includes core monitoring capabilities "
                "for DSM, DHM, MHM. Limited number of tenants."
            ),
            "enterprise": (
                "Full-featured edition. All monitoring components "
                "(DSM, DHM, MHM, FLX, FQM, WLK). Higher tenant limits. "
                "AI assistant capability."
            ),
            "unlimited": (
                "Premium edition. No tenant limits. All features including "
                "advanced AI capabilities."
            ),
        },
        "license_features_by_edition": {
            "foundation": {
                "components": ["DSM", "DHM", "MHM"],
                "tenant_limits": "Limited",
                "ai_assistant": False,
                "advanced_features": False,
            },
            "enterprise": {
                "components": ["DSM", "DHM", "MHM", "FLX", "FQM", "WLK"],
                "tenant_limits": "Higher",
                "ai_assistant": True,
                "advanced_features": True,
            },
            "unlimited": {
                "components": ["DSM", "DHM", "MHM", "FLX", "FQM", "WLK"],
                "tenant_limits": "Unlimited",
                "ai_assistant": True,
                "advanced_features": True,
            },
        },
        "registration_process": [
            "Step 1: Obtain a license key from TrackMe Solutions",
            "Step 2: Navigate to License Management in TrackMe UI",
            "Step 3: Enter the license key and submit",
            "Step 4: License is validated and activated",
            "Step 5: Verify edition and feature enablement",
        ],
        "license_states": {
            "valid": "License is active and within expiration date.",
            "expired": (
                "License has passed its expiration date. "
                "App enters read-only mode."
            ),
            "invalid": (
                "License key is not recognized or has been tampered with."
            ),
            "trial": (
                "Trial period is active (limited time, full features)."
            ),
        },
        "read_only_mode": (
            "When license expires, TrackMe enters read-only mode. "
            "Existing monitoring continues but no new tenants or "
            "configuration changes can be made."
        ),
        "developer_mode": (
            "Available for development and testing. Provides full features "
            "with limited data volume support."
        ),
        "renewal_workflow": [
            "Contact TrackMe Solutions for renewal",
            "Receive new license key",
            "Apply in License Management UI",
            "Verify activation",
        ],
        "reference_doc": "https://docs.trackme-solutions.com/latest/license_registration.html",
    }

    # Add dynamic API endpoint descriptions
    if api_endpoints:
        ref["api_endpoints"] = api_endpoints
    else:
        ref["api_endpoints"] = {
            "note": "Dynamic endpoint descriptions were not available."
        }

    # Add resource group info
    if resource_group_info:
        ref["resource_group"] = resource_group_info

    return ref


def build_license_description(service, request_info):
    """
    Build a comprehensive, AI-consumable description of the current
    TrackMe license status for the License Management AI assistant.

    Retrieves the live license status by calling the licensing REST endpoint
    (same approach as the React UI), then enriches with endpoint descriptions.

    Args:
        service: Splunk service connection (accepted for interface consistency)
        request_info: REST request info (for session key, server URI, user context)

    Returns:
        dict: Structured license description
    """

    license_status = {}

    # ------------------------------------------------------------------
    # Fetch live license status from the REST endpoint
    # (mirrors what the React UI does)
    # ------------------------------------------------------------------
    try:
        session_key = request_info.system_authtoken
        splunkd_uri = request_info.server_rest_uri

        url = "%s/services/trackme/v2/licensing/license_status" % splunkd_uri
        header = {
            "Authorization": "Splunk %s" % session_key,
            "Content-Type": "application/json",
        }

        response = requests.get(
            url,
            headers=header,
            verify=False,
            timeout=30,
        )

        if response.status_code in (200, 201):
            data = json.loads(response.text)

            # Core license fields
            license_status["license_is_valid"] = data.get("license_is_valid")
            license_status["license_type"] = data.get("license_type", "unknown")
            license_status["license_subscription_class"] = data.get(
                "license_subscription_class", "unknown"
            )
            license_status["license_expiration"] = data.get(
                "license_expiration", "unknown"
            )
            license_status["license_expiration_countdown_sec"] = data.get(
                "license_expiration_countdown_sec"
            )
            license_status["license_read_only"] = data.get(
                "license_read_only", False
            )
            license_status["message"] = data.get("message", "")
            license_status["trackme_version"] = data.get(
                "trackme_version", "unknown"
            )

            # License features
            license_features = data.get("license_features")
            if license_features:
                license_status["license_features"] = license_features

            # Active tenant and tracker usage
            license_status["license_active_tenants"] = data.get(
                "license_active_tenants", 0
            )
            license_status["license_active_tenants_list"] = data.get(
                "license_active_tenants_list", []
            )
            license_status["license_active_hybrid_trackers"] = data.get(
                "license_active_hybrid_trackers", 0
            )
            license_status["license_active_flex_trackers"] = data.get(
                "license_active_flex_trackers", 0
            )
            license_status["license_active_fqm_trackers"] = data.get(
                "license_active_fqm_trackers", 0
            )
            license_status["license_active_wlk_trackers"] = data.get(
                "license_active_wlk_trackers", 0
            )
        else:
            get_effective_logger().error(
                f'function=build_license_description, '
                f'step="fetch_license_status", '
                f'status_code="{response.status_code}"'
            )
            license_status["error"] = (
                "Unable to retrieve license status from REST endpoint. "
                f"HTTP {response.status_code}"
            )

    except Exception as e:
        get_effective_logger().error(
            f'function=build_license_description, '
            f'step="fetch_license_status", '
            f'exception="{str(e)}"'
        )
        license_status["error"] = (
            "Unable to retrieve license status from REST endpoint. "
            f"Exception: {str(e)}"
        )

    # ------------------------------------------------------------------
    # Dynamically fetch endpoint descriptions
    # ------------------------------------------------------------------
    api_endpoints = None
    resource_group_info = None

    try:
        session_key = request_info.system_authtoken
        splunkd_uri = request_info.server_rest_uri

        resource_group_info = fetch_resource_group_describe(
            session_key, splunkd_uri, "licensing", "licensing"
        )
        api_endpoints = fetch_all_endpoint_describes(
            session_key, splunkd_uri, LICENSE_ENDPOINTS
        )
    except Exception as e:
        get_effective_logger().error(
            f'function=build_license_description, '
            f'step="fetch_endpoint_describes", '
            f'exception="{str(e)}"'
        )

    # ------------------------------------------------------------------
    # Build the response payload
    # ------------------------------------------------------------------
    knowledge_reference = _build_knowledge_reference(
        api_endpoints=api_endpoints,
        resource_group_info=resource_group_info,
    )

    # Embed the Concierge advisor knowledge so the chat LLM can propose
    # ``concierge_invocation`` action contracts when the user asks for an
    # action that requires a TrackMe REST API call (e.g. "register this
    # license key", "enable developer mode"). The Concierge block also
    # ships a compact projection of the live API catalog — without it the
    # LLM falls back to training-data guesses for paths.
    try:
        knowledge_reference["concierge_advisor"] = build_concierge_knowledge(
            splunkd_uri=request_info.server_rest_uri,
            session_key=request_info.system_authtoken,
            surface="global",
            feature_context="licensing",
        )
    except Exception as e:
        get_effective_logger().error(
            f'function=build_license_description, '
            f'step="build_concierge_knowledge", '
            f'exception="{str(e)}"'
        )

    return {
        "license_description": {
            "meta": {
                "api_version": "2.0",
                "generated_at": time.time(),
                "context_type": "license",
            },
            "license_status": license_status,
            "knowledge_reference": knowledge_reference,
        }
    }
