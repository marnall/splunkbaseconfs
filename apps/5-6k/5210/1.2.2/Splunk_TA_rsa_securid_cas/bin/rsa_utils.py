##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test
import time
import os.path as op
import sys
import json
import traceback
import datetime
import re
import requests as rq
from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib.modular_input import checkpointer
import jwt
from jwt.algorithms import RSAAlgorithm


APP_NAME = __file__.split(op.sep)[-3]
ADMINLOG_SOURCETYPE = "rsa:securid:cas:adminlog:json"
USERLOG_SOURCETYPE = "rsa:securid:cas:usereventlog:json"
RISKUSER_SOURCETYPE = "rsa:securid:cas:riskuser:json"


def validate_start_date(start_date):
    """
    Validates the start_date.
    :param start_date: Query start date.
    """
    current_time = int(time.mktime(datetime.datetime.utcnow().timetuple()))
    if start_date:
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}z$", start_date):
            msg = "Start Time for Query of the input should be in YYYY-MM-DDThh:mm:ss.mmmz format"
            raise Exception(msg)
        try:
            start_date = int(
                time.mktime(time.strptime(start_date, "%Y-%m-%dT%H:%M:%S.000z"))
            )
        except Exception:
            msg = "Invalid Start Date."
            raise Exception(msg)
        if start_date > current_time:
            msg = "Start Time for Query should not be in future."
            raise Exception(msg)

        if start_date < 0:
            msg = "Start Time for Query should be greater than 01-Jan-1970 UTC."
            raise Exception(msg)

        if current_time - start_date > 2592000:
            msg = "Start Time for Query should not be older than 30 days."
            raise Exception(msg)


def call_api(url, jwt_token, proxy_settings, logger):
    """
    Calls api, if api call getting failed then it will retry three times.
    :param url:url of query which is generated based on start date.
    :param jwt_token: token used for authentication api call.
    :param proxy_settings: proxy settings configured in addon.
    :param logger: provides logger of current input.
    :return : status code and content of api call.
    """
    RETRY_COUNT = 3
    sleep_time = 1
    headers = {"Authorization": "Bearer {}".format(jwt_token)}
    while RETRY_COUNT > 0:
        try:
            response = rq.request("GET", url, proxies=proxy_settings, headers=headers)

            if response.status_code in (200, 403):
                return response.status_code, response.content

            logger.error(
                "Received response {} from api call".format(response.status_code)
            )

        except Exception as e:
            logger.error(
                "Error occured while getting response in API call. Error={}".format(e)
            )

        if RETRY_COUNT == 1:
            logger.error(
                "API call was not successfull after 3 retries. Existing the further data collection execution."
            )
            sys.exit(1)
        logger.error(
            "Error occured while getting response in API call. Retrying the API call in {} seconds".format(
                sleep_time
            )
        )
        time.sleep(sleep_time)
        RETRY_COUNT = RETRY_COUNT - 1
        sleep_time = sleep_time * 2


def generate_jwt_token(api_access_key, access_id_of_api, adminRestApiUrl, logger):
    """
    This function generates jwt token.
    :param api_access_key: access key for encoding token.
    :param access_id_of_api: access id for encoding token.
    :param adminRestApiUrl: url of admin rest api.
    :param logger: provides logger of current input.
    :return : generated jwt token.
    """
    try:
        jwt.unregister_algorithm("RS256")
    except Exception:
        pass

    try:
        jwt.register_algorithm("RS256", RSAAlgorithm(RSAAlgorithm.SHA256))
    except Exception as exception:
        logger.error(
            "Error encountered while registering the JWT RS256 algorithm. Error: {}".format(
                exception
            )
        )
        sys.exit(1)

    private_key = (api_access_key).encode("utf-8").decode("unicode_escape")
    claim_set = {
        "sub": access_id_of_api,
        "iat": int(time.time()),
        "exp": int(time.time() + 3600),
        "aud": adminRestApiUrl,
    }
    try:
        return jwt.encode(
            claim_set,
            private_key,
            algorithm="RS256",
            headers={"typ": "JWT", "alg": "RS256"},
        )
    except Exception:
        logger.error(
            "Error occured while generating JWT token: {}".format(
                traceback.format_exc()
            )
        )
        sys.exit(1)


def get_account_details(session_key, account_name, logger):
    """
    This function retrieves account details from addon configuration file.
    :param session_key: session key for particular modular input.
    :param account_name: account name configured in the addon.
    :param logger: provides logger of current input.
    :return : account details in form of a dictionary.
    """
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_rsa_securid_cas_account".format(
                APP_NAME
            ),
        )
        account_conf_file = cfm.get_conf("splunk_ta_rsa_securid_cas_account")
    except Exception:
        logger.error(
            "Failed to fetch account details from configuration. {}".format(
                traceback.format_exc()
            )
        )
        sys.exit(1)

    logger.info("Fetched configured account details.")
    return {
        "access_id_of_api": account_conf_file.get(account_name).get("access_id_of_api"),
        "adminRestApiUrl": account_conf_file.get(account_name).get("adminRestApiUrl"),
        "api_access_key": account_conf_file.get(account_name).get("api_access_key"),
    }


def get_proxy_settings(session_key, logger):
    """
    This function fetches proxy settings
    :param session_key: session key for particular modular input.
    :param logger: provides logger of current input.
    :return : proxy settings
    """

    try:
        settings_cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_rsa_securid_cas_settings".format(
                APP_NAME
            ),
        )
        splunk_ta_rsa_securid_cas_settings_conf = settings_cfm.get_conf(
            "splunk_ta_rsa_securid_cas_settings"
        ).get_all()
    except Exception:
        logger.error(
            "Failed to fetch proxy details from configuration. {}".format(
                traceback.format_exc()
            )
        )
        sys.exit(1)

    proxy_settings = None
    proxy_stanza = {}
    for key, value in splunk_ta_rsa_securid_cas_settings_conf["proxy"].items():
        proxy_stanza[key] = value

    if int(proxy_stanza.get("proxy_enabled", 0)) == 0:
        return proxy_settings
    proxy_port = proxy_stanza.get("proxy_port")
    proxy_url = proxy_stanza.get("proxy_url")
    proxy_type = proxy_stanza.get("proxy_type")
    proxy_username = proxy_stanza.get("proxy_username", "")
    proxy_password = proxy_stanza.get("proxy_password", "")

    if proxy_username and proxy_password:
        proxy_username = rq.compat.quote_plus(proxy_username)
        proxy_password = rq.compat.quote_plus(proxy_password)
        proxy_uri = "%s://%s:%s@%s:%s" % (
            proxy_type,
            proxy_username,
            proxy_password,
            proxy_url,
            proxy_port,
        )
    else:
        proxy_uri = "%s://%s:%s" % (proxy_type, proxy_url, proxy_port)

    proxy_settings = {"http": proxy_uri, "https": proxy_uri}
    logger.info("Fetched configured proxy details.")
    return proxy_settings


def get_log_level(session_key, logger):
    """
    This function returns the log level for the addon from configuration file.
    :param session_key: session key for particular modular input.
    :return : log level configured in addon.
    """
    try:
        settings_cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_rsa_securid_cas_settings".format(
                APP_NAME
            ),
        )

        logging_details = settings_cfm.get_conf(
            "splunk_ta_rsa_securid_cas_settings"
        ).get("logging")

        log_level = (
            logging_details.get("loglevel")
            if (logging_details.get("loglevel"))
            else "INFO"
        )
        return log_level

    except Exception:
        logger.error(
            "Failed to fetch the log details from the configuration taking INFO as default level."
        )
        return "INFO"


def write_riskuser_events(apidata, ew, index, source, logger):
    """
    This function write events to the Splunk.
    :param apidata:represent data of riskuser api.
    :param ew: represents event writer object.
    :param index: index on which data will be writen.
    :param source: source on which data will be writen.
    :param logger: provides logger of current input.
    """
    logger.info("Indexing the latest High Risk Users list")

    try:
        event = smi.Event(
            data=json.dumps(apidata),
            sourcetype=RISKUSER_SOURCETYPE,
            index=index,
            source=source,
        )
        ew.write_event(event)
    except Exception:
        logger.error(
            "Error writing high risk user event to Splunk: {}".format(
                traceback.format_exc()
            )
        )
        sys.exit(1)
    else:
        logger.info("Successfully indexed the latest High Risk Users list")


def write_event(
    apidata, ew, endpoint, index, source, logger, ck, checkpoint_name, checkpoint_marker
):
    """
    This function write events to the Splunk.
    :param apidata:represent data of api.
    :param ew: represents event writer object.
    :param endpoint: endpoint configured in add on.
    :param index: index on which data will be writen.
    :param source: source on which data will be writen.
    :param logger: provides logger of current input.
    :param ck : checkpoint object.
    :param checkpoint_name : name of the checkpoint
    :param checkpoint_marker : value of last saved checkpoint
    """

    if endpoint == "adminlog":
        results = apidata["elements"]
    else:
        results = apidata["userEventLogExportEntries"]
    total_events = apidata["totalElements"]
    if int(total_events) == 0:
        logger.info("No new records found.")
        sys.exit(1)
    sourcetype = ADMINLOG_SOURCETYPE if (endpoint == "adminlog") else USERLOG_SOURCETYPE
    event_count = 0
    try:
        for json_event in results:
            event = smi.Event(
                data=json.dumps(json_event),
                sourcetype=sourcetype,
                index=index,
                source=source,
            )
            ew.write_event(event)
            event_count += 1
            checkpoint_marker = json_event.get("eventLogDate")
        logger.info("Successfully ingested {} events".format(event_count))
    except Exception:
        logger.error(
            "Error writing event to Splunk: {}.".format(traceback.format_exc())
        )
        logger.info("Ingested {} events before exception".format(event_count))
        logger.info(
            "Updating the checkpoint to the last ingested event's time - {}".format(
                checkpoint_marker
            )
        )
        ck.update(checkpoint_name, checkpoint_marker)
        sys.exit(1)
    else:
        logger.info(
            "Updating the checkpoint to the last ingested event's time - {}".format(
                checkpoint_marker
            )
        )
        ck.update(checkpoint_name, checkpoint_marker)


def checkpoint_handler(checkpoint_name, start_date, session_key, input_name, logger):
    """
    This function handles checkpoint.
    :param checkpoint_name: represents checkpoint file name.
    :param start_date: represents start date configured on addon.
    :param session_key: session key for particular modular input.
    :param input_name: name of the input.
    :param logger: provides logger of current input.
    :return : checkpoint object and start date of the query.
    """

    try:
        ck = checkpointer.KVStoreCheckpointer(checkpoint_name, session_key, APP_NAME)
        checkpoint_marker = ck.get(checkpoint_name)
    except Exception:
        logger.error(
            "Error occurred while fetching checkpoint : {}".format(
                traceback.format_exc()
            )
        )
        sys.exit(1)

    if checkpoint_marker:
        logger.info(
            "Checkpoint found, hence setting start_date to {}".format(checkpoint_marker)
        )
        query_start_date = checkpoint_marker
    else:
        try:
            validate_start_date(start_date)
        except Exception as e:
            logger.error(
                "Query start date could not be validated. Error : {} Update Query start date to resume data collection.".format(
                    e
                )
            )
            sys.exit(1)

        if not start_date:
            start_date = (
                datetime.datetime.now() - datetime.timedelta(days=1)
            ).strftime("%Y-%m-%dT%H:%M:%S.000z")

            cfm = conf_manager.ConfManager(session_key, APP_NAME)
            conf = cfm.get_conf("inputs")
            conf.update(input_name, {"startTimeAfter": start_date}, None)
            logger.info(
                "Start date not found hence setting it to 24 hours back. {}".format(
                    start_date
                )
            )
        query_start_date = start_date

    return ck, query_start_date
