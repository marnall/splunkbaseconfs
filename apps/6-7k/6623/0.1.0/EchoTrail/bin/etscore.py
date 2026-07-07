#!/usr/bin/env python
# coding=utf-8

from __future__ import absolute_import, division, print_function, unicode_literals
import json
import os
import sys
import requests
from echotrail import utilities
from echotrail import cache

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option, validators

ECHOTRAIL_API_URL = 'https://api.echotrail.io/score'


@Configuration()
class ETLookup(EventingCommand):
    """
    The etlookup command looks for a Filename or Image field in each event and calls the EchoTrail API to enrich each event
    with additional details about that Filename or Image

    Example:

    ``event_id=1 | head 20 | etlookup``

    returns records with several additional fields of the form echotrail_*
    """

    def transform(self, records):
        logger = utilities.get_logger()
        api_key = utilities.get_api_key(self, logger)

        record_execution = int(self.service.confs['echotrail_settings']['scoring']['record_executions'])

        cache_enabled = 0
        cache_ttl_hours = 24
        result_cache = None
        try:
            cache_enabled = int(self.service.confs['echotrail_settings']['cache']['enabled'])
            cache_ttl_hours = int(self.service.confs['echotrail_settings']['cache']['ttl_hours'])
        except Exception as err:
            logger.error('Unable to load cache settings from echotrail_settings.conf')
            logger.error(err)

        if cache_enabled:
            result_cache = self.service.kvstore['echotrail_unique_event'].data
        if record_execution:
            uniq_event_cache = self.service.kvstore['echotrail_unique_event'].data

        try:
            splunk_ver = '.'.join(map(str, self.service.splunk_version))
        except Exception:
            splunk_ver = ''

        headers = {
            'X-Api-key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'ET-Source': 'Splunk ' + splunk_ver
        }

        for record in records:
            result = None

            # Generate a key that uniquely identifies this Splunk event
            uniq_key = ''
            if '_bkt' in record:
                uniq_key += record['_bkt'] + '_'
            if '_cd' in record:
                uniq_key += record['_cd']
            if not uniq_key:
                logger.error('Error generating a unique Key.')

            if cache_enabled:
                result = cache.get_from_cache(result_cache, 'score_' + uniq_key, cache_ttl_hours, logger)

            if not result:
                body = utilities.get_score_body(record, logger)
                if body:
                    if record_execution:
                        # Check if we've already recorded this execution
                        recorded = cache.get_from_cache(uniq_event_cache, uniq_key, 2160, logger)
                        if not recorded and uniq_key:
                            body['record_execution'] = True

                    r = requests.post(ECHOTRAIL_API_URL, json=body, headers=headers)
                    if r.status_code == 200:
                        result = json.loads(r.text)
                    elif r.status_code == 429:
                        raise Exception('You have exceeded your EchoTrail API quota, please contact sales@echotrail.io in increase it.'.format(r.status_code))
                    elif r.status_code != 200:
                        raise Exception('Error communicating with the EchoTrail API. Response code: {}'.format(r.status_code))

                    if result and record_execution and not recorded and uniq_key:
                        # Store the fact that we have now recorded this execution
                        cache.store_in_cache(uniq_event_cache, uniq_key, '1', logger)

                    # Cache the results
                    if result and cache_enabled:
                        # Don't cache the result if its the first time we've seen the execution
                        if self.get_score(result, 'customer') > 0 and self.get_score(result, 'host') > 0:
                            # Cache the result as it's less likely to change at this point
                            cache.store_in_cache(result_cache, 'score_' + uniq_key, r.text, logger)

            # Parse Results
            if 'echotrail_score' in result:
                record['echotrail_score_overall'] = result['echotrail_score']
            if 'global' in result:
                record['echotrail_score_global'] = result['global']['overall_score']
            if 'customer' in result:
                record['echotrail_score_customer'] = result['customer']['overall_score']
            if 'environment' in result:
                record['echotrail_score_environment'] = result['environment']['overall_score']
            if 'host' in result:
                record['echotrail_score_host'] = result['host']['overall_score']
            record['echotrail_score_full'] = result

            yield record

    def get_score(self, result, context):
        try:
            score = result[context]['overall_score']
        except Exception:
            score = 0
        return score


dispatch(ETLookup, sys.argv, sys.stdin, sys.stdout, __name__)
