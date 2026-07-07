#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download ThreatConnect Owner Information Command"""
# standard library
import os
import sys
from collections import OrderedDict

# third-party
from base_generating_command import BaseGeneratingCommand
from splunklib.searchcommands import Configuration, dispatch


@Configuration()
class OwnerDownloadCommand(BaseGeneratingCommand):
    """Command to download owner data from ThreatConnect API.

    Usage:
    | tcowners
    """

    # properties
    _command = 'tcowners'
    _owner_data_dict = None
    filename = os.path.basename(__file__)
    ks_owner_data = None
    owner_id_tracker = []

    def add_result(self, action, id_, name, type_):
        """Return ordered dict for results."""
        self.logger.info(f'action={action}, id={id_}, name="{name}", type={type_}')
        result_data = OrderedDict()
        result_data['Action'] = action
        result_data['ID'] = id_
        result_data['Name'] = name
        result_data['Type'] = type_
        self.results.append(result_data)

    def delete_owners(self):
        """Delete owners that have been removed from ThreatConnect"""
        for owner_id, owner_data in self.owner_data_dict.items():
            if owner_id not in self.owner_id_tracker:
                self.add_result('delete', owner_id, owner_data.get('name'), 'kvs-entry')
                self.tcs.collections.owners.delete_by_id(owner_data.get('_key'))

    def generate(self):
        """Implement generate command for downloading owners."""
        # retrieve owner data from ThreatConnect
        for owner_data in self.retrieve_owners():
            self.process_owner(owner_data)

        # delete owners not in ThreatConnect
        self.delete_owners()

        # display the results
        for r in self.results:
            yield r

    @property
    def owner_data_dict(self):
        """Return owner data dict with id as key and data as value."""
        if self._owner_data_dict is None:
            self._owner_data_dict = {}
            for owner_data in self.tcs.collections.owners.query():
                self._owner_data_dict[owner_data.id] = owner_data
        return self._owner_data_dict

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

    def process_owner(self, owner_data):
        """Process the Owner Data

        Args:
            owner_data (dict): Response object from TC API.
        """
        # add current owner id to owner id tracker
        self.owner_id_tracker.append(owner_data.get('id'))

        if int(owner_data.get('id')) not in self.owner_data_dict:
            # id doesn't exist must be a new owner
            self.process_owner_add(owner_data)
            self.add_result('add', owner_data.get('id'), owner_data.get('name'), 'kvs-entry')
        else:
            action = 'skip'
            data = self.owner_data_dict.get(owner_data.get('id'))
            if data.get('name') != owner_data.get('name'):
                action = 'update'
                # then rename owner
                self.process_owner_update(data, owner_data)
            self.add_result(action, owner_data.get('id'), owner_data.get('name'), 'kvs-entry')

    def process_owner_add(self, owner_data):
        """Add Owner data to KV Store

        Args:
            owner_data (dict): Response object from TC API.
        """
        data = {
            'id': owner_data.get('id'),
            'name': owner_data.get('name'),
            'type': owner_data.get('type'),
        }
        # insert new owner and collection _key
        data['_key'] = self.tcs.collections.owners.insert(data).get('_key')

        # add new owner to owner data dict
        self.owner_data_dict[owner_data.get('id')] = data

    def process_owner_update(self, data, owner_data):
        """Update Owner data in the KV Store

        Args:
            data (dict): KV Store owner data.
            owner_data (dict): Response object from TC API.
        """
        data['name'] = owner_data.get('name')
        self.tcs.collections.owners.update(data.get('_key'), data)

    def retrieve_owners(self):
        """Load Owner Data"""
        return self.tcs.request.owner_data


if __name__ == '__main__':
    try:
        dispatch(OwnerDownloadCommand, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception:
        # standard library
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
