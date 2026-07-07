#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download ThreatConnect Owner Information Command"""
# standard library
import datetime
import json
import os
import sys

# third-party
# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand
from splunklib.searchcommands import Configuration, Option, dispatch


@Configuration(retainsevents=True, streaming=False)
class IndicatorDownloadCommand(BaseGeneratingCommand):
    """Command to download and indicator from ThreatConnect API.

    Usage:
    | tcaddindicator <indicator> <indicator_type> <owner>
    """

    # args
    indicator = Option(doc='The indicator to add.', require=True)
    indicator_type = Option(doc='The type of indicator to add.', require=True)
    owner = Option(doc='The owner of the indicator to add.', require=True)

    # properties
    _command = 'tcaddindicator'
    filename = os.path.basename(__file__)

    def generate(self):
        """Implement generate command for downloading owners."""
        response = self.tcs.request.add_indicator(
            indicator=self.indicator, type_=self.indicator_type, owner=self.owner
        )
        if response.ok:
            yield {
                'Status': 'Success',
                'Message': 'Indicator added successfully.',
                'WebLink': response.json().get('data', {}).get('webLink', ''),
            }
        else:
            yield {
                'Status': 'Failure',
                'Message': response.text or response.reason,
            }

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

    def retrieve_indicator(self, indicator):
        """Load Owner Data"""
        cached = list(
            filter(
                lambda i: indicator in i.indicator.split(' : '),
                self.tcs.collections.ioc_cache.query(),
            )
        )
        if cached:
            for i in cached:
                yield json.loads(i.data)
        else:
            now = datetime.datetime.now().timestamp()
            fields = list(self.tcs.request.indicator_fields_data.keys())
            for i in self.tcs.request.get_indicator(indicator, {'fields': fields}):
                self.tcs.collections.ioc_cache.insert(
                    {'cached_at': now, 'indicator': indicator, 'data': json.dumps(i)}
                )
                yield i


if __name__ == '__main__':
    try:
        dispatch(IndicatorDownloadCommand, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception:
        # standard library
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
