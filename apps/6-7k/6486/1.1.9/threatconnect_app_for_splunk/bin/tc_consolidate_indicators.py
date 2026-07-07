#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download ThreatConnect Owner Information Command"""
# standard library
import datetime
import re
import sys
from collections import OrderedDict

# third-party
# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand
from splunklib.searchcommands import Configuration, dispatch


@Configuration()
class ConsolidateIndicators(BaseGeneratingCommand):
    """Playbook download command.

    This command is run via a saved search.

    Usage:
    | tcconsolidateindicators
    """

    # properties
    _command = 'tcconsolidateindicators'
    _metrics = None
    first_run = True

    def add_result(self, collection, count):
        """Return ordered dict for results."""
        self.logger.info(f'collection={collection}, count={count}.')

        result_data = OrderedDict()
        result_data['Action'] = 'Report'
        result_data['Collection'] = collection
        result_data['CSV File Name'] = self.csv_name(collection)
        result_data['Count'] = count
        result_data['First Run For Collection'] = self.first_run
        self.results.append(result_data)

    def is_first_run(self, collection_name):
        job = self.tcs.search(f'|inputlookup {self.csv_name(collection_name)} | head 1')
        return job['resultCount'] == '0'

    def construct_spl(self, collection_name, search_uuid5, last_run=None):
        """Construct the SPL for for building indicator CSV files (initial or update)."""
        csv_name = self.csv_name(collection_name)

        if self.first_run:
            return (
                f'''search index="tc_indicator_data" '''
                f'''"metadata.search_uuid5"="{search_uuid5}" '''
                '''| dedup metadata.uuid5 '''
                '''| rename metadata.deleted as deleted'''
                '''| table id, ownerName, summary, type, webLink'''
                f'''| outputlookup {csv_name}'''
            )
        elif last_run:
            return (
                f'''search index="tc_indicator_data" earliest={last_run} latest="now" '''
                f'''"metadata.search_uuid5"="{search_uuid5}" '''
                '''| dedup metadata.uuid5 '''
                '''| rename metadata.deleted as deleted'''
                '''| table id, ownerName, summary, type, webLink, deleted '''
                f'''| inputlookup append=t {csv_name} '''
                f'''| outputlookup {csv_name}'''
            )
        else:
            return (
                f'''search index="tc_indicator_data" "metadata.search_uuid5"="{search_uuid5}" '''
                '''| dedup metadata.uuid5 '''
                '''| search "metadata.deleted"=false '''
                '''| table id, ownerName, summary, type, webLink '''
                f'''| outputlookup {csv_name}'''
            )

    @staticmethod
    def csv_name(collection_name):
        """Return the name of the sanitized CSV file for the collection."""
        csv_name = collection_name.lower().replace(' ', '-')
        csv_name = re.sub(r'[^a-zA-Z0-9_]', '', csv_name)
        return f'{csv_name}.csv.gz'

    def construct_dedup_spl(self, collection_name):
        """Construct the SPL for deduping the results (after initial creation)."""
        csv_name = self.csv_name(collection_name)

        return (
            f'''| inputlookup {csv_name} '''
            '''| dedup ownerName, summary, type '''  # deleted indicators don't have an ID
            '''| eval deleted=if(isnotnull(deleted), deleted, "false")'''
            '''| search deleted = false '''
            '''| table id, ownerName, summary, type, webLink '''
            f'''| outputlookup {csv_name}'''
        )

    @property
    def metrics(self):
        """Return the last run for this command."""
        if self._metrics is None:
            self._metrics = {}
            for command_metrics in self.tcs.collections.command_metrics.query():
                if command_metrics.command.lower() == 'tcconsolidateindicators':
                    self._metrics = command_metrics
                    break
        return self._metrics

    def flush_dirty_collection(self, collection):
        """Flush the CSV file if collection is marked as dirty."""
        try:
            dirty = collection.dirty
        except KeyError:
            dirty = True

        if dirty in [False, None]:
            return

        csv_name = self.csv_name(collection.name)
        spl = f'| outputlookup {csv_name}'
        self.tcs.search(spl)
        self.logger.info(f'CSV {csv_name} cleared')
        collection['dirty'] = False
        self.tcs.collections.ioc_collection.update(key=collection._key, data=collection)

    def generate(self):
        """Implement generate command for downloading owners."""
        new_earliest = datetime.datetime.utcnow() - datetime.timedelta(minutes=15)
        new_earliest = int(new_earliest.timestamp())
        for collection in self.tcs.collections.ioc_collection.query():  # inputlookup tcic
            self.logger.info(f'Processing collection: {collection.name}.')
            self.flush_dirty_collection(collection)
            self.first_run = self.is_first_run(collection.name)
            self.logger.debug(f'First Run: {self.first_run}.')
            spl = self.construct_spl(
                collection.name, collection.search_uuid, self.metrics.get('last_run')
            )
            self.logger.debug(f'SPL: {spl}.')
            job = self.tcs.search(spl)
            if self.metrics and self.first_run is False:
                spl = self.construct_dedup_spl(collection.name)
                self.logger.debug(f'Dedup SPL: {spl}.')
                job = self.tcs.search(spl)

            self.add_result(collection.name, job['resultCount'])
            self.logger.debug(f'Results: {job["resultCount"]}.')
        data = {'command': 'tcconsolidateindicators', 'last_run': new_earliest}

        self.logger.info(f'Updated Metrics: {data}')

        if self.metrics:
            self.tcs.collections.command_metrics.update(key=self.metrics._key, data=data)
        else:
            self.tcs.collections.command_metrics.insert(data)

        # display the results
        for r in self.results:
            yield r


if __name__ == '__main__':
    try:
        dispatch(ConsolidateIndicators, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception:
        # standard library
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
