##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test  # noqa: F401 # isort: skip
import os
import sys
import traceback

import splunk.admin as admin
import splunk_ta_f5_utility as common_utility
from log_manager import setup_logging
from solnlib import hec_config
from solnlib.conf_manager import ConfStanzaNotExistException
from splunktaucclib.rest_handler.endpoint.validator import Validator

sys.path.insert(
    0, os.path.abspath(os.path.join(__file__, "..", "modinputs", "icontrol"))
)

import collector  # noqa: E402


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class ServerValidation(Validator):
    def __init__(self, *args, **kwargs):
        super(ServerValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        session_key = GetSessionKey().session_key
        logger = setup_logging(session_key, "splunk_ta_f5_server_validation")
        try:
            response = common_utility.validate_f5_bigip(
                session_key,
                data["f5_bigip_url"],
                data["account_name"],
                data["account_password"],
                logger,
            )
            if response.status_code in [200, 201]:
                return True
            elif response.status_code == 401:
                msg = "Authorization failed. Please verify if the correct credentials are provided."
                self.put_msg(msg)
                logger.error(msg)
                return False
        except Exception as e:  # noqa: F841
            msg = (
                "Failed to connect to F5 BIG-IP instance. Verify that the server is reachable and "
                "correct credentials are provided."
            )
            self.put_msg(msg)
            logger.error(f"{msg} : {e}")
            return False


class PasswordValidation(Validator):
    """
    Check if the password and confirm_password values are same or not.
    """

    def __init__(self, *args, **kwargs):
        super(PasswordValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        """
        This method validates if the values provided in the password and confirm_password fields are same or not.
        The method returns True on success else it returns False.
        :param value: value of the field for which validation is called.
        :param data: Contains dictionary of all the entities of the server configuration.
        :return: bool
        """
        logger = setup_logging(
            GetSessionKey().session_key, "splunk_ta_f5_server_validation"
        )
        if data["account_password"] != data["confirm_account_password"]:
            msg = "Password do not match with confirm password."
            self.put_msg(msg)
            logger.error(msg)
            return False

        return True


class HECValidation(Validator):
    """
    Check if the HEC Name provided is correct or not.
    """

    def __init__(self, *args, **kwargs):
        super(HECValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        if data.get("hec_name"):
            session_key = GetSessionKey().session_key
            logger = setup_logging(session_key, "splunk_ta_f5_server_validation")
            config = hec_config.HECConfig(session_key)
            try:
                hec_value = config.get_input(name=str(value))
                if hec_value:
                    return True
                else:
                    msg = "The HEC Token does not exist. Please create a new HEC Token or select a different HEC Token for data collection."  # noqa: E501
                    self.put_msg(msg)
                    logger.error(msg)

            except Exception as e:
                self.put_msg(e)
                logger.error("Error occured while validating hec token: {}".format(e))

        return False


class TemplateValidator(Validator):
    def __init__(self, *args, **kwargs):
        super(TemplateValidator, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        session_key = GetSessionKey().session_key
        logger = setup_logging(session_key, "splunk_ta_f5_server_validation")
        templates_list = data.get("templates").split("|")
        try:
            for template in templates_list:
                template_handler_object = collector.TemplateHandler(
                    template, session_key
                )
                template_handler_object.get_template()
        except ConfStanzaNotExistException as e:
            self.put_msg(e)
            logger.error("Error occured while validating Template : {}".format(e))
            return False

        return True
