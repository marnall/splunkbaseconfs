#!/usr/bin/env python
"""Custom search command: | terracequery
Search Terrace Networks IP summaries by CIDR, ASN, or actor.
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
class TerraceQueryCommand(GeneratingCommand):
    """Search Terrace Networks for IP summaries.

    ##Syntax

        | terracequery cidr=<cidr> [limit=<int>]
        | terracequery asn=<asn_number> [limit=<int>]
        | terracequery actor=<actor_slug> [limit=<int>]

    ##Examples

        | terracequery cidr="10.0.0.0/8" limit=50
        | terracequery asn=12345
        | terracequery actor=shodan
    """

    cidr = Option(name="cidr", require=False)
    asn = Option(name="asn", require=False)
    actor = Option(name="actor", require=False)
    limit = Option(name="limit", require=False, default=200, validate=validators.Integer())

    def generate(self):
        if not any([self.cidr, self.asn, self.actor]):
            yield {"_raw": "ERROR: Specify one of: cidr, asn, or actor"}
            return

        api_key = self._get_api_key()
        base_url = self._get_base_url()
        if not api_key:
            yield {"_raw": "ERROR: API key not configured"}
            return

        from terrace_api import TerraceClient, flatten_ip_detail

        client = TerraceClient(api_key=api_key, base_url=base_url)

        try:
            results = client.search_ip_summaries(
                cidr=self.cidr,
                asn=self.asn,
                actor=self.actor,
                limit=self.limit,
            )
        except Exception as e:
            yield {"_raw": f"ERROR: API call failed: {e}",
                   "debug_base_url": base_url,
                   "debug_api_key_len": str(len(api_key))}
            return

        for item in results:
            yield flatten_ip_detail(item)

    def _get_api_key(self):
        for cred in self.service.storage_passwords:
            if cred.realm == "TA-terrace" and cred.username == "api_key":
                return cred.clear_password
        return ""

    def _get_base_url(self):
        return "https://api.terracenetworks.com"


dispatch(TerraceQueryCommand, sys.argv, sys.stdin, sys.stdout, __name__)
