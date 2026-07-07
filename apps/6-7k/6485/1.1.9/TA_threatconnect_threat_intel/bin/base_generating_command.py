#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download ThreatConnect Owner Information Command"""

# standard library
import os
import sys

# must be imported before packages in bin/lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib_1_1_9"))

# standard library
import time

# third-party
from password_manager import PasswordManager
from splunklib.searchcommands import Configuration
from splunklib.searchcommands.generating_command import GeneratingCommand
from threatconnect_splunk.collections.settings import Settings
from threatconnect_splunk.request.tc_request import TcRequest
from threatconnect_splunk.session.tc_session import TcSession


@Configuration()
class BaseGeneratingCommand(GeneratingCommand):
    """Command to download owner data from ThreatConnect API."""

    results = []
    _session = None
    _request = None
    _settings = None
    password_manager = PasswordManager()

    @property
    def request(self):
        """Return an instance of the Request Class.

        A wrapper on the Python Request Module specifically for interacting with the
        ThreatConnect API.  However, this can also be used for connecting to other
        API endpoints.

        Returns:
            (object): An instance of Request Class
        """
        if self._request is None:
            self._request = TcRequest(self.session, self.log)
        return self._request

    @property
    def session(self):
        """Return an instance of Requests Session configured for the ThreatConnect API."""
        if self._session is None:
            self._session = TcSession(self.service, self.log)
        return self._session

    def log(self, level, event, message):
        """Log the provided message under the provided level with a common prefix."""

        log_msg = (
            f'app=TA_threatconnect_threat_intel, event="{event}", message="{message}"'
        )
        self.logger.__getattribute__(level.lower())(log_msg)

    def configure_session(self):
        """Configure the session using the provided params."""

        tc_api_secret_key = self.password_manager.get_password(
            self.service, "tc_api_secret_key"
        )
        tc_proxy_password = self.password_manager.get_password(
            self.service, "tc_proxy_password"
        )
        self.session.proxies = self.session.configure_proxies(
            self.settings.get("proxy_enabled"),
            self.settings.get("proxy_host"),
            self.settings.get("proxy_port"),
            self.settings.get("proxy_user"),
            tc_proxy_password,
        )
        self.session.base_url = self.settings.get("base_url")
        self.session.auth = self.session.hmac_auth(
            self.settings.get("api_access_id"), tc_api_secret_key
        )

    @property
    def settings(self):
        """Return an instance of Requests Session configured for the ThreatConnect API."""
        if self._settings is None:
            self._settings = Settings(self.service, self.log).get()
        return self._settings

    def finish(self):
        """Implement finish method."""
        search = self.metadata.searchinfo.search.strip("\n")
        self.logger.info(f"""action=completed, command='{search}\'""")
        super().finish()

    def prepare(self):
        """Implement prepare method."""
        super().prepare()
        # splunk dispatch seems to call the command multiple times before service is available
        if self.metadata.action.lower() != "execute":
            return False

        search = self.metadata.searchinfo.search.strip("\n")
        self.logger.info(f"""action=started, command='{search}\'""")
        return True

    def search(self, search, **kwargs):
        """Execute a Splunk Search."""
        self.service.parse(search, parse_only=True)
        job = self.service.jobs.create(search, **kwargs)
        while True:
            while not job.is_ready():
                pass

            stats = {
                "isDone": job["isDone"],
                "doneProgress": float(job["doneProgress"]) * 100,
                "scanCount": job["scanCount"],
                "eventCount": job["eventCount"],
                "resultCount": job["resultCount"],
            }
            time.sleep(10)
            if stats["isDone"] == "1":
                self.logger.info(f"Search stats: {stats}")
                break

        return job

    def generate(self):
        raise NotImplemented("The generate() method has not been implemented.")
