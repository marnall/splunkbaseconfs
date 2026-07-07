##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test
import sys
import json
import requests as rq
import os.path as op
import traceback
from splunklib import modularinput as smi
from solnlib import log
from rsa_utils import (
    get_proxy_settings,
    generate_jwt_token,
    call_api,
    get_log_level,
    write_event,
    checkpoint_handler,
    get_account_details,
    write_riskuser_events,
)

APP_NAME = __file__.split(op.sep)[-3]

from splunk import rest


class CLOUD_ADMINISTRATION_API(smi.Script):
    def __init__(self):
        super(CLOUD_ADMINISTRATION_API, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("cloud_administration_api")
        scheme.description = "Cloud Administration API Input"
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
                "account_name",
                title="Global Account",
                description="Select the account for which you want to collect data.",
                required_on_create=True,
                required_on_edit=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "endpoint",
                title="Endpoint",
                description="The endpoint to use for data collection",
                required_on_create=True,
                required_on_edit=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "startTimeAfter",
                title="Query Start time",
                description='The datetime after which to query and index records, in this format: "YYYY-MM-DDThh:mm:ss.000z".Defaults to 30 days earlier from now.',
                required_on_edit=False,
                required_on_create=False,
            )
        )

        return scheme

    def validate_input(self, definition):
        """
        This method validates inputs.
        :param definition: provides input definition information.
        """
        pass

    def risk_user(
        self,
        logger,
        input_name,
        endpoint,
        api_access_key,
        access_id_of_api,
        adminRestApiUrl,
        proxy_settings,
        ew,
        index,
        source,
    ):
        """
        This method is invoked for each riskuser input repeatedly at configured interval.
        :param logger: provides logger information.
        :param input_name: provides name for the input.
        :param endpoint: provides endpoint information.
        :param api_access_key: provides api_access_key information.
        :param access_id_of_api: provides access_id_of_api information.
        :param adminRestApiUrl: provides adminRestApiUrl information.
        :param proxy_settings: provides proxy_settings information.
        :param ew: represents event writer object.
        :param index: index on which data will be writen.
        :param source: source on which data will be writen.
        """
        jwt_token = None
        logger.info("Starting REST API call loop for input - {}".format(input_name))
        url = adminRestApiUrl + endpoint
        logger.info("Final search string: " + url)

        jwt_token = generate_jwt_token(
            api_access_key, access_id_of_api, adminRestApiUrl, logger
        )

        status_code, data = call_api(url, jwt_token, proxy_settings, logger)

        try:
            if data and status_code == 200:
                api_data = json.loads(data)
                write_riskuser_events(api_data, ew, index, source, logger)
            else:
                logger.error(
                    "Error occured while getting response in API call for the high risk users. Response code={}".format(
                        status_code
                    )
                )
            logger.info("Finished REST API call loop for input - {}".format(input_name))
        except Exception as exception:
            logger.error(
                "Error while fetching the High Risk users. Error={}".format(exception)
            )

    def stream_events(self, inputs, ew):
        """
        This method is invoked for each input repeatedly at configured interval.
        :param inputs: provides inputs information.
        :param ew: event wirter object used for writing events.
        """
        meta_configs = self._input_definition.metadata
        session_key = meta_configs["session_key"]

        input_items = {}
        input_name = list(inputs.inputs.keys())[0]
        input_items = inputs.inputs[input_name]

        # Generate logger with input name
        _, input_name = input_name.split("//", 2)
        logger = log.Logs().get_logger(
            "splunk_ta_rsa_securid_cas_input_{}".format(input_name)
        )

        # Log level configuration
        log_level = get_log_level(session_key, logger)
        logger.setLevel(log_level)

        logger.debug("Modular input invoked.")

        account_name = input_items.get("account_name")
        account_details = get_account_details(session_key, account_name, logger)

        access_id_of_api = account_details.get("access_id_of_api")
        adminRestApiUrl = account_details.get("adminRestApiUrl")
        if "https://" not in adminRestApiUrl:
            logger.error(
                "Base URL of Admin REST API must start with https. Update Base URL of Admin REST API in account {} to resume data collection.".format(
                    account_name
                )
            )
            sys.exit(1)
        api_access_key = account_details.get("api_access_key")
        start_date = input_items.get("startTimeAfter")
        endpoint = input_items.get("endpoint")
        index = input_items.get("index")
        source = "{}:{}".format(list(inputs.inputs.keys())[0], account_name)
        interval = int(input_items.get("interval"))
        if endpoint != "/v2/users/highrisk" and (interval < 1 or interval > 86400):
            logger.error(
                "Interval must be a number between 1 to 86400. Update interval for input {} to resume data collection.".format(
                    input_name
                )
            )
            sys.exit(1)

        if endpoint == "/v2/users/highrisk" and interval < 1:
            logger.error(
                "Interval must be a positive number greater than 1. Update interval for input {} to resume data collection.".format(
                    input_name
                )
            )
            sys.exit(1)

        # Proxy configuration
        proxy_settings = get_proxy_settings(session_key, logger)

        # Whether to use (adminlog and usereventlog) api or (riskuser) api
        if endpoint == "/v2/users/highrisk":
            self.risk_user(
                logger,
                input_name,
                endpoint,
                api_access_key,
                access_id_of_api,
                adminRestApiUrl,
                proxy_settings,
                ew,
                index,
                source,
            )
            sys.exit(1)

        # Checkpoint handling
        checkpoint_name = input_name + "_last_event_time"
        ck, query_start_date = checkpoint_handler(
            checkpoint_name,
            start_date,
            session_key,
            list(inputs.inputs.keys())[0],
            logger,
        )

        # Setup variables for use in loop and tracking pages
        page = 0
        total_pages = 1
        jwt_token = None
        logger.debug("Starting REST API call loop for input - {}".format(input_name))

        while page < total_pages:

            query = "?startTimeAfter={}&pageNumber={}".format(query_start_date, page)
            url = adminRestApiUrl + "/v1/" + endpoint + "/exportlogs" + query
            logger.info("Final search string: " + url)

            if not jwt_token:
                jwt_token = generate_jwt_token(
                    api_access_key, access_id_of_api, adminRestApiUrl, logger
                )

            status_code, data = call_api(url, jwt_token, proxy_settings, logger)

            api_data = json.loads(data)
            if (
                status_code == "403"
                and api_data.get("message") == "Expired Access Token is not allowed"
            ):
                logger.info(
                    "The JWT token has expired hence regenerating the JWT token."
                )
                jwt_token = None
                continue

            if data and status_code == 200:
                write_event(
                    api_data,
                    ew,
                    endpoint,
                    index,
                    source,
                    logger,
                    ck,
                    checkpoint_name,
                    query_start_date,
                )
                page += 1
                total_pages = api_data["totalPages"]

            else:
                logger.error(
                    "Error occured while getting response in API call. Response code={} ({})".format(
                        status_code, data
                    )
                )
                break

        logger.debug("Finished REST API call loop for input - {}".format(input_name))


if __name__ == "__main__":
    exit_code = CLOUD_ADMINISTRATION_API().run(sys.argv)
    sys.exit(exit_code)
