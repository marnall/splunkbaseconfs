#!/usr/bin/env python3.7
#
# File: modinput_s3spl_housekeeping.py - Version 1.0.4
# Copyright (c) Datapunctum AG 2024-11-22
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

import os
import sys
import uuid
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Splunk Enterprise SDK
import splunklib.client as client
from splunklib.modularinput import Script, Scheme

from s3spl_template.factory_logger import Logger
from s3spl_template.service_minit import MinitService

from s3spl.service_bucket import BucketService


class S3SelectSPLHousekeeping(Script):
    def get_scheme(self):
        scheme = Scheme("S3SelectSPL Housekeeping")

        scheme.description = "S3SelectSPL Housekeeping"
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        return scheme

    def validate_input(self, validation_definition):
        pass  # passing as there is no input provided to this modular input

    def stream_events(self, inputs, ew):
        self.uuid = str(uuid.uuid4())
        session_key = self._input_definition.metadata["session_key"]
        self.logger = Logger(logname="modinput", uuid=self.uuid)

        try:
            elastic_instance_service = BucketService(uuid=self.uuid, client=client, session_key=session_key, user="splunk-system-user")
            # Get instances runs __license_ok which will update the license status
            elastic_instance_service.get_buckets()

            # Instantiate the minit service to set the current version
            minit_service = MinitService(uuid=self.uuid, client=client, session_key=session_key, user="splunk-system-user")

        except Exception:
            self.logger.exception("Failed to run modular input")


if __name__ == "__main__":
    exitcode = S3SelectSPLHousekeeping().run(sys.argv)
    sys.exit(exitcode)
