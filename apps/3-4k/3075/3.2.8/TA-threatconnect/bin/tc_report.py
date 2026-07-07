#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Reports Command"""
import os
import sys
import time
from collections import OrderedDict
from datetime import datetime
from urllib.parse import quote

# must be imported before packages in bin/lib
from base_eventing_command import BaseEventingCommand

from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class ReportCommand(BaseEventingCommand):
    """Command to report data back to ThreatConnect API.

    This command is used by the Event Triage page to mark a multiple events
    as "False Positive" or "Reviewed".

    Usage:
    | tcreport report_type=<'False Positive'|Reviewed> add_label=<True|False>

    e.g.,
    | tcreport report_type=Reviewed add_label=False
    """

    # args
    add_label = Option(doc='If True the report type will be added as a label.', require=True)
    report_type = Option(doc='The report type (False Positive|Reviewed).', require=True)

    # properties
    filename = os.path.basename(__file__)
    owner = None
    max_batch = None

    def add_result(self, event_key, indicator, labels):
        """Add result entry for Splunk search output"""
        result_data = OrderedDict()
        result_data['_time'] = time.time()
        result_data['event_key'] = event_key
        result_data['indicator'] = indicator
        result_data['labels'] = labels
        self.results.append(result_data)

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

        # update args
        self.add_label = self.tcs.utils.to_bool(self.add_label)
        self.max_batch = int(self.tcs.config.tc_max_batch_size)

    def transform(self, records):
        """Event transform."""
        # get the current datetime value as epoch time
        last_updated = datetime.now().strftime('%s')
        self.logger.debug(f'last_updated={str(datetime.now())}')

        ioc_tracker = []  # one false positive report per indicator
        for record in records:
            # get the event (kv store) key from the event
            event_key = record.get('key')

            # retrieve the event data
            event = self.tcs.collections.event_summaries.query_by_id(event_key)

            # update event
            event['lastUpdated'] = last_updated

            # update label if requested
            if self.add_label:
                event['labels'] = self.update_labels(event['labels'])

            # add event to batch data for update
            self.tcs.collections.event_summaries.batch_data(event)

            indicator = event.get('indicator')
            self.logger.debug(f'action="mark-{self.report_type}", value={indicator}')

            # add results
            self.add_result(event_key, indicator, list(map(str.strip, self.report_type.split(','))))

            if self.report_type in ['False Positive'] and indicator not in ioc_tracker:
                # Report 1 False Positive to TC API (restriction is per day)
                self.update_indicator(
                    indicator, event.get('indicatorType'), record.get('indicatorOwnerName')
                )
                ioc_tracker.append(indicator)

        # save any remaining data
        self.tcs.collections.event_summaries.batch_save()

        # display the results
        for r in self.results:
            yield r

    def update_indicator(self, indicator, indicator_type, owner):
        """Update indicators in kvstore."""
        if not indicator_type:
            self.logger.error(f'indicator={indicator}, indicator_type={indicator_type}')
            return

        # indicator values
        indicator = quote(indicator, safe='~')
        indicator_branch = self.tcs.request.indicator_type_branch(indicator_type)

        # post false positive
        params = {'owner': owner}
        r = self.tcs.session.post(
            f'/v2/indicators/{indicator_branch}/{indicator}/falsePositive', params=params
        )
        # self.logger.info(f'r.text {r.text}')

        status = 'Failed'
        if r.ok:
            status = 'Success'

        self.logger.info(f'action="{self.report_type}", value={indicator}, status={status}')

    def update_labels(self, labels):
        """Update labels on event."""
        labels = labels or []
        if self.report_type not in labels:
            labels.append(self.report_type)

        # remove New label when "marked" Reviewed
        if self.report_type == 'Reviewed':
            try:
                labels.remove('New')
            except ValueError:
                pass

        return labels


if __name__ == '__main__':
    dispatch(ReportCommand, sys.argv, sys.stdin, sys.stdout, __name__)
