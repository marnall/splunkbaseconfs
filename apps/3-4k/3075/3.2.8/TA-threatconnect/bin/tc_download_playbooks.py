#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Playbook Download Command."""
import sys
import os
import json
from collections import OrderedDict

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from splunklib.searchcommands import dispatch, Configuration


@Configuration()
class PlaybooksDownload(BaseGeneratingCommand):
    """Command to download playbook data.

    This command is used by the Playbooks -> Playbooks menu item to manage Playbook
    data in the KV store. It performs adds, deletes, and updates are required.

    Usage:
    | tcplaybooks
    """

    # properties
    filename = os.path.basename(__file__)

    def add_result(self, action, item, data):
        """Return ordered dict for results."""
        self.logger.info(f'action="{action}", item={item}, data={data}')
        result_data = OrderedDict()
        result_data['Action'] = action
        result_data['Item'] = item
        result_data['Data'] = data
        self.results.append(result_data)

    def disable_wfa(self, playbook_key):
        """Disable workflow actions that use deleted playbooks."""
        stanza_names = []
        for wfa in self.tcs.collections.workflow_playbook_actions.paginate(
            fields='_key', query=json.dumps({'playbook_key': playbook_key})
        ):
            stanza_names.append(f'''tc_custom[key:{wfa.get('_key')}]''')

        for stanza in stanza_names:
            stanza_data = self.service.confs['workflow_actions'][stanza].update(**{'disabled': '1'})

            # add results
            self.add_result(
                action='disable', item=f'wfa-stanza-{stanza}', data=json.dumps(stanza_data.content)
            )

    def generate(self):
        """Implement generate command for downloading playbooks."""
        # get current playbooks from kvstore
        collection_data = {}
        for r in self.tcs.collections.playbooks.paginate():
            if str(r.get('id')) in collection_data:
                # remove duplicates
                self.tcs.collections.playbooks.delete_by_id(r.get('_key'))
                continue
            collection_data[str(r.get('id'))] = r

        # get playbooks from TC api
        for p in self.get_playbooks():
            if p.get('triggerType') == 'HttpLink':
                # filter labels
                if self.tcs.config.pb_label_filter:
                    for label in p.get('labels'):
                        if label in self.tcs.config.pb_label_filter:
                            break
                    else:
                        continue

                cd = collection_data.pop(str(p.get('id')), None)
                action = 'add'
                if cd is not None:
                    action = 'update'
                    p['username'] = cd.get('username')
                    p['password'] = cd.get('password')
                    p['_key'] = cd.get('_key')
                self.tcs.collections.playbooks.batch_data(p)

                # add results
                self.add_result(action=action, item='playbook', data=json.dumps(p))

        # save any remaining updates
        self.tcs.collections.playbooks.batch_save()

        # delete any playbooks in the kvstore that were not returned by api
        for pb_data in collection_data.values():
            key = pb_data.get('_key')
            self.tcs.collections.playbooks.delete_by_id(key)
            # disable wfa that use deleted playbooks
            self.disable_wfa(key)

            # add results
            self.add_result(action='delete', item='playbook', data=json.dumps(pb_data))

        # display results
        for r in self.results:
            yield r

    def get_playbooks(self):
        """Download playbooks data from ThreatConnect API."""
        # try public API endpoint first (5.8 or newer)
        playbook_data = self.get_playbooks_public()
        if playbook_data is None:
            # no results or bad schema (5.7) try internal
            playbook_data = self.get_playbooks_internal() or []

        for pbd in playbook_data:
            yield pbd

    def get_playbooks_public(self):
        """Download playbooks data from ThreatConnect API (for 5.7 labels issue)."""
        r = self.tcs.session.get('/v2/playbooks/search', params={'resultLimit': 5000})
        if not r.ok:
            err = r.text or r.reason
            self.error_exit(None, f'Could not retrieve playbooks ({err}).')
        return r.json().get('data', {}).get('playbooks')

    def get_playbooks_internal(self):
        """Download playbooks data from ThreatConnect API (for 5.7 labels issue)."""
        r = self.tcs.session.get('/internal/playbooks/search', params={'limit': 5000})
        if not r.ok:
            err = r.text or r.reason
            self.error_exit(None, f'Could not retrieve playbooks ({err}).')
        return r.json().get('results')

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return


if __name__ == '__main__':
    dispatch(PlaybooksDownload, sys.argv, sys.stdin, sys.stdout, __name__)
