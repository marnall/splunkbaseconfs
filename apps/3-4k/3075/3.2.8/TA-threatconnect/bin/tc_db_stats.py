#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect KV Store Status"""
import sys
import os
from collections import OrderedDict

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class KvStoreStatCommand(BaseGeneratingCommand):
    """Command to generate KV Store stats.

    This command is used by the Reports -> Threat Indicator Report page to
    generate stats on the number of indicator in the KV Store. If report=True
    is passed the command will return stats instead of generating the stats.

    Usage:
    | tcdbstats report=<False|True>

    e.g.,
    | tcdbstats

    # collect data
    | tcdbstats report=True
    """

    # args
    report = Option(
        default=False, doc='If True the command will display the report data.', require=False
    )

    # properties
    filename = os.path.basename(__file__)

    def collect_stats(self):
        """Collect indicator stats.

        {
            "<owner>": {
                "Address": 10,
                "File": 5
            }
        }
        """
        # get indicator count by owner/type
        owner_counts = {}

        for indicator_data in self.tcs.collections.indicators.paginate(
            fields='_key,indicator,ownerName,type'
        ):
            owner_name = indicator_data.get('ownerName')
            indicator_type = indicator_data.get('type')
            # count by owner -> indicator type
            owner_counts.setdefault(owner_name, {})
            owner_counts[owner_name].setdefault(indicator_type, 0)
            owner_counts[owner_name][indicator_type] += 1

        # clear current stats before adding stats back
        self.tcs.collections.db_stats.delete()

        for owner_name, types in owner_counts.items():
            for indicator_type, count in types.items():
                data = {
                    'time': self.tcs.utils.epoch_seconds(utc=True),
                    'ownerName': owner_name,
                    'indicatorType': indicator_type,
                    'indicatorCount': count,
                }
                self.tcs.collections.db_stats.batch_data(data)
                self.results.append(data)

        # save any remaining data
        self.tcs.collections.db_stats.batch_save()

    def generate(self):
        """Implement generate command for Collection KV Store Stats."""
        if self.report is True:
            self.logger.info('action=report-stats')
            self.report_stats()
        else:
            self.logger.info('action=collect-stats')
            self.collect_stats()

        # display the results
        for r in self.results:
            yield r

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

        # update options
        self.report = self.tcs.utils.to_bool(self.report)

    def report_stats(self):
        """Generate report from KV Store."""
        owner_counts = {}

        for stats in self.tcs.collections.db_stats.paginate(
            fields='_key,indicatorCount,indicatorType,ownerName'
        ):
            owner_name = stats.get('ownerName')
            indicator_count = stats.get('indicatorCount')
            indicator_type = stats.get('indicatorType')

            owner_counts.setdefault(owner_name, {})
            owner_counts[owner_name].setdefault(indicator_type, indicator_count)

        for owner_data in self.tcs.collections.owners.paginate(fields='name'):
            result_data = OrderedDict()
            result_data['Owner'] = owner_data.get('name')
            for indicator_type in sorted(self.tcs.request.indicator_types):
                result_data[indicator_type.replace(' ', '_')] = owner_counts.get(
                    owner_data.get('name'), {}
                ).get(indicator_type, 0)
            self.results.append(result_data)


if __name__ == '__main__':
    dispatch(KvStoreStatCommand, sys.argv, sys.stdin, sys.stdout, __name__)
