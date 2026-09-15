"""Flare API wrappers and Splunk REST handlers for the Flare integration."""

import os
import sys


if sys.version_info < (3, 7):
    sys.exit("Error: This application requires Python 3.7 or higher.")

# Ensure the vendored lib directory is on the path
_LIB_DIR = os.path.join(os.path.dirname(__file__), "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

import json
import logging
import requests
import urllib.parse

from typing import Optional


try:
    import splunk.rest
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(__file__))

import flare_constants as const

from flare_sdk_client import create_flare_client
from flareio import FlareApiClient
from flareio.exceptions import TokenError
from ingestion_config import get_proxy_settings
from splunk_storage import get_all_storage_values


logger = logging.getLogger("flare_cron_job")


# API Request Wrappers (For Cron Job)


def fetch_events_by_paginating(
    client: FlareApiClient,
    from_token: Optional[str] = None,
    size: int = const.DEFAULT_INGESTION_PAGE_SIZE,
    severities: Optional[list] = None,
    source_types: Optional[list] = None,
    start_date: Optional[str] = None,
) -> dict:
    """Fetch a page of events using the official SDK. JWT refresh is handled automatically."""
    search_body: dict = {"size": size}
    if from_token:
        search_body["from"] = from_token

    filters: dict = {}
    if start_date:
        filters["estimated_created_at"] = {"gte": start_date}
    if severities:
        filters["severity"] = severities
    if source_types:
        filters["type"] = source_types
    if filters:
        search_body["filters"] = filters

    resp = client.post(const.ENDPOINT_EVENTS_SEARCH, json=search_body)
    resp.raise_for_status()
    return resp.json()


def enrich_event_with_full_details(
    event: dict,
    client: FlareApiClient,
) -> dict:
    """Enrich an event with full details from the API. 400 UNSUPPORTED handled gracefully."""
    uid = event.get("metadata", {}).get("uid")
    if not uid:
        return event

    encoded_uid = urllib.parse.quote(uid, safe="")

    try:
        resp = client.get(f"{const.ENDPOINT_EVENTS_DETAIL}?uid={encoded_uid}")
        resp.raise_for_status()
        full_detail = resp.json()
    except requests.exceptions.HTTPError as e:
        logger.error(
            "Enrichment API returned HTTP %s for UID %s. Response body: %s",
            e.response.status_code if e.response is not None else "Unknown",
            uid,
            e.response.text if e.response is not None else "No response body",
        )
        if e.response is not None and e.response.status_code == 400:
            error_body = e.response.json() if e.response.text else {}
            if (
                isinstance(error_body, dict)
                and error_body.get("error", {}).get("code") == "UNSUPPORTED"
            ):
                logger.warning(
                    "Event UID %s is flagged as UNSUPPORTED by the enrichment API. Proceeding with base event data.",
                    uid,
                )
                return event

        # Return base event on other HTTP errors to prevent cron job crash
        return event

    if isinstance(full_detail, dict) and "data" in full_detail:
        event["data"] = full_detail["data"]

    return event


# Internal Helpers (REST handler context only)


def _get_api_key_from_payload(request: dict) -> str:
    payload = request.get("payload", "")
    params = urllib.parse.parse_qs(payload)
    if "apiKey" not in params:
        raise Exception("API Key is required")
    return params["apiKey"][0]


def _get_proxy_settings_from_session(session_key: str) -> Optional[dict]:
    if not session_key:
        return None
    try:
        _, content = splunk.rest.simpleRequest(
            f"/servicesNS/nobody/{const.APP_NAME}/storage/passwords",
            sessionKey=session_key,
            method="GET",
            # count=0 disables pagination
            getargs={"output_mode": "json", "count": "0"},
        )
        data = json.loads(content)
        return get_proxy_settings(get_all_storage_values(data.get("entry", [])))
    except Exception as e:
        logger.warning("Failed to fetch proxy settings: %s", e)
        return None


def setup_onetime_auth_client(request_obj: dict, sessionKey: str) -> FlareApiClient:
    """Create a FlareApiClient for a one-off REST handler request."""
    api_key = _get_api_key_from_payload(request_obj)

    payload = request_obj.get("payload", "")
    params = urllib.parse.parse_qs(payload)

    # Prioritize proxy settings directly from the UI payload
    if "proxy_enabled" in params:
        ui_proxy_config = {
            const.KEY_PROXY_ENABLED: params["proxy_enabled"][0],
            const.KEY_PROXY_TYPE: params.get("proxy_type", [""])[0],
            const.KEY_PROXY_HOST: params.get("proxy_host", [""])[0],
            const.KEY_PROXY_PORT: params.get("proxy_port", [""])[0],
            const.KEY_PROXY_USERNAME: params.get("proxy_username", [""])[0],
            const.KEY_PROXY_PASSWORD: params.get("proxy_password", [""])[0],
        }
        proxies = get_proxy_settings(ui_proxy_config)
    else:
        # Fallback to saved storage configuration
        proxies = _get_proxy_settings_from_session(sessionKey)

    return create_flare_client(api_key=api_key, proxies=proxies, ssl_verify=True)


def normalize_response(response_json: dict, key: str) -> dict:
    mapped = {}
    if isinstance(response_json, list):
        mapped[key] = response_json
    elif isinstance(response_json, dict):
        if key in response_json:
            mapped[key] = response_json[key]
        elif "items" in response_json:
            mapped[key] = response_json["items"]
        elif "results" in response_json:
            mapped[key] = response_json["results"]
        elif "data" in response_json:
            mapped[key] = response_json["data"]
        else:
            mapped[key] = [response_json]
    else:
        mapped[key] = []
    return mapped


def _classify_error(e: Exception) -> dict:
    """Classify an exception into a structured error response with type information."""
    # TokenError from the SDK means the API key itself is invalid
    if isinstance(e, TokenError):
        return {"error": str(e), "error_type": "auth_error"}
    # Proxy errors surface as requests.exceptions.ProxyError or ConnectionError
    # with a proxy-related message
    if isinstance(e, requests.exceptions.ProxyError):
        return {
            "error": f"Failed to connect through the configured proxy. Details: {e}",
            "error_type": "proxy_error",
        }
    if isinstance(e, (requests.exceptions.ConnectionError, ConnectionError)):
        error_str = str(e).lower()
        if "proxy" in error_str or "tunnel" in error_str:
            return {
                "error": f"Failed to connect through the configured proxy. Details: {e}",
                "error_type": "proxy_error",
            }
        return {
            "error": f"Unable to reach the Flare API. Details: {e}",
            "error_type": "connection_error",
        }
    if isinstance(e, PermissionError):
        return {"error": str(e), "error_type": "auth_error"}
    return {"error": str(e), "error_type": "unknown"}


# Splunk REST Handler Classes (Configuration/Setup page)


class FlareValidateApiKey(splunk.rest.BaseRestHandler):
    """Lightweight endpoint that validates the API key by generating a JWT token."""

    def handle_POST(self) -> None:
        try:
            client = setup_onetime_auth_client(self.request, self.sessionKey)
            # generate_token() is the SDK's public method — validates API key
            client.generate_token()
            self.response.setHeader("Content-Type", "application/json")
            self.response.write(json.dumps({"valid": True}))
        except Exception as e:
            error_info = _classify_error(e)
            if error_info["error_type"] == "proxy_error":
                self.response.setStatus(502)
            elif error_info["error_type"] == "auth_error":
                self.response.setStatus(400)
            else:
                self.response.setStatus(500)
            self.response.write(json.dumps(error_info))


class FlareUserTenants(splunk.rest.BaseRestHandler):
    def handle_POST(self) -> None:
        try:
            client = setup_onetime_auth_client(self.request, self.sessionKey)
            resp = client.get(const.ENDPOINT_TENANTS)
            resp.raise_for_status()
            self.response.setHeader("Content-Type", "application/json")
            self.response.write(json.dumps(normalize_response(resp.json(), "tenants")))
        except Exception as e:
            error_info = _classify_error(e)
            if error_info["error_type"] == "proxy_error":
                self.response.setStatus(502)
            elif error_info["error_type"] == "auth_error":
                self.response.setStatus(400)
            else:
                self.response.setStatus(500)
            self.response.write(json.dumps(error_info))


class FlareSeverityFilters(splunk.rest.BaseRestHandler):
    def handle_POST(self) -> None:
        try:
            client = setup_onetime_auth_client(self.request, self.sessionKey)
            resp = client.get(const.ENDPOINT_FILTER_SEVERITIES)
            resp.raise_for_status()
            self.response.setHeader("Content-Type", "application/json")
            self.response.write(json.dumps(resp.json()))
        except Exception as e:
            error_info = _classify_error(e)
            if error_info["error_type"] == "proxy_error":
                self.response.setStatus(502)
            elif error_info["error_type"] == "auth_error":
                self.response.setStatus(400)
            else:
                self.response.setStatus(500)
            self.response.write(json.dumps(error_info))


class FlareSourceTypeFilters(splunk.rest.BaseRestHandler):
    def handle_POST(self) -> None:
        try:
            client = setup_onetime_auth_client(self.request, self.sessionKey)
            resp = client.get(const.ENDPOINT_FILTER_TYPES)
            resp.raise_for_status()
            self.response.setHeader("Content-Type", "application/json")
            self.response.write(json.dumps(resp.json()))
        except Exception as e:
            error_info = _classify_error(e)
            if error_info["error_type"] == "proxy_error":
                self.response.setStatus(502)
            elif error_info["error_type"] == "auth_error":
                self.response.setStatus(400)
            else:
                self.response.setStatus(500)
            self.response.write(json.dumps(error_info))


class FlareSearchEvents(splunk.rest.BaseRestHandler):
    def handle_POST(self) -> None:
        try:
            client = setup_onetime_auth_client(self.request, self.sessionKey)
            payload = self.request.get("payload", "")
            params = urllib.parse.parse_qs(payload)

            search_body: dict = {"size": 50}
            if params.get("size"):
                try:
                    search_body["size"] = int(params["size"][0])
                except ValueError:
                    pass

            if params.get("from"):
                search_body["from"] = params["from"][0]
            if params.get("order"):
                search_body["order"] = params["order"][0]

            filters: dict = {}
            if params.get("severity"):
                filters["severity"] = params["severity"][0].split(",")
            if params.get("type"):
                filters["type"] = params["type"][0].split(",")
            if params.get("estimated_created_at_gte"):
                filters["estimated_created_at"] = {
                    "gte": params["estimated_created_at_gte"][0]
                }
            if filters:
                search_body["filters"] = filters

            resp = client.post(const.ENDPOINT_EVENTS_SEARCH, json=search_body)
            resp.raise_for_status()
            self.response.setHeader("Content-Type", "application/json")
            self.response.write(json.dumps(resp.json()))
        except Exception as e:
            error_info = _classify_error(e)
            if error_info["error_type"] == "proxy_error":
                self.response.setStatus(502)
            elif error_info["error_type"] == "auth_error":
                self.response.setStatus(400)
            else:
                self.response.setStatus(500)
            self.response.write(json.dumps(error_info))
