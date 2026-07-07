#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Datamodel Search Command"""
import io
import os
import sys

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

import splunklib.results as results
from base_search import BaseSearch
from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class DatamodelSearchCommand(BaseGeneratingCommand, BaseSearch):
    """Playbook download command."""

    # args
    _key = Option(doc='The key for search settings.', require=False)

    # args for manual run
    confidence_reset = Option(default=False, doc='', require=False)
    earliest = Option(default='-75m@m', doc='', require=False)
    ioc_field = Option(doc='The indicator field name.', require=False)
    ioc_types = Option(default='', doc='The indicator types in CSV format.', require=False)
    latest = Option(default='-15m@m', doc='', require=False)
    model_name = Option(doc='The datamodel name to search.', require=False)
    observations = Option(default=False, doc='The datamodel name to search.', require=False)
    victim_field = Option(doc='', require=False)

    # properties
    datamodel_job = None
    filename = os.path.basename(__file__)
    key = None
    matches = None
    search_type = 'datamodel'
    tstats_job = None

    def _chunk_matches(self, matches):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(matches), self.tcs.config.max_chunk_size):
            yield matches[i : i + self.tcs.config.max_chunk_size]

    def _datamodel_search(self, match_group):
        """Process the results returned from tstats search"""
        kwargs = {
            'earliest_time': self.search_settings.get('earliest'),
            'latest_time': self.search_settings.get('latest'),
            'exec_mode': 'normal',
        }
        search = self._datamodel_spl(match_group)
        return self.search('datamodel_search', search, **kwargs)

    def _get_datamodel_object_search_spl(self):
        if not self.search_settings.get('objectSearch'):
            return ''
        return f'''search ({self.search_settings.get('objectSearch')}) |'''

    def _get_object_name(self, model_name):
        query = {'modelName': model_name}
        record = self.tcs.collections.dm_data.query(fields='objectName', query=query)
        if not record:
            return None
        return record[0]['objectName']

    def _datamodel_spl(self, match_group):
        """Return the datamodel SPL string."""
        object_name = self._get_object_name(self.search_settings.get('modelName'))

        if not object_name:
            return ''

        datamodel_search_append = f'''" OR {self.search_settings.get('iocField')}="'''.join(
            match_group
        )
        datamodel_search = (
            '| datamodel {} {} search | {} eval epoch=_time | convert mktime(epoch) '
            '| search {}="{}" | fields *'.format(
                self.search_settings.get('modelName'),
                object_name,
                self._get_datamodel_object_search_spl(),
                self.search_settings.get('iocField'),
                datamodel_search_append,
            )
        )
        self.logger.info(f'search={datamodel_search}, type=datamodel-data')
        return datamodel_search

    def _tstats_search(self):
        """Process the results returned from tstats search"""
        kwargs = {
            'earliest_time': self.search_settings.get('earliest'),
            'latest_time': self.search_settings.get('latest'),
            'exec_mode': 'normal',
        }
        return self.search('tstat_search', self._tstats_spl, **kwargs)

    def _get_tstats_object_search_spl(self):
        if not self.search_settings.get('objectSearch'):
            return ''
        return f'''AND ({self.search_settings.get('objectSearch')})'''

    @property
    def _tstats_spl(self):
        """Return the tstats search SPL."""
        tstats_search = (
            '| tstats count FROM datamodel={0} where {1} != "unknown" {2} BY {1} '
            '| eval {1}=lower(\'{1}\')'.format(
                self.search_settings.get('modelName'),
                self.search_settings.get('iocField'),
                self._get_tstats_object_search_spl(),
            )
        )
        self.logger.info(f'search={tstats_search}, type=datamodel-tstats')
        return tstats_search

    def datamodel_search(self, matches):
        """Run datamodel search and process the results"""
        self.logger.info('action=search-start, type=datamodel')
        search_events = []

        for chunk in self._chunk_matches(matches):
            job = self._datamodel_search(chunk)
            count = 50_000
            offset = 0
            result_count = int(job['resultCount'])
            while offset < result_count:
                kwargs_paginate = {'count': count, 'offset': offset}

                # process result one at a time to check for results.Message
                for result in results.ResultsReader(
                    io.BufferedReader(job.results(**kwargs_paginate))
                ):
                    if isinstance(result, dict):
                        search_events.append(result)
                    elif isinstance(result, results.Message):
                        self.search_result_error(job, result)

                offset += count
                self.logger.debug(f'action=search, type=datamodel, offset={offset}')
        self.logger.info(f'action=search-complete, type=datamodel, count={len(search_events):,}')
        return search_events

    def generate(self):
        """Implement the generate method execute datamodel search."""
        # load or build search settings
        self.init_search_settings()

        # log settings
        self.log_search_settings()

        # tstats search
        search_indicators = self.tstats_search()

        # if there are no matches then no need to proceed.
        if search_indicators:
            # load indicators from keystore now that we have matches to process
            kv_indicator_data = self.load_indicator_data()

            indicator_matches = self.find_matches(search_indicators, kv_indicator_data.keys())

            self.logger.info(f'action=search-matches, count={len(indicator_matches):,}')

            if indicator_matches:
                events = self.datamodel_search(indicator_matches)

                # load victim filters only if we have matches
                self.load_victim_whitelist_data(
                    self.search_settings.get('filterVictimWhitelist', [])
                )

                # process events
                self.process_events(events, kv_indicator_data)

        # display results
        for r in self.results:
            yield r

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

        # update args
        self.key = self._key
        self.ioc_types = [it for it in self.ioc_types.split(',') if it]
        self.confidence_reset = self.tcs.utils.to_bool(self.confidence_reset)
        self.observations = self.tcs.utils.to_bool(self.observations)

    def tstats_search(self):
        """Run tstats search and process the results"""
        self.logger.info('action=search-start, type=tstat')
        indicators = []

        job = self._tstats_search()
        self.update_search_time_range(job)
        count = 50_000
        offset = 0
        result_count = int(job['resultCount'])

        while offset < result_count:
            self.tcs.logger.debug(
                f'[search] processing results: offset={offset}, result_count={result_count:,}'
            )
            kwargs_paginate = {'count': count, 'offset': offset}
            for result in results.ResultsReader(io.BufferedReader(job.results(**kwargs_paginate))):
                if isinstance(result, dict):
                    # extract indicator value from result
                    indicators.append(result.get(self.search_settings.get('iocField')))
                elif isinstance(result, results.Message):
                    # handle error
                    self.search_result_error(job, result)
            offset += count
        self.logger.info(f'action=search-complete, type=tstat, count={len(indicators):,}')
        return set(indicators)


if __name__ == '__main__':
    dispatch(DatamodelSearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
