#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Playbook Workflow Action Update Command."""
import json
import os
import sys
from collections import OrderedDict

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from base_playbook_workflow_action import BasePlaybookWorkflowAction
from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class PlaybookWorkflowActionUpdate(BaseGeneratingCommand, BasePlaybookWorkflowAction):
    """Playbook Workflow Action Update Command."""

    # args
    key = Option(doc='The key of the workflow action', require=True)
    disabled = Option(doc='The description of the workflow action.', require=True)
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

    def generate(self):
        """Implement generate command for updating a playbook workflow action."""
        self.update_workflow_kv_data()
        self.update_workflow_config()

        # yield search results
        for r in self.results:
            yield r

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

        # update args
        self.disabled = self.tcs.utils.to_bool(self.disabled)

    def update_workflow_kv_data(self):
        """Update Workflow Action KVStore Data."""
        if not self.workflow_action_stanza_exists:
            return

        if self.description:
            self.workflow_action_kv_data['description'] = self.description
        if self.method:
            self.workflow_action_kv_data['method'] = self.method
        if self.params:
            self.workflow_action_kv_data['params'] = json.loads(self.params)
        if self.playbook_key:
            self.workflow_action_kv_data['playbook_key'] = self.playbook_key

        status = 'Success'
        try:
            self.service.kvstore['tc_workflow_playbook_actions'].data.update(
                self.key, json.dumps(self.workflow_action_kv_data)
            )
        except Exception:
            status = 'Failed'

        # results
        result_data = OrderedDict()
        result_data['Action'] = f'Updated WFA KvStore entry ({self.key})'
        result_data['Data'] = json.dumps(self.workflow_action_kv_data, indent=2)
        result_data['Status'] = status
        self.results.append(result_data)

    def update_workflow_config(self):
        """Update System Workflow Action Config."""
        if not self.workflow_action_kv_data:
            return

        search_string = f'|tclaunchwfa wfa_key={self.key}'
        for param in json.loads(self.params):
            search_string += f" {param.get('key')}=\"{param.get('value')}\""

        content = self.workflow_action_stanza.content
        self.logger.debug(f'content {content}')

        content['display_location'] = self.display_location
        content['eventtypes'] = self.event_types
        # if not content.get('eventtypes'):
        #     content.pop('eventtypes', None)
        content['fields'] = self.fields
        content['label'] = self.label
        content['search.search_string'] = search_string
        content['disabled'] = self.disabled

        # remove null fields
        content = {k: v for k, v in content.items() if v}

        # delete and add because update doesn't remove empty fields
        self.service.confs['workflow_actions'].delete(self.stanza_name)

        status = 'Success'
        try:
            stanza = self.service.confs['workflow_actions'].create(self.stanza_name, **content)
        except Exception:
            status = 'Failed'

        # results
        result_data = OrderedDict()
        result_data['Action'] = f'Update WFA config ({self.stanza_name})'
        result_data['Data'] = json.dumps(stanza.content, indent=2)
        result_data['Status'] = status
        self.results.append(result_data)


if __name__ == '__main__':
    dispatch(PlaybookWorkflowActionUpdate, sys.argv, sys.stdin, sys.stdout, __name__)
