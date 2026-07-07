#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Playbook Filter by Label Command."""
import sys
import os

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration(local=True)
class PlaybooksFilterByLabels(BaseGeneratingCommand):
    """Playbook filter by label command."""

    # args
    # name of filter: pb_adaptive_response_filter, pb_event_triage_filter, pb_workflow_action_filter
    filter_name = Option(doc='The config property name to filter on.', require=False)
    labels = Option(doc='A comma delimited list of labels to filter on.', require=False)

    # properties
    _label_filters = []
    # properties
    filename = os.path.basename(__file__)

    def generate(self):
        """Implement generate command for filtering a playbook."""
        self.update_inputs()

        results = []
        for p in self.tcs.collections.playbooks.paginate():
            # filter based on type
            if self._label_filters:
                for label in p.get('labels'):
                    if label in self._label_filters:
                        break
                else:
                    continue
            results.append(p)

        # display results
        for r in results:
            yield r

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

    def update_inputs(self):
        """Update the input data."""
        # get filters from configuration settings
        if self.filter_name:
            self._label_filters.extend(self.tcs.config.properties.get(self.filter_name, []))

        # add labels to filter
        if self.labels:
            self._label_filters.extend([x.strip() for x in self.labels.split(',') if x])


if __name__ == '__main__':
    dispatch(PlaybooksFilterByLabels, sys.argv, sys.stdin, sys.stdout, __name__)
