"""This module provides a interface to interact with KVstore objects by
`Splunk REST API <http://docs.splunk.com/Documentation/Splunk/latest/RESTAPI/RESTcontents>`.
"""

import requests
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter, Retry
from xml.dom import minidom

RERTY_COUNT = 3
BACKOFF_FACTOR = 2
STATUS_FORCELIST = [429, 500, 502, 503, 504]
VERIFY_SSL = False  # disable SSL verification for Splunk service API


class SplunkAuthError(Exception):
    """Thrown when Splunk Service authenctication is failed due to invalid credentials."""

    pass


class SplunkProxyError(Exception):
    """Thrown when ProxyError is raised while connecting to Splunk."""

    pass


class SplunkServerError(Exception):
    """Thrown when received server error from Splunk server."""

    pass


class ObjectNotFoundError(Exception):
    """Thrown when object is not found in collection."""

    pass


class ObjectAlreadyExistsError(Exception):
    """Thrown when object is already present with the same key and user."""

    pass


class InvalidHostError(Exception):
    """Thrown when connection error occurred while connecting to Splunk."""

    pass


class BearerAuth(requests.auth.AuthBase):
    """Attaches Bearer authenctication to the given Request object."""

    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = f"Bearer {self.token}"
        return r


class KVStoreCollection():
    """This class provides methods to authenticate Splunk credentials and
    interact with kvstore object data.
    """

    def __init__(self, host, port, app, username=None, password=None, token=None, owner="nobody"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.token = token
        self.app = app
        self.owner = owner
        self.baseurl = "https://" + host + ":" + port

        self.session = requests.Session()
        adapter = HTTPAdapter(
            max_retries=Retry(
                total=RERTY_COUNT,
                backoff_factor=BACKOFF_FACTOR,
                status_forcelist=STATUS_FORCELIST
            )
        )
        self.session.mount("https://", adapter)

    def login(self):
        """This method authenticates Splunk instance with username and
        password."""
        try:
            rsp = self.session.post(
                self.baseurl + '/services/auth/login',
                data={'username': self.username, 'password': self.password},
                verify=VERIFY_SSL
            )
            rsp.raise_for_status()

            minidom.parseString(rsp.text).getElementsByTagName('sessionKey')[0].childNodes[0].nodeValue

        except requests.exceptions.ProxyError as proxyerror:
            raise SplunkProxyError(proxyerror)

        except requests.exceptions.ConnectionError:
            raise InvalidHostError(
                "Connection error occurred while authenticating Splunk Management. "
                "Please enter valid Splunk Management Port."
            )

        except Exception as error:
            if "rsp" in locals() and rsp.status_code == 401:
                raise SplunkAuthError(
                    "Splunk server authentication failed. "
                    "Please verify Splunk Management credentials."
                )
            elif "rsp" in locals() and rsp.status_code == 429:
                err_msg = "Client Error 429: Splunk Management server rate limit has been exceeded."
            else:
                err_msg = "Error occurred while authenticating Splunk Management: {}".format(error)

            raise Exception(err_msg)

    def verify_port(self):
        """Check if provided port is valid or not."""
        try:
            rsp = self.session.get(
                self.baseurl,
                verify=VERIFY_SSL
            )
            rsp.raise_for_status()

        except requests.exceptions.ProxyError as proxyerror:
            raise SplunkProxyError(proxyerror)

        except requests.exceptions.ConnectionError:
            raise InvalidHostError(
                "Connection error occurred while authenticating Splunk Management. "
                "Please enter valid Splunk Management Port."
            )

        except Exception as error:
            if "rsp" in locals() and rsp.status_code == 429:
                err_msg = "Client Error 429: Splunk Management server rate limit has been exceeded."
            else:
                err_msg = "Error occurred while authenticating Splunk Management: {}".format(error)

            raise Exception(err_msg)

    def get_by_key(self, collection, key: str):
        """Get the KVStore collection data by object id."""
        try:
            rsp = self.session.get(
                f'{self.baseurl}/servicesNS/{self.owner}/{self.app}/storage/collections/data/{collection}/{key}',
                auth=BearerAuth(self.token) if self.token else HTTPBasicAuth(self.username, self.password),
                verify=VERIFY_SSL
            )
            rsp.raise_for_status()

            return rsp.json()

        except requests.exceptions.ProxyError as proxyerror:
            raise SplunkProxyError(proxyerror)

        except Exception as error:
            if "rsp" in locals() and rsp.status_code == 401:
                raise SplunkAuthError(
                    "Splunk server authentication failed. "
                    "Please verify Splunk Management credentials."
                )
            elif "rsp" in locals() and rsp.status_code == 404:
                raise ObjectNotFoundError(
                    "Error occurred while retrieving lookup:"
                    "Object with key={} does not exist in collection={}"
                    .format(key, collection)
                )
            elif "rsp" in locals() and rsp.status_code == 429:
                err_msg = "Client Error 429: Splunk Management server rate limit has been exceeded."
            else:
                err_msg = "Error occurred while retrieving lookup: {}".format(error)

            raise Exception(err_msg)

    def insert(self, collection, data: dict):
        """Insert data into the KVStore collection."""
        try:
            rsp = self.session.post(
                f'{self.baseurl}/servicesNS/{self.owner}/{self.app}/storage/collections/data/{collection}',
                auth=BearerAuth(self.token) if self.token else HTTPBasicAuth(self.username, self.password),
                json=data,
                verify=VERIFY_SSL
            )
            rsp.raise_for_status()

            return rsp.json()

        except requests.exceptions.ProxyError as proxyerror:
            raise SplunkProxyError(proxyerror)

        except Exception as error:
            if "rsp" in locals() and rsp.status_code == 401:
                raise SplunkAuthError(
                    "Splunk server authentication failed. "
                    "Please verify Splunk Management credentials."
                )
            elif "rsp" in locals() and rsp.status_code == 409:
                raise ObjectAlreadyExistsError(
                    "Error occurred while saving lookup: "
                    "Object with key={} already exist in collection={}"
                    .format(data.get("_key"), collection)
                )
            elif "rsp" in locals() and rsp.status_code == 429:
                err_msg = "Client Error 429: Splunk Management server rate limit has been exceeded."
            else:
                err_msg = "Error occurred while saving lookup: {}".format(error)

            raise Exception(err_msg)

    def delete_by_key(self, collection, key: str):
        """Delete the KVStore collection data by object id."""
        try:
            rsp = self.session.delete(
                f'{self.baseurl}/servicesNS/{self.owner}/{self.app}/storage/collections/data/{collection}/{key}',
                auth=BearerAuth(self.token) if self.token else HTTPBasicAuth(self.username, self.password),
                verify=VERIFY_SSL
            )
            rsp.raise_for_status()

        except requests.exceptions.ProxyError as proxyerror:
            raise SplunkProxyError(proxyerror)

        except Exception as error:
            if "rsp" in locals() and rsp.status_code == 401:
                raise SplunkAuthError(
                    "Splunk server authentication failed. "
                    "Please verify Splunk Management credentials."
                )
            elif "rsp" in locals() and rsp.status_code == 404:
                raise ObjectNotFoundError(
                    "Error occurred while deleting lookup: "
                    "Object with key={} does not exist in collection={}"
                    .format(key, collection)
                )
            elif "rsp" in locals() and rsp.status_code == 429:
                err_msg = "Client Error 429: Splunk Management server rate limit has been exceeded."
            else:
                err_msg = "Error occurred while deleting lookup: {}".format(error)

            raise Exception(err_msg)
