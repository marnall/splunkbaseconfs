#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Custom Search Command"""
import io
import os
import sys

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

import splunklib.results as results
from base_search import BaseSearch
from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class CustomSearchCommand(BaseGeneratingCommand, BaseSearch):
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
    matches = None
    search_type = 'custom'
    tstats_job = None

    def _chunk_matches(self, matches):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(matches), self.tcs.config.max_chunk_size):
            yield matches[i : i + self.tcs.config.max_chunk_size]

    def _custom_search(self, match_group):
        """Process the results returned from stats search"""
        kwargs = {
            'earliest_time': self.search_settings.get('earliest'),
            'exec_mode': 'normal',
            'latest_time': self.search_settings.get('latest'),
        }
        search = self._custom_spl(match_group)
        return self.search('custom_search', search, **kwargs)

    def _custom_spl(self, match_group):
        """Return the custom search SPL."""
        custom_search_append = f'''\" OR {self.search_settings.get('iocField')}=\"'''.join(
            match_group
        )
        custom_search = (
            f'| search {self.search_settings.get("search")} | eval epoch=_time '
            '| convert mktime(epoch) '
            f'| search {self.search_settings.get("iocField")}="{custom_search_append}" | fields *'
        )
        return custom_search

    def _stats_search(self):
        """Process the results returned from stats search"""
        kwargs = {
            'earliest_time': self.search_settings.get('earliest'),
            'latest_time': self.search_settings.get('latest'),
            'exec_mode': 'normal',
        }
        return self.search('stat_search', self._stats_spl, **kwargs)

    @property
    def _stats_spl(self):
        """Return the stats SPL"""
        stats_search = '| search {0} {1}=* | dedup {1} | eval {1}=lower(\'{1}\')'.format(
            self.search_settings.get('search'), self.search_settings.get('iocField')
        )
        return stats_search

    def custom_search(self, matches):
        """Run custom search and process the results"""
        self.logger.info('action=search-start, type=custom')
        search_events = []

        for chunk in self._chunk_matches(matches):
            job = self._custom_search(chunk)
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

        # stats search
        search_indicators = self.stats_search()

        # if there are no matches then no need to proceed.
        if search_indicators:
            # load indicators from keystore now that we have matches to process
            kv_indicator_data = self.load_indicator_data()

            indicator_matches = self.find_matches(search_indicators, kv_indicator_data.keys())
            self.logger.info(f'action=search-matches, count={len(indicator_matches):,}')

            if indicator_matches:
                events = self.custom_search(indicator_matches)

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

    def stats_search(self):
        """Run tstats search and process the results"""
        self.logger.info('action=search-start, type=stats')
        indicators = []

        job = self._stats_search()
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
        self.logger.info(f'action=search-complete, type=stat, count={result_count:,}')
        return set(indicators)


if __name__ == '__main__':
    dispatch(CustomSearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
