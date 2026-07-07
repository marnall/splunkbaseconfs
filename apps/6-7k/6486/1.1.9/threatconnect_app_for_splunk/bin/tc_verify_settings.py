#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download ThreatConnect Owner Information Command"""

# standard library
import os
import sys

# must be imported before packages in bin/lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib_1_1_9"))

# third-party
from base_generating_command import BaseGeneratingCommand
from splunklib.searchcommands import Configuration, dispatch


@Configuration()
class VerifySettingsCommand(BaseGeneratingCommand):
    """Command to download owner data from ThreatConnect API.

    Usage:
    | tcverifysettingsapp
    """

    # properties
    _command = "tcverifysettingsapp"
    results = []

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
        valid = True
        errorMessage = ""
        settings = self.tcs.collections.settings.query()[0]
        try:
            r = self.tcs.session.get("/v2/owners")
            if r.ok:
                valid = True
                errorMessage = ""

                r = self.tcs.session.get(f"{settings.service_path}/sync")
                if not r.ok:
                    valid = False
                    errorMessage = f"Error connecting to Splunk Gateway Service: {r.text or r.reason}"

                    self.results.append({"valid": True, "message": errorMessage})
                else:
                    self.results.append(
                        {"valid": True, "message": "Settings are valid."}
                    )
            else:
                err = r.text or r.reason
                valid = False
                errorMessage = err
                self.results.append({"valid": False, "message": err})

        except Exception as e:
            # standard library
            import traceback

            print(traceback.format_exc(), file=sys.stderr)
            err = str(e)
            valid = False
            errorMessage = err
            self.results.append({"valid": False, "message": str(e)})

        settings["valid"] = valid
        settings["errorMessage"] = errorMessage
        self.tcs.collections.settings.update(settings._key, settings)

        # display the results
        for r in self.results:
            yield r


if __name__ == "__main__":
    try:
        dispatch(VerifySettingsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception:
        # standard library
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
