#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#


import base64
import os
import subprocess

import splunk.admin as admin
from solnlib import conf_manager, log
from splunk import rest
from splunktaucclib.rest_handler.endpoint.validator import Validator

log.Logs.set_context()
_LOGGER = log.Logs().get_logger(
    "splunk_ta_microsoft-scom_performance_filter_parameter_validation"
)


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


class ErrorMessage:
    """Store validation error"""

    def __init__(self, msg, high_priority=False):
        self.high_priority = high_priority
        self.msg = msg

    def maybe_update_and_get(self, new_msg, high_priority=False):
        """Update message if new message has high priority or existing message does not"""
        if high_priority or not self.high_priority:
            self.msg = new_msg
            self.high_priority = high_priority
        return self.msg


class FilterParameterValidator(Validator):
    """
    This class validates if the data passed for validation in input is in future.
    If so throws error in UI"""

    def __init__(self):
        super(FilterParameterValidator, self).__init__()
        self._errMsg = ErrorMessage(None)

    def templateValidator(self, data):
        try:
            templates = data["templates"]
            if isinstance(templates, list):
                templates = templates[0]
            templates = templates.split("|")
            settings_cfm = conf_manager.ConfManager(
                GetSessionKey().session_key,
                "Splunk_TA_microsoft-scom",
                realm="__REST_CREDENTIAL__#{}#configs/conf-microsoft_scom_templates".format(
                    "Splunk_TA_microsoft-scom"
                ),
            )
            scom_templates_conf = settings_cfm.get_conf(
                "microsoft_scom_templates"
            ).get_all()
            try:
                for template in templates:
                    if (
                        "Get-SCOMAllPerfData"
                        in scom_templates_conf[template]["content"]
                    ):
                        return True
            except Exception as exc:
                self.put_msg(str(exc))
            self.put_msg("Filter parameter can be used only for performance data", True)
            return False
        except Exception as exc:
            self.put_msg(str(exc))
            return False

    def validate(self, value, data):
        if not self.templateValidator(data):
            return False
        try:
            server = data.get("server")
            filterparameter = str(data.get("filter_parameters"))
            sessionkey = GetSessionKey().session_key
            serveruri = rest.makeSplunkdUri().strip("/")

            server_encoded = base64.b64encode(server.encode("utf-8")).decode()
            filterparameter_encoded = base64.b64encode(
                filterparameter.encode("utf-8")
            ).decode()
            sessionkey_encoded = base64.b64encode(sessionkey.encode("utf-8")).decode()
            serveruri_encoded = base64.b64encode(serveruri.encode("utf-8")).decode()

            splunk_home = os.path.normpath(os.environ["SPLUNK_HOME"])
            splunk_home = splunk_home.replace("\\", "\\\\")
            result = subprocess.run(
                [
                    "powershell.exe",
                    f' & "{splunk_home}\\etc\\apps\\Splunk_TA_microsoft-scom\\bin\\scom_input_validate.ps1" "{server_encoded}" "{serveruri_encoded}" "{sessionkey_encoded}" "{filterparameter_encoded}"',  # noqa : E501
                ],
                capture_output=True,
                timeout=120,
            )
            output = result.stdout.decode("utf-8")

            if output.strip() == "True":
                _LOGGER.info(
                    "Filter Parameter {} has been successfully validated".format(
                        filterparameter
                    )
                )
                return True

            self.put_msg(output.strip(), high_priority=True)
            _LOGGER.info(output.strip())
            return False

        except subprocess.SubprocessError as e:
            msg = (
                "Filter Parameter validation unsuccessful. {} Exception occured".format(
                    str(type(e).__name__)
                )
            )
            _LOGGER.error(str(msg))
            self.put_msg(str(msg))
            return False
        except Exception as exc:
            msg = "Filter Parameter validation unsuccessful. Details: {} ".format(
                str(exc)
            )

            _LOGGER.error(msg)
            self.put_msg(
                "Filter Parameter validation unsuccessful. Refer Add-on logs for more details."
            )
            return False

    def put_msg(self, new_msg_candidate, *args, **kwargs):
        new_msg_high_priority = kwargs.get("high_priority", False)
        error_message = self._errMsg.maybe_update_and_get(
            new_msg_candidate, new_msg_high_priority
        )
        super().put_msg(error_message, *args, **kwargs)
