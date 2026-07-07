#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Report Command"""
import sys
import os
from collections import OrderedDict
import urllib.parse

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class ReportSingleCommand(BaseGeneratingCommand):
    """Command to get report a Indicator as false positive or whitelisted.

    This command is used by the event triage to report False Positives.

    Usage:
    | tcreportsingle
        indicator=<Indicator Value>
        indicator_type=<Indicator Type String>
        owner=<Owner Name>
        report_type=<false positive|whitelist>

    e.g.,
    | tcreportsingle
        indicator=example.com indicator_type=Host owner=TCI report_type="false positive"
    """

    # args
    indicator = Option(
        doc='The **Indicator** to report as a False Positive|WhiteList.', require=True
    )
    indicator_type = Option(doc='The **Indicator Type**.', require=True)
    owner = Option(doc='The **Owner** to the Indicator resides in.', require=True)
    report_type = Option(doc='The type of report <**false positive | whitelisted**>', require=True)

    # properties
    filename = os.path.basename(__file__)

    def add_result(self, action, indicator, owner, status):
        """Return ordered dict for results."""
        self.logger.info(
            f'action="{action}", indicator={indicator}, owner="{owner}", status={status}'
        )
        result_data = OrderedDict()
        result_data['Action'] = action
        result_data['Indicator'] = indicator
        result_data['Owner'] = owner
        result_data['Status'] = status
        self.results.append(result_data)

    def generate(self):
        """Implement generate command for reporting single type."""
        if self.report_type.lower() == 'false positive':
            status = 'Success'
            params = {'owner': self.owner}
            api_branch = self.tcs.request.indicator_type_branch(self.indicator_type)
            safe_indicator = urllib.parse.quote(self.indicator, safe='')
            r = self.tcs.session.post(
                f'/v2/indicators/{api_branch}/{safe_indicator}/falsePositive', params=params
            )
            self.logger.debug(f'url={r.request.url}')

            if not r.ok:
                err = r.text or r.reason
                status = 'Failed'
                self.logger.error(f'status={r.status_code}, error={err}')

            self.add_result(f'Report {self.report_type}', self.indicator, self.owner, status)
        elif self.report_type == 'whitelisted':
            pass

        for result in self.results:
            yield result


if __name__ == '__main__':
    dispatch(ReportSingleCommand, sys.argv, sys.stdin, sys.stdout, __name__)
