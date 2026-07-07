#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Playbook Workflow Action Add Command."""
import json
import sys
import os
from collections import OrderedDict

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from base_playbook_workflow_action import BasePlaybookWorkflowAction
from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class PlaybookWorkflowActionAddCommand(BaseGeneratingCommand, BasePlaybookWorkflowAction):
    """Playbook Workflow Action Add Command."""

    # args
    disabled = Option(doc='The disabled status of the workflow action.', require=True)
    description = Option(doc='The description of the workflow action.', require=True)
    display_location = Option(doc='The display location of the workflow action.', require=True)
    event_types = Option(doc='The event types of the workflow action.', require=True)
    fields = Option(doc='The fields of the workflow action.', require=True)
    label = Option(doc='The label of the workflow action.', require=True)
    method = Option(doc='The request method of the workflow action.', require=True)
    params = Option(doc='The params status of the workflow action.', require=True)
    playbook_key = Option(doc='The playbook key status of the workflow action.', require=True)
    # properties
    filename = os.path.basename(__file__)

    def add_workflow_kv_data(self):
        """Add Workflow Action KVStore Data."""
        workflow_action_data = {
            'description': self.description,
            'method': self.method,
            'params': json.loads(self.params),
            'playbook_key': self.playbook_key,
        }
        self.key = (
            self.service.kvstore['tc_workflow_playbook_actions']
            .data.insert(data=json.dumps(workflow_action_data))
            .get('_key')
        )

        # status
        status = 'Success'
        if self.workflow_action_kv_data is None:
            status = 'Failed'

        # results
        result_data = OrderedDict()
        result_data['Action'] = f'Create WFA KvStore entry ({self.key})'
        result_data['Data'] = json.dumps(self.workflow_action_kv_data, indent=2)
        result_data['Status'] = status
        self.results.append(result_data)

    def add_workflow_config(self):
        """Add Workflow Action Config."""
        search_string = f'|tclaunchwfa wfa_key={self.key}'
        for param in json.loads(self.params):
            search_string += f''' {param.get('key')}=\"{param.get('value')}\"'''

        workflow_action_config = {
            'disabled': self.disabled,
            'display_location': self.display_location,
            'fields': self.fields,
            'label': self.label,
            'search.app': 'TA-threatconnect',
            'search.search_string': search_string,
            'search.preserve_timerange': True,
            'type': 'search',
        }
        if self.event_types:
            workflow_action_config['eventtypes'] = self.event_types
        if self.key:
            stanza = self.service.confs['workflow_actions'].create(
                self.stanza_name, **workflow_action_config
            )

        # status
        status = 'Success'
        if not self.workflow_action_stanza_exists:
            status = 'Failed'

        # results
        result_data = OrderedDict()
        result_data['Action'] = f'Create WFA config ({self.stanza_name})'
        result_data['Data'] = json.dumps(stanza.content, indent=2)
        result_data['Status'] = status
        self.results.append(result_data)

    def generate(self):
        """Implement generate command for creating a playbook workflow action."""
        self.add_workflow_kv_data()
        self.add_workflow_config()

        # yield search results
        for r in self.results:
            yield r

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

        # update args
        self.disabled = self.tcs.utils.to_bool(self.disabled)


if __name__ == '__main__':
    dispatch(PlaybookWorkflowActionAddCommand, sys.argv, sys.stdin, sys.stdout, __name__)
