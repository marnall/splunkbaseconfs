#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Group Types Command"""
import sys
import os

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from splunklib.searchcommands import dispatch, Configuration


@Configuration()
class DownloadGroupTypesCommand(BaseGeneratingCommand):
    """Command to get return all of the Group Types.

    This command is used by the owner config.

    Usage:
    | tcgrouptypes
    """

    # properties
    filename = os.path.basename(__file__)

    def generate(self):
        """Implement generate command for retrieving group types."""
        for gt in self.tcs.request.group_types:
            yield {'groupType': gt}


if __name__ == '__main__':
    dispatch(DownloadGroupTypesCommand, sys.argv, sys.stdin, sys.stdout, __name__)
