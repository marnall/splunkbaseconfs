#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Connectivity Test"""
import logging
import os
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib', 'arlib'))
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib', 'arlib', 'aob_py3')
)

import splunklib.client as client
from alert_actions_base import ModularAlertBase

from threatconnect_splunk import TCS
from threatconnect_splunk.splunk_handler import SplunkHandler


class BaseAlertAction(ModularAlertBase):
    """Base Alert Action Class."""

    def __init__(self, ta_name, alert_name):
        """Initialize class properties.

        Args:
            ta_name (str): The ? name.
            alert_name (str): The alert name.
        """
        super().__init__(ta_name, alert_name)
        self.ta_name = ta_name

        # properties
        self._service = None
        self._tcs = None
        self.filename = None

        # add splunk handler
        self.add_logger_to_service()

    @property
    def service(self):
        """Return Splunk SDK service client."""
        uri = self.settings.get('server_uri')
        if self._service is None:
            self._service = client.connect(
                app=self.ta_name,
                host=urlparse(uri).hostname,
                port=urlparse(uri).port,
                scheme=urlparse(uri).scheme,
                token=self.session_key,
            )
        return self._service

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

    @property
    def tcs(self):
        """Instance of ThreatConnect Splunk Module."""
        if self._tcs is None:
            self._tcs = TCS(logger=self.logger, service=self.service)
            self._tcs.update_service()
        return self._tcs
