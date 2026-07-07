#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Launch Workflow Action Command."""
import os
import re
import sys
from uuid import uuid4
from collections import OrderedDict

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from requests import request
from requests.auth import HTTPBasicAuth
from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class LaunchWfaCommand(BaseGeneratingCommand):
    """Command to launch a ThreatConnect Workflow Action.

    This command is used in the search results to trigger a configured Workflow Action passing the
    configured fields in as URL params or the entire event as the request body.

    Usage:
    | tclaunchwfa wfa_key=<Workflow Action Key>

    e.g.,
    | tclaunchwfa wfa_key=5ec3e492bbbbbfefb657e7ae
    """

    # args
    wfa_key = Option(doc='The WFA KV Store key.', require=True)

    # properties
    _playbook_kv_data = None
    _wfa_kv_data = None
    filename = os.path.basename(__file__)

    # add dynamic options
    for name in (v.group(1) for v in re.finditer(r'(\w+)=([^\s]+)', ' '.join(sys.argv[2:]))):
        if name == 'wfa_key':
            continue
        vars()[f'{str(uuid4())}'] = Option(name=name)

    def add_result(self, length, playbook, playbook_endpoint, response, status):
        """Return ordered dict for results."""
        result_data = OrderedDict()
        result_data['length'] = length
        result_data['playbook'] = playbook
        result_data['playbook_endpoint'] = playbook_endpoint
        result_data['response'] = response
        result_data['status'] = status
        self.results.append(result_data)

    def generate(self):
        """Implement generate method for demo data and results."""
        self.launch()

        # display results
        for r in self.results:
            yield r

    def launch(self):
        """Call the playbook via HTTP Trigger.

        Send the entire event via POST or user selected values via query parameters.
        """
        # defaults
        auth = None
        body = None
        headers = {'Content-Type': 'application/json'}
        url = re.sub(r'^http://', 'https://', self.playbook_kv_data.get('endpoint'))

        # auth
        if self.playbook_kv_data.get('basicAuthEnabled'):
            username = self.playbook_kv_data.get('username', None)
            password = self.tcs.config.get_storage_password(
                f"tcPlaybooks:{self.playbook_kv_data.get('id')}:"
            )
            auth = HTTPBasicAuth(username, password)

        method = self.wfa_kv_data.get('method', 'GET')

        params = {}
        for name, val in self.options.items():
            if name in [
                'wfa_key',
                'logging_configuration',
                'logging_level',
                'record',
                'show_configuration',
            ]:
                continue
            params[name] = val.value

        if method == 'POST':
            body = params
            params = {}

        # launch the playbook
        try:
            r = request(
                method=method,
                url=url,
                auth=auth,
                headers=headers,
                json=body,
                params=params,
                proxies=self.tcs.proxies,
                verify=self.tcs.config.tc_verify_ssl,
            )
        except Exception as e:
            self.error_exit(None, f'Failed launching playbook ({e})')

        if not r.ok:
            error = r.text or r.reason
            self.error_exit(
                None,
                f'Playbook exectution returned an error. Please ensure the playbook is enabled and '
                f'properly configured. ({error})',
            )

        # add result to be displayed
        self.add_result(
            len(r.content), self.playbook_kv_data.get('name'), url, r.text, r.status_code
        )

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

    @property
    def playbook_kv_data(self):
        """Return workflow action kv data."""
        if self._playbook_kv_data is None:
            self._playbook_kv_data = self.tcs.collections.playbooks.query_by_id(
                key=self.wfa_kv_data.get('playbook_key')
            )
        return self._playbook_kv_data

    @property
    def wfa_kv_data(self):
        """Return workflow action kv data."""
        if self._wfa_kv_data is None:
            self._wfa_kv_data = self.tcs.collections.workflow_playbook_actions.query_by_id(
                key=self.wfa_key
            )
        return self._wfa_kv_data


if __name__ == '__main__':
    dispatch(LaunchWfaCommand, sys.argv, sys.stdin, sys.stdout, __name__)
