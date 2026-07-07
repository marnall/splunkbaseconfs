from builtins import str
from requests.auth import AuthBase
import os
import traceback
import json
import datetime
import isilon_utilities as utilities
import const

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
myapp = "TA_EMC-Isilon"
file_path = os.path.join(SPLUNK_HOME, "etc", "apps", myapp, "local")


class TokenAuth(AuthBase):
    """
    Class to manage tokens required for the api call.

    Updates the tokens in case of expiration/invalid values.
    """

    def __init__(self, **args):
        """Initializes the parameters required for fetching or updating tokens."""
        self.response_status = None
        self.node = args["node"] if "node" in args else None
        self.session_key = args["session_key"] if "session_key" in args else None
        self.original_endpoint = args["endpoint"] if "endpoint" in args else None
        self.filename = "last_session_call_info.pos"
        self.username = args["username"]
        self.password = args["password"]
        self.proxy = args["proxy"]
        self.logger = args["logger"]

    def __call__(self, verify, response_status=None):
        """Returns the token values."""
        if response_status and response_status == 401:
            self.response_status = response_status
        else:
            self.response_status = None
        self.getSessionvalidity(verify)
        return self.cookies

    def _get_cookie_from_session(self, verify):
        """Gets the new token values and updates it in pos file."""
        headers = {"Content-Type": "application/json"}
        body = json.dumps(
            {
                "username": self.username,
                "password": self.password,
                "services": ("platform", "namespace"),
            }
        )
        nodeList = self.original_endpoint.split(":" + const.ISILON_PORT)
        self.url = (
            nodeList[0] + ":" + const.ISILON_PORT + "/session/1/session" if len(nodeList) > 0 else None
        )
        session = utilities.retry_session()
        r = session.post(
            verify=verify,
            url=self.url,
            headers=headers,
            data=body,
            proxies=self.proxy,
        )
        if r.status_code == 201 and r.cookies:
            self.logger.info(
                "message=got_new_cookies | Got new session cookie for endpoint '{}'".format(self.original_endpoint)
            )
            self.cookies = dict(r.cookies)
            response_dict = json.loads(r.text)
            time_absolute = (
                response_dict["timeout_absolute"]
                if "timeout_absolute" in response_dict
                else 0
            )
            call_validity = datetime.datetime.now() + datetime.timedelta(
                seconds=time_absolute - 600
            )
            self.node_dict = {
                "cookies": self.cookies,
                "call_validity": call_validity.strftime("%Y-%m-%d %H:%M:%S"),
            }
        else:
            self.cookies = None
            self.node_dict = None
            self.logger.error("message=cookies_not_updated | Cookies can't be updated. So setting it as None.")

    def getSessionvalidity(self, verify):
        """Checks for the session validity. If token expires then updates it."""
        try:
            file_data = utilities._read_meta_info(self.filename, self.logger, file_path)
            if file_data != -1:
                if (
                    str(self.node) in file_data
                    and file_data.get(str(self.node)) is not None
                    and file_data.get(str(self.node)).get("call_validity") is not None
                    and self.response_status is None
                ):
                    file_date_time = file_data[str(self.node)]["call_validity"]

                    if (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") <= file_date_time):
                        self.cookies = file_data[str(self.node)]["cookies"]
                    else:
                        self._get_cookie_from_session(verify)
                        if self.node_dict is not None:
                            file_data[str(self.node)] = self.node_dict
                            utilities._write_meta_info(file_data, self.filename, self.logger, file_path)
                else:
                    self._get_cookie_from_session(verify)
                    if self.node_dict is not None:
                        file_data[str(self.node)] = self.node_dict
                        utilities._write_meta_info(file_data, self.filename, self.logger, file_path)
            else:
                file_data = {}
                self._get_cookie_from_session(verify)
                if self.node_dict is not None:
                    file_data[str(self.node)] = self.node_dict
                    utilities._write_meta_info(file_data, self.filename, self.logger, file_path)

        except Exception:
            self.logger.error(
                "message=session_validity_error | Error occured while getting session validity "
                "for authentication.\n{}".format(traceback.format_exc())
            )
            self.cookies = None
