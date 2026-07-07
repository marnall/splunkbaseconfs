import ta_cloudknox_declare  # noqa: F401

import cloudknox_consts
import os
import re
import six
import datetime
import cloudknox_common_utils as utils
from cloudknox_collect import CloudKnoxCollect

from cloudknox_consts import START_DATETIME_LAST_DAYS
from log_manager import setup_logging
from solnlib.utils import is_true
from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunk_aoblib.rest_migration import ConfigMigrationHandler

_LOGGER = setup_logging("cloudknox_validators")


class SessionKeyProvider(ConfigMigrationHandler):
    """Provides Splunk session key to custom validator."""

    def __init__(self):
        """Save session key in class instance."""
        self.session_key = self.getSessionKey()


class AuthSystemType(Validator):
    """Validator for auth system type input value."""

    def validate(self, value, data):
        """Input vaildation method for auth system type value."""
        auth_system_type = data.get("auth_system_type")
        if not auth_system_type:
            self.put_msg("Auth System Type is a required field")
            return False
        if auth_system_type not in cloudknox_consts.VALID_AUTH_SYSTEMS:
            self.put_msg(
                "Auth System Type values should be one of: {}".format(
                    ", ".join(cloudknox_consts.VALID_AUTH_SYSTEMS)
                )
            )
            _LOGGER.error(
                "Auth System Type values should be one of: {} but selected: {}".format(
                    ", ".join(cloudknox_consts.VALID_AUTH_SYSTEMS), auth_system_type
                )
            )
            return False
        _LOGGER.info("Auth system type validation successful.")
        return True


class CloudKnoxAuth(Validator):
    """Validator for CloudKnox account credentials."""

    def validate(self, value, data):
        """Credential validation method for CloudKnox account configuration."""
        ck_url = data.get("cloudknox_url").strip("/")
        ck_account_id = data.get("account_id")
        ck_access_key = data.get("access_key")
        ck_secret_key = data.get("secret_key")
        ck_verify_cert = is_true(data.get("verify_cert"))

        app_name = __file__.split(os.sep)[-3]
        splunk_session_key = SessionKeyProvider().session_key

        if not all([ck_url, ck_account_id, ck_access_key, ck_secret_key]):
            return False

        proxy_uri = utils.get_proxy_uri(app_name, splunk_session_key)

        try:
            response = CloudKnoxCollect.request_ck_access_token(
                ck_url, ck_account_id, ck_access_key, ck_secret_key, ck_verify_cert, proxy_uri,
            )
        except Exception as e:
            message = "Invalid CloudKnox/Proxy details. Please enter the correct configuration details."
            self.put_msg(message)
            _LOGGER.error("{} Error: {}".format(message, str(e)))
            return False
        else:
            if response.ok:
                pass
            elif response.status_code == 401:
                message = "Invalid credentials!"
                self.put_msg(message)
                _LOGGER.error(message)
                return False
            elif response.status_code == 407:
                message = "Proxy authentication failed!"
                self.put_msg(message)
                _LOGGER.error(message)
                return False
            elif response.status_code == 500:
                message = "Invalid CloudKnox/Proxy details. Please enter the correct configuration detials."
                self.put_msg(message)
                _LOGGER.error(message)
                return False
            elif response.status_code == 400:
                reason = CloudKnoxCollect.get_error_message(response)
                message = "Unexpected error. status code: {}, reason: {}".format(
                    response.status_code, reason
                )
                self.put_msg(message)
                _LOGGER.error(message)
                return False
            else:
                message = "Unexpected status code: {}, reason: {}".format(
                    response.status_code, response.reason
                )
                self.put_msg(message)
                _LOGGER.error(message)
                return False

        try:
            response = response.json()
            utils.save_ck_credentials(app_name, splunk_session_key, response["accessToken"])
        except Exception as e:
            message = "Unexpected error occurred: {}".format(e)
            self.put_msg(message)
            _LOGGER.error(message)
            return False

        _LOGGER.info("CloudKnox account validation successful.")
        return True


class StartDatetimeValidator(Validator):
    """To validate Start DateTime Field."""

    def validate(self, value, data):
        """Validate start datetime field."""
        start_datetime = data.get('start_datetime')
        if start_datetime and (isinstance(start_datetime, six.string_types) and start_datetime.strip() != ''):
            regex = r"""^([0-9]{4})-([0-9]{2})-([0-9]{2})[tT][0-9]{2}:[0-9]{2}:[0-9]{2}[zZ]$"""
            if not re.match(r"{}".format(regex), start_datetime):
                self.put_msg("Invalid Start DateTime format. Please enter valid Start DateTime.")
                return False
            try:
                start_datetime = datetime.datetime.strptime(start_datetime.upper(), cloudknox_consts.UTC_FORMAT)
            except Exception as e:
                self.put_msg("Please enter valid Start DateTime: {}".format(str(e)))
                return False

            if start_datetime > datetime.datetime.utcnow():
                self.put_msg(
                    "Start DateTime can not exceed current UTC date and time. Please enter valid Start DateTime.")
                return False

            if (datetime.datetime.utcnow() - start_datetime) > datetime.timedelta(days=START_DATETIME_LAST_DAYS):
                self.put_msg(
                    "Start DateTime should be inside last {} days period. Please enter valid Start DateTime.".format(
                        cloudknox_consts.START_DATETIME_LAST_DAYS
                    ))
                return False
        return True
