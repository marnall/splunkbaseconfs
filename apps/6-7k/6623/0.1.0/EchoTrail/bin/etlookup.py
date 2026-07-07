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

ECHOTRAIL_API_URL = 'https://api.echotrail.io/v1/private/insights/'


@Configuration()
class ETLookup(EventingCommand):
    """
    The etlookup command looks for a Filename or Image field in each event and calls the EchoTrail API to enrich each event
    with additional details about that Filename or Image

    Example:

    ``event_id=1 | head 20 | etlookup``

    returns records with several additional fields of the form echotrail_*
    """

    filename = Option(
        doc='''**Syntax:** **Filename=***<filename>*
        **Description:** Filename to lookup in EchoTrail Insights''',
        name='filename', require=False
    )

    def transform(self, records):
        logger = utilities.get_logger()
        api_key = utilities.get_api_key(self, logger)

        cache_enabled = 0
        cache_ttl_hours = 24
        kvstore = None
        try:
            cache_enabled = int(self.service.confs['echotrail_settings']['cache']['enabled'])
            cache_ttl_hours = int(self.service.confs['echotrail_settings']['cache']['ttl_hours'])
        except Exception as err:
            logger.error('Unable to load cache settings from echotrail_settings.conf')
            logger.error(err)

        if cache_enabled:
            kvstore = self.service.kvstore['echotrail_lookup'].data

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
            if self.filename and self.filename in record:
                filename = record[self.filename].split('\\')[-1]
            else:
                filename = utilities.get_filename(record)

            if filename:
                # Check Cache first
                result = None
                if cache_enabled:
                    result = cache.get_from_cache(kvstore, filename, cache_ttl_hours, logger)

                if not result:
                    r = requests.get(ECHOTRAIL_API_URL + filename, headers=headers)
                    if r.status_code == 200:
                        result = json.loads(r.text)
                    elif r.status_code == 429:
                        raise Exception('You have exceeded your EchoTrail API quota, please contact sales@echotrail.io in increase it.'.format(r.status_code))
                    elif r.status_code != 200:
                        raise Exception('Error communicating with the EchoTrail API. Response code: {}'.format(r.status_code))

                    if result and cache_enabled:
                        cache.store_in_cache(kvstore, filename, r.text, logger)

                # Parse Results
                if 'description' in result:
                    record['echotrail_descripton'] = result['description']
                if 'rank' in result:
                    record['echotrail_rank'] = result['rank']
                if 'eps' in result:
                    record['echotrail_eps'] = result['eps']
                if 'host_prev' in result:
                    record['echotrail_host_prev'] = result['host_prev']
                if 'intel' in result:
                    record['echotrail_intel'] = result['intel']

            yield record


dispatch(ETLookup, sys.argv, sys.stdin, sys.stdout, __name__)