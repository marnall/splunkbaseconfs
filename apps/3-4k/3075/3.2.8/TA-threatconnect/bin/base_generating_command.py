#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Generating Module"""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from splunklib.searchcommands import GeneratingCommand

from threatconnect_splunk import TCS
from threatconnect_splunk.splunk_handler import SplunkHandler


class BaseGeneratingCommand(GeneratingCommand):
    """Base Generating Class."""

    # properties
    _tcs = None
    filename = os.path.basename(__file__)
    results = []

    def add_logger_to_service(self):
        """Add logger to service."""
        # add splunk handler to current logger
        # This is used to update the self.service with needed methods.
        if self.tcs:
            self.logger.setLevel(logging.DEBUG)
            sh = SplunkHandler(self.filename, self.service)
            sh.set_name('Splunk')
            sh.set_level_name(self.tcs.config.logging_level)
            self.logger.addHandler(sh)

    def finish(self):
        """Implement finish method."""
        search = self.metadata.searchinfo.search.strip('\n')
        self.logger.info(f"action=completed, command='{search}'")
        super().finish()

    def prepare(self):
        """Implement prepare method."""
        super().prepare()
        # splunk dispatch seems to call the command multiple times before service is available
        if self.metadata.action.lower() != 'execute':
            return False

        self.add_logger_to_service()
        search = self.metadata.searchinfo.search.strip('\n')
        self.logger.info(f"action=started, command='{search}'")
        return True

    @property
    def tcs(self):
        """Instance of ThreatConnect Splunk Module."""
        if self._tcs is None:
            self._tcs = TCS(logger=self.logger, service=self.service)
            self._tcs.update_service()
        return self._tcs
