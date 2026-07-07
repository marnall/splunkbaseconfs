#!/usr/bin/env python
import logging
import sys
from typing import Generator

from vendor.splunklib.searchcommands import (
    StreamingCommand,
    dispatch,
    Configuration,
    Option,
)

from recordedfuture.api.rfclient import RFClient
from recordedfuture.core.app_env import RfesAppEnv
from recordedfuture.core.logging import setup_logging
from recordedfuture.metrics.timeit import Timeit
from rfes_configuration import get_configured_indicators, CORRELATION_MODE


@Configuration(distributed=False)
class AtoFeedCommand(StreamingCommand):
    """
    A streaming command that fetches a streaming feed, and streams it
    back as entries.

    Usage:

    | rffeed id="<indicator id>"
    """

    id = Option(
        doc="""**Syntax** *id=<field_name>*
            **Description** a field that is the automation id""",
    )

    def __init__(self):
        super().__init__()
        self.rf_logger = setup_logging()

    def stream(self, records) -> Generator[str, None, None]:  # noqa
        """Fetches ioc records for the given config id, thus will never populate existing records"""
        in_dict = {
            "session_key": self.metadata.searchinfo.session_key,
            "server_uri": self.metadata.searchinfo.splunkd_uri,
        }
        self.app_env = RfesAppEnv(in_dict, self.rf_logger, modalert=True)
        self.client = RFClient(self.app_env)

        with Timeit(log_level=logging.WARNING) as timeit:
            timeit.label = "rffeed_command"

            configured_indicators = get_configured_indicators(
                self.app_env, CORRELATION_MODE
            )
            for entry in self.client.feed.get_ato_feed(self.id, configured_indicators):
                yield entry


dispatch(AtoFeedCommand, sys.argv, sys.stdin, sys.stdout, __name__)
