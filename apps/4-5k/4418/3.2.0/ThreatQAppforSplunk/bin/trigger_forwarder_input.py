"""This module contain class and method related to updating the finding state."""
import sys
import os
import requests
import base64
import traceback
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..')))
import logger_manager as log
import json
from six.moves.urllib.parse import quote
from splunk.persistconn.application import PersistentServerConnectionApplication  # noqa: E402
import threatq_utils as utility
from solnlib.utils import is_true
from threatq_const import VERIFY_SSL_FORWARDER
logger = log.setup_logging("ta_threatquotient_add_on_trigger_forwarder_input")
APP_NAME = "ThreatQAppforSplunk"


class InvokeForwarderInput(PersistentServerConnectionApplication):
    """Invoke Forwarder Input Handler."""

    def __init__(self, _command_line, _command_arg):
        """Initialize object with given parameters."""
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a synchronous from splunkd.
    def handle(self, in_string):
        """
        After user clicks on Cancel Run button, Called for a simple synchronous request.

        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """
        
        try:
            logger.info("starting_script | Starting the script to invoke the input on the Forwarder machine.")
            req_data = json.loads(in_string)
            session = dict(req_data.get("session"))
            session_key = session.get("authtoken")
            form_data = dict(req_data).get("form")
            admin_session_key = req_data.get('system_authtoken', None)

            logger.debug("forwarder_details | Fetching Forwarder details as saved in Configuration page.")
            settings_conf_file = utility.get_conf_file(admin_session_key, APP_NAME, "threatquotient_app_settings")
            splunk_forwarder_username = settings_conf_file.get("splunk_forwarder_config").get("splunk_forwarder_username")
            splunk_forwarder_password = settings_conf_file.get("splunk_forwarder_config").get('splunk_forwarder_password')
            splunk_forwarder_url = settings_conf_file.get("splunk_forwarder_config").get("splunk_forwarder_url")
            splunk_forwarder_port = settings_conf_file.get("splunk_forwarder_config").get("splunk_forwarder_port")
            forwarder_proxy_enabled = settings_conf_file.get("splunk_forwarder_config").get("forwarder_proxy_enabled")
            forwarder_proxy_type = settings_conf_file.get("splunk_forwarder_config").get("forwarder_proxy_type")
            forwarder_proxy_url = settings_conf_file.get("splunk_forwarder_config").get("forwarder_proxy_url")
            forwarder_proxy_port = settings_conf_file.get("splunk_forwarder_config").get("forwarder_proxy_port")
            forwarder_proxy_username = settings_conf_file.get("splunk_forwarder_config").get("forwarder_proxy_username")
            forwarder_proxy_password = settings_conf_file.get("splunk_forwarder_config").get("forwarder_proxy_password")
            logger.debug("Fetched_details | Successfully fetched Forwarder details.")

            if not any([
                splunk_forwarder_username,
                splunk_forwarder_password,
                splunk_forwarder_url,
                splunk_forwarder_port
            ]):
                return {'payload': "failure_no_values_provided", 'status': 500}
 
            proxy_data = None
            if all(
                [
                    is_true(forwarder_proxy_enabled),
                    forwarder_proxy_url,
                    forwarder_proxy_type,
                ]
            ):
                logger.debug("proxy_enabled | Proxy is Enabled. Fetching Proxy details as well.")
                http_uri = forwarder_proxy_url
                if forwarder_proxy_port:
                    http_uri = "{}:{}".format(http_uri, forwarder_proxy_port)
                if forwarder_proxy_username and forwarder_proxy_password:
                    http_uri = "{}:{}@{}".format(
                        quote(forwarder_proxy_username, safe=""),
                        quote(forwarder_proxy_password, safe=""),
                        http_uri,
                    )

                http_uri = "{}://{}".format(forwarder_proxy_type, http_uri)
                proxy_data = {"http": http_uri, "https": http_uri}
                logger.debug("proxy_details_fetched | Proxy details fetched successfully.")

            logger.debug("input_info | Fetching input details for the input saved on the Forwarder machine.")
            auth_header = "Basic " + base64.b64encode(f"{splunk_forwarder_username}:{splunk_forwarder_password}".encode()).decode()
            if splunk_forwarder_url in ['127.0.0.1', 'localhost']:
                headers_for_input = {
                    "Content-type": "application/json",
                    "Accept": "text/plain",
                    "Authorization": "Splunk {}".format(admin_session_key)
                }
            else:
                headers_for_input = {
                    "Content-type": "application/json",
                    "Authorization": auth_header
                }
            input_url = "".join(
                [
                    "https://",
                    splunk_forwarder_url,
                    ":",
                    splunk_forwarder_port,
                    "/servicesNS/nobody/TA-threatquotient-add-on",
                    "/data/inputs/threatq_indicators/"
                ]
            )
            params = {"output_mode": "json"}
            response = requests.get(input_url, verify=is_true(VERIFY_SSL_FORWARDER), headers=headers_for_input, params=params, proxies=proxy_data)
            resp = response.json()
            if not resp.get("entry"):
                logger.error("input_fetch_error | Could not fetch the input details. Please make sure to have the input configured on the 'ThreatQuotient Add-on for Splunk' app on the Forwarder machine.")
                return {'payload': "failure_no_input_found", 'status': 500}
            input_name = resp.get("entry")[0].get("name", None)
            logger.debug("input_fetched | Successfully fetched the input. Input name: {}.".format(input_name))

            logger.debug("disabling_input | Disabling the input.")
            if splunk_forwarder_url in ['127.0.0.1', 'localhost']:
                request_headers = {
                    "Content-type": "application/json",
                    "Accept": "text/plain",
                    "Authorization": "Splunk {}".format(admin_session_key)
                }
            else:
                request_headers = {
                    "Authorization": auth_header,
                    "Content-Type": "application/x-www-form-urlencoded",
                }
            splunk_disable_enable_url = "".join(
                [
                    "https://",
                    splunk_forwarder_url,
                    ":",
                    splunk_forwarder_port,
                    "/servicesNS/nobody/TA-threatquotient-add-on",
                    "/data/inputs/threatq_indicators/{}/{}"
                ]
            )
            splunk_disable_url = splunk_disable_enable_url.format(input_name, "disable")
            requests.post(
                splunk_disable_url,
                headers=request_headers,
                verify=is_true(VERIFY_SSL_FORWARDER),
                proxies=proxy_data
            )
            logger.debug("enabling_input | Enabling the input.")
            splunk_enable_url = splunk_disable_enable_url.format(input_name, "enable")
            requests.post(
                splunk_enable_url,
                headers=request_headers,
                verify=is_true(VERIFY_SSL_FORWARDER),
                proxies=proxy_data
            )
            logger.debug("disable_enable_success | Successfully disabled and enabled the input.")
            logger.info("script_finished | Successfully invoked the input on the Forwarder machine.")
            logger.info("exiting | Exiting the script.")
            return {'payload': "Success", 'status': 200}
        except Exception as e:
            logger.error("Error occurred while invoking the input on Forwarder."
                         " Error: {}".format(traceback.format_exc()))
            return {'payload': str(e), 'status': 500}

    def handleStream(self, handle, in_string):
        """For future use."""
        raise NotImplementedError("PersistentServerConnectionApplication.handleStream")

    def done(self):
        """Virtual method which can be optionally overridden to receive a callback after the request completes."""
        pass
