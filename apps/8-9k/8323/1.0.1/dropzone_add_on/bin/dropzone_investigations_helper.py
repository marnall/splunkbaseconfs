"""
Dropzone AI Investigations Input Helper Module

This module implements the investigations collection functionality for
fetching completed investigation data from Dropzone AI.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional

import import_declare_test
import requests
from solnlib import conf_manager, credentials, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

ADDON_NAME = "dropzone_add_on"


def logger_for_input(input_name: str) -> logging.Logger:
    """Get a logger instance for the specified input."""
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def max_iso8601_timestamp(timestamps: list) -> Optional[str]:
    """
    Find the maximum ISO8601 timestamp from a list.

    Args:
        timestamps: List of ISO8601 timestamp strings

    Returns:
        The maximum timestamp string, or None if no valid timestamps
    """
    if not timestamps:
        return None

    max_ts = None
    max_dt = None

    for ts in timestamps:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if max_dt is None or dt > max_dt:
                max_dt = dt
                max_ts = ts
        except (ValueError, AttributeError):
            continue

    return max_ts


def validate_input(definition: smi.ValidationDefinition) -> None:
    """Validate input configuration before saving."""
    pass


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    """
    Stream investigation events from Dropzone AI.

    This function is called by Splunk to collect data from the modular input.
    It fetches completed investigations from the Dropzone AI API and writes
    them as Splunk events. It uses checkpointing to avoid duplicate data.
    """
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)

        try:
            session_key = inputs.metadata["session_key"]
            checkpoint_dir = inputs.metadata.get("checkpoint_dir", "")

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
                realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#data/inputs/dropzone_investigations",
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

            if not api_key:
                logger.error(f"Input {normalized_input_name}: api_key is required")
                continue

            # Log raw API key format for debugging
            logger.info(
                f"Raw api_key type: {type(api_key)}, length: {len(api_key)}, starts_with_brace: {api_key.strip().startswith('{')}"
            )

            # Parse API key if it's stored as JSON (UCC framework behavior)
            if api_key.strip().startswith("{"):
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

            # Initialize checkpointer for state management
            ckpt = None
            checkpoint_key = f"dropzone_investigations_{normalized_input_name}"
            checkpoint_data = {}

            if checkpoint_dir:
                try:
                    ckpt = checkpointer.FileCheckpointer(checkpoint_dir)
                    checkpoint_data = ckpt.get(checkpoint_key) or {}
                except Exception as e:
                    logger.warning(f"Failed to get checkpoint: {e}")

            last_max_created_at = checkpoint_data.get("last_max_created_at", "")

            # Build URL with optional timestamp parameter
            url = f"{base_url}/app/api/v1/investigation"
            if last_max_created_at:
                url = f"{url}?inv_complete_from={last_max_created_at}"

            # Handle API key with or without "Api-Key" prefix
            if api_key.strip().startswith("Api-Key "):
                auth_header = api_key.strip()
                logger.info(
                    f"Using API key with existing prefix (first 15 chars: {api_key[:15]}...)"
                )
            else:
                auth_header = f"Api-Key {api_key.strip()}"
                logger.info(
                    f"Added Api-Key prefix (first 15 chars of result: Api-Key {api_key[:8]}...)"
                )

            logger.info(f"Final Authorization header length: {len(auth_header)}")
            headers = {"Authorization": auth_header}
            sourcetype = "dropzone:investigation"

            try:
                response = requests.get(url, headers=headers, timeout=30, verify=False)
                response.raise_for_status()

                # Handle empty response
                if response.status_code == 204 or not response.text.strip():
                    logger.info(f"No new investigations for {normalized_input_name}")
                    log.modular_input_end(logger, normalized_input_name)
                    continue

                data = response.json()
                investigations = data.get("results", [])

                if not investigations:
                    logger.info(f"No investigations found for {normalized_input_name}")
                    log.modular_input_end(logger, normalized_input_name)
                    continue

                # Extract created_at timestamps for checkpointing
                created_at_list = [
                    inv.get("created_at")
                    for inv in investigations
                    if inv.get("created_at")
                ]
                new_max_created_at = max_iso8601_timestamp(created_at_list)

                # Write each investigation as a separate event
                for investigation in investigations:
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(
                                investigation, ensure_ascii=False, default=str
                            ),
                            index=index,
                            sourcetype=sourcetype,
                        )
                    )

                # Update checkpoint with new max timestamp
                if new_max_created_at and ckpt:
                    try:
                        ckpt.update(
                            checkpoint_key, {"last_max_created_at": new_max_created_at}
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update checkpoint: {e}")

                logger.info(
                    f"Collected {len(investigations)} investigations for {normalized_input_name}"
                )

                log.events_ingested(
                    logger,
                    input_name,
                    sourcetype,
                    len(investigations),
                    index,
                )

            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Failed to fetch investigations for {normalized_input_name}: {e}"
                )
            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to parse JSON response for {normalized_input_name}: {e}"
                )

            log.modular_input_end(logger, normalized_input_name)

        except Exception as e:
            log.log_exception(
                logger,
                e,
                "investigations_error",
                msg_before=f"Exception raised while collecting investigations for {normalized_input_name}: ",
            )
