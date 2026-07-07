#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Label Manager"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

import splunklib.results as results  # pylint: disable=wrong-import-position


class BaseLabelManager:
    """ThreatConnect Base Label Manager Class"""

    # properties
    logger = None
    tcs = None

    def add_result(self, action, label):
        """Implement in Child Class"""
        raise NotImplementedError('Child class must implement this method.')

    def refresh_labels(self):
        """Refetch and dedup labels"""
        labels = self.tcs.search(
            '| inputlookup tces where labels=* '
            '| dedup labels '
            '| mvexpand labels '
            '| dedup labels '
            '| fields labels'
        )

        # wait until search is complete to ensure label are unavailable for shortest period of time
        self.tcs.collections.labels.delete()
        self.add_result('clearing labels', '__all__')

        for label_data in results.ResultsReader(labels.results()):
            if label_data in [None, '', ' ']:
                continue

            label = label_data.get('labels').strip()
            self.tcs.collections.labels.batch_data({'name': label})
            self.add_result('add-label', label)

        # save any remaining data
        self.tcs.collections.labels.batch_save()
