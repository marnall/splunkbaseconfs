#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import import_declare_test

import requests
import os
import sys
import json
from palo_utils import (
    get_access_token,
    logger_instance,
    get_proxy_settings,
    get_account_credentials,
    APP_NAME,
)
from splunklib import modularinput as smi
from solnlib import conf_manager, log


REGIONS = {
    "us": "https://api.aperture.paloaltonetworks.com",
    "apac": "https://api.aperture-apac.paloaltonetworks.com",
    "eu": "https://api.aperture-eu.paloaltonetworks.com",
    "uk": "https://api.aperture-uk.paloaltonetworks.com",
    "in1": "https://api.in1.prisma-saas.paloaltonetworks.com",
    "au1": "https://api.au1.prisma-saas.paloaltonetworks.com",
    "uk2": "https://api.uk2.prisma-saas.paloaltonetworks.com",
    "jp1": "https://api.jp1.prisma-saas.paloaltonetworks.com",
}

bin_dir = os.path.basename(__file__)


class DataSecurityScript(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self) -> smi.Scheme:
        scheme = smi.Scheme("data_security")
        scheme.description = "Data Security"
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
                "data_security_account",
                required_on_create=True,
            )
        )

        return scheme

    def validate_input(self, definition) -> None:
        return

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter) -> None:
        """
        Main entry point to start the data ingest for each modinput
        :param inputs: inputs configured via the UI in the inputs.conf
        :param event_writer: EventWriter object to ingest data to Splunk
        :return: None
        """
        for input_name, input_item in inputs.inputs.items():
            logger = logger_instance(input_name)
            try:
                session_key = self._input_definition.metadata["session_key"]
                log_level = conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=APP_NAME,
                    conf_name="splunk_ta_paloalto_networks_settings",
                )
                logger.setLevel(log_level)
                proxies = get_proxy_settings(logger, session_key)
                account_name = input_item.get("data_security_account")
                logger.info("Getting Data Security Account Credentials")
                data_security_creds = get_account_credentials(
                    session_key, account_name, "data_security_account", logger
                )
                data_security_client_id = data_security_creds.get("client_id")
                data_security_client_secret = data_security_creds.get("client_secret")
                api_region = REGIONS.get(data_security_creds.get("region"))
                token_url = f"{api_region}/oauth/token"
                logger.info("Getting api token to collect events")
                token = get_access_token(
                    logger,
                    data_security_client_id,
                    data_security_client_secret,
                    token_url,
                    proxies,
                )
                events_url = f"{api_region}/api/v1/log_events_bulk"
                headers = {"Authorization": "Bearer " + token}
                response = requests.get(
                    url=events_url,
                    headers=headers,
                    proxies=proxies,
                )
                status = response.status_code
                sourcetype = "pan:data:security"
                count = 0
                if status == 200:
                    events = response.json()["events"]
                    for event in events:
                        try:
                            event = smi.Event(
                                data=json.dumps(event, ensure_ascii=False, default=str),
                                sourcetype=sourcetype,
                            )
                            ew.write_event(event)
                            count += 1
                        except Exception as e:
                            log.log_exception(
                                logger,
                                e,
                                "Data Security Error",
                                msg_before=f"Exception during ingesting Data Security events. Error: {e}",
                            )
                elif status == 204:
                    logger.debug("Status 204: No events found")

                log.events_ingested(
                    logger,
                    input_name,
                    sourcetype,
                    count,
                    input_item["index"],
                )
            except Exception as e:
                log.log_exception(
                    logger,
                    e,
                    "Data Security Error",
                    msg_before=f"Exception during ingesting Data Security events. Error: {e}",
                )


if __name__ == "__main__":
    exit_code = DataSecurityScript().run(sys.argv)
    sys.exit(exit_code)
