#!/usr/bin/env python3.9
#
# File: sla_housekeeping.py - Version 3.8.1
# Copyright © Datapunctum AG 2026-04-07
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.modularinput import Argument, Scheme

from ame.modinput_ame import AmeModularInput


class SLAHouseKeeping(AmeModularInput):
    def get_scheme(self) -> Scheme:
        scheme = Scheme("AME SLA Housekeeping")
        scheme.description = "This task processes house keeping tasks for the SLA Engine"

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

    def handle_stream_events(
        self,
        inputs: Any,  # noqa: ANN401
        ew: Any,  # noqa: ANN401
    ) -> None:
        try:
            sla_service = self.service_factory.sla_service
            sla_service.process_sla_entries()
            self.logger.debug({"action": "process_slas", "status": "success"})
        except Exception as exc:
            self.logger.exception(
                {"action": "handle_stream_events", "status": "failed", "exception": exc}
            )


if __name__ == "__main__":
    sys.exit(SLAHouseKeeping().run(sys.argv))
