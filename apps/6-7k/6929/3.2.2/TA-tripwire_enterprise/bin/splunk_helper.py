import sys
import os
from pathlib import Path
from functools import partial
from xml.etree import ElementTree as ET

import requests
import splunk
from requests.auth import HTTPBasicAuth

DEFAULT_REALM = "te_console"


def getAppName() -> str:
    """Get splunk app name associated with the current source

    """
    app_dir_name = os.path.basename(Path(__file__).resolve().parents[1].name)
    return app_dir_name.strip()

def token_from_stdin():
    """Splunk token read from Stdin

    Should be used only once within data input scripts that have been configured with passAuth
    """
    return sys.stdin.readline().strip()


def management_url():
    return f"https://{splunk.getDefault('host')}:{splunk.getDefault('port')}"


class PasswordManager:
    def __init__(self, auth_token, username=None, password=None, verify_cert=False):
        """Password Manager helper for Splunk

        auth_token is a Splunk session token.
        If auth_token is None, Splunk username and password must be provided.
        """
        APP_NAME = getAppName()
        if auth_token:
            headers = {"Authorization": f"Splunk {auth_token}"}
            self.request_get = partial(
                requests.get, headers=headers, verify=verify_cert
            )
            self.request_post = partial(
                requests.post, headers=headers, verify=verify_cert
            )
        else:
            basic = HTTPBasicAuth(username, password)
            self.request_get = partial(requests.get, auth=basic, verify=verify_cert)
            self.request_post = partial(requests.post, auth=basic, verify=verify_cert)
        self.base_url = (
            f"{management_url()}/servicesNS/nobody/{APP_NAME}/storage/passwords"
        )

    def create_password(self, username, password, realm=DEFAULT_REALM):
        """Create a username, password, realm entry in Splunk storage"""

        payload = {"name": username, "password": password, "realm": realm}
        resp = self.request_post(self.base_url, data=payload)
        resp.raise_for_status()

    def update_password(self, username, password, realm=DEFAULT_REALM):
        """Update the password associated to realm:username in Splunk storage"""

        url = f"{self.base_url}/{realm}:{username}"
        payload = {"password": password}
        resp = self.request_post(url, data=payload)
        resp.raise_for_status()

    def get_password(self, username, realm=DEFAULT_REALM):
        """Get the password associated to realm:username from Splunk storage"""
        try:
            url = f"{self.base_url}/{realm}:{username}"
            resp = self.request_get(url)
            if not resp.ok:
                return ""
            tree = ET.fromstring(resp.text)
            # find the first element in the XML doc that has an attribute of name with the value of clear_password
            element = tree.find(".//*[@name='clear_password']")
            return element.text
        except:
            return ""

    def set_password(self, username, password, realm=DEFAULT_REALM):
        if self.get_password(username, realm):
            self.update_password(username, password, realm)
        else:
            self.create_password(username, password, realm)
