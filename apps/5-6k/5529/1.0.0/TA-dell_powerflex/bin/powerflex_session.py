import os
import requests
import json
from threading import Lock
import re
import base64
from powerflex_lock import JLock
import powerflex_utilities

REQUEST_TIMEOUT = 60   # seconds

class AuthenticationFailed(Exception):
    pass

class PowerFlexRequestError(Exception):
    def __init__(self, msg, status_code):
        super(PowerFlexRequestError, self).__init__(msg)
        self.status_code = status_code

class PowerFlexSession(object):
    """
    Checkpoint file pattern: <account>_cache.ckpt
    Lock file: <account>_cache.lock
    """
    AVAILABLE, UPDATING, AUTHENTICATING, ERROR = range(4)
    RETRY_COUNT = 3

    def __init__(self, account, session_key, modinput_helper=None, logger=None):
        """
        PowerFlexSession class to connect to PowerFlex REST API and request to them.
        :param account: The dictionary object with account credentials
        :param session_key: Splunk session key
        :param logger: Logger object
        """
        self.lock = Lock()
        self.logger = logger
        self.account = account
        self.token_cache = None
        self.state = PowerFlexSession.AVAILABLE
        self.modinput_helper = modinput_helper
        self.credential_manager = powerflex_utilities.CredentialManager(session_key)

        # Logger
        if not logger:
            self.logger = powerflex_utilities.get_logger(session_key, 'powerflex_session', account.name)
        
        # Proxy 
        self.proxy_uri = powerflex_utilities.get_proxy_uri(session_key, logger)
        self.ssl_verification, self.http_scheme = powerflex_utilities.get_additional_parameters(session_key)
    
    def _handle_status_code(self, status_code):
        """
        Handle status_code returned by each request
        """
        msg = None
        if 200 <= status_code < 300:
            return
        elif status_code == 400:
            msg = "Badly formed URI, parameters, headers, or body content. Essentially a request syntax error."
        elif status_code == 401:
            msg = "Invalid username or password."
        elif status_code == 403:
            msg = "PowerFlex OS Gateway is disabled. Contact your PowerFlex OS administrator to enable it."
        elif status_code == 404:
            msg = "Resource does not exist or URL not found."
        elif status_code == 405:
            msg = "Method not allowed."
        elif status_code == 406:
            msg = "This request is not acceptable."
        elif status_code == 409:
            msg = "The request could not be completed due to a conflict with the current state of the resource."
        elif status_code == 422:
            msg = "Semantically invalid content on a POST, which could be a range error, inconsistent properties, or something similar."
        elif status_code >= 500:
            msg = "Internal server error is received. Please check in the PowerFlex system and try again."
        else:
            msg = "Invalid status code"
        raise PowerFlexRequestError("Status code:{} - {}".format(status_code, msg), status_code=status_code)
 
    def _request(self, url, method="GET", params=None, data=None, headers={}, auth=None):
        """
        Request to the PowerFlex endpoints
        """
        self.logger.debug("Requesting: url={}, method={}, params={}, data={}, ssl_verify={}".format(url, method, params, data, self.ssl_verification))
        url = "{}://{}{}".format(self.http_scheme, self.account.endpoint, url)

        if method == "GET": 
            res = requests.get(url, params=params, headers=headers, proxies=self.proxy_uri, auth=auth, verify=self.ssl_verification, timeout=REQUEST_TIMEOUT)
        elif method == "POST":
            headers.update({"Content-Type": "application/json"})
            if not data:
                data = dict()
            res = requests.post(url, params=params, data=json.dumps(data), headers=headers, proxies=self.proxy_uri, auth=auth, verify=self.ssl_verification, timeout=REQUEST_TIMEOUT)
        else:
            raise ValueError("Only GET & POST requests are supported")

        self.logger.debug("Got response: status={}".format(res.status_code))
        self._handle_status_code(res.status_code)

        try:
            return res.json()
        except:
            self.logger.debug("returning an text response. response={} ".format(res.text[:100]))
            return res.text

    def request(self, url, method="GET", params=None, data=None):
        """send HTTP request to the url with the data
        Try 3 times with PowerFlex session token of 1. token_cache 2. ckpt_file 3. authenticate

        1. Get the token using get_token()
        2. If Call Failed give the token back & fetch new (file_ckpt)
        3. If Call Failed give the token back & fetch new (authenticate)
        4. If Call Failed, raise Exception 
        """
        def one_request_try(persist_token):
            self.logger.debug("Fetching token, try={}, with_previous_token={}".format(retry, bool(persist_token["token"])))

            token = self.get_token(persist_token["token"])
            headers = {"Authorization": "Basic {}".format(token)}

            # Update the persist_token to maintain the last token used for the request
            persist_token["token"] = token

            # Request
            return self._request(url, method=method, params=params, data=data, headers=headers)

        # persist_token to maintain the valid & invalid tokens used.
        persist_token = {"token": None}
        for retry in range(self.RETRY_COUNT - 1):
            try:
                return one_request_try(persist_token)
            except PowerFlexRequestError as e:
                if e.status_code == 401:
                    self.logger.info("Failed to send request. Retry_count={} :: msg={}".format(retry, str(e)))
                else:
                    raise
        else:
            # Last request without try-except to get the exact exception
            return one_request_try(persist_token)

    def _get_ckpt_token(self):
        """
        Get Token from the checkpoint file
        """
        if not self.modinput_helper:
            raise Exception("Please provide modular_input handler to use checkpoints")

        ckpt_name = "{}_token".format(self.account.name)
        self.logger.debug("Getting checkpoint file for: ckpt_name={}".format(ckpt_name))
        ckpt_obj = self.credential_manager.get_credential(ckpt_name)

        if not ckpt_obj:
            return None
        self.logger.debug("Got checkpoint file for: ckpt_name={} with PID={} & state={}".format(ckpt_name, ckpt_obj["PID"], ckpt_obj["state"]))
        if ckpt_obj["state"] == self.ERROR:
            with self.lock:
                self.state = self.ERROR
            self.logger.warning("An Input with PID={} could not authenticate properly. Will try again.".format(ckpt_obj["PID"]))
            return None

        return ckpt_obj["token"]

    def _safe_set_ckpt_token(self):
        if self.modinput_helper:
            return self._set_ckpt_token()

    def _set_ckpt_token(self):
        """
        Set Token in the checkpoint file
        : state: Current state of the Session. (Available or ERROR)
        : token: the latest maintained token
        """
        if not self.modinput_helper:
            raise Exception("Please provide modular_input handler to use checkpoints")

        ckpt_name = "{}_token".format(self.account.name)
        with self.lock:
            ckpt_obj = {
                "state": self.state,
                "token": self.token_cache,
                "PID": os.getpid()
            }
        self.logger.info("Setting the checkpoint file for: ckpt_name={}".format(ckpt_name))
        self.credential_manager.store_password(ckpt_name, ckpt_obj)
        self.logger.info("Successfully set checkpoint file for: ckpt_name={}".format(ckpt_name))


    def get_state(self):
        with self.lock:
            return self.state

    def get_token(self, invalid_token=None):
        """
        Get the Token to do REST request. Execute the get_token 3 times to get the token in worst cases
        :param invalid_token: If any request has failed previously
        """
        with self.lock:
            if self.state == self.ERROR:
                self.logger.error("Previous try of authentication has failed")
                raise AuthenticationFailed("Previous try of authentication has failed")

            if self.state == self.AVAILABLE and self.token_cache and invalid_token != self.token_cache:
                return self.token_cache
            elif self.state == self.AVAILABLE:
                self.state = self.UPDATING
        self.logger.debug("Try to acquire the lock")
        with JLock(self.account):
            self.logger.debug("Acquired the lock")

            # If another thread has already authenticated and updated the state
            with self.lock:
                if self.state == self.AVAILABLE and self.token_cache:
                    self.logger.debug("Another thread has already authenticated")
                    return self.token_cache

                # If another thread got error while authenticating
                if self.state == self.ERROR:
                    self.logger.error("Previous try of authentication in another thread has failed")
                    raise AuthenticationFailed("Previous try of authentication has failed")

            # Get the latest token from the checkpoint file
            ckpt_token = self._get_ckpt_token()

            # Return the checkpoint token if it's not invalid
            if ckpt_token and (invalid_token != ckpt_token):
                self.logger.debug("Returning checkpoint token")
                with self.lock:
                    self.token_cache = ckpt_token
                    self.state = self.AVAILABLE
                return ckpt_token
            else:
                # Authenticate if the checkpoint does not have a token or it is invalid
                with self.lock:
                    self.state = self.AUTHENTICATING
                token = self.authenticate()
                with self.lock:
                    self.state = self.AVAILABLE
                self._set_ckpt_token()
                self.logger.debug("Returning authenticated token")
                return token

    def authenticate(self):
        """ Authenticate to the endpoint using credentials and store the token in the checkpoint file """
        try:
            self.logger.info("Authenticating...")
            res = self._request(powerflex_utilities.AUTH_URL, method="GET", auth=(self.account.username, self.account.password))
            token = str(res).strip('"')
            token = base64.b64encode(":{}".format(token).encode("utf-8")).decode("utf-8")
            with self.lock:
                self.token_cache = token
            self.logger.info("Authenticated")
            return token
        except Exception as e:
            self.logger.exception("Error while authenticating. {}".format(str(e)))
            with self.lock:
                self.state = self.ERROR
            self._safe_set_ckpt_token()
            raise
