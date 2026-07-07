import json
import os
import requests as rq
import datetime
import calendar

import logger_manager as log
from config import POLL_OFFSET_FOR_48_HOURS

import splunk.rest as rest
import splunk.admin as admin
from splunktaucclib.rest_handler.endpoint import validator


logger = log.setup_logging('ta_flashpoint_intelligence_account_validation')
URL = "https://api.flashpoint.io/finished-intelligence/v1/reports?limit=1"


class StartDateValidator(validator.Validator):
    """Validator class to validate values for Start Date field."""

    def validate(self, value, data):
        """Validate method to perform action."""
        start_date = data["start_date"]
        event_type = data["type"]
        interval = data["interval"]
        current_time = int(datetime.datetime.utcnow().timestamp())

        if event_type in ['compromised_credentials']:
            if int(interval) < 300:
                msg = "Interval should not be less than 5 mins."
                self.put_msg("Error: " + msg)
                return False
        elif event_type in ['indicators']:
            if int(interval) < 3600:
                msg = "Interval should not be less than 60 mins."
                self.put_msg("Error: " + msg)
                return False
        else:
            if int(interval) < 1800:
                msg = "Interval should not be less than 30 mins."
                self.put_msg("Error: " + msg)
                return False

        try:
            start_date = int(calendar.timegm(
                datetime.datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S").timetuple()))
        except Exception:
            msg = 'Invalid Start Date.'
            self.put_msg("Error: " + msg)
            return False

        # Check future date
        if start_date > current_time:
            msg = 'Start Date should not be a future time.'
            self.put_msg("Error: " + msg)
            return False

        # check too old date
        if start_date < 0:
            msg = 'Start Date should be greater than 01-Jan-1970 UTC.'
            self.put_msg("Error: " + msg)
            return False

        # For CVE start_date can not be within last 48 hours.'
        if event_type == "cve" and start_date > current_time - POLL_OFFSET_FOR_48_HOURS:
            msg = 'Start Date can not be within last 48 hours for CVE.'
            self.put_msg("Error: " + msg)
            return False

        return True


class GetSessionKey(admin.MConfigHandler):
    """This class is used to get Splunk session key."""

    def __init__(self):
        """Init method for class."""
        self.session_key = self.getSessionKey()


class APIKeyValidator(validator.Validator):
    """This class extends base class of Validator."""

    __URL_FORMAT = "__REST_CREDENTIAL__#TA-flashpoint-intelligence#configs/conf-ta_flashpoint_intelligence_settings:proxy``splunk_cred_sep``1:"  # noqa:E501
    __URL_ENCODE = rq.compat.quote_plus(__URL_FORMAT)

    def validate(self, value, data):
        """We define API validation here for verifying credentials when storing account information."""
        self.my_app = __file__.split(os.sep)[-3]
        api_key = data.get('api_key')

        try:
            proxy_settings = self.get_proxy()
        except Exception as exception:
            logger.exception("Error while fetching proxy information.\n Error: {}".format(exception))
            self.put_msg("Error while fetching proxy information.")
            return False

        try:
            headers = {'Authorization': '{} {}'.format('Bearer', api_key)}
            response = rq.request("GET", URL, headers=headers, proxies=proxy_settings, verify=True)
            status_code = response.status_code

            if status_code == 200:
                logger.info("Account created successfully.")
                return True
            elif status_code in range(500, 512):
                self.put_msg("Server Error! Try again in a while.")
                logger.error("Server Error! Try again in a while. \n Error: {}".format(response.content))
            else:
                self.put_msg("Invalid API Key!")
                logger.error("Invalid API Key!")

        except rq.exceptions.ProxyError as proxy_error:
            self.put_msg("Proxy error! Check your proxy configuration")
            logger.exception("Proxy Error: {}".format(proxy_error))
        except rq.ConnectionError as connection_error:
            self.put_msg("Connection error! Check your internet connection")
            logger.exception("Connection Error: {}".format(connection_error))
        except rq.TooManyRedirects as too_many_redirects_error:
            self.put_msg("Too many redirects!")
            logger.exception("Too many redirect Error {}".format(too_many_redirects_error))
        except Exception as general_exception:
            self.put_msg("Error while connecting to the Flashpoint server")
            logger.exception("Error occurred\n Error: {}".format(general_exception))

    def get_proxy(self):
        """Gives information of proxy if proxy is enable.

        :return: dictionary having proxy information
        """
        session_key = GetSessionKey().session_key
        proxy_settings = None

        _, response_content = rest.simpleRequest(
            "/servicesNS/nobody/TA-flashpoint-intelligence/configs/conf-ta_flashpoint_intelligence_settings/proxy",
            sessionKey=session_key, getargs={"output_mode": "json"}, raiseAllErrors=True)
        proxy_info = json.loads(response_content)['entry'][0]['content']
        if int(proxy_info.get("proxy_enabled", 0)) == 0:
            return proxy_settings

        proxy_port = proxy_info.get('proxy_port')
        proxy_url = proxy_info.get('proxy_url')
        proxy_type = proxy_info.get('proxy_type')
        proxy_username = proxy_info.get('proxy_username', '')
        proxy_password = ''

        if proxy_username:
            try:
                _, response_content = rest.simpleRequest(
                    "/servicesNS/nobody/TA-flashpoint-intelligence/storage/passwords/" + APIKeyValidator.__URL_ENCODE,
                    sessionKey=session_key, getargs={"output_mode": "json"}, raiseAllErrors=True)
                response_dict = json.loads(response_content)['entry'][0]['content']
                cred = json.loads(response_dict.get('clear_password', '{}'))
                proxy_password = cred.get("proxy_password", None)
            except Exception as e:
                self.put_msg("Error While Fetching Proxy")
                logger.exception("Error While fetching proxy \n Error: {}".format(str(e)))
        proxy_settings = APIKeyValidator.get_proxy_setting(
            proxy_type, proxy_username, proxy_password, proxy_url, proxy_port
        )
        return proxy_settings

    @staticmethod
    def get_proxy_setting(proxy_type, proxy_username, proxy_password, proxy_url, proxy_port):
        """Function To get Proxy Setting."""
        if proxy_username and proxy_password:
            proxy_username = rq.compat.quote_plus(proxy_username)
            proxy_password = rq.compat.quote_plus(proxy_password)
            proxy_uri = "%s://%s:%s@%s:%s" % (proxy_type, proxy_username, proxy_password, proxy_url, proxy_port)
        else:
            proxy_uri = "%s://%s:%s" % (proxy_type, proxy_url, proxy_port)
        proxy_settings = {
            "http": proxy_uri,
            "https": proxy_uri
        }

        return proxy_settings
