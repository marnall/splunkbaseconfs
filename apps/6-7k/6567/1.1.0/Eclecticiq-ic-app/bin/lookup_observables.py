"""Lookup Observables Workflow Action."""
# Add the lib and current directory to the python path
import os
import re
import sys


(path, _) = os.path.split(os.path.realpath(__file__))
sys.path.insert(0, path)

import splunklib.client as client
from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.clilib import cli_common as cli
import requests
import traceback
from constants.defaults import (  # pylint: disable=C0413
    ACCOUNTS_CONF,
    DEFAULT_TIMEOUT,
    LOCAL_DIR,
    SETTINGS_CONF,
)  # pylint: disable=C0413
from constants.general import CREDS, PROXY, PROXY_PASSWORD, URL  # pylint: disable=C0413
from constants.messages import (
    API_ERROR,  # pylint: disable=C0413,W0611
    CREDS_NOT_FOUND,
    EVENTS_RESPONSE_ERROR_CODE,
    JSON_EXCEPTION,
)
from utils.formatters import format_proxy_uri  # pylint: disable=C0413
from utils.logger_manager import setup_logging  # pylint: disable=C0413
import json
import logging
import logging.handlers



logger = setup_logging("eclecticiq_ic_app_lookup_observables", log_level=logging.DEBUG)

INPUT_NAME = "lookup_observables"

if sys.platform == "win32":
    import msvcrt

    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)  # pylint: disable=E1101
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)  # pylint: disable=E1101
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)  # pylint: disable=E1101


class Send(PersistentServerConnectionApplication):  # type: ignore
    """Looksup the observables from EclecticIQ Platform."""

    def __init__(self, command_line, command_arg):  # pylint: disable=W0613
        PersistentServerConnectionApplication.__init__(self)

    @staticmethod
    def parse_form_data(form_data):
        """Parse the payload.

        :param form_data: payload of the request
        :type form_data: dict
        """
        parsed = {}
        # form_data = form_data.split("&")
        for [key, value] in form_data:
            parsed[key] = value
        return parsed

    @staticmethod
    def create_send_resp(response, status_code):
        """Create response to send back to JS.

        :param status: status code
        :type status: int
        :param message: message to send
        :type message: str
        :return: response dict
        :rtype: dict
        """
        return {
            "payload": response,
            "status": status_code,
            "headers": {"Content-Type": "application/json"},
        }

    @staticmethod
    def get_response_content(response):
        """Get the response content from the response.

        :param response: Response to retrieve content
        :type response: Response
        :return: Response content
        :rtype: dict / None
        """
        content = {}
        logger.info("getting response content")
        try:
            content = json.loads(response.content)
        except json.decoder.JSONDecodeError as error:
            logger.info("Error while getting response content")
            logger.error(JSON_EXCEPTION.format(error))

        return content

    @staticmethod
    def prepare_observable_data(data):
        """Prepare Observable data to show on UI.

        :param data: Observable data
        :type data: dict
        :return: Only selected fields dict
        :rtype: dict
        """
        new_data = {}
        new_data["type"] = data.get("type")
        new_data["value"] = data.get("value")
        new_data["classification"] = data.get("meta").get("maliciousness")
        return new_data

    @staticmethod
    def prepare_entity_data(data, obs_data):
        """Prepare entity data to show on UI.

        :param data: Entity data
        :type data: dict
        :param data: Observable data
        :type data: list
        :return: Only selected fields dict
        :rtype: dict
        """
        new_data = {}
        if data.get("data"):
            new_data["title"] = (
                data.get("data").get("title") if data.get("data").get("title") else ""
            )

            new_data["description"] = (
                data.get("data").get("description")
                if data.get("data").get("description")
                else ""
            )
            new_data["confidence"] = (
                data.get("data").get("confidence")
                if data.get("data").get("confidence")
                else ""
            )
            
        if data.get("meta"):
            new_data["threat_start_time"] = (
                data.get("meta").get("estimated_threat_start_time")
                if data.get("meta").get("estimated_threat_start_time")
                else ""
            )
            if data.get("data").get("producer"):
                new_data["source_name"] = (
                    data.get("data").get("producer").get("identity")
                    if data.get("data").get("producer").get("identity")
                    else ""
                )
            else:
                new_data["source_name"] = ""
            new_data["tags"] = (
                ",".join(data.get("meta").get("tags")) if data.get("meta").get("tags") else ""
            )
            new_data["observables"] = obs_data

        return new_data

    @staticmethod
    def fetch_entity_details(entity_id, url, api_key, verify_ssl, proxy):
        """Get entity details by id.

        :param entity_id: Entity ID
        :type: str
        :return: response content
        :rtype: dict
        """
        logger.info("In get fetch entity details..")
        logger.info(entity_id)
        endpoint = url + "/entities" + "/" + entity_id

        headers = {"Authorization": f"Bearer {api_key}"}

        logger.info(endpoint)
        try:
            response = Send.send_request(
                endpoint, {}, verify_ssl, headers=headers, proxy=proxy
            )
        except Exception as err:
            logger.error(err)
            return {}

        content = json.loads(response.content)
        data = content.get("data")
        return data

    @staticmethod
    def get_observable_by_id(obs_id, url, api_key, verify_ssl, proxy):
        """Get observables by id.

        :param obs_id: Observable ID
        :type: str
        :return: response content
        :rtype: dict
        """
        logger.info("In get observable by id .")
        endpoint = url + "/observables" + "/" + obs_id

        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            response = Send.send_request(
                endpoint, {}, verify_ssl, headers=headers, proxy=proxy
            )
        except Exception as err:
            logger.error(err)
            return {}

        content = json.loads(response.content)
        data = content.get("data")
        return data

    @staticmethod
    def get_entity_data(data_item, url, api_key, verify_ssl, proxy):
        """Get entity data to show on UI.

        :param data_item: Data from lookup obsrvables Dict
        :type data_item: dict
        :param eiq_api: EIQ API object
        :type eiq_api: object
        :return: prepared data to show on UI
        :rtype: dict
        """
        logger.info("Inside Get entity data.")
        entity_data_dict = []
        for item in data_item.get("entities"):
            entity_data = Send.fetch_entity_details(
                str(item.split("/")[-1]), url, api_key, verify_ssl, proxy
            )
            observables = (
                entity_data.get("observables") if entity_data.get("observables") else []
            )
            logger.info(observables)

            obs_data_list = []
            for observable in observables:
                obs_data = Send.get_observable_by_id(
                    str(observable.split("/")[-1]), url, api_key, verify_ssl, proxy
                )

                append_data = Send.prepare_observable_data(obs_data)

                obs_data_list.append(append_data)

            entity_data_dict.append(
                Send.prepare_entity_data(entity_data, obs_data_list)
            )

        logger.info("Entity_data_dict ={}".format(entity_data_dict))
        return entity_data_dict

    @staticmethod
    def send_request(url, params, verify_ssl, headers, proxy):
        """Send an API request to the URL provided with headers and parameters.

        :param logger: Splunk logger to send request
        :type logger: BaseModInput
        :param url: API URL to send request
        :type url: str
        :param params: Parameters to be sent to API
        :type params: dict
        :param headers: Headers to be included in the request
        :type headers: dict
        :param proxy: proxy details to be included in the request
        :type proxy: dict
        :return: API response
        :rtype: dict
        """
        if proxy.get("proxy_enabled") == "1":
            proxy_settings = format_proxy_uri(proxy)
        else:
            proxy_settings = None
        try:
            response = requests.request(
                "GET",
                url,
                headers=headers,
                params=params,
                verify=verify_ssl,
                timeout=DEFAULT_TIMEOUT,
                proxies=proxy_settings,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if str(response.status_code).startswith("5"):
                logger.critical(API_ERROR.format(input=INPUT_NAME, err=err))
                logger.critical(
                    EVENTS_RESPONSE_ERROR_CODE.format(
                        input=INPUT_NAME,
                        code=response.status_code,
                        error=str(response.content),
                    )
                )
            else:
                logger.error(API_ERROR.format(input=INPUT_NAME, err=err))
                logger.error(
                    EVENTS_RESPONSE_ERROR_CODE.format(
                        input=INPUT_NAME,
                        code=response.status_code,
                        error=str(response.content),
                    )
                )
            raise err
        except requests.exceptions.ConnectionError as err:
            logger.error(API_ERROR.format(input=INPUT_NAME, err=err))
            raise err
        except requests.exceptions.Timeout as err:
            logger.error(API_ERROR.format(input=INPUT_NAME, err=err))
            raise err
        except requests.exceptions.RequestException as err:
            logger.error(API_ERROR.format(input=INPUT_NAME, err=err))
            logger.error(
                EVENTS_RESPONSE_ERROR_CODE.format(
                    input=INPUT_NAME,
                    code=response.status_code,
                    error=str(response.content),
                )
            )
            raise err
        except Exception as err:
            logger.error(traceback.format_exc())
            raise err
        return response

    @staticmethod
    def get_type(value):
        """Get the type of the observable.

        :param value: observable value
        :type value: str
        :return: type of the observable
        :rtype: str
        """
        if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", value):
            obs_type = "ipv4"
        elif re.match(
            r"^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$",  # pylint: disable=C0301
            value,
        ):
            obs_type = "ipv6"
        elif re.match(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]+", value):
            obs_type = "email"
        elif re.match(r"[^\:]+\:\/\/[\S]+", value):
            obs_type = "uri"
        elif re.match(r"[\S]+\.[\S]+", value):
            obs_type = "domain"
        elif re.match(r"^[a-f0-9A-F]{32}$", value):
            obs_type = "hash-md5"
        elif re.match(r"^[a-f0-9A-F]{64}$", value):
            obs_type = "hash-sha256"
        elif re.match(r"\b[0-9a-f]{5,40}\b", value):
            obs_type = "hash-sha1"
        elif re.match(r"^\w{128}$", value):
            obs_type = "hash-sha512"
        else:
            obs_type = ""
        return obs_type

    def handle(self, in_string):
        """Handle request made to the endpoint services/lookup_observables.

        :param self: Object of the class
        :type in_string: Send
        :param in_string: Payload of the request in string
        :type in_string: str
        :return: Response to be send
        :rtype: dict
        """
        logger.info("Request received.")
        in_dict = json.loads(in_string)
        session_key = in_dict.get("session")
        session_key = session_key.get("authtoken")
        payload = Send.parse_form_data(in_dict["form"])

        service = client.connect(token=session_key, owner="nobody", app="TA-eclecticiq")
        confs = service.confs
        url = ""
        account_name = ""
        proxy = {}
        certificate_validation = ""
        for conf in confs:
            if conf.name == "ta_eclecticiq_account":
                stanzas = conf.list()
                for stanza in stanzas:
                    url = stanza.content.get("url")
                    account_name = stanza.name
                    certificate_validation = stanza.content.get(
                        "certificate_validation"
                    )
                    break
            elif conf.name == "ta_eclecticiq_settings":
                stanzas = conf.list()
                for stanza in stanzas:
                    if stanza.name == "proxy":
                        proxy = stanza.content
        sp_list = service.storage_passwords
        api_key = ""  # nosec
        proxy_pass = ""  # nosec
        for item in sp_list.list():
            conf_username = item.content.get("username")
            if account_name == conf_username.split("``")[
                0
            ] and "splunk_cred_sep" not in item.content.get("clear_password"):
                creds = json.loads(item.content.get("clear_password"))
                api_key = creds["api_key"]
            if "proxy" in item.content.get(
                "username"
            ) and "splunk_cred_sep" not in item.content.get("clear_password"):
                creds = json.loads(item.content.get("clear_password"))
                proxy_pass = creds["proxy_password"]

        # make sure we have a username and a password
        # before we try to authenticate
        if not url:
            logger.error("No url found in config.")
            return Send.create_send_resp(CREDS_NOT_FOUND, 401)

        if not api_key:
            logger.error("No api_key found for user {}.".format(account_name))
            return Send.create_send_resp(CREDS_NOT_FOUND, 401)

        # url = payload.get("acc_url")
        if certificate_validation == "1":  # pylint: disable=R1703
            verify_ssl = True
        else:
            verify_ssl = False
        logger.info(verify_ssl)
        logger.info("Found API key!")

        if proxy:
            proxy[PROXY_PASSWORD] = proxy_pass
        logger.info("prepared proxy !")
        headers = {"Authorization": f"Bearer {api_key}"}
        value = payload.get("value")
        params = {"filter[value]": value}
        obs_type = Send.get_type(value)
        if obs_type:
            params["filter[type]"] = obs_type
        try:
            logger.info("sending request to lookup observables!")
            response = Send.send_request(
                url + "/observables", params, verify_ssl, headers, proxy
            )
        except Exception as err:
            logger.error(err)
            return Send.create_send_resp(str(err), 500)

        logger.info("Request successful to lookup observables, got response!")
        content = Send.get_response_content(response)
        logger.info("content={}".format(content))
        final_data = []
        logger.info("getting data from response!")
        data = content.get("data")
        logger.info("data={}".format(data))
        for data_item in data:
            if data_item.get("entities"):
                logger.info("getting entitiy data!")
                entity_data = self.get_entity_data(
                    data_item, url, api_key, verify_ssl, proxy
                )
                final_data.append(entity_data)
        final_data.append(value)

        logger.info(final_data)

        return Send.create_send_resp(final_data, response.status_code)
