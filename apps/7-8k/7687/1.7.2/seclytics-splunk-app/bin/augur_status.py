#!/usr/bin/env python
import sys

from augur_command import AugurCommand
from splunklib.searchcommands import Configuration, GeneratingCommand, dispatch


@Configuration(type="reporting", distributed=False, local=True)
class AugurStatusCommand(GeneratingCommand, AugurCommand):
    """Use Search Command V2 protocol."""

    def generate(self):
        """Build data needed for staus check."""
        yield {
            "access_token_set": self.has_access_token_set,
            "proxy_enabled": bool(self.proxies),
            "api_access": self.has_api_access,
            "internet_access": self.has_internet_access,
        }

    @property
    def has_access_token_set(self):
        return bool(self.access_token)

    @property
    def has_api_access(self):
        success = False
        try:
            node = self.augur_api.ip("13.33.148.37")
            success = node.ioc_type == "ip"
        except Exception:
            return False
        return success

    @property
    def has_internet_access(self):
        success = False
        try:
            url = "https://api.seclytics.com/status"
            response = self.requests_session.get(url, timeout=10)
            success = response.status_code == 200
        except Exception:
            return False
        return success


dispatch(AugurStatusCommand, sys.argv, sys.stdin, sys.stdout, __name__)
