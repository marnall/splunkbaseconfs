#!/usr/bin/env python3.9
#
# File: tag_keeping.py - Version 3.8.1
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


class TagKeeper(AmeModularInput):
    def get_scheme(self) -> Scheme:
        scheme = Scheme("AME Tag Housekeeping")
        scheme.description = "This task goes through all events and creates tags for all tenants."

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
            tag_service = self.service_factory.tag_service
            tag_service.create_event_tags()
        except Exception as exc:
            self.logger.exception(
                {"action": "handle_stream_events", "status": "failed", "exception": exc}
            )


if __name__ == "__main__":
    sys.exit(TagKeeper().run(sys.argv))
