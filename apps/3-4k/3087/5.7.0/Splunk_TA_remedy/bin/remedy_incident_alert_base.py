#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""

* isort ignores:
- isort: skip = Should not be sorted.
* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""

import splunk_ta_remedy_declare  # isort: skip # noqa: F401

import uuid

import remedy_consts as c
from logger_manager import get_logger
from remedy_config import RemedyConfig
from remedy_incident_service import RemedyIncidentService
from solnlib import utils
from splunktaucclib.splunk_aoblib.setup_util import Setup_Util

_LOGGER = get_logger("alert", set_invocation_id=True)

parameters_map = {
    "correlation_id": "mc_ueid",
    "summary": "Summary",
    "impact": "Impact",
    "urgency": "Urgency",
    "incident_status": "Incident_Status",
    "create_incident_on_zero_results": "Create_Incident_on_Zero_Results",
    "incident_status_reason": "Incident_Status_Reason",
    "work_info_details": "Work_Info_Details",
    "ci": "HPD_CI",
}


class RemedyIncidentAlertBase:
    def __init__(self, payload, server_uri):
        self.first_try = True
        self._payload = payload
        self.server_uri = server_uri
        self._payload["configuration"]["Action"] = "PROCESS_EVENT"
        self._payload["configuration"][
            "OutboundIdentifier"
        ] = "Splunk-" + self._payload.get("result", {}).get("host", "")
        self._get_remedy_account()
        self.http_scheme = self.remedy_account.get(c.HTTP_SCHEME).strip()
        self.disable_ssl_certificate_validation = utils.is_true(
            self.remedy_account.get(c.DISABLE_SSL_CERTIFICATE_VALIDATION)
        )
        self.certificate_path = self.remedy_account.get(c.CERTIFICATE_PATH)
        setup_util = Setup_Util(self.server_uri, self._payload["session_key"])
        self.proxy_settings = setup_util.get_proxy_settings()

    def _get_remedy_account(self):
        self.remedy_account = (
            self._get_remedy_conf().get_stanzas().get(c.REMEDY_ACCOUNT)
        )

    def _get_session_key(self):
        return self._payload["session_key"]

    def _get_remedy_conf(self):
        try:
            sk = self._get_session_key()
            try:
                splunk_uri = self.server_uri
            except Exception as ex:
                _LOGGER.error(
                    "Internal error occurs: Failed to get the splunk_uri: %s", str(ex)
                )
                raise
            remedy_conf = RemedyConfig(splunk_uri, sk)
            return remedy_conf
        except Exception as ex:
            _LOGGER.error(
                "Internal error occurs: Failed to get config of Remedy server for custom command and alert:  "
                "%s Please go to setup page to reconfigure the Remedy server.",
                str(ex),
            )
            raise

    def _check_remedy_setting(self):
        remedy_url = self.remedy_account.get("server_url", "")
        remedy_server_name = self.remedy_account.get("server_name", "")
        remedy_user = self.remedy_account.get("user", "")

        if (
            remedy_user
            and remedy_user.strip()
            and remedy_url
            and remedy_url.strip(" /")
            and remedy_server_name
            and remedy_server_name.strip()
        ):
            return True
        else:
            _LOGGER.error(
                "[Remedy Alert] The remedy server is not configured correctly. Please go to the setup page "
                "to configure the Remedy server."
            )
            return False

    def _get_correlation_id(self):
        return "splunk_" + uuid.uuid4().hex

    def _check_parameters(self):
        parameters = self._payload.get("configuration", {})
        for param in parameters_map:
            if param in parameters:
                self._payload.get("configuration")[
                    parameters_map[param]
                ] = parameters.get(param)
                del self._payload.get("configuration")[param]

        # Extract custom fields
        raw_custom_fields = parameters.get("custom_fields").strip()
        if raw_custom_fields:
            for item in raw_custom_fields.split("||"):
                field_kv_list = item.split("=", 1)
                # Verifying that custom fields are in key value format and key is not null
                if len(field_kv_list) == 2 and field_kv_list[0].strip():
                    self._payload["configuration"][
                        field_kv_list[0].strip()
                    ] = field_kv_list[1].strip()
                else:
                    _LOGGER.error(
                        "[Remedy Incident Alert] The search name: {}. "
                        'Custom field "{}" is not in key value format. '
                        "Expected format: key1=value||key2=value2 ...".format(
                            self._payload.get("search_name", ""), item
                        )
                    )
                    return False
        del self._payload["configuration"]["custom_fields"]

        # Access the "configuration" dictionary directly and delete the key
        if "Create_Incident_on_Zero_Results" in self._payload.get("configuration", {}):
            del self._payload["configuration"]["Create_Incident_on_Zero_Results"]

        if not parameters.get("mc_ueid", ""):
            self._payload["configuration"]["mc_ueid"] = self._get_correlation_id()
            _LOGGER.info(
                '[Remedy Incident Alert] The search name: {}. The parameter "Correlation ID" configured '
                "is empty or can not be found in the event. Generating a random correlation ID.".format(
                    self._payload.get("search_name", "")
                )
            )

        # Limiting the length of the correlation_id/mc_ueid to 100 characters
        if len(parameters.get("mc_ueid", "")) > 100:
            _LOGGER.error(
                '[Remedy Incident Alert] The search name: {}. The parameter "Correlation ID" '
                "should be less than or equal to 100 characters. Please try again.".format(
                    self._payload.get("search_name", "")
                )
            )
            return False

        if parameters.get("Incident_Status", "") not in {"1", "Resolved"}:
            if parameters.get("Incident_Status", "") == "0":
                del self._payload["configuration"]["Incident_Status"]
            if "Incident_Status_Reason" in list(parameters.keys()):
                del self._payload["configuration"]["Incident_Status_Reason"]
            return True
        elif not parameters.get("Incident_Status_Reason", ""):
            _LOGGER.error(
                "[Remedy Incident Alert] The search name: {}. "
                "The Status Reason should not be empty when Status is set to be resolved. "
                "Please select one Status Reason.".format(
                    self._payload.get("search_name", "")
                )
            )
            return False
        else:
            self._payload["configuration"]["Incident_Status"] = "Resolved"
        return True

    def _check_result(self, result):
        # If user set Incident_Status to be resolved, check the result is as expected
        # If it not as expected, remove the parameter 'Incident_Status' and 'Incident_Status_Reason'
        # to create an incident firstly and then add the parameters back and then update the status.

        if (
            self.first_try
            and self.args.get("Incident_Status", "") == "Resolved"
            and (
                result.get("incident_status", "") != "Resolved"
                or result.get("Request_ID", "")
                == "No open Incident \
            found"
            )
        ):
            self.first_try = False
            # replace mc_ueid with incident_number
            if result.get("Request_ID", "").startswith("INC"):
                incident_number = result.get("Request_ID")
                if "mc_ueid" in list(self.args.keys()):
                    del self.args["mc_ueid"]
                    self.args["Incident_Number"] = incident_number
            inc_status = self.args.get("Incident_Status")
            inc_status_reason = self.args.get("Incident_Status_Reason")
            # remove the two parameters to retry
            del self.args["Incident_Status"]
            del self.args["Incident_Status_Reason"]
            try:
                result = self.ris.incident_operate(self.wsdl, self.args)
                # add the parameters back to update the incident status
                self.args["Incident_Status"] = inc_status
                self.args["Incident_Status_Reason"] = inc_status_reason
                result = self.ris.incident_operate(self.wsdl, self.args)
            except Exception as ex:
                _LOGGER.error(
                    "[Remedy Alert] The search name: {0}. Error occurs when calling Remedy API. "
                    "The wsdl: {1}. The args: {2}. The first_try: {3}. Error "
                    "message: %s. ".format(
                        self._payload.get("search_name", ""),
                        self.wsdl,
                        self.args,
                        self.first_try,
                    ),
                    str(ex),
                )
                return False, result
            else:
                return self._check_result(result)
        elif result.get("Request_ID", "").startswith("INC"):
            _LOGGER.info(
                "[Remedy Incident Alert] The search name: {0}. The incident {1} is created/updated "
                "successfully.".format(
                    self._payload.get("search_name", ""), result.get("Request_ID", "")
                )
            )
            return True, result
        else:
            _LOGGER.error(
                "[Remedy Incident Alert] The search name: {0}. Fail to create/update the incident. "
                "Detail: "
                "{1}".format(self._payload.get("search_name", ""), result)
            )
            return False, result

    def handle(self):
        if self._check_remedy_setting() and self._check_parameters():
            self.ris = RemedyIncidentService(
                self.remedy_account.get("user", "").strip(),
                self.remedy_account.get("password", ""),
                self.http_scheme,
                self.disable_ssl_certificate_validation,
                self.certificate_path,
                self.proxy_settings,
            )
            self.remedy_url = (
                self.remedy_account.get("http_scheme")
                + "://"
                + self.remedy_account.get("server_url", "").strip(" /")
            )
            self.remedy_servername = self.remedy_account.get("server_name", "").strip()
            self.wsdl = (
                self.remedy_url
                + "/arsys/WSDL/public/"
                + self.remedy_servername
                + "/"
                + "HPD_IncidentServiceInterface"
            )
            self.args = self._payload.get("configuration", {})
            _LOGGER.debug(
                "[Remedy Alert] The args for do_incident_operate is: {}".format(
                    self.args
                )
            )
            self.do_incident_operate()

    def query_incident(self, query):
        wsdl_get = (
            self.remedy_url
            + "/arsys/WSDL/public/"
            + self.remedy_servername
            + "/"
            + "HPD_IncidentOutboundEvent"
        )
        args_get = {"Qualification": query}

        try:
            incident_detail = self.ris.getIncidents(wsdl_get, args_get)
        except Exception as ex:
            _LOGGER.debug(
                "[Remedy Alert] The search name: {0}. Error occurs when calling Remedy API "
                "to query incident.They query is {1} The wsdl: {2}. The args: {3}. Error "
                "message: %s".format(
                    self._payload.get("search_name", ""), query, wsdl_get, args_get
                ),
                str(ex),
            )
            return None
        return incident_detail

    def do_incident_operate(self):
        # try to query the incident with the event id mc_ueid
        # Check whether the incident already exist.
        mc_ueid = self.args.get("mc_ueid").replace('"', '""')
        query = "'EventId'=\"{}\"".format(mc_ueid)
        incident_detail = self.query_incident(query)
        if incident_detail:
            del self.args["mc_ueid"]
            incident_numbers = [i.get("IncidentNumber") for i in incident_detail]
            for incident_number in incident_numbers:
                self.args["Incident_Number"] = incident_number
                _LOGGER.debug(
                    "[Remedy Alert] Remove mc_ueid from args and add Incident_Number parameter. The args is: "
                    "{}".format(self.args)
                )
                self._do_incident_operate()
        else:
            self._do_incident_operate()

    def _do_incident_operate(self):
        try:
            result = self.ris.incident_operate(self.wsdl, self.args)
        except Exception as ex:
            _LOGGER.error(
                "[Remedy Alert] The search name: {0}. Error occurs when calling Remedy API. "
                "The wsdl: {1}. The args: {2}. Error message: %s. ".format(
                    self._payload.get("search_name", ""), self.wsdl, self.args
                ),
                str(ex),
            )
            return
        else:
            is_success, result = self._check_result(result)
            if is_success:
                query = "'IncidentNumber'=\"{}\"".format(result.get("Request_ID"))
                incident_detail = self.query_incident(query)
                if incident_detail:
                    _LOGGER.info(
                        "[Remedy Alert] The search name: {0}. The incident detail info is {1}".format(
                            self._payload.get("search_name", ""), incident_detail
                        )
                    )
                else:
                    _LOGGER.error(
                        "[Remedy Alert] The search name: {0}. Error occurs when calling Remedy API "
                        "to get the detail info of incident {1}. ".format(
                            self._payload.get("search_name", ""),
                            result.get("Request_ID"),
                        )
                    )
            else:
                _LOGGER.error(
                    "[Remedy Alert] The search name: {0}. The incident operation failed. The wsdl: {1}, "
                    "the args: {2}".format(
                        self._payload.get("search_name", ""), self.wsdl, self.args
                    )
                )
                return
