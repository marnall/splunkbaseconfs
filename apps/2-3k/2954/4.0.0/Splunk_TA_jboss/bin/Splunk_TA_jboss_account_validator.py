#
# SPDX-FileCopyrightText: 2026 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import os.path as op
import subprocess
from splunktaucclib.rest_handler.endpoint.validator import Validator
import splunktalib.common.log as log
import splunk.admin as admin
from solnlib import conf_manager
import jboss_consts as c
import java_args_gen as jag

_LOGGER = log.Logs(default_level="INFO").get_logger(c.INPUT_VALIDATION_LOG_FILE)


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class ServerValidator(Validator):
    """This class extends base class of Validator."""

    APP_NAME = "Splunk_TA_jboss"

    _DIR_NAME = "jmx-op-invoke-1.2.0"

    _OP_INVOKE_HOME = op.join(op.dirname(op.abspath(__file__)), "java", _DIR_NAME)

    _MAIN_CLASS = "com.splunk.jmxopinvoke.JMXServerValidator"

    def initialize_variables(self):
        """Initialize the required variables such as log level, args for Java process"""
        session_key_obj = GetSessionKey()
        session_key = session_key_obj.session_key

        settings_cfm = conf_manager.ConfManager(
            session_key,
            self.APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(
                self.APP_NAME, c.JBOSS_SETTINGS_CONF
            ),
        )

        self.log_level = (
            settings_cfm.get_conf(c.JBOSS_SETTINGS_CONF)
            .get(c.LOG_STANZA)
            .get(c.LOG_LEVEL, "INFO")
        )
        log.Logs().set_level(level=self.log_level, name=c.INPUT_VALIDATION_LOG_FILE)

        log4j2_xml_path = op.sep.join([self._OP_INVOKE_HOME, "config", "log4j2.xml"])
        vm_arguments = {
            c.LOG_PATH_PARAMS: c.LOG_PATH,
            c.LOG_LEVEL_PARAMS: self.log_level,
            c.LOG4J_2_PROP_FILE: log4j2_xml_path,
        }

        args_generator = jag.JavaArgsGenerator(
            app_home=self._OP_INVOKE_HOME,
            vm_arguments=vm_arguments,
            main_class=self._MAIN_CLASS,
        )
        java_args = args_generator.generate()
        return java_args

    def validate(self, value, data):
        """Validates the server details provided by the user. Logs and shows the relevant messages."""

        java_args = self.initialize_variables()

        input_json = str(data).encode("utf-8")

        self._process = subprocess.Popen(
            java_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,  # nosemgrep false-positive : The value java_args is static value from java_args_gen.py file. It doesn't take any external/user inputs.
            stderr=subprocess.PIPE,
        )
        self._process.stdin.write(input_json)
        self._process.stdin.close()

        output = self._process.stdout.readline()
        output = output.decode("utf-8")
        message = ""

        if self._process.poll() == 3:
            message = "Failed to establish connection. Please verify the provided details and that the server is running."
            _LOGGER.error(message)
            self.put_msg(message)
            return False
        elif output == "Connection successfully closed.":
            _LOGGER.debug("The server has been successfully been configured.")
            return True
        else:
            message = "Failed to connect. Please check the log files for more details."
            self.put_msg(message)
            _LOGGER.error(
                "{} {}".format(message, "Return code: {}".format(self._process.poll()))
            )
            return False
