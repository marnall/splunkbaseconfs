#!/usr/bin/env python3
# coding=utf-8
"""
ansible_es.py 

Splunk ES Adaptive Response Script

Logic:
-------------
1) Inherits from cim_actions.ModularAction so Splunk ES recognizes it as an adaptive response.
2) Reads gzipped CSV results from Splunk, iterates each row, and logs introspection events
   for ES using the Common Action Model (update(), invoke(), message(), etc.).
3) Sends data to your configured webhook endpoint using integration_client.send_data_webhook_async().
   - Reuses the same chunking, concurrency, SSL, auth logic in integration_client.py.
4) Writes out any new Splunk events if desired (e.g., you could call self.addevent()
   and self.writeevents() to produce additional data).

Usage:
------
1. Triggered by Splunk ES (manually in Incident Review or by correlation search).
2. Or tested with: | sendalert ansible_es param.alert_type="webhook" param.environment="local"
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import csv
import gzip
import asyncio
import base64
import logging
import traceback
from typing import Any, Optional

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "Splunk_SA_CIM", "lib"]))  # Adjust if needed
from cim_actions import ModularAction, ModularActionTimer

import integration_client
from integration_client import update_dynamic_log_level

from solnlib.log import Logs
Logs.set_context(
    directory=f"{os.environ.get('SPLUNK_HOME', '/opt/splunk')}/var/log/splunk",
    namespace="ansible_addon_for_splunk"
)
logger = Logs().get_logger("es_alert")

class AnsibleESAction(ModularAction):
    def __init__(self, settings, logger, action_name="ansible_es"):
        super(AnsibleESAction, self).__init__(settings, logger, action_name)

        # Set dynamic log level
        session_key = self.settings.get("session_key")
        update_dynamic_log_level(logger, session_key, "ansible_addon_for_splunk")
        # Read user parameters from self.configuration
        # or from the top-level settings object
        self.alert_type = self.configuration.get("alert_type", "webhook").lower()
        self.environment = self.configuration.get("environment", "")
        self.send_all_results = self.configuration.get("send_all_results", "no").lower()

    def validate(self, result):
        """
        Called once per result after self.update(result).
        We'll check if environment and alert_type are valid.
        """
        # Only do "outer" param checks if we haven't done so yet
        # (len(self.rids) <= 1 => first iteration)
        if len(self.rids) <= 1:
            if self.alert_type not in ("webhook", "kafka"):
                raise ValueError("Invalid alert_type; must be 'webhook' or 'kafka'.")
            if not self.environment and self.alert_type == "webhook":
                raise ValueError("Missing 'environment' param for webhook mode.")

        # Check mandatory field for each row (like 'rid')
        # If not set, you can raise an exception
        if "rid" not in result:
            raise ValueError("Result row is missing 'rid' field.")

    def dowork(self, result):
        """
        Called for each result after validate(). 
        If you want to do per-event logic (like partial calls or local transforms), do it here.
        Otherwise, you can wait until after the loop to send all results at once.
        For example, you might call self.addevent(...) to add a local Splunk event about each row.
        """
        # We are not doing anything row by row here right now,because we plan to gather all results for a single webhook call at the end.
        pass

    def run_main(self):
        """
        Custom method that encloses:
        1) Reading the gzipped CSV results
        2) Iterating per row => update(), invoke(), validate(), dowork()
        3) Then either sending data to the webhook or finishing
        """
        # Initialize introspection events
        self.addevent(
            raw=f"Adaptive response action 'ansible_es' invoked. Alert type: {self.alert_type}, Environment: {self.environment}.",
            sourcetype="ansible:alert"
        )
        # If alert_type != "webhook", skip
        if self.alert_type == "kafka":
            self.message("Skipping kafka in this script", status="skipped")
            self.addevent(
                raw="Alert type 'kafka' detected. No processing performed.",
                sourcetype="ansible:alert"
            )
            self.writeevents(index="main", source="ansible:alert")
            return 0

        # Gather results in memory, depending on send_all_results param
        # We'll store them in `self.all_results` for final posting
        self.all_results = None
        rows_processed = 0
        
        try:
            if self.send_all_results == "compressed":
                self.all_results = self._encode_results_as_base64()
                rows_processed = 1 if self.all_results else 0
            elif self.send_all_results == "plaintext":
                self.all_results = []
                with gzip.open(self.results_file, mode="rt", encoding="utf-8") as fh:
                    reader = csv.DictReader(fh)
                    for idx, row in enumerate(reader):
                        rows_processed += 1
                        if "rid" not in row:
                            row["rid"] = str(idx)
                        # Common Action Model calls
                        self.update(row)
                        self.invoke()
                        self.validate(row)
                        self.dowork(row)
                        self.all_results.append(row)
            else:
                with gzip.open(self.results_file, mode="rt", encoding="utf-8") as fh:
                    reader = csv.DictReader(fh)
                    first_row = next(reader, None)
                    if first_row:
                        if "rid" not in first_row:
                            first_row["rid"] = "0"
                        self.update(first_row)
                        self.invoke()
                        self.validate(first_row)
                        self.dowork(first_row)
                        self.all_results = [first_row]
                        rows_processed = 1

            # Add introspection events
            self.addevent(
                raw=f"Processed {rows_processed} result rows from Splunk. Send all results mode: {self.send_all_results}.",
                sourcetype="ansible:alert"
            )

            # Actual webhook call
            try:
                self._send_webhook_data()
                self.message("Data successfully sent to the webhook", status="success")
                self.addevent(
                    raw="Webhook data successfully sent.",
                    sourcetype="ansible:alert"
                )
            except Exception as exc:
                self.message(f"Failed to send data: {exc}", status="failure", level=logging.ERROR)
                self.addevent(
                    raw=f"Failed to send data to webhook: {exc}.",
                    sourcetype="ansible:alert"
                )
                self.logger.debug(traceback.format_exc())
                return 3

        except Exception as e:
            self.message(f"Error processing results: {e}", status="failure", level=logging.ERROR)
            self.addevent(
                raw=f"Error during processing: {e}.",
                sourcetype="ansible:alert"
            )
            self.logger.debug(traceback.format_exc())
            return 3

        # Write all introspection events to Splunk
        self.writeevents(index="main", source="ansible:alert")
        return 0

    def _encode_results_as_base64(self) -> Optional[str]:
        """
        Reads the entire results_file (gzipped) into memory, base64-encodes it,
        and returns the string. This is used for 'compressed' mode.
        """
        if not os.path.exists(self.results_file):
            raise FileNotFoundError(f"Results file not found: {self.results_file}")

        with open(self.results_file, "rb") as fh:
            raw_bytes = fh.read()
            b64 = base64.b64encode(raw_bytes).decode("utf-8")
            return b64

    def _send_webhook_data(self):
        """
        Actually obtains the environment config, sets up metadata,
        and calls integration_client.send_data_webhook_async(...).
        """
        # 1) Get environment config from ansible_addon_for_splunk_environment.conf
        env_config = integration_client.get_webhook_env_config(self.environment, self.session_key)

        # 2) Splunk metadata
        sid = self.settings.get("sid")
        search_name = self.settings.get("search_name")
        owner = self.settings.get("owner") or self.settings.get("user")
        app = self.settings.get("app")
        results_web_link = self.settings.get("results_link")
        # Optionally build a REST link to results
        results_rest_link = None
        if sid:
            from solnlib import splunkenv
            splunkd_scheme, splunkd_host, splunkd_port = splunkenv.get_splunkd_access_info(self.session_key)
            external_host = self.settings.get("server_host", splunkd_host)
            results_rest_link = f"{splunkd_scheme}://{external_host}:{splunkd_port}/services/search/v2/jobs/{sid}/results"

        # 3) Decide how many results per batch
        param_rpb = self.configuration.get("results_per_batch")
        default_rpb = env_config.get("results_per_batch", integration_client.MAX_RECORDS_PER_BATCH)
        results_per_batch = int(param_rpb) if param_rpb else int(default_rpb)

        # 4) Make the async call
        #    raw_payload_mode=False => old universal wrapper with "sid", "search_name", "results"
        self.logger.info("Initiating async webhook POST to %s", env_config.get("webhook_endpoint", "??"))
        asyncio.run(
            integration_client.send_data_webhook_async(
                all_results=self.all_results,
                sid=sid,
                search_name=search_name,
                owner=owner,
                app=app,
                results_web_link=results_web_link,
                results_rest_link=results_rest_link,
                env_config=env_config,
                send_all_results_mode=self.send_all_results,
                results_per_batch=results_per_batch,
                raw_payload_mode=False
            )
        )
        self.logger.info("Webhook data send completed successfully.")

if __name__ == "__main__":
    """
    Execution entry point when Splunk calls our adaptive response script.
    We parse the JSON from stdin, initialize our AnsibleESAction, and run_main().
    The .run() method calls parseargs + process_event => we override "process_event"
    by hooking into "run_main()" for the entire logic. 
    """
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        print("FATAL: This script must be run via --execute mode in Splunk (Adaptive Response).", file=sys.stderr)
        sys.exit(1)

    exit_code = 1
    try:
        # 1) Read JSON settings payload from Splunk
        payload = sys.stdin.read()

        # 2) Create our action instance
        modaction = AnsibleESAction(settings=payload, logger=logger, action_name="ansible_es")

        # 3) Optionally measure the main code block run time
        with ModularActionTimer(modaction, "main", modaction.start_timer):
            # The default "process_event(...)" from ModularAction is replaced by our own method
            # so we can do everything in a single pass. We can simply call a custom method:
            exit_code = modaction.run_main()

    except Exception as e:
        # Log any failure to ES introspection
        try:
            if "modaction" in locals():
                modaction.message(str(e), status="failure", level=logging.CRITICAL)
            logger.critical(e)
        except:
            logger.critical(e)
        print(f"ERROR: {e}", file=sys.stderr)
        exit_code = 3

    sys.exit(exit_code)
