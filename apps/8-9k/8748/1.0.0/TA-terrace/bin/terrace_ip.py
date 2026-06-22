#!/usr/bin/env python
"""Custom search command: | terraceip ip=1.2.3.4
Looks up a single IP against Terrace Networks threat intelligence.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

from splunklib.searchcommands import (
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
    validators,
)


@Configuration(type="reporting")
class TerraceIPCommand(GeneratingCommand):
    """Look up a single IP against Terrace Networks.

    ##Syntax

        | terraceip ip=<ip_address>

    ##Example

        | terraceip ip=1.2.3.4
    """

    ip = Option(name="ip", require=True, validate=validators.Match(
        "ip", r"^[\d.:a-fA-F]+$"
    ))

    def generate(self):
        api_key = self._get_api_key()
        base_url = self._get_base_url()

        if not api_key:
            yield {"_raw": "ERROR: API key not found in terrace.conf",
                   "debug_conf": str(self._get_terrace_conf())}
            return

        from terrace_api import TerraceClient, flatten_ip_detail

        client = TerraceClient(api_key=api_key, base_url=base_url)
        try:
            detail = client.get_ip_detail(self.ip)
        except Exception as e:
            yield {"_raw": f"ERROR: API call failed: {e}",
                   "debug_base_url": base_url,
                   "debug_api_key_len": str(len(api_key))}
            return

        yield flatten_ip_detail(detail)

    def _get_api_key(self):
        for cred in self.service.storage_passwords:
            if cred.realm == "TA-terrace" and cred.username == "api_key":
                return cred.clear_password
        return ""

    def _get_base_url(self):
        return "https://api.terracenetworks.com"


dispatch(TerraceIPCommand, sys.argv, sys.stdin, sys.stdout, __name__)
