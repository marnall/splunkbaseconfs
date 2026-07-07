import sys
import os
import json
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..")))
import import_declare_test  # noqa 401, E402
import requests  # noqa E402
import urllib.parse  # noqa E402
from splunk.persistconn.application import (  # noqa E402
    PersistentServerConnectionApplication,
)  # noqa E402
from log_helper import setup_logging  # noqa E402
from thousandeyes_constant import (  # noqa E402
    THOUSANDEYES_BASE_URL,
    THOUSANDEYES_TOKEN_API_ENDPOINT,
    THOUSANDEYES_CURRENT_USER_ENDPOINT,
    CLIENT_ID,
    GRANT_TYPE,
    REQUEST_TIMEOUT,
)
from thousandeyes_utils import get_proxy_info  # noqa E402


logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0].lower())


class OAuthTokens(PersistentServerConnectionApplication):
    """
    Get the Oauth Authorize data.

    :param PersistentServerConnectionApplication: inhereting PersistentServerConnectionApplication
    """

    def __init__(self, _command_line, _command_arg):
        """
        Initialize Rest handler.

        :param _command_line: command
        :param _command_arg: commandline arguments
        """
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, in_string):
        """
        Get the OAuth device code, user code and verification url.

        :param in_string: request data passed in

        :return: dictionary with Auth tokens.
        """
        logger.info("Generating access tokens.")
        try:
            req_data = json.loads(in_string)
            session_key = req_data.get("system_authtoken", None)
            url = f"{THOUSANDEYES_BASE_URL}{THOUSANDEYES_TOKEN_API_ENDPOINT}"
            device_code = ""
            user_code = ""
            for form_data in req_data.get("form"):
                if "device_code" in form_data:
                    device_code = form_data[1]
                elif "user_code" in form_data:
                    user_code = form_data[1]
            payload = {
                "client_id": CLIENT_ID,
                "device_code": device_code,
                "grant_type": GRANT_TYPE,
            }
            payload = urllib.parse.urlencode(payload)
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            proxy, verify = get_proxy_info(session_key, logger)
            response = requests.post(
                url,
                headers=headers,
                data=payload,
                proxies=proxy,
                verify=verify,
                timeout=REQUEST_TIMEOUT,
            )
            resp = response.json()
            account_tokens = {}
            if response.status_code == 200:
                logger.info(
                    f"Sucessfully generated OAuth tokens for user code : {user_code}."
                )
                account_tokens["access_token"] = resp.get("access_token")
                account_tokens["refresh_token"] = resp.get("refresh_token")
            else:
                raise Exception(resp.get("error_description"))

            url = f"{THOUSANDEYES_BASE_URL}{THOUSANDEYES_CURRENT_USER_ENDPOINT}"
            headers = {"Authorization": f"Bearer {account_tokens.get('access_token')}"}
            payload = {}
            response = requests.get(
                url,
                headers=headers,
                data=payload,
                proxies=proxy,
                verify=verify,
                timeout=REQUEST_TIMEOUT,
            )
            user_email = None
            resp = response.json()
            if response.status_code == 200:
                logger.info(f"Sucessfully obtained email for : {user_code}.")
                user_email = resp.get("email")
            else:
                err_msg = resp.get("errorMessage", None)
                if err_msg is None:
                    err_msg = resp.get("error_description", None)
                if err_msg is None:
                    err_msg = f"Response Status: {response.status_code}. Error Message: {response.text}."
                raise Exception(err_msg)
            account_tokens["email"] = user_email
            return {"payload": account_tokens, "status": 200}
        except requests.exceptions.ProxyError as e:
            logger.error(
                f"Error during token generation : {str(e)}. {traceback.format_exc()}"
            )
            err_msg = "Proxy Error occured, Please verify the configured proxy details."
            return {"payload": f"{err_msg}", "status": 500}
        except requests.exceptions.SSLError as e:
            logger.error(
                f"Error during token generation : {str(e)}. {traceback.format_exc()}"
            )
            err_msg = "SSL Error occured, Please verify the certificate for provided configuration."
            return {"payload": f"{err_msg}", "status": 500}
        except Exception as e:
            logger.error(
                f"Error during token generation : {str(e)} {traceback.format_exc()}"
            )
            return {"payload": f"{e} Please check the logs.", "status": 500}

    def handleStream(self, handle, in_string):
        """For future use."""
        raise NotImplementedError("PersistentServerConnectionApplication.handleStream")

    def done(self):
        """Virtual method to optionally override function to receive a callback after the request completes."""
        pass
