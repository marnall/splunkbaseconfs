#!/usr/bin/env python

from urllib.parse import quote

import requests
from cached_property import cached_property
from seclytics import Seclytics


class AugurCommand(object):
    @cached_property
    def access_token(self):
        """Get the token from the splunk password store.

        Returns:
            an access token
        """
        for entry in self.service.storage_passwords:
            if entry.username == "command":
                return entry.clear_password
        raise ValueError("Access Token Not Defined.")

    @cached_property
    def proxies(self):
        """Build our proxy connection if we need it.

        Returns:
            a dict used for requests proxy
        """
        augur_conf = self.service.confs["seclytics"]
        if "augur_proxy" not in augur_conf:
            raise RuntimeError("missing proxy conf")
        stanza = augur_conf["augur_proxy"]
        return self.build_proxy_for_stanza(stanza)

    @cached_property
    def requests_session(self):
        """Build a cached shared session for all requests.

        This improves performance and handles proxies.
        """
        session = requests.Session()
        session.proxies = self.proxies
        return session

    @cached_property
    def augur_api(self):
        return Seclytics(self.access_token, session=self.requests_session)

    @staticmethod
    def build_proxy_for_stanza(proxy_info):
        """Prepare dict containing proxy details.

        Proxy_info is not a dict it's Splunk Collection so methods like
              get actually call the splunk API.

        Returns:
            a dictionary of proxy conf strings
        """
        proxy_data = {
            "proxy_enabled": bool(int(proxy_info["proxy_enabled"])),
            "proxy_hostname": proxy_info["proxy_url"],
            "proxy_port": proxy_info["proxy_port"],
            "proxy_username": proxy_info["proxy_username"],
            "proxy_password": proxy_info["proxy_password"],
            "proxy_type": proxy_info["proxy_type"],
        }

        # Return None if proxy_enabled is false or proxy hostname or proxy port is not found
        if (
            not proxy_data["proxy_enabled"]
            or not proxy_data["proxy_port"]
            or not proxy_data["proxy_hostname"]
        ):
            return None

        # Quote username and password if available
        user_pass = ""
        if proxy_data.get("proxy_username") and proxy_data.get("proxy_password"):
            username = quote(proxy_data["proxy_username"], safe="")
            password = quote(proxy_data["proxy_password"], safe="")
            user_pass = "{user}:{password}@".format(user=username, password=password)

        # Prepare proxy string
        proxy = "{proxy_type}://{user_pass}{host}:{port}".format(
            proxy_type=proxy_data["proxy_type"],
            user_pass=user_pass,
            host=proxy_data["proxy_hostname"],
            port=proxy_data["proxy_port"],
        )
        proxies = {
            "http": proxy,
            "https": proxy,
        }
        return proxies
