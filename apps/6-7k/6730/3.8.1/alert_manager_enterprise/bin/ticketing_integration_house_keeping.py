#!/usr/bin/env python3.9
#
# File: ticketing_integration_house_keeping.py - Version 3.8.1
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

from ame.modinput_ame import AmeModularInput
from dpshared.consts.LogEntryStatus import LogEntryStatus


class TicketingIntegrationHouseKeeper(AmeModularInput):
    def get_scheme(self) -> Scheme:
        scheme = Scheme("AME Ticketing Integration Housekeeping")
        scheme.description = "This task processes all updates that are queued up for remote, and loads all remote events into the local state"

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

    def sync_local_to_remote(self) -> None:
        try:
            self.logger.info(
                {
                    "action": "sync_local_to_remote",
                    "status": LogEntryStatus.STARTED,
                }
            )
            local_to_remote_start_time = time.time()
            self.service_factory.ticketing_integration_service.process_queue()
            self.logger.info(
                {
                    "action": "sync_local_to_remote",
                    "status": LogEntryStatus.SUCCESS,
                    "duration": time.time() - local_to_remote_start_time,
                }
            )
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "sync_local_to_remote",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )

    def sync_remote_to_local(self) -> None:
        try:
            self.logger.info(
                {
                    "action": "sync_remote_to_local",
                    "status": LogEntryStatus.STARTED,
                }
            )
            remote_to_local_start_time = time.time()
            self.service_factory.ticketing_integration_service.process_all_events_with_ticketing_integration()
            self.logger.info(
                {
                    "action": "sync_remote_to_local",
                    "status": LogEntryStatus.SUCCESS,
                    "duration": time.time() - remote_to_local_start_time,
                }
            )
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "sync_remote_to_local",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )

    def handle_stream_events(
        self,
        inputs: Any,  # noqa: ANN401
        ew: Any,  # noqa: ANN401
    ) -> None:
        try:
            self.sync_local_to_remote()
            self.sync_remote_to_local()
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "handle_stream_events",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )


if __name__ == "__main__":
    sys.exit(TicketingIntegrationHouseKeeper().run(sys.argv))
