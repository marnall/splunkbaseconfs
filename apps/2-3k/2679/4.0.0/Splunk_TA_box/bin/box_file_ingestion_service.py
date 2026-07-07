#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa F401

import sys
import box_file_ingestion_input_helper

from splunklib import modularinput as smi


class BOX_FILE_INGESTION_SERVICE(smi.Script):
    def __init__(self):
        super(BOX_FILE_INGESTION_SERVICE, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("box_file_ingestion_service")
        scheme.description = "File Ingestion Input"
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
                "rest_endpoint",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "file_or_folder_id",
                required_on_create=True,
            )
        )

        return scheme

    def validate_input(self, definition):
        return True

    def stream_events(self, inputs, ew):
        box_file_ingestion_input_helper.stream_events(self, inputs)


if __name__ == "__main__":
    exit_code = BOX_FILE_INGESTION_SERVICE().run(sys.argv)
    sys.exit(exit_code)
