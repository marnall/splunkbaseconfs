#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download ThreatConnect Owner Information Command"""
import os
import random
import re
import sys
from collections import OrderedDict
from datetime import datetime

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from dateutil.relativedelta import relativedelta
from splunklib.searchcommands import dispatch, Configuration


@Configuration()
class OwnerDownloadCommand(BaseGeneratingCommand):
    """Command to download owner data from ThreatConnect API.

    This command is used by the Indicator Download page to manage Owner data
    in the KV store. It performs adds, deletes, and updates are required.

    Usage:
    | tcowner
    """

    # properties
    _owner_data_dict = None
    filename = os.path.basename(__file__)
    g_stanza_prefix = 'TC-Group-Download'
    i_stanza_prefix = 'TC-Indicator-Download'
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

    def create_saved_searches(self):
        """Add indicator and group saved searches"""
        cron_time = datetime(2008, 12, 12, 0, random.randint(0, 59))  # nosec

        for owner_id, owner_data in sorted(self.owner_data_dict.items()):
            self.saved_search_indicator_create(owner_id, owner_data, cron_time)
            self.saved_search_group_create(owner_id, owner_data, cron_time)
            cron_time = cron_time + relativedelta(minutes=+10)

    def delete_owners(self):
        """Delete owners that have been removed from ThreatConnect"""
        for owner_id, owner_data in self.owner_data_dict.items():
            if owner_id not in self.owner_id_tracker:
                self.add_result('delete', owner_id, owner_data.get('name'), 'kvs-entry')
                self.tcs.collections.owners.delete_by_id(owner_data.get('_key'))

                # remove saved searches
                self.saved_search_group_delete(owner_id)
                self.saved_search_indicator_delete(owner_id)

                # clear indicator for deleted owner
                self.delete_owners_indicators(owner_data.get('name'))

    def delete_owners_indicators(self, owner):
        """Delete Owner data in KV Store"""
        query = {'ownerName': owner}
        self.tcs.collections.indicators.delete(query=query)

    def generate(self):
        """Implement generate command for downloading owners."""
        # retrieve owner data from ThreatConnect
        for owner_data in self.retrieve_owners():
            self.process_owner(owner_data)

        # add saved searches
        self.create_saved_searches()

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
                # remove indicator first
                self.process_owner_update_indicators(owner_data)

                # then rename owner
                self.process_owner_update(data, owner_data)
            self.add_result(action, owner_data.get('id'), owner_data.get('name'), 'kvs-entry')

    def process_owner_add(self, owner_data):
        """Add Owner data to KV Store

        Args:
            owner_data (dict): Response object from TC API.
        """
        data = {
            'filterIndicatorTypes': self.tcs.request.indicator_types,
            'filterFalsePositive': -1,
            'filterTags': [],
            'filterTagsExclude': [],
            'filterRating': 3,
            'filterConfidence': 50,
            'groupTypes': self.tcs.request.group_types,
            'id': owner_data.get('id'),
            # null allows for 'Unknown' to be displayed in UI
            # 'indicatorCount': 0,
            # 'indicatorCountApi': 0,
            'lastRun': None,
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

    def process_owner_update_indicators(self, owner_data):
        """Update ownerName for indicators after owner rename.

        Args:
            owner_data (dict): Response object from TC API.
        """
        query = {'ownerId': owner_data.get('id')}
        for data in self.tcs.collections.indicators.query(query=query):
            data['ownerName'] = owner_data.get('name')
            self.tcs.collections.indicators.batch_data(data)

        # save any remaining items
        self.tcs.collections.indicators.batch_save()

    def retrieve_owners(self):
        """Load Owner Data"""
        return self.tcs.request.owner_data

    def saved_search_indicator_create(self, owner_id, owner_data, cron_time):
        """Save indicator download saved search"""
        name = f'{self.i_stanza_prefix}-{owner_id}'
        key = owner_data.get('_key')
        search = f'| tciocdownload owner_key={key}'

        try:
            # check for existing saved search with this name
            saved_search = self.service.saved_searches[name]
            search = saved_search['search']
            pattern = r'.*owner_key=(\w+)'
            z = re.match(pattern, search)
            if not z:
                return
            previous_key = z.groups()[0].strip()
            if previous_key == key:
                return
            new_search = search.replace(previous_key, key)
            kwargs = {
                'search': new_search,
                'cron_schedule': saved_search['cron_schedule'],
                'description': saved_search['description'],
                'disabled': saved_search['disabled'],
            }
            saved_search.update(**kwargs).refresh()
        except KeyError:
            # add new saved search
            ss = self.service.saved_searches.create(name, search)
            description = f'ThreatConnect Indicator Download for "{owner_data["name"]}".'
            kwargs = {
                'cron_schedule': f'{cron_time.minute} {cron_time.hour} * * *',
                'description': description,
                'disabled': 'true',
            }
            ss.update(**kwargs).refresh()
            self.add_result('add', owner_id, name, 'saved-search')
            self.logger.info(f'action=add, item=saved-search, name={name}')

    def saved_search_group_create(self, owner_id, owner_data, cron_time):
        """Save group download saved search"""
        name = f'{self.g_stanza_prefix}-{owner_id}'
        search = f'''|tcgroupdownload owner_key={owner_data.get('_key')}'''
        try:
            # check for existing saved search with this name
            self.service.saved_searches[name]
        except KeyError:
            # add new saved search
            ss = self.service.saved_searches.create(name, search)
            kwargs = {
                'cron_schedule': f'{cron_time.minute} {cron_time.hour} * * *',
                'description': f"ThreatConnect Group Download for \"{owner_data['name']}\".",
                'disabled': 'true',
            }
            ss.update(**kwargs).refresh()
            self.add_result('add', owner_id, name, 'saved-search')
            self.logger.info(f'action=add, item=saved-search, name={name}')

    def saved_search_group_delete(self, owner_id):
        """Delete group download saved search"""
        name = f'{self.g_stanza_prefix}-{owner_id}'
        try:
            self.add_result('delete', owner_id, name, 'saved-search')
            self.logger.info(f'action=delete, item=saved-search, name={name}')
            self.service.saved_searches.delete(name)
        except KeyError:
            self.logger.warning(f'Could not delete saved search: {name}.')

    def saved_search_indicator_delete(self, owner_id):
        """Delete indicator download saved search"""
        name = f'{self.i_stanza_prefix}-{owner_id}'
        try:
            self.add_result('delete', owner_id, name, 'saved-search')
            self.logger.info(f'action=delete, item=saved-search, name={name}')
            self.service.saved_searches.delete(name)
        except KeyError:
            self.logger.warning(f'Could not delete saved search: {name}.')


if __name__ == '__main__':
    dispatch(OwnerDownloadCommand, sys.argv, sys.stdin, sys.stdout, __name__)
