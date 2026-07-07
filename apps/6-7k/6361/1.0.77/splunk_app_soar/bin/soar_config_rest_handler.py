# Copyright (C) 2023-2024 Splunk Inc. All Rights Reserved.

import json
import logging
import os
import sys
from traceback import format_exc
from urllib.parse import quote, unquote, urlparse, ParseResult

import requests
import splunk
import splunk.rest
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.persistconn.application import PersistentServerConnectionApplication

APP_HOME_DIR = make_splunkhome_path(["etc", "apps", "splunk_app_soar"])
sys.path.insert(0, os.path.join(APP_HOME_DIR, "bin"))

from soar_utils import (
    setup_logging,
    make_request_and_handle_redirect_helper,
    RedirectDetectedException,
)
from soar_imports import (
    APP_NAME,
    SOAR_CONF_PROPS,
    GLOBAL_ACCOUNT,
    PHANTOM_VERIFY_SERVER_URL_USER_SETTINGS,
    INPUT_ENDPOINT,
    REDIRECT_DETECTED_MSG,
    SERVER_MUST_BE_HTTPS_MSG,
    INVALID_SERVER_URL,
    INVALID_PROXY_URL,
    FAILED_TO_VERIFY_SERVER_MSG,
)

POST_REQUIRED_FIELDS = ["name", "server", "password"]  # user is optional

CERT_FILE_LOCATION_DEFAULT = os.path.join(
    os.environ['SPLUNK_HOME'], 'etc', 'apps', APP_NAME, 'default', 'cert_bundle.pem'
)
CERT_FILE_LOCATION_LOCAL = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', APP_NAME, 'local', 'cert_bundle.pem')


class SoarConfigRESTHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        self.log = setup_logging("soar_configuration.log", "soar_server")
        self.session_key = None
        self.payload = None
        self.path_info = None
        self.config_id = None
        self.custom_name = None
        self.server = None
        self.username = None
        self.auth_token = None
        self.proxy = None
        self.verify_certs = None
        self.input_id = None
        self.allow_redirects = False
        PersistentServerConnectionApplication.__init__(self)

    def _set_proxy(self, proxy=None):
        if not proxy:
            self.proxy = None
        if isinstance(proxy, dict):
            for key, value in proxy.items():
                self.proxy = {key: value}
            else:
                self.proxy = {"https": proxy}
        if isinstance(proxy, str):
            self.proxy = {"https": proxy}

    def _is_proxy_url_valid(self):
        # Proxy is optional
        if not self.proxy:
            return True
        if not self.proxy.get('https'):
            return True
        # Question marks are not allowed in proxy URL for security
        # reasons . More details in VULN-15009 ticket
        return all(self._is_server_url_valid(proxy_url.lower()) for proxy_url in self.proxy.values())

    def get_forms_args_as_dict(self, form_args):
        if type(form_args) == str:
            return json.loads(form_args)
        return form_args

    def update_log_level(self, level):
        if level == 'DEBUG':
            self.log.setLevel(logging.DEBUG)
        elif level == 'INFO':
            self.log.setLevel(logging.INFO)
        elif level == 'WARNING':
            self.log.setLevel(logging.WARNING)
        elif level == 'ERROR':
            self.log.setLevel(logging.ERROR)
        elif level == 'CRITICAL':
            self.log.setLevel(logging.CRITICAL)

    def handle(self, args):
        request = json.loads(args)
        method = request["method"]
        payload = request.get("payload", {})
        self.path_info = request.get("path_info")
        self.payload = self.get_forms_args_as_dict(payload)
        self._set_proxy(self.payload.get("soar_proxy"))
        self.config_id = self.payload.get("name", "")
        self.custom_name = self.payload.get("custom_name")
        self.server = self.payload.get("server")
        self.username = self.payload.get("username", "")
        self.auth_token = unquote(unquote(self.payload.get("password", "")))

        self.input_id = self.payload.get("inputs", {}).get("name", "")

        self.session_key = request["session"]["authtoken"]

        # Retrieve log level from soar.conf
        try:
            path = quote(f"{SOAR_CONF_PROPS}/log_level/value")
            success, status, content = self.splunk_get(path)
            log_level = str(content, 'utf-8')
            self.log.info(f"Log level: {log_level}")

            self.update_log_level(log_level)
        except Exception:
            self.log.info(f"Log level: INFO (default)")
            # No custom log level set

        # Retrieve verify_certs flag from soar.conf
        path = quote(f"{SOAR_CONF_PROPS}/verify_certs/value")
        success, status, content = self.splunk_get(path)
        self.verify_certs = bool(content) if success else False

        if self.verify_certs and os.path.isfile(CERT_FILE_LOCATION_LOCAL):
            self.verify_certs = CERT_FILE_LOCATION_LOCAL
        elif self.verify_certs and os.path.isfile(CERT_FILE_LOCATION_DEFAULT):
            self.verify_certs = CERT_FILE_LOCATION_DEFAULT

        if method == "POST":
            contents = self.handle_POST()
        elif method == "GET":
            contents = self.handle_GET()
        elif method == "DELETE":
            contents = self.handle_DELETE()
        else:
            contents = {"error": "Invalid or missing arguments", "status": 404}

        status = contents.get("status")
        return json.dumps({"payload": contents, "status": status})

    """
    @param username (optional)
    @param password: ph-auth-token
    @param server: SOAR server
    @param custom_name (optional)
    @param name: config id
    @param proxy (optional)
    """

    def handle_POST(self):
        self.log.info("POST server config")
        # Make sure all required params present
        payload_keys = self.payload.keys()

        if any(required_field not in payload_keys for required_field in POST_REQUIRED_FIELDS):
            return {"message": "Not all required fields present in request", "status": 400}

        if self.path_info != "test_connectivity" and not self.payload.get("server_validated"):
            return {"message": "Server must be validated before saving", "status": 400}

        # Verify server connection
        valid, message = self.verify_server()
        self.log.info(f"Verify SOAR server: {valid}, message: {message}")
        if valid is True:
            self.username = message.get("username")
            roles = message.get("roles")
            if "Observer" not in roles:
                self.log.error("Observer role missing from roles")
                return {"error": "User needs 'observer' role in SOAR.", "status": 200}
            if self.custom_name in [None, ""]:
                self.custom_name = f"{self.username} ({self.server})"
        else:
            default_error_message = "Invalid server information provided."

            if REDIRECT_DETECTED_MSG in message:
                return {"error": f"Failed to communicate with server: {message}", "status": 200}
            if INVALID_SERVER_URL in message:
                return {"error": f"{message}. Please update your server config.", "status": 200}
            if INVALID_PROXY_URL in message:
                return {"error": f"{message}. Please update your server config.", "status": 200}
            if FAILED_TO_VERIFY_SERVER_MSG in message:
                return {
                    "error": f'{message}. Note: Make sure automation user has "observer" role.',
                    "status": 200,
                }
            if SERVER_MUST_BE_HTTPS_MSG in message:
                return {
                    "error": f"{default_error_message} SOAR only supports https, please update your server config.",
                    "status": 200,
                }

            return {
                "error": f'{default_error_message} Note: Make sure automation user has "observer" role.',
                "status": 200,
            }

        if self.path_info == "test_connectivity":
            return {"message": "Test connectivity successful. Connection is valid.", "status_code": 200, "status": 200}

        # Add to soar.conf and passwords.conf
        # Check if this is a new or existing stanza
        global_account_path = quote(f"{GLOBAL_ACCOUNT}/{self.config_id}")
        config = self.format_server_config_value()

        stanza_exists_soar_conf = False
        try:
            stanza_exists_soar_conf = self.validate_conf_stanza(global_account_path)
        except Exception:
            pass

        # Post to splunk_app_soar_account.conf
        # Post proxy settings to
        if stanza_exists_soar_conf is True:
            self.log.info(f"Updating [{self.config_id}] in splunk_app_soar_account.conf")
            success_ga_conf, status_ga_conf, content_ga_conf = self.splunk_post(
                global_account_path, config
            )
            if success_ga_conf is False:
                return {"error": content_ga_conf, "status": status_ga_conf}
        else:
            self.log.info(f"Creating [{self.config_id}] in splunk_app_soar_account.conf")
            config.update({"name": self.config_id})
            success_ga_conf, status_ga_conf, content_ga_conf = self.splunk_post(
                GLOBAL_ACCOUNT, config
            )
            if success_ga_conf is False:
                return {"error": content_ga_conf, "status": status_ga_conf}

        return {"message": "POST successful", "user": self.username, "custom_name": self.custom_name, "status": 200}

    """
    Append global_account_path to end of URL 
    If an audit input config exists for the given global_account_path (SOAR server),
        the audit input config will also be deleted
    """

    def handle_DELETE(self):
        # Delete from splunk_app_soar_account.conf
        global_account_path = quote(f"{GLOBAL_ACCOUNT}/{self.path_info}")
        success_ga_conf, status_ga_conf, content_ga_conf = self.splunk_delete(global_account_path)
        if success_ga_conf is False:
            # It either didn't exist initially or there is a real issue
            success_ga_conf, status_ga_conf, content_ga_conf = self.splunk_get(global_account_path)
            self.log.info(f"{success_ga_conf}, {status_ga_conf}, {content_ga_conf}")

            return {"error": content_ga_conf, "status": status_ga_conf}

        # # Delete from inputs.conf
        if self.input_id:
            inputs_conf_path = f"{INPUT_ENDPOINT}/{self.input_id}"
            success_inputs_conf, status_inputs_conf, content_inputs_conf = self.splunk_delete(
                inputs_conf_path
            )
            if status_inputs_conf < 200 or status_inputs_conf > 300:
                return {"error": content_inputs_conf, "status": status_inputs_conf}

        return {"message": "DELETE successful", "status": 200}

    def format_server_config_value(self):
        config = {
            "custom_name": self.custom_name,
            "server": self.server,
            "username": self.username,
            "soar_proxy": self.payload.get("soar_proxy"),
            "password": self.auth_token,
        }
        return config

    def validate_conf_stanza(self, path):
        success, status, content = self.splunk_get(path)
        return success

    def _fallback_verify_server(self, username):
        """
        DEPRECATED
        Fallback to the previous server verification (username, roles pull).
        This is only for cases, when Splunk SOAR wasn't updated to 6.2.2 yet.

        Uses old method of checking username and roles using the ph_user endpoint
        listing with filtering by using the auth key (which is unsafe and should be
        stopped ASAP).

        Keep in mind that this method doesn't validate server and proxy URLs for
        security vulnerabilities so make sure that this validation is performed
        before calling this method.
        """
        self.log.warning(
            "Deprecation Warning: "
            "You are still using old method of Splunk SOAR server verification. "
            "A new method of verification will be available starting with Splunk SOAR 6.2.2. "
            "Make sure to update your Splunk SOAR server."
        )

        # unsafe to use and the main reason for removal of this implementation
        PHANTOM_VERIFY_SERVER_URL_ASSET = "{server}/rest/asset?_filter_token__key='{auth_token}'"
        PHANTOM_VERIFY_SERVER_URL_PH_USER = (
            "{server}/rest/ph_user?include_automation=true&_filter_username='{username}'"
        )

        auth_headers = {"ph-auth-token": self.auth_token}
        response_json = None

        try:
            base_uri = PHANTOM_VERIFY_SERVER_URL_PH_USER.format(
                server=self.server, username=username
            )
            response = make_request_and_handle_redirect_helper(
                helper=self,
                http_method="GET",
                url=base_uri,
                auth_headers=auth_headers,
            )
        except RedirectDetectedException:
            return False, REDIRECT_DETECTED_MSG
        except requests.exceptions.ConnectionError as e:
            url_encoded_token = (
                self.auth_token.replace("=", "%3D").replace("+", "%2B").replace("&", "%26")
            )
            redacted_exception = str(e).replace(url_encoded_token, "<token>")
            self.log.error(FAILED_TO_VERIFY_SERVER_MSG)
            self.log.debug(
                f"A ConnectionError has occurred when trying to verify SOAR "
                f"server: {redacted_exception}"
            )
            return False, FAILED_TO_VERIFY_SERVER_MSG
        except Exception as e:
            self.log.error(FAILED_TO_VERIFY_SERVER_MSG)
            self.log.debug(
                f"An Exception has occurred when trying to verify SOAR "
                f"server: {e}"
            )
            return False, FAILED_TO_VERIFY_SERVER_MSG
        try:
            if response.status_code != 200:
                try:
                    message = response.json().get("message", FAILED_TO_VERIFY_SERVER_MSG)
                except Exception:
                    message = FAILED_TO_VERIFY_SERVER_MSG
                self.log.debug(f"Status Code: {response.status_code}. Error: {message}")
                return False, FAILED_TO_VERIFY_SERVER_MSG

            response_json = response.json()
            if int(response_json["count"]) < 1:
                raise Exception("Token not found")

        except Exception:
            base_uri = PHANTOM_VERIFY_SERVER_URL_ASSET.format(
                server=self.server, auth_token=quote(self.auth_token)
            )
            try:
                response = make_request_and_handle_redirect_helper(
                    helper=self,
                    http_method="GET",
                    url=base_uri,
                    auth_headers=auth_headers,
                )
            except RedirectDetectedException:
                return False, REDIRECT_DETECTED_MSG

            if response.status_code != 200:
                self.log.debug(f"Status code for asset URL: {response.status_code}")
                return False, FAILED_TO_VERIFY_SERVER_MSG
            try:
                response_json = response.json()
                self.log.debug(f"Response for asset URL: {response_json}")
                if int(response_json["count"]) < 1:
                    return False, FAILED_TO_VERIFY_SERVER_MSG
            except Exception as ex:
                self.log.debug(f"Cannot parse response for asset URL: {ex}")
                return False, FAILED_TO_VERIFY_SERVER_MSG

        return_json = {
            "username": username,
            "roles": response_json.get("data", [])[0].get("roles"),
        }
        return True, return_json

    def verify_server(self):
        self.log.info("Verifying server...")
        auth_headers = {"ph-auth-token": self.auth_token}

        # Validating server and proxy URLs:
        if not self.server.lower().startswith('https://'):
            return False, SERVER_MUST_BE_HTTPS_MSG
        if not self._is_server_url_valid(self.server.lower()):
            return False, INVALID_SERVER_URL
        if not self._is_proxy_url_valid():
            return False, INVALID_PROXY_URL

        base_uri = PHANTOM_VERIFY_SERVER_URL_USER_SETTINGS.format(
            server=self.server
        )
        try:
            response = make_request_and_handle_redirect_helper(
                helper=self,
                http_method="GET",
                url=base_uri,
                auth_headers=auth_headers,
            )
        except RedirectDetectedException:
            return False, REDIRECT_DETECTED_MSG
        except Exception as e:
            self.log.error(FAILED_TO_VERIFY_SERVER_MSG)
            self.log.debug(
                f"An exception has occurred when trying to verify SOAR "
                f"server: {e}"
            )
            return False, FAILED_TO_VERIFY_SERVER_MSG

        try:
            response_json = response.json()
            if response.status_code != 200:
                message = response_json.get("message", FAILED_TO_VERIFY_SERVER_MSG)
                self.log.debug(f"Status Code: {response.status_code}. Error: {message}")
                return False, FAILED_TO_VERIFY_SERVER_MSG
        except json.JSONDecodeError as e:  # error in parsing JSON data from response
            self.log.debug(f"Status Code: {response.status_code}. Error: {e}")
            return False, FAILED_TO_VERIFY_SERVER_MSG

        username = response_json.get("username")
        roles = response_json.get("roles")

        # Fallback to the deprecated method of roles checking
        if roles is None:
            self.log.debug(
                "'roles' absent in response from the SOAR server. Falling "
                "back to the deprecated method of verifying server"
            )
            return self._fallback_verify_server(username)

        return True, {
            "username": username,
            "roles": roles,
        }

    def _is_server_url_valid(self, url: str) -> bool:
        """
        Validates server URL. The URL must consist only of 'https://IP:PORT'.
        Any other element like '?', ';', '/' or '#' creates a security
        vulnerability as it allows the user to manipulate server path.
        More details in VULN-15009 ticket.
        """
        parsed_url: ParseResult = urlparse(url)
        # Valid URL can't have 'path', 'params', 'query' and 'fragment'
        # components, so it must consist only of 'scheme' and 'netloc'
        allowed_url: str = f"{parsed_url.scheme}://{parsed_url.netloc}"
        return url == allowed_url

    def splunk_post(self, path, params=None):
        if params is None:
            params = {}
        success, status, content = self.splunk_rest(path, params, method="POST")
        content = json.loads(content)
        self.log.debug(f"success {success}, status {status} content {content}")
        return success, status, content

    def splunk_delete(self, path, params=None):
        if params is None:
            params = {}
        success, status, content = self.splunk_rest(path, params, method="DELETE")
        self.log.debug(f"{success}, {status}, {content}")
        content = json.loads(content)
        return success, status, content

    def splunk_get(self, path, params=None):
        if params is None:
            params = {}
        success, status, content = self.splunk_rest(path, params, method="GET")
        try:
            content = json.loads(content)
        except Exception:
            pass
        return success, status, content

    def splunk_rest(self, path, payload, method):
        success = False
        try:
            payload["output_mode"] = "json"
            args = {"method": method, "sessionKey": self.session_key}
            if method == "POST" or method == "DELETE":
                args["postargs"] = payload
            else:
                args["getargs"] = payload
            response, content = splunk.rest.simpleRequest(path, **args)
            success = 200 <= int(response.get("status")) < 300
            return success, int(response.status), content
        except splunk.AuthorizationFailed as e:
            self.log.error(format_exc())
            message = f"Authorization Error while talking to Splunk [{method}][{path}]: {e}"
            return False, 404, message
        except Exception as e:
            message = f"Exception: [{method}][{path}]: {e}"
            return False, 404, message
