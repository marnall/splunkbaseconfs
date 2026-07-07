# Copyright (C) 2025 Stairwell Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License found in the LICENSE file in the root directory of
# this source tree. Also found at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Streaming search command for Stairwell"""

import os
import sys
import json

# Since we need to bundle Python dependencies with the Splunk app to ensure it's portable, we need
# to work around some packages that do not use relative imports by explicitly adding their locations
# to sys.path. It's ~~a bit~~ hacky, but works for now.
# It also needs to go here instead of `__init__.py`, since Splunk does not seem to evaluate it.
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "stairwelllib"))


from logging import Logger
from typing import Optional
from stairwelllib.stairwellapi import search_stairwell_ip_addresses_api
from stairwelllib.stairwellapi import search_stairwell_object_api
from stairwelllib.stairwellapi import search_stairwell_hostname_api
from stairwelllib.client import StairwellAPI, StairwellEnrichmentClient
from stairwelllib.swlogging import setup_logging
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option

BASE_URL = "https://app.stairwell.com/"

SECRET_REALM = "stairwell_realm"
SECRET_NAME = "admin"


def get_encrypted_token(search_command):
    """Retrieves an app configuration token, comprising password, organizationId, userId"""
    secrets = search_command.service.storage_passwords
    return next(
        secret
        for secret in secrets
        if (secret.realm == SECRET_REALM and secret.username == SECRET_NAME)
    ).clear_password


@Configuration()
class Stairwell(StreamingCommand):
    """Class providing a streaming search command for Stairwell"""

    ip = Option(require=False)
    object = Option(require=False)
    hostname = Option(require=False)

    client: Optional[StairwellAPI] = (
        None  # If None, will be intialized when the command is run
    )
    custom_logger: Logger

    def init_client(self) -> StairwellAPI:
        """Initializes the Stairwell enrichment API client using values from the secrets store."""
        self.prepare()  # required to initialize `SearchCommand.service`.
        secrets = get_encrypted_token(self)
        secrets_json = json.loads(secrets)
        auth_token = secrets_json["password"]
        organization_id = secrets_json["organizationId"]
        user_id = secrets_json["userId"]

        client = StairwellEnrichmentClient(
            BASE_URL, auth_token, organization_id, user_id, self.custom_logger
        )
        return client

    def __init__(
        self,
        client: Optional[StairwellAPI] = None,
        custom_logger: Optional[Logger] = None,
    ):
        super().__init__()
        if custom_logger == None:
            custom_logger = setup_logging()
        self.custom_logger = custom_logger
        self.client = client

    def stream(self, records):
        logger = self.custom_logger
        logger.info("Stairwell - stream - entered")

        # Unless we're injecting a double, we want to initialize the client here as doing so earlier
        # does not give us access to credentials stored via Splunk's secret storage.
        if self.client == None:
            logger.info("Initializing Stairwell API client...")
            self.client = self.init_client()

        arg_counter = 0
        if self.ip and len(self.ip) != 0:
            arg_counter += 1
            ip_field = self.ip
        if self.object and len(self.object) != 0:
            arg_counter += 1
            object_field = self.object
        if self.hostname and len(self.hostname) != 0:
            arg_counter += 1
            hostname_field = self.hostname
        if arg_counter == 0:
            logger.error("No input field specified")
            raise ValueError("No input field specified")
        elif arg_counter > 1:
            logger.error("Multiple inputs received")
            raise ValueError("Multiple inputs received")

        for record in records:
            logger.debug("record before = %s", record)
            if "ip_field" in locals() and ip_field in record and record[ip_field] != "":
                # Send request to Stairwell API
                response_dictionary = search_stairwell_ip_addresses_api(
                    self.client, logger, record[ip_field]
                )
                for key, value in response_dictionary.items():
                    record[key] = value

            elif (
                "object_field" in locals()
                and object_field in record
                and record[object_field] != ""
            ):
                # Send request to Stairwell API
                response_dictionary = search_stairwell_object_api(
                    self.client, logger, record[object_field]
                )
                for key, value in response_dictionary.items():
                    record[key] = value

            elif (
                "hostname_field" in locals()
                and hostname_field in record
                and record[hostname_field] != ""
            ):
                # Send request to Stairwell API
                response_dictionary = search_stairwell_hostname_api(
                    self.client, logger, record[hostname_field]
                )
                for key, value in response_dictionary.items():
                    record[key] = value

            logger.debug("record after = %s", record)

            try:
                yield record
            except StopIteration:
                logger.error("Stairwell - stream - received StopIteration")
                return

        logger.info("Stairwell - stream - exit")


dispatch(Stairwell, sys.argv, sys.stdin, sys.stdout, __name__)
