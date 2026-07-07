#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa F401
import sys

import box_input_helper
from splunklib import modularinput as smi


class BOX_LIVE_MONITORING_SERVICE(smi.Script):
    def __init__(self):
        super(BOX_LIVE_MONITORING_SERVICE, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("box_live_monitoring_service")
        scheme.description = "Live Monitoring Inputs"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name",
                title="Name",
                description="Name",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "account",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "rest_endpoint",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "reuse_checkpoint",
                required_on_create=False,
            )
        )

        return scheme

    def validate_input(self, definition):
        box_input_helper.validate_input(self, definition)

    def stream_events(self, inputs, ew):
        box_input_helper.stream_events(self, inputs, ew)


if __name__ == "__main__":
    exit_code = BOX_LIVE_MONITORING_SERVICE().run(sys.argv)
    sys.exit(exit_code)
