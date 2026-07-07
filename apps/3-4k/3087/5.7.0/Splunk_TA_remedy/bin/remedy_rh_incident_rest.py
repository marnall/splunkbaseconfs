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
import json

import remedy_consts as c
import remedy_helper
import splunk.admin
from account_manager import AccountManager
from logger_manager import get_logger
from solnlib import log, utils
from splunktaucclib.rest_handler import util

util.remove_http_proxy_env_vars()

_LOGGER = get_logger("rh_incident_rest")
remedy_helper.set_logger(_LOGGER)
log_enter_exit = log.log_enter_exit(_LOGGER)


class RemedyIncidentHandler(splunk.admin.MConfigHandler):
    @log_enter_exit
    def setup(self):
        self.supportedArgs.addOptArg("incident_number")
        self.supportedArgs.addOptArg("correlation_id")
        self.supportedArgs.addReqArg("account")

    @staticmethod
    def _build_error_response(response, code, error_msg):
        response.append("code", code)
        response.append("message", error_msg)

    @log_enter_exit
    def handleList(self, conf_info):
        resp = conf_info["IncidentResult"]

        incident_id = self.callerArgs.data.get("incident_number")
        correlation_id = self.callerArgs.data.get("correlation_id")
        account_name = self.callerArgs.data["account"][0]

        incident_id = incident_id[0] if incident_id else ""
        correlation_id = correlation_id[0] if correlation_id else ""

        incident_id = incident_id or ""
        correlation_id = correlation_id or ""
        account_name = account_name or ""

        # throw error if incident_id and correlation_id both are empty
        if not incident_id.strip() and not correlation_id.strip():
            msg = "Unable to find 'incident_id' or 'correlation_id' query params. Please provide either param to fetch the incident."
            _LOGGER.error(msg)
            self._build_error_response(
                resp,
                400,
                msg,
            )
            return

        if incident_id.strip():
            if correlation_id.strip():
                _LOGGER.info(
                    "Both 'incident_id' and 'correlation_id' query parameters passed. Defaulting to use 'incident_id'."
                )
            # Limiting the length of the incident_id to 100 characters
            if len(incident_id) > 100:
                msg = "incident_id should be less than or equal to 100 characters"
                _LOGGER.error(msg)
                self._build_error_response(
                    resp,
                    400,
                    msg,
                )
                return

            search_by = "incident_id"
            # prepare query parameters
            query_params = {
                "q": "'Incident Number'=\"{}\"".format(incident_id.strip()),
            }
        else:
            # Limiting the length of the correlation_id to 100 characters
            if len(correlation_id) > 100:
                msg = "correlation_id should be less than or equal to 100 characters"
                _LOGGER.error(msg)
                self._build_error_response(
                    resp,
                    400,
                    msg,
                )
                return

            search_by = "correlation_id"
            # prepare query parameters
            query_params = {
                "q": "'mc_ueid'=\"{}\"".format(correlation_id.replace('"', '""')),
            }

        if not account_name.strip():
            msg = "Value provided to the 'account' parameter is invalid"
            _LOGGER.error(msg)
            self._build_error_response(
                resp,
                400,
                msg,
            )
            return

        session_key = self.getSessionKey()
        account_manager = AccountManager(session_key)

        try:
            account_info = account_manager.get_account_details(account_name)
        except Exception:
            msg = "Enter a configured account name or create new account by going to Configuration page of the Add-on"
            _LOGGER.error(msg)
            self._build_error_response(resp, 400, msg)
            return
        _LOGGER.info(
            "Received request with Incident ID '{}' , Correlation ID '{}' and account '{}'".format(
                incident_id,
                correlation_id,
                account_name,
            )
        )

        proxy_config = remedy_helper.get_proxy_config(session_key)

        verify_ssl = remedy_helper.get_sslconfig(
            session_key,
            utils.is_true(
                account_info.get("disable_ssl_certificate_validation", False)
            ),
            _LOGGER,
        )

        retrier = remedy_helper.Retry(
            session_key,
            account_name,
            proxy_config,
            account_manager,
            verify_ssl,
            store_token=False,
        )

        try:
            response = retrier.retry(
                remedy_helper.fetch_form_data,
                form_name=remedy_helper.INCIDENT_FORM,
                params=query_params,
                verify_ssl=verify_ssl,
                proxy_config=proxy_config,
            )
            incident_details = [item["values"] for item in response.get("entries", [])]

            url_mode = (
                account_info.get("midtier_url", "").strip(" /")
                + "/arsys/forms/"
                + account_info.get("server_name", "").strip()
                + "/SHR:LandingConsole/Default Administrator View/?mode=search&F304255500=HPD:Help "
                "Desk&F1000000076=FormOpenNoAppList&F303647600=SearchTicketWithQual&F304255610"
                "='1000000161'=\"{}\""
            )

            if not incident_details:
                msg = "Record not found"
                _LOGGER.info(msg)
                self._build_error_response(resp, 404, msg)
                return

            smart_it_url = account_info.get("smart_it_url", None)
            if smart_it_url:
                smart_it_url = smart_it_url + c.SMART_IT_INSTANCE_ID_ENDPOINT

            incident_number_list = []
            incident_url_list = []
            for item in incident_details:
                incident_number_list.append(item["Incident Number"])
                incident_url_list.append(url_mode.format(item["Incident Number"]))
                if smart_it_url:
                    incident_url_list.append(smart_it_url.format(item["InstanceId"]))

            response_as_str = json.dumps(incident_details)
            _LOGGER.info("Sucessfully fetched incident content")

            resp.append("incident_detail_list", response_as_str)
            resp.append("incident_number_list", incident_number_list)
            resp.append("incident_url_list", incident_url_list)

        except Exception as ex:
            msg = "Failed to fetch incident for {} = {} , account_name = {}".format(
                search_by,
                incident_id if search_by == "incident_id" else correlation_id,
                account_name,
            )
            _LOGGER.error("{} reason=%s" % (msg, str(ex)))
            self._build_error_response(
                resp,
                404,
                msg,
            )


@log_enter_exit
def main():
    splunk.admin.init(RemedyIncidentHandler, splunk.admin.CONTEXT_NONE)


if __name__ == "__main__":
    main()
