#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Label Manager"""
import sys
import os
from collections import OrderedDict
from datetime import datetime  # pylint: disable=wrong-import-position

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from base_label_manager import BaseLabelManager
from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class LabelManagerCommand(BaseGeneratingCommand, BaseLabelManager):
    """Event label management command.

    Manages adding a label to specific event summaries, bulk applying them, or refreshing the
    labels collection.

    Usage:
    | tclabelmanager action=<action> key=<key> labels=<labels>
    """

    # args
    action = Option(default='set', doc='The action to take on the label.', require=True)
    key = Option(doc='The key of the event.', require=False)
    labels = Option(default='', doc='Comma delimited list of labels to apply.', require=False)

    # properties
    filename = os.path.basename(__file__)
    key_object = None
    last_updated = datetime.now().strftime('%s')

    def add_result(self, action, label):
        """Return ordered dict for results."""
        self.logger.info(f'action="{action}", label={label}')
        result_data = OrderedDict()
        result_data['Action'] = action
        result_data['Label'] = label
        self.results.append(result_data)

    def generate(self):
        """Implement generate method for demo data and results."""
        if self.action.lower() == 'set':
            self.set_labels_on_key_object()
        elif self.action.lower() == 'refresh_labels':
            self.refresh_labels()

        # display results
        for r in self.results:
            yield r

    def get_object_from_key(self, key):
        """Retrieve a event summary given the key

        Args:
            key: The summaries key.

        Returns: The summary object.
        """
        try:
            keyed_object = self.tcs.collections.event_summaries.query_by_id(key)
        except Exception:
            self.logger.error(f'ERROR: event summary not found from key: {key}.')
            return None

        if 'labels' not in keyed_object:
            keyed_object['labels'] = []

        return keyed_object

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

        # update args
        self.labels = [s for s in self.labels.split(',') if s]

        if self.action.lower() != 'refresh_labels' and self.key:
            self.key_object = self.get_object_from_key(self.key)

    def set_labels_on_key_object(self):
        """Set Labels on the keyed event summaries."""
        self.key_object['labels'] = self.labels
        self.key_object['lastUpdated'] = self.last_updated
        self.add_result('updating-labels', self.labels)
        self.tcs.collections.event_summaries.update(key=self.key, data=self.key_object)


if __name__ == '__main__':
    dispatch(LabelManagerCommand, sys.argv, sys.stdin, sys.stdout, __name__)
