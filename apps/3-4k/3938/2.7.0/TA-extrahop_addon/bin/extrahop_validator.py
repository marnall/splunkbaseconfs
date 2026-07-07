import requests
import base64
from xml.dom import minidom
import os

import extrahop_common as common
from splunk.clilib import cli_common as cli
from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunk_aoblib.rest_migration import ConfigMigrationHandler


class SessionKeyProvider(ConfigMigrationHandler):
    """Provides Splunk session key to custom validator."""

    def __init__(self):
        """Save session key in class instance."""
        self.session_key = self.getSessionKey()


class ValidateFields(Validator):
    """Validator class to empty fields corresponding to dropdown value."""

    def validate(self, value, data):
        """Validate method to perform action."""
        try:
            if data['instance_type'] == "on_prem_instance":
                if not data.get("api_key"):
                    msg = "Instance Type On Prem Instance is selected but API Key is not provided!"
                    raise Exception(msg)
                data['client_id'] = ''
                data['client_secret'] = ''

            else:
                if not data.get("client_id"):
                    msg = "Instance Type Cloud Instance is selected but Client ID is not provided!"
                    raise Exception(msg)
                elif not data.get("client_secret"):
                    msg = "Instance Type Cloud Instance is selected but Client Secret is not provided!"
                    raise Exception(msg)
                data['api_key'] = ''
            return True
        except Exception as exc:
            self.put_msg(exc)
            return False

class ValidateInterval(Validator):
    """Validator class to validate Interval value."""

    def validate(self, value, data):
        """Validate method to perform action."""
        CYCLE_SIZES = {"30sec": 30, "5min": 300, "1hr": 3600}
        # Valida interval value
        try:
            interval = int(data["interval"])
            assert interval > 0
        except ValueError:
            msg = "Interval should be integer value."
            self.put_msg(msg)
            return False
        except AssertionError:
            msg = "Interval should be greater than 0."
            self.put_msg(msg)
            return False

        try:
            cyclesize = data["cyclesize"]
            if interval < CYCLE_SIZES[cyclesize] or interval % CYCLE_SIZES[cyclesize] != 0:
                msg = "Interval should be a multiple of the Metric Cycle Length."
                self.put_msg(msg)
                return False
            else:
                return True
        except Exception as e:
            msg = "Something went wrong while validating Interval field. Error: {}".format(e)
            self.put_msg(msg)
            return False

class ValidateAccount(Validator):
    """Validator class to empty fields corresponding to dropdown value."""

    def validate(self, value, data):
        """Validate method to perform action."""
        # Get Splunk Session Key
        splunk_session_key = SessionKeyProvider().session_key

        # Get proxy settings information
        try:
            proxy_settings = common.get_proxy_uri(splunk_session_key)
        except Exception as e:
            msg = "Unknown error occurred while reading proxy details: {}".format(e)
            self.put_msg(msg)
            return False

        hostname = data['hostname']
        auth_req_url = f"https://{hostname}/api/v1/appliances/0"
        auth_url = f"https://{hostname}/oauth2/token"
        verify_certs = cli.getConfStanza('ta_extrahop_addon_settings', 'additional_parameters').get(
            'validate_ssl_certificates', '1')
        verify_certs = False if verify_certs in ["False", "0", "false"] else True
        try:
            if data['instance_type'] == "on_prem_instance":
                headers = {
                    "Accept": "application/json",
                    "Authorization": "ExtraHop apikey={}".format(data['api_key']),
                    "ExtraHop-Integration": "Splunk-{}-TA-ExtraHop-{}".format(common.get_splunk_version(splunk_session_key), common.get_app_version(splunk_session_key))
                }
                resp = requests.get(auth_req_url, headers=headers, proxies=proxy_settings, verify=verify_certs)
                resp.raise_for_status()
                return True
            else:
                # Generate API Token
                API_token = base64.b64encode("{}:{}".format(data['client_id'], data['client_secret']).encode()).decode()

                payload = 'grant_type=client_credentials'
                headers = {
                    'Authorization': 'Basic {}'.format(API_token),
                    'Content-Type': 'application/x-www-form-urlencoded',
                    "ExtraHop-Integration": "Splunk-{}-TA-ExtraHop-{}".format(common.get_splunk_version(splunk_session_key), common.get_app_version(splunk_session_key))
                }

                # Get Access Token
                resp = requests.request(
                    "POST", auth_url, headers=headers, data=payload, proxies=proxy_settings, verify=verify_certs)
                resp.raise_for_status()
                access_token = resp.json().get('access_token')
                headers = {
                    "Accept": "application/json",
                    "Authorization": "Bearer {}".format(access_token),
                    "ExtraHop-Integration": "Splunk-{}-TA-ExtraHop-{}".format(common.get_splunk_version(splunk_session_key), common.get_app_version(splunk_session_key))
                }
                resp = requests.get(auth_req_url, headers=headers, proxies=proxy_settings, verify=verify_certs)
                resp.raise_for_status()
                return True
        except requests.exceptions.SSLError as e:
            self.put_msg("SSL Certificate verification failed.")
            return False
        except Exception as e:
            if "resp" in locals() and resp.status_code == 400:
                msg = "Invalid Client ID or Client Secret. Please enter the valid credentials."
            elif "resp" in locals() and resp.status_code == 401:
                msg = "Invalid API Key. Please validate the provided details."
            elif "resp" in locals() and resp.status_code == 500:
                msg = "Internal server error. Cannot verify Extrahop instance."
            else:
                msg = "Unable to request Extrahop instance. "\
                      "Validate the Hostname, Proxy configurations or check the network connectivity."

            self.put_msg(msg)
            return False


class ValidateSplunkManagement(Validator):
    """Validator class to validate Splunk Management credentials."""

    def validate(self, value, data):
        """Validate method to perform action."""
        # Get Splunk Session Key
        splunk_session_key = SessionKeyProvider().session_key

        splunk_mgmt_env_type = data.get("splunk_mgmt_env_type")
        splunk_mgmt_host = data.get("splunk_mgmt_host")
        splunk_mgmt_port = data.get("splunk_mgmt_port")
        splunk_mgmt_username = data.get("splunk_mgmt_username")
        splunk_mgmt_password = data.get("splunk_mgmt_password")

        if splunk_mgmt_env_type == "local_instance":
            try:
                splunk_mgmt_session = requests.Session()
                splunk_mgmt_auth_response = splunk_mgmt_session.get(
                    f'https://localhost:{splunk_mgmt_port}',
                    verify=False    # ssl verification is disabled
                )
                splunk_mgmt_auth_response.raise_for_status()

                return True

            except requests.exceptions.ProxyError as proxyerror:
                self.put_msg(
                    "Proxy error occurred while authenticating Splunk Management. "
                    "Please verify proxy settings and Splunk Management host/port. Error: {}"
                    .format(proxyerror)
                )
                return False

            except requests.exceptions.ConnectionError:
                self.put_msg(
                    "Connection error occurred while authenticating Splunk Management. "
                    "Please enter valid Splunk Management Port."
                )
                return False

            except Exception as error:
                if "splunk_mgmt_auth_response" in locals() and splunk_mgmt_auth_response.status_code == 404:
                    err_msg = "Invalid token provided."
                elif "splunk_mgmt_auth_response" in locals() and splunk_mgmt_auth_response.status_code == 429:
                    err_msg = "Splunk Management server rate limit has been exceeded. Please try again after sometime."
                elif "splunk_mgmt_auth_response" in locals() and splunk_mgmt_auth_response.status_code in range(500, 601):
                    err_msg = "Splunk Management server internal error. Please try again later."
                else:
                    err_msg = "Error occurred while authenticating Splunk Management. : {}".format(error)

                self.put_msg(err_msg)
                return False

        # Setup Proxy
        try:
            proxies = common.get_proxy_uri(splunk_session_key)
            if proxies:
                # Splunk's local network call throws error if NO_PROXY is not set.
                # This is a list of hostnames, which should not go through proxy.
                os.environ["no_proxy"] = "localhost,127.0.0.1,0.0.0.0,localaddress"
                os.environ["NO_PROXY"] = "localhost,127.0.0.1,0.0.0.0,localaddress"

                os.environ["http_proxy"] = proxies.get('http')
                os.environ["HTTP_PROXY"] = proxies.get('http')

                os.environ["https_proxy"] = proxies.get('https')
                os.environ["HTTPS_PROXY"] = proxies.get('https')
        except Exception as e:
            msg = "Unknown error occurred while reading proxy details: {}".format(e)
            self.put_msg(msg)
            return False

        if not splunk_mgmt_username:
            self.put_msg("Username can not be empty for cluster environment.")
            return False
        if not splunk_mgmt_password:
            self.put_msg("Password can not be empty for cluster environment.")
            return False

        splunk_mgmt_baseurl = "https://" + splunk_mgmt_host + ":" + splunk_mgmt_port

        # validate Splunk Management credentials
        try:
            splunk_mgmt_session = requests.Session()
            splunk_mgmt_auth_response = splunk_mgmt_session.post(
                splunk_mgmt_baseurl + '/services/auth/login',
                data={'username': splunk_mgmt_username, 'password': splunk_mgmt_password},
                verify=False    # ssl verification is disabled
            )
            splunk_mgmt_auth_response.raise_for_status()

            minidom.parseString(
                splunk_mgmt_auth_response.text
            ).getElementsByTagName('sessionKey')[0].childNodes[0].nodeValue
            # Splunk Management authentication successful
            return True

        except requests.exceptions.ProxyError as proxyerror:
            self.put_msg(
                "Proxy error occurred while authenticating Splunk Management. "
                "Please verify proxy settings and Splunk Management host/port. Error: {}"
                .format(proxyerror)
            )
            return False

        except Exception as error:
            if "splunk_mgmt_auth_response" in locals() and splunk_mgmt_auth_response.status_code == 401:
                err_msg = "Invalid credentials. Please verify Splunk Management credentials."
            elif "splunk_mgmt_auth_response" in locals() and splunk_mgmt_auth_response.status_code == 429:
                err_msg = "Splunk Management server rate limit has been exceeded. Please try again after sometime."
            elif "splunk_mgmt_auth_response" in locals() and splunk_mgmt_auth_response.status_code in range(500, 601):
                err_msg = "Splunk Management server internal error. Please try again later."
            else:
                err_msg = "Error occurred while authenticating Splunk Management: {}".format(error)

            self.put_msg(err_msg)
            return False
