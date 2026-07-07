#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Playbook Workflow Action Command.

https://docs.splunk.com/DocumentationStatic/PythonSDK/1.6.5/searchcommands.html
"""


class BasePlaybookWorkflowAction(object):
    """Playbook Workflow Action Parent Class."""

    # properties
    _workflow_action_config = None
    _workflow_action_kv_data = {}
    key = None
    metadata = None
    service = None
    tcs = None

    @property
    def stanza_name(self):
        """Return workflow action stanza name."""
        return f'tc_custom[key:{self.key}]'

    @property
    def workflow_action_stanza_exists(self):
        """Return True if Workflow Action Stanza exists."""
        for stanza in self.service.confs['workflow_actions'].list():
            if stanza.name == self.stanza_name:
                return True
        return False

    @property
    def workflow_action_stanza(self):
        """Return Workflow Action Config."""
        if self._workflow_action_config is None:
            conf = self.service.confs['workflow_actions']
            try:
                self._workflow_action_config = conf[self.stanza_name]
            except AttributeError:
                pass
        return self._workflow_action_config

    @property
    def workflow_action_kv_data(self):
        """Return workflow action kv data."""
        if self._workflow_action_kv_data is None:
            wfa_kvstore = self.service.kvstore['tc_workflow_playbook_actions']
            self._workflow_action_kv_data = wfa_kvstore.data.query_by_id(self.key)
        return self._workflow_action_kv_data
