import input_module_cofense_triage  # noqa: F401
import requests
import json
import os
from datetime import datetime
import traceback

from log_manager import setup_logging
from CofenseConnect import constants
import cofense_triage_common_utils as utils
from cofense_triage_custom_exceptions import InputValidationError

from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunk_aoblib.rest_migration import ConfigMigrationHandler


_LOGGER = setup_logging("ta_cofense_triage_setup")
APP_NAME = __file__.split(os.sep)[-3]


class ValidateInput(Validator):
    """Validator class to empty fields corresponding to dropdown value."""

    def validate(self, value, data):
        """Validate method to perform action."""
        if data['endpoint'] == "status" or data['endpoint'] == "executive_summary":
            data['start_time'] = ''
            data['end_time'] = ''
            data['re_ingest'] = '0'
        else:
            start = data.get('start_time')
            end = data.get('end_time')

            # Current time in UTC timezone
            current_time = datetime.utcnow()

            # Initializing these variables to None. Update only if values are provided.
            start_time = end_time = None

            try:
                # Check if end time is provided without start time
                if end and not start:
                    raise InputValidationError("Start Time is required if End Time is provided.")

                # Check if entered start time and end time is in future:
                # If true, raise exception
                if start:
                    start_time = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
                    if start_time > current_time:
                        raise InputValidationError("Start Time should not be a future time.")

                if end:
                    end_time = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
                    if end_time > current_time:
                        raise InputValidationError("End Time should not be a future time.")

                # Check if start time is greater than end time:
                # If true, raise the exception
                if start_time and end_time and start_time > end_time:
                    raise InputValidationError("Start Time should not be greater than End Time.")
            except InputValidationError as e:
                _LOGGER.error(e)
                self.put_msg(e)
                return False
            except ValueError:  # To handle scenario where invalid date is provided.
                msg = "Invalid date. Please enter valid date in YYYY-MM-DD HH:MM:SS format."
                _LOGGER.error(msg)
                self.put_msg(msg)
                return False
            except Exception as e:
                msg = "Unknown error occurred while validating inputs: {}".format(e)
                _LOGGER.error(msg)
                self.put_msg(msg)
                return False
        return True


class SessionKeyProvider(ConfigMigrationHandler):
    """Provides Splunk session key to custom validator."""

    def __init__(self):
        """Save session key in class instance."""
        self.session_key = self.getSessionKey()


class ValidateCofenseInstance(Validator):
    """Validator for Cofense Triage instance and token."""

    def validate(self, value, data):
        """
        Check if the given value is valid.

        :param value: value to validate.
        :param data: whole payload in request.
        :return True or False
        """
        _LOGGER.info("Initiating configuration validation.")

        # Get Splunk Session Key
        splunk_session_key = SessionKeyProvider().session_key

        # Get proxy settings information
        try:
            proxy_settings = utils.get_proxy_uri(splunk_session_key)
        except Exception as e:
            msg = "Unknown error occurred while reading proxy details: {}".format(e)
            _LOGGER.error(msg)
            self.put_msg(msg)
            return False

        # Set parameters
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
        host_url = data.get("host_url").strip("/")

        req_url = "{}{}".format("https://", host_url)

        payload = json.dumps({
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        })
        headers = {
            'Content-Type': 'application/json'
        }
        # Create Connection
        try:
            resp = requests.post(req_url + "/oauth/token",
                                 headers=headers,
                                 data=payload,
                                 proxies=proxy_settings,
                                 verify=constants.SSL_VERIFY)
            resp.raise_for_status()
            access_token = resp.json().get('access_token')

            # Revoke access token
            payload = json.dumps({
                "client_id": client_id,
                "client_secret": client_secret,
                "token": access_token
            })
            resp = requests.post(req_url + "/oauth/revoke",
                                 headers=headers,
                                 data=payload,
                                 proxies=proxy_settings,
                                 verify=constants.SSL_VERIFY)
            _LOGGER.info("Configurations validated successfully.")

            return True
        except Exception:
            if "resp" in locals() and resp.status_code == 401:
                msg = "Invalid Client ID or Client Secret. Please enter the valid credentials."
            elif "resp" in locals() and resp.status_code == 404:
                msg = "Please validate the provided details."
            elif "resp" in locals() and resp.status_code == 429:
                msg = "API limit has exceeded. Please retry after some time."
            elif "resp" in locals() and resp.status_code == 500:
                msg = "Internal server error. Cannot verify Cofense Triage instance."
            else:
                msg = "Unable to request Cofense instance. "\
                      "Please validate the provided credentials and "\
                      "Proxy configurations or check the network connectivity."

            _LOGGER.error(traceback.format_exc())
            _LOGGER.error(msg)
            self.put_msg(msg)
            return False
