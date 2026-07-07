#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Launching a Playbook Command"""
import sys
import os
import re
import json
from requests import request
from requests.auth import HTTPBasicAuth

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

import splunklib.results as results
from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class LaunchPlaybookCommand(BaseGeneratingCommand):
    """Command to launch a ThreatConnect Playbook.

    This command is used by the Event Triage page to kick off a playbook passing in specific
    fields as URL params or the entire event as the request body.

    Usage:
    | tclaunchplaybook
        tc_builtin_method_type=<GET|POST|Defaults=GET>
        tc_builtin_playbook=<Playbook Key>
        params=<GET Params>
        tc_builtin_owner=<Owner Name>

    e.g.,
    | tclaunchplaybook
        tc_builtin_playbook=5ec3e492bbbbbfefb657e7ae
        tc_builtin_method_type=GET
        tc_builtin_uuid=25dbfb7b-bad6-4090-b84b-789a86228e9f
        tc_builtin_owner="TCI"
        params="[
            {\"key\":\"id\",\"value\":\"2001\"},
            {\"key\":\"severity\",\"value\":\"critical\"},
            {\"key\":\"fwrule\",\"value\":\"60001\"}
        ]"
    """

    # args
    params = Option(doc='The parameters to pass in to GET requests to the playbook', require=False)
    tc_builtin_method_type = Option(
        doc='What type of request to make to the playbook.', require=False, default='GET'
    )
    tc_builtin_playbook = Option(doc='The playbook key.', require=True)
    tc_builtin_uuid = Option(doc='The event_data key.', require=False)
    tc_builtin_owner = Option(doc='The name of the owner the playbook resides in.', require=False)

    # properties
    _playbook_kv_data = None
    filename = os.path.basename(__file__)

    def generate(self):
        """Implement generate method to launch playbook.

        Send the entire event via POST or user selected values via query parameters.
        """
        # defaults
        auth = None
        body = None
        headers = {'Content-Type': 'application/json'}
        params = {}
        url = re.sub(r'^http://', 'https://', self.playbook_kv_data.get('endpoint'))

        # auth
        if self.playbook_kv_data.get('basicAuthEnabled'):
            username = self.playbook_kv_data.get('username', None)
            password = self.tcs.config.get_storage_password(
                f"tcPlaybooks:{self.playbook_kv_data.get('id')}:"
            )
            auth = HTTPBasicAuth(username, password)
        if self.tc_builtin_uuid and self.tc_builtin_owner and self.tc_builtin_method_type == 'POST':
            body = self.retrieve_results(self.tc_builtin_owner, self.tc_builtin_uuid)
            method = 'POST'
        else:
            method = 'GET'
            for param in json.loads(self.params):
                key = param.get('key')
                if key in params:
                    if not isinstance(params.get(key), list):
                        params[key] = [params.get(key)]
                    params[key].append(param.get('value'))
                params[key] = param.get('value')

        # launch the playbook
        try:
            r = request(
                method,
                url,
                auth=auth,
                headers=headers,
                json=body,
                params=params,
                proxies=self.tcs.proxies,
                verify=self.tcs.config.tc_verify_ssl,
            )
        except Exception as e:
            self.error_exit(None, f'Failed launching playbook ({e}).')

        if not r.ok:
            error = r.text or r.reason
            self.error_exit(
                None,
                'Playbook execution returned an error. Please ensure the '
                f'playbook is enabled and properly configured. ({error})',
            )

        response_data = {
            'length': len(r.content),
            'playbook': self.playbook_kv_data.get('name'),
            'playbook_endpoint': url,
            'response': r.text,
            'status': r.status_code,
        }

        yield response_data

    @property
    def playbook_kv_data(self):
        """Return workflow action kv data."""
        if self._playbook_kv_data is None:
            playbook_kvstore = self.service.kvstore['tc_playbooks']
            self._playbook_kv_data = playbook_kvstore.data.query_by_id(self.tc_builtin_playbook)
        return self._playbook_kv_data

    def retrieve_results(self, owner, uuid):
        """Retrieve the event data.

        Args:
            owner (str): The owner name.
            uuid (str): The UUID of the event.
        """
        query = (
            f'|search index=tc_event_data uuid={uuid} AND indicatorOwnerName="{owner}" '
            f'|join type=inner uuid [ |inputlookup tces where uuid={uuid}] |fields *'
        )
        indicators = self.tcs.search(query)
        try:
            # only 1 results expected at anytime.
            data = {}
            for indicator in results.ResultsReader(indicators.results()):
                data = indicator

            # update data format and only keep fields related to the event
            data['labels'] = data.get('labels', '').split('\n')
            del data['_bkt']
            del data['_cd']
            del data['_indextime']
            del data['_raw']
            del data['_serial']
            del data['_si']
            del data['_sourcetype']
            del data['_time']
            del data['linecount']
            del data['punct']
            del data['sourcetype']
            del data['timestamp']

            return data
        except IndexError:
            self.error_exit(None, f'Could not find event with UUID: {uuid}.')


if __name__ == '__main__':
    dispatch(LaunchPlaybookCommand, sys.argv, sys.stdin, sys.stdout, __name__)
