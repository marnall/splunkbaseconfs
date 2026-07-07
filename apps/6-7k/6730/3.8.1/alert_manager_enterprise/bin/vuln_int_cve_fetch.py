#!/usr/bin/env python3.9
#
# File: vuln_int_cve_fetch.py - Version 3.8.1
# Copyright © Datapunctum AG 2026-04-07
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.modularinput import Argument, Scheme

from ame.consts.AppSettings import AppSettings
from ame.models.vuln_int.VulnIntFetchMetaData import FetchStatus, VulnIntFetchMetaData
from ame.modinput_ame import AmeModularInput
from ame.utilities.MessageSearchLinkBuilder import build_trace_uuid_search_link
from dpshared.consts.LogEntryStatus import LogEntryStatus


class VulnIntCVEFetcher(AmeModularInput):
    def get_scheme(self) -> Scheme:
        scheme = Scheme("AME CVE fetcher")
        scheme.description = "This task fetches CVE information."

        ## Optional settings
        # Run this script for all instances
        scheme.use_single_instance = False
        # External validation, if set to true, validate_input() will be run.
        scheme.use_external_validation = True

        # Add arguments to the scheme. Has to match with inputs.conf.spec
        dummy_argument = Argument("default")
        dummy_argument.data_type = Argument.data_type_string
        dummy_argument.description = "Unused Default Argument"
        dummy_argument.required_on_create = True
        scheme.add_argument(dummy_argument)

        return scheme

    def should_run(self) -> bool:
        vuln_int_config = self.vuln_int_config_service.vuln_int_config
        if vuln_int_config.api_key == AppSettings.PASSWORD_PLACEHOLDER:
            # not yet configured - skip all runs
            self.logger.debug(
                {
                    "action": "should_run",
                    "status": LogEntryStatus.SKIPPED,
                    "reason": "Vulnerability intelligence API key is not configured",
                }
            )
            return False
        return True

    def fetch_cves(self) -> None:
        self.logger.info(
            {
                "action": "fetch_cves",
                "status": LogEntryStatus.STARTED,
            }
        )
        try:
            if self.vuln_int_fetch_meta_data_service.has_last_vuln_int_meta_data():
                last_vuln_int_metadata = (
                    self.vuln_int_fetch_meta_data_service.vuln_int_fetch_meta_data
                )
            else:
                last_vuln_int_metadata = VulnIntFetchMetaData(
                    started_at=int(time.time()),
                    completed_at=0,
                    last_run_uuid="",
                    status=FetchStatus.INITIAL,
                )
            self.vuln_fetch_service.fetch_vuln_int_data(metadata=last_vuln_int_metadata)
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "fetch_cves",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )
        self.logger.info(
            {
                "action": "fetch_cves",
                "status": LogEntryStatus.SUCCESS,
            }
        )

    def fetch_cve_modifications(self) -> None:
        pass

    def handle_stream_events(
        self,
        inputs: Any,  # noqa: ANN401
        ew: Any,  # noqa: ANN401
    ) -> None:
        try:
            self.vuln_int_config_service = self.service_factory.vuln_int_config_service
            self.vuln_int_fetch_meta_data_service = (
                self.service_factory.vuln_int_fetch_meta_data_service
            )
            self.vuln_fetch_service = self.service_factory.vuln_int_fetch_service

            if not self.should_run():
                self.logger.info(
                    {
                        "action": "handle_stream_events",
                        "status": LogEntryStatus.SKIPPED,
                        "should_run": False,
                    }
                )
                return

            try:
                self.fetch_cves()
                self.fetch_cve_modifications()
            except Exception as exc:
                self.sdk_wrapper.send_message(
                    name="cve_fetch_error",
                    value=f'Failed to fetch CVE data for vulnerability intelligence with error "{exc}". {build_trace_uuid_search_link(self.sdk_wrapper.uuid)}',
                    severity="error",
                )

        except Exception as exc:
            self.logger.exception(
                {
                    "action": "handle_stream_events",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )


if __name__ == "__main__":
    sys.exit(VulnIntCVEFetcher().run(sys.argv))
