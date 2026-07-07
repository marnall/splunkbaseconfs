#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
Rest handler file for the scom inputs.

* isort ignores:
- isort: skip = Should not be sorted.

* flake8 ignores:
- noqa: E401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
- noqa: E203 -> Def = Colons should not have any space before them
    Reason for ignoring = The whitespace is intended.
"""


import import_declare_test  # isort: skip # noqa: F401

import logging
from datetime import datetime, timedelta
from urllib.request import pathname2url

import splunk_ta_ms_scom_util as scom_util
import splunktalib.rest as rest_handler
from solnlib.utils import is_true
from splunk import rest
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError

from splunk_ta_ms_scom_filterparameter_validation import (  # isort: skip
    FilterParameterValidator,
)

from splunk_ta_ms_scom_input_validators import (  # isort: skip
    DateValidator,
    IntervalValidation,
)
from splunktaucclib.rest_handler.endpoint import (  # isort: skip
    RestModel,
    SingleModel,
    field,
    validator,
)

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "description",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192,
            min_len=1,
        ),
    ),
    field.RestField(
        "templates", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "filter_parameters",
        required=False,
        encrypted=False,
        default="CounterName IS NOT NULL",
        validator=FilterParameterValidator(),
    ),
    field.RestField(
        "server", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=None,
        validator=IntervalValidation(),
    ),
    field.RestField(
        "index",
        required=True,
        encrypted=False,
        default="default",
        validator=validator.String(
            max_len=80,
            min_len=1,
        ),
    ),
    field.RestField(
        "starttime",
        required=False,
        encrypted=False,
        default=None,
        validator=DateValidator(),
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)

endpoint = SingleModel(
    "microsoft_scom_tasks",
    model,
)


class ScomTaskHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        self._scom_loader_path = (
            '& "$SplunkHome\\etc\\apps\\'
            "Splunk_TA_microsoft-scom\\bin"
            '\\scom_command_loader.ps1"'
        )
        self._scom_stanza_prefix = "_Splunk_TA_microsoft_scom_internal_used_"
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleCreate(self, confInfo):
        self.checkStartTime()
        AdminExternalHandler.handleCreate(self, confInfo)
        input_params = self._task_to_scom_input_params(
            self.callerArgs.id, self.callerArgs.data
        )
        self._update_scom_input(input_params)

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)
        prefix = self.appName + ":"
        for inputStanzaKey, inputStanzaValue in list(confInfo.items()):
            template = inputStanzaValue.get("templates")
            if template and (prefix in template):
                inputStanzaValue["templates"] = template.replace(" ", "").replace(
                    prefix, ""
                )

    def handleEdit(self, confInfo):
        self.checkStartTime()
        AdminExternalHandler.handleEdit(self, confInfo)
        if "disabled" not in self.callerArgs.data:
            input_params = self._task_to_scom_input_params(
                self.callerArgs.id, self.callerArgs.data
            )
            self._update_scom_input(input_params)
        else:
            disabled = (self.callerArgs.data.get("disabled"))[0]
            stanza = self._scom_stanza_prefix + self.callerArgs.id
            if is_true(disabled):
                success = scom_util.disable_internal_input(
                    stanza, self.getSessionKey(), self.userName, self.appName
                )
            else:
                success = scom_util.enable_internal_input(
                    stanza, self.getSessionKey(), self.userName, self.appName
                )
            if not success:
                msgx = "cannot enable/disable stanza={} in inputs.conf".format(stanza)
                raise RestError("400", str(msgx))

    def handleRemove(self, confInfo):
        stanza = self._scom_stanza_prefix + self.callerArgs.id
        success = scom_util.delete_internal_input(
            stanza, self.getSessionKey(), self.userName, self.appName
        )
        if not success:
            msgx = "cannot delete stanza={} in inputs.conf".format(stanza)
            raise RestError("400", str(msgx))
        AdminExternalHandler.handleRemove(self, confInfo)

    def _update_scom_input(self, params):
        # validate the interval params

        name = "{}{}".format(self._scom_stanza_prefix, params.pop("name"))

        if self._input_exists(name):
            # update input directly without 'disabled' field
            success = scom_util.update_internal_inputs(
                name, params, self.getSessionKey(), self.userName, self.appName
            )

        else:
            params["name"] = name
            success = scom_util.create_internal_input(
                params, self.getSessionKey(), self.userName, self.appName
            )

        if not success:
            msgx = "cannot write to inputs.conf stanza={}".format(name)
            raise RestError("400", str(msgx))

    def _input_exists(self, name):
        url = "{uri}/servicesNS/{user}/{app}/data/inputs/powershell/" "{name}".format(
            uri=rest.makeSplunkdUri().strip("/"),
            user=self.userName,
            app=self.appName,
            name=pathname2url(name),
        )
        response = rest_handler.splunkd_request(
            url, session_key=self.getSessionKey(), method="GET"
        )
        return response.status_code != 404

    def _task_to_scom_input_params(self, stanza_name, req_params):
        all_templates = scom_util.get_all_templates(
            self.getSessionKey(), self.userName, self.appName
        )

        selected_template_ids = [
            item.strip()
            for item in req_params.get("templates")[0].split("|")
            if item.strip() != ""
        ]
        prefix = self.appName + ":"
        final_selected_template_ids = []
        for item in selected_template_ids:
            if item.startswith(prefix):
                final_selected_template_ids.append(item[len(prefix) :])  # noqa: E203
            else:
                final_selected_template_ids.append(item)

        selected_template_contents = [
            all_templates[id]
            for id in final_selected_template_ids
            if id in all_templates
        ]

        selected_metrics = [
            metric.strip()
            for content in selected_template_contents
            for metric in content.split(",")
        ]

        groups, commands = [], []
        for metric in selected_metrics:
            if (
                metric.startswith("group=")
                and metric.replace("group=", "").strip() != ""
            ):
                groups.append(
                    '"{}"'.format(metric.replace("group=", "").strip().lower())
                )
            elif metric.startswith("cmd=") and metric.replace("cmd=", "").strip() != "":
                # semgrep ignore reason: commands being used here is a variable,
                # and not a python module, hence its a false positive.
                commands.append(  # nosemgrep: contrib.dlint.dlint-equivalent.insecure-commands-use
                    '"{}"'.format(metric.replace("cmd=", "").strip().lower())
                )

        # get the param string of SCOM script
        param = ""
        if groups:
            param = " -groups {}".format(",".join(groups))

        if commands:
            param += " -commands {}".format(",".join(commands))
        log_level = scom_util.get_log_level(
            self.getSessionKey(), self.userName, self.appName
        )
        if req_params.get("server")[0] == "localhost":
            script = "{} {} -loglevel {}".format(
                self._scom_loader_path, param, log_level
            )
        else:
            for item in req_params.get("server"):
                script = f'{self._scom_loader_path} {param} -server "{item}" -loglevel {log_level},'
                script = script[:-1]
        if req_params.get("starttime") and req_params.get("starttime")[0]:
            script = '{} -starttime "{}"'.format(script, req_params.get("starttime")[0])
        if (
            FilterParameterValidator().templateValidator(req_params)
            and req_params.get("filter_parameters")
            and req_params.get("filter_parameters")[0]
        ):
            script = '{} -performancefilter "{}"'.format(
                script, req_params.get("filter_parameters")[0]
            )
        result = {
            "name": stanza_name,
            "script": script,
            "schedule": req_params.get("interval")[0],
            "index": req_params.get("index")[0],
            "sourcetype": "microsoft:scom",
        }
        return result

    def checkStartTime(self):
        now = datetime.utcnow() - timedelta(days=1)
        # Check if starttime field is empty.
        # If so, set its default value to one day ago (UTC) so that it reflects on UI.
        if not self.payload.get("starttime"):
            self.payload["starttime"] = datetime.strftime(now, "%Y-%m-%dT%H:%M:%SZ")
            self.callerArgs.data["starttime"] = datetime.strftime(
                now, "%Y-%m-%dT%H:%M:%SZ"
            )


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=ScomTaskHandler,
    )
