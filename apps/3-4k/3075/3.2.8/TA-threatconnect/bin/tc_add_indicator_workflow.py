#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Add Indicator Workflow"""
import sys
import time
import os
from urllib.parse import unquote, quote

# must be imported before packages in bin/lib
from base_eventing_command import BaseEventingCommand

from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class AddIndicatorCommand(BaseEventingCommand):
    """Command to report data back to ThreatConnect API.

    This command is used by the Event Triage page to mark a multiple events
    as "False Positive" or "Reviewed".

    Usage:
    | tcworkflowaddindicator indicator=$src$ indicator_type=Address source=$source$
      sourcetype=$sourcetype$ raw=$_raw$

    e.g.,
    | tcworkflowaddindicator indicator="170.180.190.200" indicator_type="Address"
      sourcetype="PFSense" rating="5" confidence="77" raw="a log file entry"
      tags="one,two" source="udp:514"
    """

    filename = os.path.basename(__file__)
    # args
    confidence = Option(doc='The confidence rating for the provided indicator.', require=False)
    # group_ids = Option(
    #     default='',
    #     doc='A comma separated list of group id to associate to the indicator.',
    #     require=False
    # )
    indicator = Option(doc='The indicator value to add.', require=True)
    indicator_type = Option(doc='The indicator type for the provided indicator.', require=True)
    owner = Option(doc='The owner name where the indicator should be added.', require=False)
    rating = Option(doc='The threat rating for the provided indicator.', require=False)
    raw = Option(doc='The raw data for the event.', require=False)
    source = Option(doc='The source of the event.', require=False)
    sourcetype = Option(doc='The sourcetype of the event', require=False)
    tags = Option(default='', doc='A comma separated list of tags values.', require=False)

    def transform(self, records):
        """Implement generate command for adding a indicator workflow."""

        if self.raw is not None:
            attribute_length = None
            safe_indicator_type = quote(self.indicator_type, safe='')
            r = self.tcs.session.get(f'/v2/types/attributeTypes?filters=type={safe_indicator_type}')
            if r.ok:
                types = r.json().get('data', {}).get('attributeType', [])
                for attribute_type in types:
                    if attribute_type.get('name') == 'Events':
                        attribute_length = attribute_type.get('maxSize', 500)
                if attribute_length and len(self.raw) > attribute_length:
                    self.raw = self.raw[: (attribute_length - 3)] + '...'
            if not attribute_length:
                self.raw = None

        indicator_data = {
            'associatedGroup': [],
            'attribute': [],
            'summary': self.indicator,
            'tag': [],
            'type': self.indicator_type,
        }

        if self.rating is not None:
            indicator_data['rating'] = self.rating

        if self.confidence is not None:
            indicator_data['confidence'] = self.confidence

        if self.raw is not None:
            indicator_data['attribute'].append({'type': 'Events', 'value': self.raw})

        if self.source is not None:
            indicator_data['attribute'].append({'type': 'Source', 'value': self.source})

        # for g_id in self.group_ids:
        #     indicator_data['associatedGroup'].append(g_id)

        for tag in self.tags:
            indicator_data['tag'].append({'name': tag})

        self.tcs.logger.debug(f'indicator_data: {indicator_data}')

        response = {}
        try:
            batch_data = {'indicator': [indicator_data]}
            response = self.tcs.request.batch(batch_data, self.owner)
            self.tcs.logger.debug(f'response: {response}')
        except Exception as e:
            self.error_exit(None, f'Failed to add indicator ({e}).')

        batch_status = response.get('data', {}).get('batchStatus', {})
        batch_status['_time'] = time.time()
        self.tcs.logger.debug(f'batch_status: {batch_status}')
        yield batch_status

    def log_args(self):
        """Log provide args."""
        self.logger.info(f'indicator={self.indicator}')
        self.logger.info(f'indicator_type={self.indicator_type}')
        self.logger.info(f'owner={self.owner}')
        self.logger.info(f'confidence rating={self.confidence}')
        self.logger.info(f'threat rating={self.rating}')
        self.logger.info(f'tags={self.tags}')

        # attribute fields
        self.logger.info(f'raw={self.raw}')
        self.logger.info(f'source={self.source}')
        self.logger.info(f'sourcetype={self.sourcetype}')

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

        # update options
        # self.group_ids = [g for g in self.group_ids.strip().split(',') if g]
        self.owner = self.owner or self.tcs.request.default_owner
        self.tags = [t for t in self.tags.strip().split(',') if t]

        if self.raw:
            self.raw = unquote(self.raw)
        if self.source is not None and self.sourcetype is not None:
            self.source = f'Splunk: {self.sourcetype} ({self.source})'


if __name__ == '__main__':
    dispatch(AddIndicatorCommand, sys.argv, sys.stdin, sys.stdout, __name__)
