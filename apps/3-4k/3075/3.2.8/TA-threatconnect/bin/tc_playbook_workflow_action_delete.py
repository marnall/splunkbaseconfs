#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Playbook Workflow Action Delete Command."""
import sys
import os
from collections import OrderedDict

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from base_playbook_workflow_action import BasePlaybookWorkflowAction
from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class PlaybookWorkflowActionDeleteCommand(BaseGeneratingCommand, BasePlaybookWorkflowAction):
    """Playbook Workflow Action Delete Command."""

    # args
    key = Option(doc='The key of the workflow action', require=True)
    # properties
    filename = os.path.basename(__file__)

    def delete_workflow_kv_data(self):
        """Add Workflow Action KVStore Data."""
        status = 'Success'
        try:
            self.service.kvstore['tc_workflow_playbook_actions'].data.delete_by_id(self.key)
        except Exception:
            status = 'Failed'

        # results
        result_data = OrderedDict()
        result_data['Action'] = f'Delete WFA KvStore entry ({self.key})'
        result_data['Status'] = status
        self.results.append(result_data)

    def delete_workflow_config(self):
        """Add Workflow Action KVStore Data."""
        if self.workflow_action_stanza_exists:
            self.service.confs['workflow_actions'].delete(self.stanza_name)

        # status
        status = 'Success'
        if self.workflow_action_stanza_exists:
            status = 'Failed'

        # results
        result_data = OrderedDict()
        result_data['Action'] = f'Delete WFA config ({self.stanza_name})'
        result_data['Status'] = status
        self.results.append(result_data)

    def generate(self):
        """Implement generate command for deleting a playbook workflow action."""
        self.delete_workflow_kv_data()
        self.delete_workflow_config()

        # yield search results
        for r in self.results:
            yield r


if __name__ == '__main__':
    dispatch(PlaybookWorkflowActionDeleteCommand, sys.argv, sys.stdin, sys.stdout, __name__)
