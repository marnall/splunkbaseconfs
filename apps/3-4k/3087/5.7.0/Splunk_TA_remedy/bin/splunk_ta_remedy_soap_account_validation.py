#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import ssl
import traceback

import remedy_consts as c
import splunk.admin as admin
import splunk.clilib.cli_common as scc
from logger_manager import get_logger
from remedy_config import RemedyConfig
from remedy_connection_helper import get_suds_client
from solnlib import utils
from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunktaucclib.splunk_aoblib.setup_util import Setup_Util

_LOGGER = get_logger("soap_account_validation")


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class SoapAccountValidation(Validator):
    def __init__(self, *args, **kwargs):
        super(SoapAccountValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        _LOGGER.info("Verifying the credentials entered for the BMC Remedy Server")

        try:
            session_key_obj = GetSessionKey()
            session_key = session_key_obj.session_key

            try:
                splunk_uri = scc.getMgmtUri()
            except Exception as ex:
                _LOGGER.error(
                    "Internal error occured: Failed to get the splunk_uri: %s", str(ex)
                )
                raise

            remedy_conf = RemedyConfig(splunk_uri, session_key)
            remedy_account = remedy_conf.get_stanzas().get(c.REMEDY_ACCOUNT)

            # Passing the values received from UI in dictionary
            for k in data:
                remedy_account[k] = data[k]

            # Checking if http_scheme and disable_ssl_certificate_validation are not empty
            if not all(
                (
                    remedy_account.get("http_scheme", "").strip(),
                    remedy_account.get(
                        "disable_ssl_certificate_validation", ""
                    ).strip(),
                )
            ):
                _LOGGER.error(
                    "The Remedy Settings for http_scheme/certificate are not configured correctly. "
                    "Please configure it in splunk_ta_remedy_settings.conf."
                )

            disable_ssl_certificate_validation = utils.is_true(
                remedy_account.get(c.DISABLE_SSL_CERTIFICATE_VALIDATION)
            )
            certificate_path = remedy_account.get(c.CERTIFICATE_PATH)
            setup_util = Setup_Util(splunk_uri, session_key)
            proxy_settings = setup_util.get_proxy_settings()
            http_scheme = remedy_account.get(c.HTTP_SCHEME).strip()

            # Passing empty incident number to the service which provides incident details
            args = {"Incident_Number": ""}
            wsdl = (
                remedy_account.get("http_scheme", "").strip()
                + "://"
                + remedy_account.get("server_url", "").strip(" /")
                + "/arsys/WSDL/public/"
                + remedy_account.get("server_name", "").strip()
                + "/"
                + "HPD_IncidentInterface_WS"
            )

            try:
                client = get_suds_client(
                    wsdl,
                    remedy_account.get("user", ""),
                    remedy_account.get("password", ""),
                    http_scheme,
                    disable_ssl_certificate_validation,
                    certificate_path,
                    proxy_settings,
                )
                _ = client.service.HelpDesk_Query_Service(**args)
                return True
            except ssl.SSLError:
                msg = "SSLError occured. Please look into the {} file for more details.".format(
                    "splunk_ta_remedy_soap_account_validation.log"
                )
                self.put_msg(msg, True)
                _LOGGER.error(
                    "SSLError occurred. If you are using self signed certificate "
                    "and your certificate is at /etc/ssl/ca-bundle.crt, "
                    "please refer the troubleshooting section in add-on documentation. Traceback = {}".format(
                        traceback.format_exc()
                    )
                )
                return False
            except Exception as e:
                # If credentials are correct, then only this response is received
                if "entry does not exist" in str(e).lower():
                    _LOGGER.debug(traceback.format_exc())
                    return True
                elif "authentication failed" in str(e).lower():
                    msg = "Failed to verify username and password. Reason: Authentication failed"
                    _LOGGER.error(
                        "Failure occurred while verifying username and password. Reason: Authentication failed"
                    )
                    _LOGGER.debug(traceback.format_exc())
                    self.put_msg(msg, True)
                    return False
                else:
                    msg = "Unable to reach server at {}. Check configurations and network settings.".format(
                        wsdl
                    )
                    _LOGGER.error(
                        "Unable to reach Remedy Server at {0}. The reason for failure is={1}".format(
                            wsdl, traceback.format_exc()
                        )
                    )
                    self.put_msg(msg, True)
                    return False

        except Exception:
            msg = "Internal Error Occured. Check logs for details."
            _LOGGER.error(
                "Internal error occured. The Reason for error is=%s",
                traceback.format_exc(),
            )
            self.put_msg(msg, True)
            return False
