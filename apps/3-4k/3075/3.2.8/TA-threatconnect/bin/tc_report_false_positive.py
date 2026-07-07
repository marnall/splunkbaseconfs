#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Report False Positive Command"""
import sys
import os
import urllib.parse

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class ReportFalsePositiveCommand(BaseGeneratingCommand):
    """Command to get Report a Indicator as False Positive.

    This command is used by tc_splunk.json.

    Usage:
    | tcfalsepositive
        indicator=<Indicator Value> indicator_type=<Indicator Type String> owner=<Owner Name>

    e.g.,
    | tcfalsepositive indicator=example.com indicator_type=Host owner=TCI
    """

    indicator = Option(doc='The **Indicator** to report as a False Positive.', require=True)
    indicator_type = Option(doc='The **Indicator Type**.', require=True)
    owner = Option(doc='The **Owner** to the Indicator resides in.', require=True)
    # properties
    filename = os.path.basename(__file__)

    def generate(self):
        """Implement generate command for reporting a false positive on a indicator."""
        # Indicator Resource
        params = {'owner': self.owner}
        api_branch = self.tcs.request.indicator_type_branch(self.indicator_type)
        safe_indicator = urllib.parse.quote(self.indicator, safe='')
        r = self.tcs.session.post(
            f'/v2/indicators/{api_branch}/{safe_indicator}/falsePositive', params=params
        )
        results = []

        # log failure
        if not r.ok:
            self.logger.error(f'Status {r.status_code}')
        else:
            results.append({'results': r.json().get('status')})

        for result in results:
            yield result

        self.logger.info('status=complete')


if __name__ == '__main__':
    dispatch(ReportFalsePositiveCommand, sys.argv, sys.stdin, sys.stdout, __name__)
