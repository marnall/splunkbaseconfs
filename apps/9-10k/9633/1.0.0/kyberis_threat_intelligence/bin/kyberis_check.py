"""Diagnostic generating command: | kyberischeck [profile=<name>]

Resolves a named Kyberis credential profile into a client configuration and
reports the outcome as a single result row. Emits whether an API key is stored
for the profile — never the key itself.
"""

import os
import sys
import time

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BIN_DIR, "lib"))
sys.path.insert(0, BIN_DIR)

from splunklib.searchcommands import Configuration, GeneratingCommand, Option, dispatch

from kyberis_splunk import logscrub
from kyberis_splunk.settings import KyberisSettingsError, build_client


@Configuration()
class KyberisCheckCommand(GeneratingCommand):
    profile = Option(
        require=False,
        doc="Credential profile to resolve; defaults to default_profile from kyberis.conf.",
    )

    def generate(self):
        logscrub.install()
        logscrub.register_secret(getattr(self.metadata.searchinfo, "session_key", None))
        try:
            client, resolved = build_client(self.service, self.profile)
        except KyberisSettingsError as error:
            self.write_error(str(error))
            return

        yield {
            "_time": time.time(),
            "status": "ok",
            "profile": resolved.profile,
            "base_url": resolved.config.base_url,
            "api_prefix": resolved.config.api_prefix,
            "timeout_seconds": resolved.config.timeout_seconds,
            "max_retries": resolved.config.max_retries,
            "cache_ttl_seconds": resolved.cache_ttl_seconds,
            "cim_min_threat": resolved.cim_min_threat,
            "log_level": resolved.log_level,
            "api_key_present": "true",
            "client_ready": "true" if client else "false",
        }


dispatch(KyberisCheckCommand, sys.argv, sys.stdin, sys.stdout, __name__)
