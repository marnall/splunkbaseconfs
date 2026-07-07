#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download ThreatConnect Owner Information Command"""
# standard library
import os
import sys

# third-party
from base_generating_command import BaseGeneratingCommand
from splunklib.searchcommands import Configuration, dispatch


@Configuration()
class IOCTypeDownloadCommand(BaseGeneratingCommand):
    """Command to download owner data from ThreatConnect API.

    Usage:
    | tcindicatortypes
    """

    # properties
    _command = 'tcindicatortypes'
    filename = os.path.basename(__file__)

    def generate(self):
        """Implement generate command for downloading owners."""
        # retrieve ioc type data from ThreatConnect
        yield from self.tcs.request.ioc_types

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return


if __name__ == '__main__':
    try:
        dispatch(IOCTypeDownloadCommand, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception:
        # standard library
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
