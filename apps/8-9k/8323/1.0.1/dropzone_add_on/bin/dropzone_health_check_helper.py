"""
Dropzone AI Health Check Input Helper Module

This module implements the health check functionality for monitoring
Dropzone AI instance availability.
"""

import json
import logging
import os
import sys

import import_declare_test
import requests
from solnlib import conf_manager, credentials, log
from splunklib import modularinput as smi

ADDON_NAME = "dropzone_add_on"


def logger_for_input(input_name: str) -> logging.Logger:
    """Get a logger instance for the specified input."""
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def validate_input(definition: smi.ValidationDefinition) -> None:
    """Validate input configuration before saving."""
    pass


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    """
    Stream health check events from Dropzone AI.

    This function is called by Splunk to collect data from the modular input.
    It makes a request to the Dropzone AI ping endpoint and writes the result
    as a Splunk event.
    """
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)

        try:
            session_key = inputs.metadata["session_key"]

            # Set log level from configuration
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name=f"{ADDON_NAME}_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            # Get input configuration
            base_url = input_item.get("base_url", "").rstrip("/")
            index = input_item.get("index", "default")

            if not base_url:
                logger.error(f"Input {normalized_input_name}: base_url is required")
                continue

            # Retrieve encrypted API key from credential storage
            # The CredentialManager.get_password() method expects just the base username
            # (without the ``splunk_cred_sep``N suffix) because it internally strips that
            # when building the clear password list
            cred_mgr = credentials.CredentialManager(
                session_key=session_key,
                app=ADDON_NAME,
                realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#data/inputs/dropzone_health_check",
            )

            # Get credential for this specific input - use just the input name, not the full credential username
            try:
                # get_password expects the base username, it will find all parts with ``splunk_cred_sep``N
                api_key = cred_mgr.get_password(normalized_input_name)
                if not api_key:
                    api_key = ""
                logger.info(
                    f"Retrieved credential for {normalized_input_name}, length: {len(api_key) if api_key else 0}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to retrieve credential for {normalized_input_name}: {e}"
                )
                api_key = ""

            # Log raw API key format for debugging
            logger.info(
                f"Raw api_key type: {type(api_key)}, length: {len(api_key) if api_key else 0}, starts_with_brace: {api_key.strip().startswith('{') if api_key else False}"
            )

            # Parse API key if it's stored as JSON (UCC framework behavior)
            if api_key and api_key.strip().startswith("{"):
                logger.info(f"API key appears to be JSON, attempting to parse")
                try:
                    api_key_json = json.loads(api_key)
                    original_key = api_key
                    api_key = api_key_json.get("api_key", "")
                    logger.info(
                        f"Successfully parsed JSON credential, extracted api_key field (length: {len(api_key)})"
                    )
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Failed to parse API key JSON for {normalized_input_name}: {e}"
                    )

            # Make health check request
            url = f"{base_url}/app/api/dev/ping"
            headers = {}
            if api_key:
                # Handle API key with or without "Api-Key" prefix
                if api_key.strip().startswith("Api-Key "):
                    headers["Authorization"] = api_key.strip()
                    logger.info(
                        f"Using API key with existing prefix (first 15 chars: {api_key[:15]}...)"
                    )
                else:
                    headers["Authorization"] = f"Api-Key {api_key.strip()}"
                    logger.info(
                        f"Added Api-Key prefix (first 15 chars of result: Api-Key {api_key[:8]}...)"
                    )
                logger.info(
                    f"Final Authorization header length: {len(headers['Authorization'])}"
                )
            else:
                logger.warning(f"No API key provided for {normalized_input_name}")

            sourcetype = "dropzone:healthcheck"

            try:
                response = requests.get(url, headers=headers, timeout=10, verify=False)
                status_code = response.status_code

                # Accept any 2xx status code as healthy
                is_healthy = 200 <= status_code < 300

                event_data = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "status_code": status_code,
                }

                logger.info(
                    f"Health check for {normalized_input_name}: "
                    f"status={event_data['status']}, code={status_code}"
                )

            except requests.exceptions.RequestException as e:
                logger.error(f"Health check failed for {normalized_input_name}: {e}")
                event_data = {
                    "status": "error",
                    "status_code": None,
                    "url": url,
                    "error": str(e),
                }

            # Write event to Splunk
            event_writer.write_event(
                smi.Event(
                    data=json.dumps(event_data, ensure_ascii=False, default=str),
                    index=index,
                    sourcetype=sourcetype,
                )
            )

            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                1,
                index,
            )
            log.modular_input_end(logger, normalized_input_name)

        except Exception as e:
            log.log_exception(
                logger,
                e,
                "health_check_error",
                msg_before=f"Exception raised while collecting health check for {normalized_input_name}: ",
            )
