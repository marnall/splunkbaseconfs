import os
import traceback
import json
import re
import const
import splunk.admin as admin
import splunk.entity as en
from splunktaucclib.rest_handler.endpoint.validator import Validator
import isilon_logger_manager as log
from isilon_utilities import get_proxy_data, retry_session

APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]
logger = log.setup_logging("ta_emc_isilon_account")


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


class IntervalValidator(Validator):
    """Class to validate the interval."""

    def validate(self, value, data):
        """Validates the interval value."""
        interval = data.get("interval")
        try:
            interval = int(interval)
            if interval < 60 or interval > 86400:
                raise Exception
            return True
        except Exception:
            logger.error("message=interval_error | Interval should not be less than 60 and greater than 86400.")
            self.put_msg("Interval should not be less than 60 and greater than 86400.")
            return False


class IndexValidator(Validator):
    """Class to Validate the index."""

    def validate(self, value, data):
        """Validates the index value."""
        logger.debug("message=index_validation | Validating the index whether it is present or not.")
        index = data.get("index")
        index = index.strip()
        if len(index) < 1 and len(index) > 80:
            self.put_msg("Length of index name should be between 1 and 80.")
            return False
        sessionKey = GetSessionKey().session_key
        indexes = en.getEntities(["data", "indexes"], count=-1, sessionKey=sessionKey)

        if index not in list(indexes.keys()):
            logger.error("message=index_error | Index '{}' does not exist.".format(index))
            self.put_msg("Index Error: Index {} does not exist".format(index))
            return False
        logger.debug("message=index_validation | Index validated successfully.")
        return True


class AccountValidator(Validator):
    """This class extends base class of Validator."""

    def check_authentication(self, host, username, password, verify, proxy):
        """Checks for the authentication of the server."""
        logger.debug("message=checking_authentication | Checking for server authentication.")
        try:
            self.url = (
                "https://" + host + ":" + const.ISILON_PORT + "/session/1/session"
            )
            headers = {"Content-Type": "application/json"}

            body = json.dumps(
                {
                    "username": username,
                    "password": password,
                    "services": ("platform", "namespace"),
                }
            )
            session = retry_session()
            r = session.post(
                verify=verify,
                url=self.url,
                headers=headers,
                data=body,
                proxies=proxy,
            )
            r.raise_for_status()
            logger.debug("message=authentication_successful | Successfully authenticated to the server.")
            return True

        except Exception as e:
            logger.error("message=error_while_authenticating | Error occured while authenticating "
                         "to server.\n{}".format(traceback.format_exc()))
            if 'r' in locals() and r.status_code == 401:
                raise Exception("Invalid username or password. Please enter the valid username and password.")
            elif "ProxyError" in str(e):
                raise Exception("Invalid Proxy values. Please validate the proxy values.")
            elif "Failed to establish a new connection" in str(e):
                raise Exception("Connection to {} is refused. Please check the IP Address.".format(host))
            elif "CERTIFICATE_VERIFY_FAILED" in str(e) or "invalid path" in str(e):
                raise Exception('SSL Certificate verification failed. '
                                'Please check the SSL Certificate or if it is not required, then save it to False'
                                ' in TA_EMC-Isilon/bin/const.py file.')
            raise Exception(
                "Error occurred while authenticating to server. Please validate the provided values and try again."
            )

    def validate(self, value, data):
        """We define Custom validation here for verifying credentials when storing account information."""
        username = data.get("username")
        password = data.get("password")
        host = data.get("ip_address")
        logger.info("message=validating_node_details | Validating provided details on cluster node page.")
        if bool(re.search(r"""^(?:https|http)://\S+""", host)):
            logger.error(
                "message=invalid_value_entered | IP Address must not contain protocol."
                " Please remove the http(s) scheme from IP Address."
            )
            self.put_msg(
                "IP Address must not contain protocol. Please remove the http(s) scheme from IP Address."
            )

        verify = const.VERIFY_SSL
        self.appName = APP_NAME
        sessionKey = GetSessionKey().session_key

        proxies = get_proxy_data(sessionKey, APP_NAME, logger)

        try:
            self.check_authentication(host, username, password, verify, proxies)
            logger.info("message=validation_successful | Cluster node details validation successful.")
            return True
        except Exception as e:
            logger.error("message=validation_error | Error occured while validating node details.\n{}"
                         .format(traceback.format_exc()))
            self.put_msg(e)
            return False
