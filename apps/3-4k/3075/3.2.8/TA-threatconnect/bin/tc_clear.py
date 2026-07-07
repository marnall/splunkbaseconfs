#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Clear Collection Command."""
import json
import os
import sys
from collections import OrderedDict

from base_generating_command import BaseGeneratingCommand
from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class KvStoreClearCommand(BaseGeneratingCommand):
    """Command to clear data from KV Store

    Used in the indicator download page to clear indicator collection for an owner.

    Usage:
    | tcclear collection=<collection name> owner_name=<owner name>

    e.g.,
    # list collections
    | tcclear collection=list

    # clear indicator collection
    | tcclear collection=tc_indicators

    # add a query for requests
    | tcclear collection=tc_event_summaries query="{\"eventTime\":{\"$lt\":1621002188}}"

    # clear all KV Store collections
    | tcclear collection=ALL confirm=YES
    """

    # args
    collection = Option(doc='The KV Store collection to be cleared.', require=True)
    confirm = Option(
        doc='If set to YES and collection is "ALL" then all collections will be cleared.',
        require=False,
    )
    query = Option(
        default='{}',
        doc=(
            'A string input containing a properly '
            'formatted query (e.g. {"eventTime":{"$lt":1609459200}}).'
        ),
        require=False,
    )
    indicator = Option(
        doc='An indicator value use to clear in some of the collections.', require=False
    )
    owner_name = Option(doc='The owner name to be cleared.', require=False)

    # properties
    filename = os.path.basename(__file__)

    @property
    def _q(self):
        try:
            return json.loads(self.query)
        except ValueError:
            self.error_exit(None, 'Invalid query provided.')

    def add_result(self, action, item, item_type):
        """Return ordered dict for results."""
        self.logger.info(f'action={action}, name={item}, type={item_type}')
        result_data = OrderedDict()
        result_data['Action'] = action
        result_data['Name'] = item
        result_data['Type'] = item_type
        self.results.append(result_data)

    def clear_tc_custom_search_settings(self):
        """Clear 'tc_customer_search_settings' KvStore."""

        # iterate all custom searches
        for config in self.tcs.collections.custom_search_settings.paginate():
            saved_search_name = f'''TC-Custom-Search-{config.get('_key')}'''
            try:
                self.service.saved_searches.delete(saved_search_name)
                self.add_result('delete', saved_search_name, 'saved search')
            except KeyError:
                self.logger.warning(f'Could not delete {saved_search_name}.')

        self.tcs.collections.custom_search_settings.delete(query=self._q)
        self.add_result('clear', 'tc_custom_search_settings', 'kvstore')

    def clear_tc_db_stats(self):
        """Clear 'tc_db_stats' KvStore."""
        self.tcs.collections.db_stats.delete(query=self._q)
        self.add_result('clear', 'tc_db_stats', 'kvstore')

    def clear_tc_dm_data(self):
        """Clear 'tc_dm_data' KvStore."""
        self.tcs.collections.dm_data.delete(query=self._q)
        self.add_result('clear', 'tc_dm_data', 'kvstore')

    def clear_tc_dm_search_settings(self):
        """Clear 'tc_dm_search_settings' KvStore."""
        # iterate all custom searches
        for config in self.tcs.collections.dm_search_settings.paginate():
            saved_search_name = f'''TC-DataModel-Search-{config.get('_key')}'''
            try:
                self.service.saved_searches.delete(saved_search_name)
                self.add_result('delete', saved_search_name, 'saved search')
            except KeyError:
                self.logger.warning(f'Could not delete {saved_search_name}.')

        self.tcs.collections.dm_search_settings.delete(query=self._q)
        self.add_result('clear', 'tc_dm_search_settings', 'kvstore')

    def clear_tc_download_stats(self):
        """Clear 'tc_download_stats' KvStore."""
        self.tcs.collections.download_stats.delete(query=self._q)
        self.add_result('clear', 'tc_download_stats', 'kvstore')

    def clear_tc_events(self):
        """Clear LEGACY 'tc_events' KvStore."""
        try:
            collection = self.tcs.collection.kvstore('tc_events')
            collection.data.delete(query=self._q)
        except Exception:  # nosec
            pass
        self.add_result('clear', 'tc_events', 'kvstore')

    def clear_tc_events_data(self):
        """Clear LEGACY 'tc_events_data' KvStore."""
        try:
            collection = self.tcs.collection.kvstore('tc_events_data')
            collection.data.delete(query=self._q)
        except Exception:  # nosec
            pass
        self.add_result('clear', 'tc_events_data', 'kvstore')

    def clear_tc_event_summaries(self):
        """Clear 'tc_event_summaries' KvStore."""
        query = dict(self._q)
        if self.indicator is not None:
            query.update({'indicator': self.indicator})
            self.tcs.collections.event_summaries.delete(query=query)
        else:
            self.tcs.collections.event_summaries.delete(query=query)
        self.add_result('clear', f'tc_event_summaries [query: {query}]', 'kvstore')

    def clear_tc_groups(self):
        """Clear 'tc_groups' KvStore."""
        query = dict(self._q)
        if self.owner_name is not None:
            query.update({'ownerName': self.owner_name})
            self.tcs.collections.groups.delete(query=query)
        else:
            self.tcs.collections.groups.delete(query=query)
        self.add_result('clear', f'tc_groups [query: {query}]', 'kvstore')

    def clear_tc_indicator_whitelist(self):
        """Clear 'tc_indicator_whitelist' KvStore."""
        self.tcs.collections.indicator_whitelist.delete(query=self._q)
        self.add_result('clear', 'tc_indicator_whitelist', 'kvstore')

    def clear_tc_indicators(self):
        """Clear 'tc_indicators' KvStore."""
        query = dict(self._q)
        if self.owner_name is not None:
            query.update({'ownerName': self.owner_name})
            self.tcs.collections.indicators.delete(query=query)
            self.reset_last_run(self.owner_name)
        else:
            self.tcs.collections.indicators.delete(query=query)
            if self.collection != 'ALL':
                self.reset_last_run()
        self.add_result('clear', f'tc_indicators [query: {query}]', 'kvstore')

    def clear_tc_labels(self):
        """Clear 'tc_labels' KvStore."""
        self.tcs.collections.labels.delete(query=self._q)
        self.add_result('clear', 'tc_labels', 'kvstore')

    def clear_tc_observations(self):
        """Clear 'tc_observations' KvStore."""
        self.tcs.collections.observations.delete(query=self._q)
        self.add_result('clear', 'tc_observations', 'kvstore')

    def clear_tc_owners(self):
        """Clear 'tc_owners' KvStore."""
        # iterate all custom searches
        for data in self.tcs.collections.owners.query():
            saved_search_group = f'''TC-Group-Download-{data.get('id')}'''
            try:
                self.service.saved_searches.delete(saved_search_group)
                self.add_result('delete', saved_search_group, 'saved search')
            except KeyError:
                self.logger.warning(f'Could not delete {saved_search_group}.')

            saved_search_indicator = f'''TC-Indicator-Download-{data.get('id')}'''
            try:
                self.service.saved_searches.delete(saved_search_indicator)
                self.add_result('delete', saved_search_indicator, 'saved search')
            except KeyError:
                self.logger.warning(f'Could not delete {saved_search_indicator}.')

        # clear orphaned saved searches
        for ss in self.service.saved_searches:
            if ss.name.startswith('TC-Group-Download-') or ss.name.startswith(
                'TC-Indicator-Download-'
            ):
                self.service.saved_searches.delete(ss.name)
                self.add_result('delete', ss.name, 'saved search')

        self.tcs.collections.owners.delete(query=self._q)
        self.add_result('clear', 'tc_owners', 'kvstore')

    def clear_tc_playbooks(self):
        """Clear 'tc_playbooks' KvStore."""
        self.tcs.collections.playbooks.delete(query=self._q)
        self.add_result('clear', 'tc_playbooks', 'kvstore')

    def clear_tc_settings(self):
        """Clear 'tc_settings' KvStore."""
        self.tcs.collections.settings.delete(query=self._q)
        self.add_result('clear', 'tc_settings', 'kvstore')

    def clear_tc_victim_whitelist(self):
        """Clear 'tc_victim_whitelist' KvStore."""
        self.tcs.collections.victim_whitelist.delete(query=self._q)
        self.add_result('clear', 'tc_victim_whitelist', 'kvstore')

    def clear_tc_workflow_playbook_actions(self):
        """Clear 'tc_workflow_playbook_actions' KvStore."""
        self.tcs.collections.workflow_playbook_actions.delete(query=self._q)
        self.add_result('clear', 'tc_workflow_playbook_actions', 'kvstore')

    @property
    def collection_map(self):
        """Return collection to method map."""
        # TODO: [LOW] replace this with a function per collection name???
        return {
            'tc_custom_search_settings': self.clear_tc_custom_search_settings,
            'tc_db_stats': self.clear_tc_db_stats,
            'tc_dm_data': self.clear_tc_dm_data,
            'tc_dm_search_settings': self.clear_tc_dm_search_settings,
            'tc_download_stats': self.clear_tc_download_stats,
            'tc_events': self.clear_tc_events,
            'tc_events_data': self.clear_tc_events_data,
            'tc_event_summaries': self.clear_tc_event_summaries,
            'tc_groups': self.clear_tc_groups,
            'tc_indicator_whitelist': self.clear_tc_indicator_whitelist,
            'tc_indicators': self.clear_tc_indicators,
            'tc_labels': self.clear_tc_labels,
            'tc_observations': self.clear_tc_observations,
            'tc_owners': self.clear_tc_owners,
            'tc_playbooks': self.clear_tc_playbooks,
            'tc_settings': self.clear_tc_settings,
            'tc_victim_whitelist': self.clear_tc_victim_whitelist,
            'tc_workflow_playbook_actions': self.clear_tc_workflow_playbook_actions,
        }

    def generate(self):
        """Implement generate command for Clear Collection."""
        if self.collection.lower() == 'list':
            for collection_name in sorted(self.collection_map):
                self.results.append({'Name': collection_name})
            # example of retrieving collections via Splunk REST API
            # for collection in self.service.kvstore:
            #     if collection.name.startswith('tc_'):
            #         self.results.append({'Name': collection.name})
        elif self.collection in self.collection_map:
            self.collection_map.get(self.collection)()
        elif self.collection == 'ALL' and self.confirm == 'YES':
            for clear_method in self.collection_map.values():
                clear_method()
        elif self.collection == 'ALL':
            self.error_exit(None, 'To clear ALL you must pass "confirm=YES" to proceed.')
        else:
            self.error_exit(None, f'Invalid option ({self.collection}) provided.')

        # display results
        for r in self.results:
            yield r

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

    def reset_last_run(self, owner_name=None):
        """Reset the lastRun timestamp in tc_owners collection."""
        if owner_name is not None:
            # update owner configuration
            query = {'name': self.owner_name}
            owner_data = self.tcs.collections.owners.query(query=query)[0]

            owner_key = owner_data.pop('_key')
            owner_data['lastRun'] = None
            self.tcs.collections.owners.update(owner_key, owner_data)
            self.add_result('reset-lastRun', f'tc_owners [query: {query}]', 'kvstore')
        else:
            for owner_data in self.tcs.collections.owners.query():
                owner_key = owner_data.pop('_key')
                owner_name = owner_data.get('name')
                owner_data['lastRun'] = None
                self.tcs.colletions.owners.update(owner_key, owner_data)
                self.add_result('reset lastRun', f'tc_owners [owner: {owner_name}]', 'kvstore')


if __name__ == '__main__':
    dispatch(KvStoreClearCommand, sys.argv, sys.stdin, sys.stdout, __name__)
