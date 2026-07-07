#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download ThreatConnect Owner Information Command"""

# standard library
import os
import sys
from inspect import trace

# must be imported before packages in bin/lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib_1_1_9"))

# third-party
from password_manager import PasswordManager
from splunklib.searchcommands import Configuration, dispatch
from splunklib.searchcommands.generating_command import GeneratingCommand
from threatconnect_splunk.collections.settings import Settings
from threatconnect_splunk.session.tc_session import TcSession


@Configuration()
class VerifySettingsCommand(GeneratingCommand):
    """Command to download owner data from ThreatConnect API.

    Usage:
    | tcverifysettings
    """

    # properties
    filename = os.path.basename(__file__)
    results = []
    password_manager = PasswordManager()

    def finish(self):
        """Implement finish method."""
        search = self.metadata.searchinfo.search.strip("\n")
        self.logger.info(f"action=completed, command='{search}'")
        super().finish()

    def prepare(self):
        """Implement prepare method."""
        super().prepare()
        # splunk dispatch seems to call the command multiple times before service is available
        if self.metadata.action.lower() != "execute":
            return False

        search = self.metadata.searchinfo.search.strip("\n")
        self.logger.info(f"action=started, command='{search}'")
        self._settings = None
        self._session = None
        return True

    def generate(self):
        """Implement generate command for downloading owners."""
        # retrieve owner data from ThreatConnect

        key = self.settings["_key"]
        try:
            self.configure_session()
            r = self.session.get("/v2/owners")
            if r.ok:
                self.settings["valid"] = True
                self.settings["errorMessage"] = ""
                if self.settings.get("servicePath"):
                    r = self.session.get(f"{self.settings['servicePath']}/sync")
                    if not r.ok:
                        err = f"Error connecting to Splunk Gateway Service: {r.text or r.reason}"
                        self.settings["valid"] = False
                        self.settings["errorMessage"] = err
                        self.results.append({"valid": True, "message": err})
                    else:
                        self.results.append(
                            {"valid": True, "message": "Settings are valid."}
                        )
                else:
                    self.results.append(
                        {"valid": True, "message": "Settings are valid."}
                    )
            else:
                err = r.text or r.reason
                self.settings["valid"] = False
                self.settings["errorMessage"] = err
                self.results.append({"valid": False, "message": err})
        except Exception as e:
            # standard library
            import traceback

            print(traceback.format_exc(), file=sys.stderr)
            err = str(e)
            self.settings["valid"] = False
            self.settings["errorMessage"] = err
            self.results.append({"valid": False, "message": str(e)})

        Settings(self.service, self.log).update(key, self.settings)

        # display the results
        for r in self.results:
            yield r

    def configure_session(self):
        """Configure the session using the provided params."""
        tc_api_secret_key = self.password_manager.get_password(
            self.service, "tc_api_secret_key"
        )
        tc_proxy_password = self.password_manager.get_password(
            self.service, "tc_proxy_password"
        )
        self.session.proxies = self.session.configure_proxies(
            self.settings.get("proxyEnabled"),
            self.settings.get("proxyHost"),
            self.settings.get("proxyPort"),
            self.settings.get("proxyUser"),
            tc_proxy_password,
        )
        self.session.base_url = self.settings.get("baseUrl")
        self.session.auth = self.session.hmac_auth(
            self.settings.get("apiAccessId"), tc_api_secret_key
        )

    @property
    def session(self):
        """Return an instance of Requests Session configured for the ThreatConnect API."""
        if self._session is None:
            self._session = TcSession(self.service, self.log)
        return self._session

    @property
    def settings(self):
        """Return an instance of Requests Session configured for the ThreatConnect API."""
        if self._settings is None:
            self._settings = Settings(self.service, self.log).get()
        return self._settings

    def log(self, level, event, message):
        """Log the provided message under the provided level with a common prefix."""

        log_msg = f"app=TA_threatconnect_threat_intel event={event} message={message}"
        if self.job_uuid:
            log_msg = f"{log_msg} job_uuid={self.job_uuid}"
        self.event_writer.log(level.upper(), log_msg)


if __name__ == "__main__":
    try:
        dispatch(VerifySettingsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
    except:
        # standard library
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
