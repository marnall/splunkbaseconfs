import sys
import os
import json
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..")))
import import_declare_test  # noqa F401, E402
import requests  # noqa E402
from splunk.persistconn.application import (  # noqa E402
    PersistentServerConnectionApplication,
)  # noqa E402
from log_helper import setup_logging  # noqa E402
from thousandeyes_constant import (  # noqa E402
    THOUSANDEYES_BASE_URL,
    THOUSANDEYES_AUTH_ENDPOINT,
    CLIENT_ID,
    AUTH_SCOPE,
    REQUEST_TIMEOUT,
)
from thousandeyes_utils import get_proxy_info  # noqa E402


logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0].lower())


class OAuth(PersistentServerConnectionApplication):
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

        :return: dictionary with Authorization codes.
        """
        logger.info(
            "Generating device code, user code and validation url for Authorizaton."
        )
        try:
            req_data = json.loads(in_string)
            session_key = req_data.get("system_authtoken", None)
            url = f"{THOUSANDEYES_BASE_URL}{THOUSANDEYES_AUTH_ENDPOINT}"
            data = {"scope": AUTH_SCOPE, "client_id": CLIENT_ID}
            proxy, verify = get_proxy_info(session_key, logger)
            response = requests.post(
                url, data, proxies=proxy, verify=verify, timeout=REQUEST_TIMEOUT
            )
            res_data = response.json()
            if response.status_code == 200:
                logger.info(
                    "Sucessfully generated device code, user code and validation url for Authorizaton."
                )
                return {"payload": res_data, "status": 200}
            else:
                raise Exception(res_data.get("error_description"))
        except requests.exceptions.ProxyError as e:
            logger.error(
                f"Error during authorization : {str(e)}. {traceback.format_exc()}"
            )
            err_msg = "Proxy Error occured, Please verify the configured proxy details."
            return {"payload": f"{err_msg}", "status": 500}
        except requests.exceptions.SSLError as e:
            logger.error(
                f"Error during authorization : {str(e)}. {traceback.format_exc()}"
            )
            err_msg = "SSL Error occured, Please verify the certificate for provided configuration."
            return {"payload": f"{err_msg}", "status": 500}
        except Exception as e:
            logger.error(
                f"Error during authorization : {str(e)}. {traceback.format_exc()}"
            )
            return {"payload": f"{e} Please check the logs.", "status": 500}

    def handleStream(self, handle, in_string):
        """For future use."""
        raise NotImplementedError("PersistentServerConnectionApplication.handleStream")

    def done(self):
        """Virtual method to optionally override function to receive a callback after the request completes."""
        pass
