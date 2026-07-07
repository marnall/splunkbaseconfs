#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download ThreatConnect Owner Information Command"""
# standard library
import os
import sys

# third-party
# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand
from splunklib.searchcommands import Configuration, Option, dispatch


@Configuration(retainsevents=True, streaming=False)
class IndicatorFalsePositiveCommand(BaseGeneratingCommand):
    """Command to download and indicator from ThreatConnect API.

    Usage:
    | tcreportfalsepositive <indicator> <indicator_type> <owner>
    """

    # args
    indicator = Option(doc='The indicator report as a false positive.', require=True)
    # owner = Option(doc='The owner of the indicator to add.', require=True)

    # properties
    _command = 'tcreportfalsepositive'
    filename = os.path.basename(__file__)

    def generate(self):
        """Implement generate command for downloading owners."""
        iocs = self.tcs.request.get_indicator(indicator=self.indicator)
        response = None
        for ioc in iocs:
            ioc_type = ioc.get('type')
            if not ioc_type:
                continue
            response = self.tcs.request.report_false_positive(self.indicator, ioc_type)
            if response.ok:
                yield {'_raw': response.json()}
                break
        else:
            if response:
                yield {'_raw': response.json()}
            else:
                yield {'_raw': {'Status': 'Failure', 'Message': 'Indicator not found.'}}

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return


if __name__ == '__main__':
    try:
        dispatch(IndicatorFalsePositiveCommand, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception:
        # standard library
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
