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
import traceback

import remedy_consts as c
import splunk.admin
import splunk.clilib.cli_common as scc
from logger_manager import get_logger
from remedy_config import RemedyConfig
from remedy_incident_service import RemedyIncidentService as ris
from solnlib import log, utils
from splunktaucclib.rest_handler import util
from splunktaucclib.splunk_aoblib.setup_util import Setup_Util

util.remove_http_proxy_env_vars()

_LOGGER = get_logger("incident")
log_enter_exit = log.log_enter_exit(_LOGGER)


class RemedyIncidentHandler(splunk.admin.MConfigHandler):
    @log_enter_exit
    def setup(self):
        self.supportedArgs.addOptArg("incident_number")
        self.supportedArgs.addOptArg("correlation_id")

    def _get_remedy_account(self):
        try:
            sk = self.getSessionKey()
            try:
                splunk_uri = scc.getMgmtUri()
            except Exception as ex:
                _LOGGER.error(
                    "Internal error occurs: Failed to get the splunk_uri: %s", str(ex)
                )
                raise
            remedy_conf = RemedyConfig(splunk_uri, sk)
            remedy_account = remedy_conf.get_stanzas().get(c.REMEDY_ACCOUNT)

            if not all(
                (
                    remedy_account.get("user", "").strip(),
                    remedy_account.get("server_url", "").strip(),
                    remedy_account.get("server_name", "").strip(),
                    remedy_account.get("http_scheme", "").strip(),
                    remedy_account.get(
                        "disable_ssl_certificate_validation", ""
                    ).strip(),
                )
            ):
                _LOGGER.error(
                    "The Remedy account is not configured correctly. Please configure it in the setup page."
                )
                raise  # pylint: disable=misplaced-bare-raise
            return remedy_account
        except Exception as ex:
            _LOGGER.error(
                "Internal error occurs: Failed to get config of Remedy server for custom command and alert:  "
                "%s Please go to setup page to reconfigure the Remedy server.",
                str(ex),
            )
            _LOGGER.error(traceback.format_exc())
            raise

    def _retrieve_incident(self, remedy_account, search_by, value):
        disable_ssl_certificate_validation = utils.is_true(
            remedy_account.get(c.DISABLE_SSL_CERTIFICATE_VALIDATION)
        )
        certificate_path = remedy_account.get(c.CERTIFICATE_PATH)
        setup_util = Setup_Util(self.server_uri, self.session_key)
        proxy_settings = setup_util.get_proxy_settings()
        http_scheme = remedy_account.get(c.HTTP_SCHEME).strip()

        remedy_is = ris(
            remedy_account.get("user", ""),
            remedy_account.get("password", ""),
            http_scheme,
            disable_ssl_certificate_validation,
            certificate_path,
            proxy_settings,
        )
        # Handle the double quote in value of Incident ID or Correlation ID
        value = value.replace('"', '""')
        args = {
            "Qualification": "'{}'=\"{}\"".format(
                "IncidentNumber" if search_by == "incident_id" else "EventId", value
            )
        }
        wsdl = (
            remedy_account.get("http_scheme").strip()
            + "://"
            + remedy_account.get("server_url", "").strip(" /")
            + "/arsys/WSDL/public/"
            + remedy_account.get("server_name", "").strip()
            + "/"
            + "HPD_IncidentOutboundEvent"
        )
        content = remedy_is.getIncidents(wsdl_url=wsdl, args=args)
        return content, wsdl

    @staticmethod
    def _build_error_response(response, code, error_msg):
        response.append("code", code)
        response.append("message", error_msg)

    @log_enter_exit
    def handleList(self, conf_info):
        resp = conf_info["IncidentResult"]

        incident_id = self.callerArgs.data.get("incident_number")
        correlation_id = self.callerArgs.data.get("correlation_id")

        incident_id = incident_id[0] if incident_id else ""
        correlation_id = correlation_id[0] if correlation_id else ""

        incident_id = incident_id or ""
        correlation_id = correlation_id or ""

        _LOGGER.info(
            f"Received request with Incident ID = '{incident_id}' , Correlation ID = '{correlation_id}'"
        )

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
            value = incident_id
        else:
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
            value = correlation_id

        self.server_uri = scc.getMgmtUri()
        self.session_key = self.getSessionKey()

        try:
            remedy_account = self._get_remedy_account()
        except Exception as e:
            _LOGGER.error("Failed to get remedy account, reason=%s" % str(e))
            self._build_error_response(
                resp,
                400,
                "Failed to get details for the remedy account. See 'splunk_ta_remedy_incident.log' logs for more details",
            )
            return
        try:
            response_as_json, url = self._retrieve_incident(
                remedy_account, search_by=search_by, value=value
            )
            incident_number_list = [
                r.get("IncidentNumber", "") for r in response_as_json
            ]
            url_mode = (
                remedy_account.get("http_scheme").strip()
                + "://"
                + remedy_account.get("server_url", "").strip(" /")
                + "/arsys/forms/"
                + remedy_account.get("server_name", "").strip()
                + "/SHR:LandingConsole/Default Administrator View/?mode=search&F304255500=HPD:Help "
                "Desk&F1000000076=FormOpenNoAppList&F303647600=SearchTicketWithQual&F304255610"
                "='1000000161'=\"{}\""
            )
            incident_url_list = [
                url_mode.format(incnum) for incnum in incident_number_list
            ]
            response_as_str = json.dumps(response_as_json)
            _LOGGER.info(
                "Fetched incident content %s from url %s" % (response_as_json, url)
            )

            resp.append("incident_detail_list", response_as_str)
            resp.append("incident_number_list", incident_number_list)
            resp.append("incident_url_list", incident_url_list)
        except Exception as e:
            _LOGGER.error(
                f"Failed to fetch incident for {search_by} = {value}, reason={str(e)}"
            )
            self._build_error_response(resp, 404, "Record not found")


@log_enter_exit
def main():
    splunk.admin.init(RemedyIncidentHandler, splunk.admin.CONTEXT_NONE)


if __name__ == "__main__":
    main()
