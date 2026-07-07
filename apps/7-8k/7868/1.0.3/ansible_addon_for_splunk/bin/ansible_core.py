#!/usr/bin/env python3
# coding=utf-8

"""
ansible_core.py

Logic:
-------------
- Reads search results via self.get_events()
- Builds the standard Splunk "wrapped" JSON shape with "sid", "search_name", etc.
- Sends data to your webhook via integration_client.send_data_webhook_async(), with
  raw_payload_mode=False to preserve the old "universal wrapper" approach.

This script is aligned with the newly refactored integration_client.py that supports
a 'raw_payload_mode' toggle.

Usage:
------
This script is triggered by Splunk when a saved search alert fires or via the | sendalert command.
It references configuration for environment, auth, SSL, etc. from
ansible_addon_for_splunk_environment.conf.
"""

import os
import sys

import asyncio
import base64
import logging
import logging.config
import traceback
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunktaucclib.alert_actions_base import ModularAlertBase
from solnlib.log import Logs
from solnlib import conf_manager, splunkenv

import integration_client
from integration_client import update_dynamic_log_level

Logs.set_context(
    directory=f"{os.environ.get('SPLUNK_HOME', '/opt/splunk')}/var/log/splunk",
    namespace="ansible_addon_for_splunk"
)
splunk_logger = Logs().get_logger("core_alert")

class AlertActionWorkeransible_core(ModularAlertBase):
    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkeransible_core, self).__init__(ta_name, alert_name)
        session_key = self.settings.get("session_key")
        update_dynamic_log_level(splunk_logger, session_key, "ansible_addon_for_splunk")
        self.log_debug(f"Parsed payload: {self.settings}")
        self._app = self.settings.get("app")
        if not self._app:
            raise ValueError("Missing 'app' in the alert payload. Ensure the payload includes the app name.")
    
    def validate_params(self) -> bool:
        """Ensure alert_type is valid and environment is specified if alert_type=webhook."""
        alert_type = self.get_param("alert_type") or "webhook"
        if alert_type not in ["webhook", "kafka"]:
            self.log_error("Invalid alert_type. Must be 'webhook' or 'kafka'.")
            return False

        environment = self.get_param("environment")
        if not environment:
            self.log_error(f"For '{alert_type}' alert_type, 'environment' is required.")
            return False

        return True

    def _encode_results_file_as_base64(self) -> Optional[str]:
        """
        Reads and base64-encodes the gzipped results file for "compressed" mode.
        """
        try:
            if not os.path.exists(self.results_file):
                self.log_error(f"Results file {self.results_file} does not exist.")
                return None

            size = os.path.getsize(self.results_file)
            self.log_debug(f"Found results file at {self.results_file}, size={size} bytes.")

            with open(self.results_file, "rb") as f:
                gz_data = f.read()
                b64_data = base64.b64encode(gz_data).decode("utf-8")
                self.log_debug(f"Encoded file => base64 length={len(b64_data)}")
                return b64_data

        except Exception as e:
            self.log_error(f"Error encoding gzipped results: {e}")
            self.log_debug(traceback.format_exc())
            return None

    def process_event(self, *args, **kwargs) -> int:
        """
        Main entry point for Splunk to call this custom alert action.
        """
        self.log_info(f"Python runtime: {sys.version}, executable: {sys.executable}")

        if not self.validate_params():
            return 4

        alert_type = self.get_param("alert_type")
        self.log_info(f"Alert type={alert_type}")

        if alert_type == "kafka":
            # For Kafka, user might handle it differently
            self.log_info("Kafka selected, skipping for this script.")
            return 0

        if alert_type == "webhook":
            environment = self.get_param("environment")
            send_all_results = (self.get_param("send_all_results") or "no").lower()
            self.log_debug(f"Webhook => environment={environment}, send_all_results={send_all_results}")

            # 1) Retrieve environment config from ansible_addon_for_splunk_environment.conf
            try:
                env_config = self._get_webhook_env_config(environment)
            except ValueError as e:
                self.log_error(str(e))
                return 3

            # 2) Gather data from self.get_events() based on 'send_all_results'
            if send_all_results in [None, "0", "no"]:
                first_row = next(self.get_events(), None)
                results_data = [first_row] if first_row else []
            elif send_all_results == "plaintext":
                results_data = list(self.get_events())
            elif send_all_results == "compressed":
                encoded = self._encode_results_file_as_base64()
                if not encoded:
                    self.log_error("Failed to read/encode gzipped results.")
                    return 3
                results_data = encoded
            else:
                self.log_error(f"Invalid send_all_results option: {send_all_results}")
                return 3

            # 3) Collect Splunk metadata
            sid = self.settings.get("sid")
            search_name = self.settings.get("search_name")
            app = self.settings.get("app")
            owner = self.settings.get("owner")
            results_web_link = self.settings.get("results_link")
            results_rest_link = None
            if sid:
                splunkd_scheme, splunkd_host, splunkd_port = splunkenv.get_splunkd_access_info(self.session_key)
                external_host = self.settings.get("server_host", splunkd_host)
                results_rest_link = f"{splunkd_scheme}://{external_host}:{splunkd_port}/services/search/v2/jobs/{sid}/results"

            # 4) Kick off async sending using integration_client
            self.log_info("Beginning async send to the webhook.")
            try:
                asyncio.run(
                    self._send_results_async(
                        env_config, sid, search_name, owner, app,
                        results_web_link, results_rest_link, results_data, send_all_results
                    )
                )
                self.log_info("Data successfully sent to the webhook.")
                return 0
            except Exception as e:
                self.log_error(f"Failed to send data: {e}")
                self.log_debug(traceback.format_exc())
                return 3

        # If we get here, unknown type
        self.log_error(f"Unknown alert_type={alert_type}")
        return 3

    def _get_webhook_env_config(self, environment: str) -> dict:
        """
        Load stanza from ansible_addon_for_splunk_environment.conf matching:
           integration_type=webhook & environment=<env>
        """
        session_key = self.session_key
        if not session_key:
            raise ValueError("Missing session_key for environment retrieval.")
        app_context = "ansible_addon_for_splunk"  # or your actual add-on name
        realm = f"__REST_CREDENTIAL__#{app_context}#configs/conf-ansible_addon_for_splunk_environment"
        self.log_debug(f"Fetching environment={environment}, realm={realm}")

        try:
            cfm = conf_manager.ConfManager(session_key, app_context, realm=realm)
            env_conf = cfm.get_conf("ansible_addon_for_splunk_environment").get_all()
            self.log_debug(f"Got {len(env_conf)} stanzas from environment conf.")
        except Exception as e:
            self.log_error(f"Error reading environment conf: {e}")
            raise

        # find matching environment
        for stanza_name, stanza_data in env_conf.items():
            if stanza_data.get("integration_type") == "webhook" and stanza_data.get("environment") == environment:
                self.log_debug(f"Matched environment '{environment}' in stanza '{stanza_name}'")
                return stanza_data

        error_msg = f"No webhook stanza found for environment='{environment}'"
        self.log_error(error_msg)
        raise ValueError(error_msg)

    async def _send_results_async(
        self,
        env_config: dict,
        sid: Optional[str],
        search_name: Optional[str],
        owner: Optional[str],
        app: Optional[str],
        results_web_link: Optional[str],
        results_rest_link: Optional[str],
        all_results: Any,
        send_all_results_mode: str
    ) -> None:
        """
        Asynchronous helper that calls integration_client.send_data_webhook_async()
        with raw_payload_mode=False to preserve the "universal wrapper" payload format.
        """
        self.log_debug(f"Starting _send_results_async => sid={sid}, search_name={search_name}")

        # Parse results_per_batch from param or environment config
        param_rpb = self.get_param("results_per_batch")
        default_rpb = env_config.get("results_per_batch", integration_client.MAX_RECORDS_PER_BATCH)
        results_per_batch = int(param_rpb) if param_rpb else int(default_rpb)

        self.log_debug(f"Using results_per_batch={results_per_batch} from either param or config")
        # Actually send via integration_client
        await integration_client.send_data_webhook_async(
            all_results=all_results,
            sid=sid,
            search_name=search_name,
            owner=owner,
            app=app,
            results_web_link=results_web_link,
            results_rest_link=results_rest_link,
            env_config=env_config,
            send_all_results_mode=send_all_results_mode,
            results_per_batch=results_per_batch,
            raw_payload_mode=False  # <-- THIS ensures old "sid/results" wrapper
        )
        self.log_debug("Completed call to integration_client.send_data_webhook_async.")

if __name__ == "__main__":
    exitcode = AlertActionWorkeransible_core("ansible_addon_for_splunk", "ansible_core").run(sys.argv)
    sys.exit(exitcode)
