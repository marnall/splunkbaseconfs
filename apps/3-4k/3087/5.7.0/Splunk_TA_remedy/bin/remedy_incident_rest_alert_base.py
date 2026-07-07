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

import remedy_helper
from account_manager import AccountManager
from logger_manager import get_logger
from solnlib import utils

_LOGGER = get_logger("rest_alert", set_invocation_id=True)
remedy_helper.set_logger(_LOGGER)

parameters_map = {
    "summary": "Summary",
    "impact": "Impact",
    "urgency": "Urgency",
    "incident_status": "Incident_Status",
    "create_incident_on_zero_results": "Create_Incident_on_Zero_Results",
    "incident_status_reason": "Status_Reason",
    "work_info_details": "z1D_WorklogDetails",
    "ci": "HPD_CI",
}


class RemedyRestIncidentAlertBase:
    def __init__(self, helper):
        self.helper = helper
        self.setup_util = helper.setup_util
        self.settings = self.helper.settings
        self.server_uri = self.settings["server_uri"]
        self.session_key = self.settings["session_key"]
        self.data = self.settings["configuration"]
        self._setup_proxy()

    def _get_correlation_id(self):
        return "splunk_" + uuid.uuid4().hex

    def validate_and_prepare_data(self):
        self.data["z1D_Action"] = "PROCESS_EVENT"
        self.data["OutboundIdentifier"] = "Splunk-" + self.settings.get(
            "result", {}
        ).get("host", "")

        del self.data["account"]

        parameters = self.data
        for param in parameters_map:
            if param in parameters:
                self.data[parameters_map[param]] = parameters.get(param)
                del self.data[param]

        for key in list(parameters.keys()):
            if key.startswith("_"):
                del self.data[key]

        # Extract custom fields
        raw_custom_fields = parameters.get("custom_fields").strip()
        if raw_custom_fields:
            for item in raw_custom_fields.split("||"):
                field_kv_list = item.split("=", 1)
                # Verifying that custom fields are in key value format and key is not null
                if len(field_kv_list) == 2 and field_kv_list[0].strip():
                    self.data[field_kv_list[0].strip()] = field_kv_list[1].strip()
                else:
                    _LOGGER.error(
                        "[Remedy Incident REST Alert] The search name: {}. "
                        'Custom field "{}" is not in key value format. '
                        "Expected format: key1=value||key2=value2 ...".format(
                            self.settings.get("search_name", ""), item
                        )
                    )
                    return False
        del self.data["custom_fields"]

        if parameters.get("HPD_CI", "").strip() == "":
            del self.data["HPD_CI"]

        if parameters.get("z1D_WorklogDetails", "").strip() == "":
            del self.data["z1D_WorklogDetails"]

        # Limiting the length of the correlation_id/mc_ueid to 100 characters
        if len(parameters.get("mc_ueid", "")) > 100:
            _LOGGER.error(
                '[Remedy Incident REST Alert] The search name: {}. The parameter "Correlation ID" '
                "should be less than or equal to 100 characters. Please try again.".format(
                    self.settings.get("search_name", "")
                )
            )
            return False

        # Access the "configuration" dictionary directly and delete the key
        if "Create_Incident_on_Zero_Results" in self.data:
            del self.data["Create_Incident_on_Zero_Results"]

        if parameters.get("Incident_Status", "") not in {"1", "Resolved"}:
            if parameters.get("Incident_Status", "") == "0":
                del self.data["Incident_Status"]
            if "Status_Reason" in list(parameters.keys()):
                del self.data["Status_Reason"]
            return True
        elif not parameters.get("Status_Reason", ""):
            _LOGGER.error(
                "[Remedy Incident REST Alert] The search name: {}. "
                "The Status Reason should not be empty when Status is set to be resolved. "
                "Please select one Status Reason.".format(
                    self.settings.get("search_name", "")
                )
            )
            return False
        else:
            self.data["Incident_Status"] = "Resolved"
        return True

    def setup_account(self):
        try:
            self.account_name = self.data["account"]
            self.account_manager = AccountManager(self.session_key)
            self.account_info = self.account_manager.get_account_details(
                self.account_name
            )
        except Exception:
            _LOGGER.exception(
                '[Remedy Incident REST Alert] The search name: {}. Unable to find "{}" account details. '
                "Enter a configured account name or create new account by "
                "going to Configuration page of the Add-on.".format(
                    self.settings.get("search_name", ""), self.account_name
                )
            )
            return False
        return True

    def _setup_proxy(self):
        self.proxy_config = None
        self.proxy_config = remedy_helper.get_proxy_config(self.session_key)

    def query_incident_by_mc_ueid(self, mc_ueid, verify_ssl):
        try:
            response = self.retrier.retry(
                remedy_helper.fetch_form_data,
                form_name="HPD:IncidentOutboundEvent",
                params={
                    "q": "'EventId'=\"{}\"".format(mc_ueid.replace('"', '""')),
                    "fields": "values(IncidentNumber, Request ID)",
                },
                verify_ssl=verify_ssl,
                proxy_config=self.proxy_config,
            )
        except Exception as ex:
            _LOGGER.debug(
                "[Remedy Incident REST Alert] The search name: {}. "
                "Error occured while calling Remedy API to query incident. {}".format(
                    self.settings.get("search_name", ""), str(ex)
                )
            )
            return None

        return [item["values"] for item in response.get("entries", [])]

    def post_incident(self, verify_ssl):
        payload = self.data.copy()
        try:
            for i in range(2):
                response = self.retrier.retry(
                    remedy_helper.create_incident,
                    form_name="HPD:ServiceInterface",
                    params={"fields": "values(Incident Number, Incident_Status)"},
                    payload={"values": payload},
                    verify_ssl=verify_ssl,
                    proxy_config=self.proxy_config,
                )

                if payload["z1D_Action"] == "RELATE_CI":
                    _LOGGER.info(
                        "[Remedy Incident REST Alert] Successfully related CI. Search Name={}, CI={}, "
                        "Try={}, 'Incident Number'={}, Status={}".format(
                            self.settings.get("search_name", ""),
                            payload["HPD_CI"],
                            i + 1,
                            response["Incident Number"],
                            response["Incident_Status"],
                        )
                    )
                else:
                    _LOGGER.info(
                        "[Remedy Incident REST Alert] The search name: {}. Successfully Created/Updated Incident. "
                        "Try: {}. the Incident Number is {} and Status is {}".format(
                            self.settings.get("search_name", ""),
                            i + 1,
                            response["Incident Number"],
                            response["Incident_Status"],
                        )
                    )
                # If we create a new incident with Incident_Status as Resolved,
                # Remedy Creates incident without Incident_Status = Resolved
                # so If user set Incident_Status to be resolved, check the response is as expected
                # If it is not, update an incident again to update the Incident_Status.
                if (
                    payload.get("Incident_Status", "") == "Resolved"
                    and response["Incident_Status"] != "Resolved"
                ):
                    payload["Incident Number"] = response["Incident Number"]
                    continue
                else:
                    break

        except Exception:
            _LOGGER.exception(
                "[Remedy Incident REST Alert] The search name: {}. Failed to Create/Update incident".format(
                    self.settings.get("search_name", "")
                )
            )
            return

    def handle(self):
        if not self.setup_account():
            return

        if not self.validate_and_prepare_data():
            return

        verify_ssl = remedy_helper.get_sslconfig(
            self.session_key,
            utils.is_true(
                self.account_info.get("disable_ssl_certificate_validation", False)
            ),
            _LOGGER,
        )

        self.retrier = remedy_helper.Retry(
            self.session_key,
            self.account_name,
            self.proxy_config,
            self.account_manager,
            verify_ssl,
            store_token=False,
        )

        hpd_ci = self.data.get("HPD_CI", None)
        if hpd_ci:
            del self.data["HPD_CI"]
        mc_ueid = self.data.get("mc_ueid", None).strip()
        incident_details = None
        if mc_ueid:
            incident_details = self.query_incident_by_mc_ueid(
                self.data["mc_ueid"], verify_ssl
            )

        if not mc_ueid or not incident_details:
            self.data["mc_ueid"] = mc_ueid if mc_ueid else self._get_correlation_id()
            self.post_incident(verify_ssl)
            if hpd_ci:
                _LOGGER.info(
                    "[Remedy Incident REST Alert] Proceeding to relate CI "
                    f"for Correlation ID = {self.data['mc_ueid']}"
                )
                self.data = {
                    "z1D_Action": "RELATE_CI",
                    "mc_ueid": self.data["mc_ueid"],
                    "HPD_CI": hpd_ci,
                }
                self.post_incident(verify_ssl)
            return

        for item in incident_details:
            self.data["Incident Number"] = item["IncidentNumber"]
            _LOGGER.info(
                "[Remedy Incident REST Alert] Incident already exists "
                "for mc_ueid='{}'. Updating the '{}' Incident.".format(
                    mc_ueid, item["IncidentNumber"]
                )
            )
            self.post_incident(verify_ssl)

            if hpd_ci:
                _LOGGER.info(
                    "[Remedy Incident REST Alert] Proceeding to relate CI for "
                    f"{item['IncidentNumber']} Incident"
                )
                self.data = {
                    "z1D_Action": "RELATE_CI",
                    "Incident Number": item["IncidentNumber"],
                    "HPD_CI": hpd_ci,
                }
                self.post_incident(verify_ssl)
