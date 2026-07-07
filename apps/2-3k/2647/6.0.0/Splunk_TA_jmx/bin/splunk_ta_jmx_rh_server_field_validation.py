#
# SPDX-FileCopyrightText: 2026 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#

import base64
import os
from subprocess import PIPE, Popen
from traceback import format_exc

import java_const
import splunk.admin as admin
import splunk_ta_jmx_logger_helper as log_helper
from solnlib import conf_manager
from splunk_ta_jmx_utility import APPNAME, ibm_java_args_generator
from splunktaucclib.rest_handler.endpoint.validator import Validator

PROCESS_CONNECTION_TYPE = ["pidCommand", "pidFile", "pid"]
PROTOCOL_CONNECTION_TYPE = [
    "soap",
    "soapssl",
    "hessian",
    "hessianssl",
    "burlap",
    "burlapssl",
    "IBMsoap",
]
PROTOCOL_FIELDS = ["account_name", "account_password"]
URL_FIELDS = ["jmx_url", "account_name", "account_password"]
STUBSOURCE_FIELD_RELATIONS = {
    "ior": ["encodedStub"],
    "stub": ["encodedStub"],
    "jndi": ["host", "jmxport", "lookupPath"],
    "jndi_reg_ssl": ["host", "jmxport", "lookupPath"],
}
ALL_REQUIRED_FIELDS = [
    "pidCommand",
    "pid",
    "pidFile",
    "jmx_url",
    "host",
    "jmxport",
    "stubSource",
    "encodedStub",
]
PYTHON_JAVA_PARAM_DICT = {
    "jmx_url": "jmxServiceURL",
    "stubSource": "stubSource",
    "account_name": "jmxuser",
    "account_password": "jmxpass",
    "description": "jvmDescription",
}

_LOGGER = log_helper.setup_logging(log_name="ta_jmx_rh_server_field_validation")


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class RequiredFieldValidation(Validator):
    """
    Validate required fields
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_connection_type_fields(self, data):
        """
        Returns a List containing two arrays one containing fields to be displayed
        and other with fields to be hidden depended on Connection Type dropdown
        :param data: Dict containing field-value
        :return: List
        """
        shown_fields = []
        selected_connection_type = data.get("protocol")
        if selected_connection_type:
            if selected_connection_type in PROCESS_CONNECTION_TYPE:
                shown_fields.append(selected_connection_type)
            elif (
                selected_connection_type == "rmi" or selected_connection_type == "iiop"
            ):
                shown_fields += PROTOCOL_FIELDS
                shown_fields.append("stubSource")
            elif selected_connection_type == "url":
                shown_fields += URL_FIELDS
            elif selected_connection_type in PROTOCOL_CONNECTION_TYPE:
                shown_fields += PROTOCOL_FIELDS

        return shown_fields

    def get_stubsource_fields(self, data):
        """
        Returns a List containing two arrays one containing fields to be displayed
        and other with fields to be hidden depended on Stub source dropdown
        :param data: Dict containing field-value
        :return: List
        """
        shown_fields = []
        selected_stubsource = data.get("stubSource")
        if selected_stubsource in STUBSOURCE_FIELD_RELATIONS:
            shown_fields += STUBSOURCE_FIELD_RELATIONS[selected_stubsource]
        return shown_fields

    def validate_required_fields(self, msg, fields, data):
        """
        Validates values of fields are not empty. Provides message in UI as well as in log file.
        :param fields: List of field
        :param msg: Error message string
        :param data: Dict containing field-value
        :return: None
        """
        for field in fields:
            if not data.get(field):
                self.put_msg(msg.format(field))
                _LOGGER.error(msg.format(field))
                return False
        return True

    def validate(self, value, data):
        """
        This method validates all the server fields and returns True on success else False
        :param value: value of the field for which validation is called
        :param data: Contains dictionary of all parameters of the server configuration
        :return: bool
        """
        all_fields = self.get_connection_type_fields(data) + self.get_stubsource_fields(
            data
        )
        required_fields = [
            field for field in all_fields if field in ALL_REQUIRED_FIELDS
        ]
        msg = "{} field is required."
        if not self.validate_required_fields(msg, required_fields, data):
            return False

        if data.get("account_name") and not data.get("account_password"):
            self.put_msg(msg.format("account_password"))
            _LOGGER.error(msg.format("account_password"))
            return False

        if not data.get("account_name") and data.get("account_password"):
            self.put_msg(msg.format("account_name"))
            _LOGGER.error(msg.format("account_name"))
            return False

        if not self.validate_server_configuration(data):
            return False

        # Remove server_name field after server is validated
        data.pop("server_name", None)
        return True

    @staticmethod
    def get_java_certificate_password(
        validation_args: list, session_key: str = ""
    ) -> tuple:
        """
        The method returns the modified Java arguments by adding the properties related to
        trustStore, keyStore and maximum certificate length and returns a dict of passwords for the keystores.
        """
        conf_file = "splunk_ta_jmx_settings"
        cert_passwords = {}
        if not session_key:
            # when validating the server, we need to get the session key explicitly.
            session_key_obj = GetSessionKey()
            session_key = session_key_obj.session_key
            _LOGGER.debug("Successfully generated the session key.")

        java_sys_conf = conf_manager.ConfManager(
            session_key,
            APPNAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(APPNAME, conf_file),
        )
        java_sys_props = java_sys_conf.get_conf(conf_file, refresh=True).get(
            "java_sys_prop"
        )

        ts_file_path = os.path.sep.join(
            [
                java_const.SPLUNK_HOME,
                "etc",
                "apps",
                APPNAME,
                "bin",
                "mx4j.ks",
            ]
        )
        ts_password = (java_sys_props.get("ts_password") or "").strip()
        ks_file_path = os.path.sep.join(
            [
                java_const.SPLUNK_HOME,
                "etc",
                "apps",
                APPNAME,
                "bin",
                "jmx_client.ks",
            ]
        )
        ks_password = (java_sys_props.get("ks_password") or "").strip()
        # Setting the default length to 10 as it is as per documentation
        cert_length = java_sys_props.get("cert_length") or "10"

        validation_args.insert(-1, "-Djdk.tls.maxCertificateChainLength=" + cert_length)

        if os.path.isfile(ks_file_path):
            validation_args.insert(-1, "-Djavax.net.ssl.keyStore=" + ks_file_path)
            if ks_password:
                cert_passwords["ks_password"] = ks_password

        if os.path.isfile(ts_file_path):
            validation_args.insert(-1, "-Djavax.net.ssl.trustStore=" + ts_file_path)
            if ts_password:
                cert_passwords["ts_password"] = ts_password

        return (validation_args, cert_passwords)

    @staticmethod
    def get_key_value_format(data: dict) -> str:
        """
        This method takes dictionary and returns a string of following format
        'key=value\n
         key1=value1\n
         .............
         keyn=valuen\n'
        Addtional to that it also encodes 'password' field's value if present
        :param data: dict
        :return: string
        """
        input_parameters = ""
        param_value = "{}={}\n"
        for key, value in list(data.items()):
            if not value:
                continue
            # Encode fields having passwords
            if key in ("account_password", "ks_password", "ts_password"):
                value = base64.b64encode(value.encode("utf-8")).decode()
            key = PYTHON_JAVA_PARAM_DICT.get(key, key)
            input_parameters += param_value.format(key, value)
        return input_parameters

    def validate_server_configuration(self, data: dict):
        """
        Because Splunk can't directly invoke Java , we use this python wrapper script that
        simply proxys through to the Java program.

        This method logs error and success message depending on the type of exit code received
        from Java program. Depending on that exit code it returns boolean value
        :param data: dict
        :return: bool
        """

        input_parameters = self.get_key_value_format(data)
        try:
            if data.get("protocol") == "IBMsoap":
                # If IBMsoap protocol is used while connection to jmx server, update java arguments by
                # adding connection properties files
                ibm_was_server_validation_args = ibm_java_args_generator(
                    java_const.IBM_WAS_JAVA_SERVER_VALIDATION_ARGS,
                    data.get("server_name"),
                    _LOGGER,
                )
                if ibm_was_server_validation_args:
                    process = Popen(  # nosemgrep false-positive : The value ibm_was_server_validation_args is a static value which comes from the java_const.py file. It doesn't take any external/user inputs. # noqa: E501
                        ibm_was_server_validation_args, stdin=PIPE
                    )
                else:
                    msg = (
                        "Failed to connect with the JMX server."
                        " Verify the provided properties files are at expected location."
                    )
                    self.put_msg(msg)
                    _LOGGER.error(msg)
                    return False
            else:
                server_validation_args, passwords = self.get_java_certificate_password(
                    java_const.JAVA_SERVER_VALIDATION_ARGS
                )
                if len(passwords) > 0:
                    # We need to manipulate `data` only when the Java System Properties are provided.
                    data.update(passwords)
                    input_parameters = self.get_key_value_format(data)
                    for key in passwords.keys():
                        data.pop(key)
                process = Popen(  # nosemgrep false-positive : The value JAVA_SERVER_VALIDATION_ARGS is a static value which comes from the java_const.py file. It doesn't take any external/user inputs. # noqa: E501
                    server_validation_args, stdin=PIPE
                )

            process.communicate(input=input_parameters.encode("utf-8"))
            process.wait()

        except Exception:
            msg = "Failed to connect with JMX Server."
            self.put_msg(msg)
            _LOGGER.error("{} Reason: {}".format(msg, format_exc()))
            return False

        else:
            if process.returncode == 2:
                msg = (
                    "Failed to connect with the JMX server."
                    " Review the values of the fields on this page and try again."
                )
                self.put_msg(msg)
                _LOGGER.error(msg)
                return False
            elif process.returncode == 1:
                msg = "Invalid parameter found in connection URL. Verify the provided connection configurations."
                self.put_msg(msg)
                _LOGGER.error(msg)
                return False
            _LOGGER.info("Successfully established connection with JMX server.")
            return True
