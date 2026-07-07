#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""

* isort ignores:
- isort: skip = Should not be sorted.
* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""

import splunk_ta_remedy_declare  # isort: skip # noqa: F401
import sys

import remedy_input_helper
from splunklib import modularinput as smi


class REMEDY_INPUT(smi.Script):
    def __init__(self):
        super(REMEDY_INPUT, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("remedy_input")
        scheme.description = "Remedy Input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
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
                "form_name",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "include_properties",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "exclude_properties",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "timefield",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "reuse_checkpoint",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "query_start_date",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "qualification",
                required_on_create=False,
            )
        )

        return scheme

    def validate_input(self, definition):
        remedy_input_helper.validate_input(self, definition)

    def stream_events(self, inputs, ew):
        remedy_input_helper.stream_events(self, inputs, ew)


if __name__ == "__main__":
    exit_code = REMEDY_INPUT().run(sys.argv)
    sys.exit(exit_code)
