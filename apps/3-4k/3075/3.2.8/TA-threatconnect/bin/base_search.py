#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Search Module"""
import collections
import ipaddress
import json
import re
import time
import uuid
from datetime import datetime


class BaseSearch:
    """ThreatConnect Search Module"""

    # properties
    metadata = None
    search_type = None
    search_settings = None

    # indicator data
    ioc_by_type = {}  # type (key) / data (value)
    ioc_data = {}  # indicator (key) / type (value)
    ioc_data_cache = {}  # cache kv indicator data to save time on lookups

    # observations
    observations_consolidated = {}

    # tracker
    tracker_indicator_victim = {}

    # victim whitelist
    victim_tracker = {}
    victim_tracker_whitelisted = {}
    victim_wl = {}

    # implement child class / other parent properties
    confidence_reset = None
    earliest = None
    ioc_field = None
    ioc_types = None
    key = None
    logger = None
    model_name = None
    observations = None
    results = []
    service = None
    tcs = None
    victim_field = None

    def add_result(self, event):
        """Add result entry for Splunk search output"""
        # build ordered dict to display in results pane
        result_data = collections.OrderedDict()
        result_data['timestamp'] = event.get('epoch')
        result_data['Type'] = event.get('tc_data').get('diamondType')
        result_data['IOC'] = event.get('tc_data').get('indicator')
        result_data['Victim'] = event.get('tc_data').get('diamondVictim') or ''
        result_data['SourceType'] = event.get('sourcetype')
        self.results.append(result_data)

    @staticmethod
    def diamond_type(indicator_type):
        """Determine the Diamond Model type using the indicator type.

        Args:
            indicator_type (string): The defined indicator type.

        Return:
            string: The defined Diamond Model type of Capability or
                Infrastructure.
        """
        if indicator_type in ['Address', 'EmailAddress', 'Host', 'URL']:
            return 'Infrastructure'

        if indicator_type in ['File']:
            return 'Capability'

        return 'Custom'

    @staticmethod
    def find_matches(search_indicators, kvstore_indicators):
        """Find indicator matches."""
        return list(set(kvstore_indicators).intersection(set(search_indicators)))

    def indicator_data_filter_confidence(self, query):
        """Update query to filter on confidence"""
        # filter indicators on confidence
        confidence_filter = self.search_settings.get('filterConfidence')
        if confidence_filter is not None and confidence_filter != -1:
            query['confidence'] = {'$gte': int(confidence_filter)}
        return query

    def indicator_data_filter_owners(self, query):
        """Update query to filter on rating"""
        owners_filter = self.search_settings.get('filterOwners')
        if isinstance(owners_filter, list) and owners_filter:
            _filter = [{'ownerName': v} for v in list(set(owners_filter))]
            query.setdefault('$and', []).append({'$or': _filter})
        return query

    def indicator_data_filter_rating(self, query):
        """Update query to filter on rating"""
        rating_filter = self.search_settings.get('filterRating')
        if rating_filter is not None and rating_filter != -1:
            query['rating'] = {'$gte': int(rating_filter)}
        return query

    def indicator_data_filter_tags(self, query):
        """Update query to filter on tag."""
        tags_filter = self.search_settings.get('filterTags')
        if isinstance(tags_filter, list) and tags_filter:
            _filter = [{'tag.name': v} for v in list(set(tags_filter))]
            query.setdefault('$and', []).append({'$and': _filter})
        return query

    def indicator_data_filter_threat_assess_score(self, query):
        """Update query to filter on threat assess score."""
        # filter indicators on threat assess score
        threat_assess_score_filter = self.search_settings.get('filterThreatAssessScore')
        if threat_assess_score_filter is not None and threat_assess_score_filter != -1:
            query['threatAssessScore'] = {'$gte': int(threat_assess_score_filter)}
        return query

    def indicator_data_filter_type(self, query):
        """Update query to filter on type."""
        type_filters = self.search_settings.get('iocTypes')
        _types = []
        if isinstance(type_filters, list):
            for t in type_filters:
                # remove subtype
                if '.' in t:
                    t, _ = t.split('.')
                _types.append(t)

            query['$or'] = [{'type': v} for v in list(set(_types))]
        return query

    @property
    def indicator_type_field(self):
        """Get all requested indicator types and sub-types

        "iocTypes": [
            "Address",
            "EmailAddress",
            "File.MD5",
            "Registry Key.Value Name"
        ]
        """
        # get indicator type and index from indicator fields (e.g. User Agent.User Agent )
        type_field = {}
        for indicator_type in self.search_settings.get('iocTypes', []):
            indicator_subtype = None
            # get "User Agent" from "User Agent.User Agent"
            if '.' in indicator_type:
                indicator_type, indicator_subtype = indicator_type.split('.')
            type_field.setdefault(indicator_type, [])
            if indicator_subtype is not None:
                type_field[indicator_type].append(indicator_subtype.lower())
        return type_field

    def indicator_victim_processed(self, indicator, victim):
        """Check if the indicator-victim combo has already been processed"""
        indicator_victim = f'{indicator}-{victim}'
        if indicator_victim in self.tracker_indicator_victim:
            return True
        self.tracker_indicator_victim[indicator_victim] = True
        return False

    def init_search_settings(self):
        """Load or build search settings"""
        if self.key is not None:
            self.init_search_settings_load()
        elif self.model_name is not None and self.ioc_field is not None and self.ioc_types:
            self.init_search_settings_build()
        else:
            self.error_exit(None, 'Missing search paramaters')  # pylint: disable=no-member

    def update_search_time_range(self, job):
        """Update the earliest and latest search values based on response of job.

        This is to address jira issue SUP-11122.
        """
        if not job:
            self.logger.warning('Cannot update job time range. Job None.')
            return
        if not job.content.get('isDone'):
            self.logger.warning('Cannot update job time range if job is not complete.')
            return

        current_earliest = self.search_settings.get('earliest')
        current_latest = self.search_settings.get('latest')
        job_earliest = job.content.get('searchEarliestTime', current_earliest)
        job_latest = job.content.get('searchLatestTime', current_latest)
        search = job.content.get('request', {}).get('search')

        self.search_settings['earliest'] = job_earliest
        self.search_settings['latest'] = job_latest
        self.logger.debug(
            f'Updating time range based on job search: {search} from using earliest-latest: '
            f'{current_earliest}-{current_latest} to {job_earliest}-{job_latest}'
        )

    def init_search_settings_load(self):
        """Load search settings from kv store"""
        if self.search_type == 'custom':
            self.search_settings = self.tcs.collections.custom_search_settings.query_by_id(self.key)
        elif self.search_type == 'datamodel':
            self.search_settings = self.tcs.collections.dm_search_settings.query_by_id(self.key)

        # for upgrades from 2.x version of the App ensure that latest is set.
        self.search_settings['latest'] = self.search_settings.get('latest', 'now')

    def init_search_settings_build(self):
        """Build search settings"""
        self.search_settings = {
            'confidenceReset': self.confidence_reset,
            'earliest': self.earliest,
            'iocField': self.ioc_field,
            'iocTypes': self.ioc_types,
            'jobName': 'manual',
            'modelName': self.model_name,
            'observations': self.observations,
            'victimField': self.victim_field,
        }

    def indicator_parse_subtypes(self, indicator_type, indicator):
        """Parse indicator subtype for matching.

        Some indicator such as Files (hashes) and Custom Indicators can have multiple indicator
        values (e.g. md5, sha1, sha256). This method provides a generator to iterate over all
        indicator values.

        For indicators that have only one value such as **ip** or **hostName** the generator will
        only return the one result.

        .. code-block:: python
            :linenos:
            :lineno-start: 1

            # the individual indicator JSON from the API
            for i in resource.indicators(indicator_data):
                print(i.get('type'))  # md5, sha1, sha256, etc
                print(i.get('value'))  # hash or custom indicator value

        .. Warning:: This method could break for custom indicators that have " : " in the value of
                     the indicator while using the summary field.

        .. Note:: For ``/v2/indicators`` and ``/v2/indicators/bulk/json`` API endpoints only one
                  hash is returned for a file Indicator even if there are multiple in the platform.
                  If all hashes are required the ``/v2/indicators/files`` or
                  ``/v2/indicators/files/<hash>`` endpoints will provide all hashes.

        Args:
            indicator_type (str): The indicator type
            indicator (str): The indicator value.

        Returns:
            (dictionary): A dict containing the indicator type and value.
        """
        indicators = self.tcs.utils.expand_indicators(indicator)
        index = 1
        for i in indicators:
            if i is None:
                continue
            i = i.strip()  # clean up badly formatted summary string
            i_type = None
            if indicator_type == 'File':
                # specifically handle hashes in any order
                hash_patterns = {
                    'md5': re.compile(r'^([a-fA-F\d]{32})$'),
                    'sha1': re.compile(r'^([a-fA-F\d]{40})$'),
                    'sha256': re.compile(r'^([a-fA-F\d]{64})$'),
                }
                if hash_patterns['md5'].match(i):
                    i_type = 'md5'
                elif hash_patterns['sha1'].match(i):
                    i_type = 'sha1'
                elif hash_patterns['sha256'].match(i):
                    i_type = 'sha256'
                else:
                    self.logger.warning(f'Cannot determine hash type: "{indicator}"')
                    continue
            else:
                # parse all of types of multi-part indicators
                subtype_field = f'value{index}Label'
                i_type = self.tcs.request.indicator_types_data.get(indicator_type, {}).get(
                    subtype_field
                )
            index += 1
            yield {'type': i_type.lower(), 'value': i}

    def load_indicator_data(self):
        """Load the Indicator data from KV Store

        {
            "rating": {
                "$gte": 3
            },
            "confidence": {
                "$gte": 75
            },
            "$or": [
                {
                    "type": "Address"
                },
                {
                    "type": "EmailAddress"
                }
            ],
            "$and": [
                {
                    "$and": [
                        {
                            "tag.name": "Tag1"
                        },
                        {
                            "tag.name": "Tag2"
                        }
                    ]
                },
                {
                    "$or": [
                        {
                            "ownerName": "MyOrganization"
                        },
                        {
                            "ownerName": "MyCommunity"
                        },
                        {
                            "ownerName": "MySource"
                        }
                    ]
                }
            ]
        }

        """
        # kvstore query parameters
        fields = '_key,indicator,ownerName,tag'
        query = {}

        # filter indicators on confidence
        query = self.indicator_data_filter_confidence(query)

        # filter indicators on rating
        query = self.indicator_data_filter_owners(query)

        # filter indicators on rating
        query = self.indicator_data_filter_rating(query)

        # filter indicators on rating
        query = self.indicator_data_filter_tags(query)

        # filter indicators on threat assess score
        query = self.indicator_data_filter_threat_assess_score(query)

        # filter indicators on type
        query = self.indicator_data_filter_type(query)

        # using indicator_type_field to ensure only pulling "main" indicator type once
        return self.load_indicator_data_types(fields, query)

    def load_indicator_data_types(self, fields, query):
        """Load indicators for all supported types."""
        indicator_count = 0
        indicator_data = {}
        self.logger.info(f'action=load-indicators, query={query}')

        indicator_type_data = self.indicator_type_field
        # for indicator_type, indicator_subtypes in self.indicator_type_field.items():
        for i in self.tcs.collections.indicators.paginate(fields=fields, query=query):
            indicator_type = i.get('type')
            indicator_subtypes = indicator_type_data.get(indicator_type, [])

            if indicator_subtypes:
                # NOTE: for indicators with subtypes the indicator value will not be the entire
                #       summary (e.g. NOT <value> : <value> : <value>), but one of the values.
                #       each subtype that was selected will be it's own indicator.
                for i_sub in self.indicator_parse_subtypes(indicator_type, i.get('indicator')):
                    if i_sub.get('type') in indicator_subtypes:
                        # NOTE: the kvstore could have a single indicator multiple times
                        #       if it was in multiple owners. storing "indicator_data" as
                        #       dict of "indicator value": [<list of _keys>].
                        indicator_data.setdefault(i_sub.get('value').lower(), []).append(
                            i.get('_key')
                        )
                        indicator_count += 1
            else:
                indicator_data.setdefault(i.get('indicator', '').lower(), []).append(i.get('_key'))
                indicator_count += 1

                # values = [i.get('indicator', '')]
                # TODO: [high] why would this every hit?
                # if indicator_type.lower() == 'file':
                #     values = i.get('indicator').split(' : ')

                # for value in values:
                #     indicator_data.setdefault(value.lower(), []).append(i.get('_key'))
                #     indicator_count += 1
        return indicator_data

    def load_kvs_indicators(self, indicator, keys):
        """Load Indicator data from cache or KV Store."""
        if indicator.lower() in self.ioc_data_cache:
            data = self.ioc_data_cache.get(indicator.lower())
        else:
            data = []
            for key in keys:
                data.append(self.tcs.collections.indicators.query_by_id(key))
            self.ioc_data_cache.setdefault(indicator.lower(), data)
        return data

    def load_victim_whitelist_data(self, whitelists):
        """Retrieve Victim whitelist collection"""
        fields = '_key,filterName,filterType,filterValue,filterGlobal'
        count = 0
        for wl in self.tcs.collections.victim_whitelist.paginate(fields=fields):
            if wl.get('filterGlobal') or wl.get('filterName') in whitelists:
                value = wl.get('filterValue')
                # NOTE: legacy versions of App had filterValue as string. handling both types
                #       of data.
                if isinstance(value, list):
                    self.victim_wl.setdefault(wl.get('filterType'), []).extend(
                        wl.get('filterValue')
                    )
                    count += len(value)
                else:
                    self.victim_wl.setdefault(wl.get('filterType'), []).append(
                        wl.get('filterValue')
                    )
                    count += 1

    def log_search_settings(self):
        """Log search settings"""
        for k, v in self.search_settings.items():
            self.logger.info(f'setting=search, type={k}, value={v}')

    def process_events(self, events, kvstore_indicators):
        """Match has been found, now process Splunk Event"""
        match_count = 0

        for event in events:
            if not isinstance(event, dict):
                continue

            indicator = event.get(self.search_settings.get('iocField'))
            # load individual indicator data from cache or kv store
            kvs_indicators = self.load_kvs_indicators(
                indicator, kvstore_indicators.get(indicator.lower())
            )
            indicator_type = kvs_indicators[0].get('type')
            victim = event.get(self.search_settings.get('victimField', ''))
            # log warning when victim can't be found
            if not victim:
                self.logger.warning(
                    '''action=get-victim, warning=no-victim, '''
                    f'''field={self.search_settings.get('victimField')}'''
                )

            # check victim against whitelist
            if victim and self.victim_whitelisted(victim):
                continue

            # build event data
            event['tc_data'] = {
                'timestamp': time.time(),
                'diamondType': self.diamond_type(indicator_type),
                'diamondVictim': victim,
                'indicator': indicator,
                'indicatorType': indicator_type,
                'uuid': str(uuid.uuid4()),
            }

            # add event for output to UI
            self.add_result(event)

            # skip events with exact ioc/victim that have already been processed
            if not self.indicator_victim_processed(indicator, victim):
                # add event data to batch queue
                self.tcs.collections.event_summaries.batch_data(
                    self.process_events_build_event(event)
                )

                for indicator_data in kvs_indicators:
                    # TODO: [LOW] cache this stuff
                    ga = self.tc_group_associations(
                        indicator, indicator_type, indicator_data.get('ownerName')
                    )
                    event_data = self.process_events_build_event_data(event, indicator_data, ga)

                    # this option uses socket stream to send events to Splunk
                    # TODO: [LOW] this needs testing on cluster environment
                    # see options @
                    # https://github.com/splunk/splunk-sdk-python/blob/master/examples/genevents.py
                    # self.event_data_index.write('{}\r\n'.format(json.dumps(event_data)))
                    self.service.tc_index('tc_event_data').submit(
                        json.dumps(event_data),
                        source='threatconnect-search-datamodel',
                        sourcetype='threatconnect-event-data',
                    )
                match_count += 1
            else:
                self.logger.debug(f'action=skipped-existing, value={indicator}-{victim}')

            # process observations
            if self.search_settings.get('observations'):
                self.process_events_observations(event)

        # save any remaining events
        self.tcs.collections.event_summaries.batch_save()

        # save observations
        self.tcs.collections.observations.batch_save(list(self.observations_consolidated.values()))

        # log match count
        self.logger.info(f'action=process-events, count={match_count:,}')

    def process_events_build_event(self, event):
        """Build the event to store in KV Store"""
        indicator_type = event.get('tc_data').get('indicatorType')

        tc_event = collections.OrderedDict()
        tc_event['timestamp'] = event.get('tc_data').get('timestamp')
        # tc_event['diamond_ioc'] = event.get('tc_data').get('indicator')
        tc_event['diamondType'] = self.diamond_type(indicator_type)
        tc_event['diamondVictim'] = event.get('tc_data').get('diamondVictim')
        tc_event['eventCd'] = event.get('_cd')
        tc_event['eventIndexTime'] = event.get('_indextime')
        tc_event['eventRaw'] = event.get('_raw')
        tc_event['eventSourcetype'] = event.get('sourcetype')
        tc_event['eventTime'] = event.get('epoch')
        tc_event['indicator'] = event.get('tc_data').get('indicator')
        tc_event['indicatorType'] = indicator_type
        tc_event['searchMethod'] = 'auto'
        tc_event['searchName'] = self.search_settings.get('jobName')
        tc_event['searchString'] = self.metadata.searchinfo.search
        tc_event['labels'] = self.process_events_build_event_labels(
            event, self.search_settings.get('addLabels', ['New'])
        )
        tc_event['uuid'] = event.get('tc_data').get('uuid')
        return tc_event

    @staticmethod
    def process_events_build_event_data(event, indicator_data, ga):
        """Build the event data to store in KV Store"""
        tc_event_data = collections.OrderedDict()
        tc_event_data['timestamp'] = event.get('tc_data').get('timestamp')
        tc_event_data['indicator'] = event.get('tc_data').get('indicator')
        tc_event_data['indicatorId'] = indicator_data.get('id')
        tc_event_data['indicatorDateAdded'] = indicator_data.get('dateAdded')
        tc_event_data['indicatorLastModified'] = indicator_data.get('lastModified')
        tc_event_data['indicatorOwnerName'] = indicator_data.get('ownerName')
        tc_event_data['indicatorType'] = indicator_data.get('type')
        tc_event_data['indicatorWebLink'] = indicator_data.get('webLink')
        tc_event_data['indicatorConfidence'] = indicator_data.get('confidence', '')
        tc_event_data['indicatorRating'] = indicator_data.get('rating', '')
        tc_event_data['indicatorTags'] = [tag.get('name') for tag in indicator_data.get('tag', [])]
        tc_event_data['indicatorAssociations'] = ga
        tc_event_data['uuid'] = event.get('tc_data').get('uuid')
        return tc_event_data

    def process_events_build_event_labels(self, event, labels):
        """Process labels on events."""
        # Remove empty labels or None labels
        labels = [label for label in labels if label]
        if not event:
            if not labels:
                return ['New']

            truncated_labels = self.truncate_labels(labels, 25)
            if 'New' not in truncated_labels:
                truncated_labels.append('New')
            return truncated_labels

        if 'New' not in labels:
            labels.append('New')

        for key, value in event.items():
            key_replacement = '$' + key + '$'
            if '$' + key + '$' in labels:
                labels.remove(key_replacement)
                if value:
                    labels.append(value)

        for label in labels:
            if label.startswith('$') and label.endswith('$'):
                labels.remove(label)

        labels = self.truncate_labels(labels, 25)
        return labels

    def process_events_observations(self, event):
        """Build the event data to store in KV Store"""
        # conslidate observations count by day
        date_observed = re.sub(
            r'[0-9]{2}:[0-9]{2}:[0-9]{2}$',
            '00:00:00',
            datetime.isoformat(datetime.fromtimestamp(float(event.get('epoch')))),
        )

        observation_key = f'''{event.get('tc_data').get('indicator')}-{date_observed}'''
        if observation_key in self.observations_consolidated:
            self.observations_consolidated[observation_key]['observationCount'] += 1
        else:
            self.observations_consolidated[observation_key] = {
                'confidenceReset': self.search_settings.get('confidenceReset'),
                'dateObserved': date_observed,
                'indicator': event.get('tc_data').get('indicator'),
                'observationCount': 1,
                'type': event.get('tc_data').get('indicatorType'),
            }

    def search(self, name, query, **kwargs):
        """Run search using the splunklib library to search Splunk."""
        self.logger.info(f'action=search, spl="{query}"')
        self.logger.debug(f'search kwargs: {kwargs}')

        # seconds of inactivity before auto-cancel of job (0 means never)
        kwargs.update({'auto_cancel': kwargs.get('auto_cancel', 0)})

        # create search job
        job = self.service.jobs.create(query, **kwargs)

        # Set the job's time-to-live (ttl) value, which is the time before
        # the search job expires and is still available. After it has finished
        # job.set_ttl(600) # 10 minutes

        # stop checking status if search exceeds predefined time limit
        search_timeout = int(time.time()) + int(self.tcs.config.search_timeout)

        # check that job is ready or some job properties are not available
        while not job.is_ready():
            self.logger.debug('waiting on search to be ready ...')
            time.sleep(1)

        while not job.is_done():
            # add some debugging data for long running or hung searches
            job_debug = {
                'isDone': job['isDone'],
                'doneProgress': float(job['doneProgress']) * 100,
                'scanCount': job['scanCount'],
                'eventCount': job['eventCount'],
                'resultCount': job['resultCount'],
            }
            self.logger.debug(f'[search] job debug: {job_debug}')
            time.sleep(self.tcs.config.search_sleep)

            # limit length of time the search can run
            if int(time.time()) > search_timeout:
                err = f'{name} status check exceeded max count'
                self.logger.error(f'search="{query}", error={err}, sid={job.sid}')
                job.cancel()
                self.error_exit(None, err)  # pylint: disable=no-member

        job_debug = {
            'isDone': job['isDone'],
            'doneProgress': float(job['doneProgress']) * 100,
            'scanCount': job['scanCount'],
            'eventCount': job['eventCount'],
            'resultCount': job['resultCount'],
        }
        self.logger.info(f'[search] job debug: {job_debug}')
        return job

    def search_result_error(self, job, result):
        """Handle search errors."""
        if result.type == 'ERROR':
            job.cancel()
            self.logger.error(f'error={result.message}, sid={job.sid}')
            self.error_exit(  # pylint: disable=no-member
                None, 'Encountered error running search. Please see logs.'
            )

    def tc_group_associations(self, indicator, indicator_type, owner):
        """Build the event data to store in KV Store"""
        # TODO: do we really need this method?
        group_associations = []
        try:
            groups = self.tcs.request.get_group_associations(
                {'indicator': indicator, 'type': indicator_type}, params={'ownerName': owner}
            )
            for group in groups:
                group_associations.append(
                    {
                        'id': group.get('id'),
                        'name': group.get('name'),
                        'type': group.get('type'),
                        'weblink': group.get('webLink'),
                    }
                )
        except Exception:  # nosec
            # best effort on getting group associations
            pass

        return group_associations

    @staticmethod
    def truncate_labels(labels, max_length):
        """Truncate the label to the provided max_length."""
        truncated_labels = []
        for label in labels:
            if len(label) > max_length:
                truncated_labels.append(label[: (max_length - 3)] + '...')
            else:
                truncated_labels.append(label)
        return truncated_labels

    def victim_whitelist_cidr(self, victim):
        """Victim whitelist CIDR comparison"""
        try:
            ip = ipaddress.ip_address(victim)
        except ValueError:
            return False

        for cidr in self.victim_wl.get('CIDR', []):
            try:
                cidr_network = ipaddress.ip_network(cidr)
            except Exception:
                self.logger.warning(
                    f'action=skipped-cidr, reason=invalid cidr "{cidr}" in victim filter.'
                )
                continue
            if ip in cidr_network:
                self.logger.debug(
                    f'filter=whitelist-cidr, victim={victim}, filter={cidr}, check=failed'
                )
                return True

        return False

    def victim_whitelist_regex(self, victim):
        """Victim whitelist regex comparison"""
        for rex in self.victim_wl.get('Regex', []):
            try:
                rex_compiled = re.compile(r'{}'.format(rex))
            except re.error:
                self.logger.warning(
                    f'action=skipped-regex, reason=invalid regex "{rex}" in victim filter.'
                )
                continue

            if re.match(rex_compiled, victim):
                self.logger.debug(
                    f'filter=whitelist-regex, victim={victim}, filter={rex}, check=failed'
                )
                return True
        return False

    def victim_whitelist_string(self, victim):
        """Victim whitelist string comparison"""
        wl_values = self.victim_wl.get('String', [])
        if victim in wl_values:
            self.logger.debug(
                f'filter=whitelist-string, victim={victim}, filter={wl_values}, check=failed'
            )
            return True
        return False

    def victim_whitelisted(self, victim):
        """Validate Victim field against victim blacklist/whitelist."""
        # NOTE: quick check for None value which can not be validated and previously validated
        #       victim values.
        if victim is None or victim in self.victim_tracker:
            return False

        # victim whitelist checks
        if victim in self.victim_tracker_whitelisted:
            self.victim_tracker_whitelisted[victim] = True
            return True
        if self.victim_whitelist_cidr(victim):
            self.victim_tracker_whitelisted[victim] = True
            return True
        if self.victim_whitelist_regex(victim):
            self.victim_tracker_whitelisted[victim] = True
            return True
        if self.victim_whitelist_string(victim):
            self.victim_tracker_whitelisted[victim] = True
            return True

        # add victim value to tracker for values that have already passed validation.
        self.victim_tracker[victim] = True
        return False
