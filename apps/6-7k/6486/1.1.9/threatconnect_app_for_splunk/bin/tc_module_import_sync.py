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
class ModuleImportSync(BaseGeneratingCommand):
    """Command to download owner data from ThreatConnect API.

    Usage:
    | tcmoduleimportpush
    """

    # properties
    _command = "tcmoduleimportpush"

    def generate(self):
        """Implement generate command for downloading owners."""
        service_path = self.tcs.config.service_path
        service_id = self.tcs.config.service_id
        configs = self.tcs.collections.ioc_collection.query()
        params = {"splunk_id": service_id} if service_id else {}
        response = self.tcs.session.post(
            f"{service_path}/sync", json=configs, params=params
        )

        yield {"status_code": response.status_code, "body": response.text}

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return


if __name__ == "__main__":
    try:
        dispatch(ModuleImportSync, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception:
        # standard library
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
