# -*- coding: utf-8 -*-
"""ThreatConnect Indicator Download Command"""
import ipaddress
import os
import operator
import re
import sys
import time
from collections import OrderedDict
from datetime import datetime

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from pytz import timezone
from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class IndicatorDownloadService(BaseGeneratingCommand):
    """Playbook download command."""

    # args
    owner_key = Option(require=True, doc='The **owner key** from the KV Store.')

    # properties
    filename = os.path.basename(__file__)
    indicator_count = 0
    indicator_count_api = 0
    indicator_whitelist = {}
    ioc_data = {}
    last_run = None
    max_batch = None
    md = None
    od = {}

    # stats
    stats = {
        'timestamp': time.time(),
        'added': 0,
        'deleted': 0,
        'filtered': 0,
        'total': 0,
        'unaltered': 0,
        'updated': 0,
    }

    @staticmethod
    def _process_indicators_field(indicator_data, indicator_type_data, field_label):
        """Process indicator field."""
        value = ''
        case_preference = indicator_type_data['casePreference'] or 'sensitive'

        if indicator_type_data.get(field_label) in indicator_data:
            value = indicator_data[indicator_type_data[field_label]]

        if case_preference == 'lower':
            value = value.lower()
        elif case_preference == 'upper':
            value = value.upper()
        return value

    def add_result(self, action, indicator):
        """Add result entry for Splunk search output"""
        result_data = OrderedDict()
        result_data['action'] = action
        result_data['indicator'] = indicator
        self.results.append(result_data)

    def delete_indicator_data(self, delete_flag=False):
        """Delete Indicator from KV Store"""
        if self.od is not None:
            query = {'ownerName': self.od.name}
            if delete_flag:
                query['delete'] = True
            else:
                self.indicator_count = 0
            self.tcs.collections.indicators.delete(query=query)

    def filter_indicator(self, indicator_data):  # pylint: disable=too-many-return-statements
        """Run filters on returned indicators"""

        # filter threat assess score (requires TC 5.7+)
        if self.filter_indicator_ta_score(indicator_data):
            return True

        # filter confidence
        if self.filter_indicator_confidence(indicator_data):
            return True

        # filter rating
        if self.filter_indicator_rating(indicator_data):
            return True

        # filter false positive count
        if self.filter_indicator_false_positive(indicator_data):
            return True

        # filter tag exclude
        if self.filter_indicator_tag_exclude(indicator_data):
            return True

        # filter tags
        if self.filter_indicator_tag_include(indicator_data):
            return True

        # filter whitelist
        if self.filter_indicator_whitelist(indicator_data):
            return True

        return False

    def filter_indicator_confidence(self, indicator_data):
        """Filter indicator on confidence"""
        if int(self.od.filter_confidence) != -1:
            indicator = indicator_data.get('indicator')
            if indicator_data.get('confidence') is None:
                self.logger.debug(
                    f'filter=confidence, reason=no-confidence, '
                    f'check=failed, indicator={indicator}'
                )
                return True

            confidence = int(indicator_data.get('confidence') or 0)
            if operator.lt(confidence, self.od.filter_confidence):
                self.logger.debug(
                    f'filter=confidence, reason={confidence} < {self.od.filter_confidence}, '
                    f'check=failed, indicator={indicator}'
                )
                return True
        return False

    def filter_indicator_false_positive(self, indicator_data):
        """Filter indicator on false positive count"""
        if self.od.filter_false_positive != -1:
            indicator = indicator_data.get('indicator')
            false_positive_count = int(indicator_data.get('falsePositiveCount') or 0)
            if operator.gt(false_positive_count, self.od.filter_false_positive):
                self.logger.debug(
                    f'filter=false-positive, '
                    f'reason={false_positive_count} < {self.od.filter_false_positive}, '
                    f'check=failed, indicator={indicator}'
                )
                return True
        return False

    def filter_indicator_rating(self, indicator_data):
        """Filter indicator on rating"""
        if int(self.od.filter_rating) != -1:
            indicator = indicator_data.get('indicator')
            if indicator_data.get('rating') is None:
                self.logger.debug(
                    f'filter=rating, reason=no-rating, ' f'check=failed, indicator={indicator}'
                )
                return True

            rating = int(indicator_data.get('rating', 0))
            if operator.lt(rating, self.od.filter_rating):
                self.logger.debug(
                    f'filter=rating, reason={rating} < {self.od.filter_rating}, '
                    f'check=failed, indicator={indicator}'
                )
                return True
        return False

    def filter_indicator_tag_exclude(self, indicator_data):
        """Filter indicator on tag excludes"""
        indicator = indicator_data.get('indicator')
        for tag in indicator_data.get('tag', []):
            if tag.get('name') in self.od.filter_tags_exclude:
                self.logger.debug(
                    f'''filter=tags-exclude, reason={tag.get('name')} is in tag-exclude-list, '''
                    f'''check=failed, indicator={indicator}'''
                )
                return True
        return False

    def filter_indicator_tag_include(self, indicator_data):
        """Filter indicator on tag includes"""
        indicator = indicator_data.get('indicator')
        indicator_tags = [t.get('name') for t in indicator_data.get('tag', [])]
        if self.od.filter_tags_include_or:
            not_found = True

            for tag in self.od.filter_tags:
                if tag in indicator_tags:
                    not_found = False
                    break

            if not_found and self.od.filter_tags:
                self.logger.debug(
                    'filter=tags-or, reason=tag-include not found, '
                    f'check=failed, indicator={indicator}'
                )
                return True
        else:
            for tag in self.od.filter_tags:
                if tag not in indicator_tags:
                    self.logger.debug(
                        'filter=tags-and, reason=tag-includes not found, '
                        f'check=failed, indicator={indicator}'
                    )
                    return True
        return False

    def filter_indicator_ta_score(self, indicator_data):
        """Filter indicator on rating"""
        if int(self.od.filter_threat_assess_score) != -1:
            indicator = indicator_data.get('indicator')
            if indicator_data.get('threatAssessScore') is None:
                self.logger.debug(
                    f'filter=ta-score, reason=no-score, ' f'check=failed, indicator={indicator}'
                )
                return True

            threat_assess_score = int(indicator_data.get('threatAssessScore', 0))
            if operator.lt(threat_assess_score, self.od.filter_threat_assess_score):
                self.logger.debug(
                    f'filter=ta-score, reason={threat_assess_score} '
                    f'< {self.od.filter_threat_assess_score}, '
                    f'check=failed, indicator={indicator}'
                )
                return True
        return False

    def filter_indicator_type(self, indicator_data):
        """Filter indicator on indicator type"""
        if indicator_data.get('type') not in self.od.filter_indicator_types:
            indicator = indicator_data.get('indicator')
            self.logger.debug(
                f'filter=indicator-type, reason=indicator-type is not in indicator-type-list '
                f'check=failed, indicator={indicator}'
            )
            return True
        return False

    def filter_indicator_whitelist(self, indicator_data):
        """Validate Indicator field against victim blacklist/whitelist"""
        indicator = indicator_data.get('indicator')
        indicator_type = indicator_data.get('type')
        if self.filter_indicator_whitelist_cidr(indicator, indicator_type):
            return True
        if self.filter_indicator_whitelist_regex(indicator, indicator_type):
            return True
        if self.filter_indicator_whitelist_string(indicator, indicator_type):
            return True
        return False

    def filter_indicator_whitelist_cidr(self, indicator, indicator_type):
        """Filter Indicator whitelist CIDR comparison"""
        try:
            ip = ipaddress.ip_address(indicator)
        except ValueError:
            return False

        for cidr in self.indicator_whitelist.get('CIDR', {}).get(indicator_type, []):
            try:
                cidr_network = ipaddress.ip_network(cidr)
            except Exception:
                self.logger.warning(
                    f'action=skipped-cidr, reason=invalid cidr "{cidr}" in indicator filter.'
                )
                continue

            if ip in cidr_network:
                self.logger.debug(
                    f'filter=whitelist-cidr, filter={cidr}, ' f'check=failed, indicator={indicator}'
                )
                return True
        return False

    def filter_indicator_whitelist_regex(self, indicator, indicator_type):
        """Filter Indicator whitelist regex comparison"""
        for rex in self.indicator_whitelist.get('Regex', {}).get(indicator_type, []):
            try:
                rex_compiled = re.compile(r'{}'.format(rex))
            except re.error:
                self.logger.warning(
                    f'action=skipped-regex, reason=invalid regex "{rex}" in indicator filter.'
                )
                continue

            if re.match(rex_compiled, indicator):
                self.logger.debug(
                    f'filter=whitelist-regex, filter={rex}, ' f'check=failed, indicator={indicator}'
                )
                return True
        return False

    def filter_indicator_whitelist_string(self, indicator, indicator_type):
        """Filter Indicator whitelist string comparison"""
        wl_values = self.indicator_whitelist.get('String', {}).get(indicator_type, [])
        if indicator in wl_values:
            self.logger.debug(
                f'filter=whitelist-string, filter={wl_values}, '
                f'check=failed, indicator={indicator}'
            )
            return True
        return False

    def generate(self):
        """Implement generate command for indicator downloads."""
        # load owner data
        self.load_owner_data(self.owner_key)

        # load indicator whitelist
        self.load_indicator_whitelist()

        # load indicator data
        self.load_indicator_data()

        # retrieve the API indicator count
        self.retrieve_indicator_count()

        if self.od.last_run is not None:
            # only delete if not first run
            for i_data in self.retrieve_deleted_indicators():
                # process deleted indicator data
                self.process_deleted_indicators(i_data)

            # only retrieve inactive if not first run
            for i_data in self.retrieve_inactive_indicators():
                # process inactive indicator data (delete)
                self.process_deleted_indicators(i_data)

        # retrieve indicator data from ThreatConnect
        self.retrieve_indicators()

        # process any remaining indicators
        self.tcs.collections.indicators.batch_save()

        # delete indicators marked for deletion
        self.delete_indicator_data(True)

        # update owner with last run timestamp
        self.update_owner_data()

        # report download metrics to ThreatConnect
        self.report_metrics()

        # update stats
        self.update_stats_data()

        self.logger.info(
            f'''status=complete, added={self.stats.get('added')}, '''
            f'''deleted={self.stats.get('deleted')}, filtered={self.stats.get('filtered')}, '''
            f'''unaltered={self.stats.get('unaltered')}, updated={self.stats.get('updated')}, '''
            f'''total={self.stats.get('total')}, owner={self.od.name}'''
        )

        for r in self.results:
            yield r

    def load_indicator_data(self):
        """Load indicator data from KV Store"""
        if self.od:
            for indicator_data in self.tcs.collections.indicators.paginate(
                fields='_key,indicator,lastModified', query={'ownerName': self.od.name}
            ):
                indicator = indicator_data.get('indicator')

                # remove duplicates from kvstore
                if indicator in self.ioc_data:
                    self.tcs.collections.indicators.delete_by_id(indicator_data.get('_key'))
                    self.logger.debug(f'action=delete-duplicate, indicator={indicator}')
                    continue
                # store the indicator key for update and lastModified for update comparisson
                self.ioc_data[indicator] = {
                    '_key': indicator_data.get('_key'),
                    'lastModifed': indicator_data.get('lastModified'),
                }
            self.indicator_count = len(self.ioc_data)

    def load_indicator_whitelist(self):
        """Retrieve Indicator whitelist collection.

        self.indicator_whitelist = {
            'CIDR': {
                'Address': [
                    '1.1.1.1',
                    '1.1.1.2'
                ]
            },
            'Regex': {
                'URL': [
                    '^http://www.google.com/.*$'
                ]
            }
            'String': {
                'Host': [
                    'www.google.com'
                ]
            }
        }
        """
        count = 0
        for wl in self.tcs.collections.indicator_whitelist.paginate(
            fields='_key,filterIndicatorTypes,filterName,filterType,filterValue,filterGlobal'
        ):
            if wl.get('filterGlobal') or wl.get('filterName') in self.od.filter_indicator_whitelist:
                filter_type = wl.get('filterType')
                self.indicator_whitelist.setdefault(filter_type, {})
                for it in wl.get('filterIndicatorTypes', []):
                    count += len(wl.get('filterValue'))
                    self.indicator_whitelist[filter_type].setdefault(it, []).extend(
                        wl.get('filterValue')
                    )

    def load_owner_data(self, owner_key):
        """Load owner configuration data from KV store"""
        self.od = self.tcs.collections.owners.query_by_id(owner_key)
        self.stats['owner'] = self.od.name

        self.logger.info(
            f'action=data-loaded, count={len(self.od)}, '
            f'source=tc_owners-collection, key={owner_key}'
        )

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

        self.max_batch = int(self.tcs.config.tc_max_batch_size)
        self.md = (
            datetime.now(timezone('UTC'))
            .astimezone(timezone(self.tcs.config.timezone))
            .strftime('%Y-%m-%dT%H:%M:%S%z')
        )

    def process_deleted_indicators(self, indicator_data):
        """Process ThreatConnect Indicators"""
        indicator_data['indicator'] = indicator_data.pop('summary')
        indicator = indicator_data.get('indicator')

        # check if indicator is in KV store
        if self.ioc_data.get(indicator) is not None:
            self.add_result('Deleted', indicator)
            self.stats['deleted'] += 1
            indicator_data['_key'] = self.ioc_data.get(indicator).get('_key')
            indicator_data['delete'] = True
            self.tcs.collections.indicators.batch_data(indicator_data)

    @staticmethod
    def process_indicator_summary(field1, field2, field3):
        """Process indicator summary field."""
        summary = ''

        if field1 is not None and len(field1) > 0:
            summary = field1

        if field2 is not None and len(field2) > 0:
            if summary:
                summary = summary + ' : '
            summary = summary + field2

        if field3 is not None and len(field3) > 0:
            if summary:
                summary = summary + ' : '
            summary = summary + field3

        return summary

    def process_indicators(self, indicator_data, indicator_type_data):
        """Process ThreatConnect Indicators"""
        indicator_data['field1'] = self._process_indicators_field(
            indicator_data, indicator_type_data, 'value1Label'
        )
        indicator_data['field2'] = self._process_indicators_field(
            indicator_data, indicator_type_data, 'value2Label'
        )
        indicator_data['field3'] = self._process_indicators_field(
            indicator_data, indicator_type_data, 'value3Label'
        )
        indicator_data['indicator'] = self.process_indicator_summary(
            indicator_data.get('field1'), indicator_data.get('field2'), indicator_data.get('field3')
        )
        indicator_data['ownerId'] = self.od.id
        indicator = indicator_data.get('indicator')
        action = None

        if self.filter_indicator(indicator_data):
            # NOTE: this method won't hit for confidence/rating filters on first run due to using
            #       API filter query parameters.
            # failed filter validation
            action = 'Filtered'
            # check if indicator had previously passed filter and if so then mark for deletion
            if self.ioc_data.get(indicator) is not None:
                action = 'Filtered-Deleted'
                self.stats['deleted'] += 1
                indicator_data['_key'] = self.ioc_data.get(indicator).get('_key')
                indicator_data['delete'] = True
                self.tcs.collections.indicators.batch_data(indicator_data)
            else:
                self.stats['filtered'] += 1
        elif self.od.last_run is None:
            # if first run, then blindly add indicators that have passed filters
            action = 'Add'
            self.stats['added'] += 1
            self.tcs.collections.indicators.batch_data(indicator_data)
        elif indicator in self.ioc_data:
            # if indicator already exist then see if it needs to be updated
            if self.update_indicator_data(indicator_data):
                action = 'Updated'
                self.stats['updated'] += 1
                i_key = self.ioc_data.get(indicator).get('_key')
                indicator_data['_key'] = i_key
                self.tcs.collections.indicators.batch_data(indicator_data)
            else:
                action = 'Unaltered'
                self.stats['unaltered'] += 1
        else:
            # new indicator, add indicators that have passed filters
            action = 'Add'
            self.stats['added'] += 1
            self.tcs.collections.indicators.batch_data(indicator_data)

        # Logging
        self.logger.debug(f'action={action}, indicator={indicator}')
        self.add_result(action, indicator)

    def report_metrics(self):
        """Report Metrics to ThreatConnect"""
        # added by owner
        metrics = self.tcs.metric(
            'Splunk Indicator Adds By Owner',
            'Splunk App Indicators added by ThreatConnect Owner',
            'Sum',
            'Daily',
            True,
        )
        added = self.stats.get('added', 0)
        metrics.add(added, key=self.od.name)
        self.logger.info(
            'action=report-metric, metric="Splunk Added By Owner", '
            f'owner={self.od.name}, count={added}'
        )

        # deleted by owner
        metrics = self.tcs.metric(
            'Splunk Indicator Deletes By Owner',
            'Splunk App Indicators deleted by ThreatConnect Owner',
            'Sum',
            'Daily',
            True,
        )
        deleted = self.stats.get('deleted', 0)
        metrics.add(deleted, key=self.od.name)
        self.logger.info(
            'action=report-metric, metric="Splunk Indicator Deletes By Owner", '
            f'owner={self.od.name}, count={deleted}'
        )

        # indicator by action
        metrics = self.tcs.metric(
            'Splunk Indicator Download By Action',
            'Splunk App Indicator Downloads by Action',
            'Sum',
            'Daily',
            True,
        )
        metrics.add(self.stats.get('added', 0), key='added')
        metrics.add(self.stats.get('deleted', 0), key='deleted')
        metrics.add(self.stats_filtered, key='filtered')
        metrics.add(self.stats.get('unaltered', 0), key='unaltered')
        metrics.add(self.stats.get('updated', 0), key='updated')

    def retrieve_deleted_indicators(self, result_limit=10000):
        """Download Indicators from ThreatConnect API"""
        params = {'owner': self.od.name, 'resultLimit': result_limit}
        if self.od.last_run is not None:
            params['deletedSince'] = self.od.last_run

        for indicator_data in self.tcs.request.iterate(
            'v2/indicators/deleted', params, 'indicator'
        ):
            self.logger.debug(
                '''filter=deleted, reason=indicator has been deleted, '''
                f'''check=failed, indicator={indicator_data.get('summary')}'''
            )
            yield indicator_data

    def retrieve_indicator_count(self, result_limit=1):
        """Download Indicators count from ThreatConnect API"""
        params = {'owner': self.od.name, 'resultLimit': str(result_limit), 'resultStart': '0'}
        r = self.tcs.session.get('/v2/indicators', params=params)
        self.logger.debug(f'url={r.request.url}')

        if not r.ok:
            self.logger.warning(f'Could not retrieve indicator count ({r.text}).')
        else:
            data = r.json()
            if data.get('status') == 'Success':
                self.indicator_count_api = data.get('data', {}).get('resultCount')

    def retrieve_indicators(self):
        """Retrieve indicators."""
        indicator_types = self.retrieve_indicator_types()

        for indicator_type in self.od.filter_indicator_types:
            for i_data in self.retrieve_indicators_by_type(indicator_type):
                i_data['type'] = indicator_type  # API doesn't return type so it needs to be added
                self.process_indicators(i_data, indicator_types[indicator_type])

    def retrieve_indicator_types(self):
        """Retrieve indicator types."""
        indicator_types = {}
        for indicator_type, itd in self.tcs.request.indicator_types_data.items():
            indicator_type_data = {
                'name': indicator_type,
                'casePreference': None,
                'value1Label': None,
                'value2Label': None,
                'value3Label': None,
            }
            if self.tcs.utils.to_bool(itd['custom']) is False:
                if indicator_type == 'Address':
                    indicator_type_data['casePreference'] = 'upper'
                    indicator_type_data['value1Label'] = 'ip'
                elif indicator_type == 'EmailAddress':
                    indicator_type_data['casePreference'] = 'lower'
                    indicator_type_data['value1Label'] = 'address'
                elif indicator_type == 'Host':
                    indicator_type_data['casePreference'] = 'lower'
                    indicator_type_data['value1Label'] = 'hostName'
                elif indicator_type == 'URL':
                    indicator_type_data['casePreference'] = 'sensitive'
                    indicator_type_data['value1Label'] = 'text'
                elif indicator_type == 'File':
                    indicator_type_data['casePreference'] = 'upper'
                    indicator_type_data['value1Label'] = 'md5'
                    indicator_type_data['value2Label'] = 'sha1'
                    indicator_type_data['value3Label'] = 'sha256'
            elif self.tcs.utils.to_bool(itd['custom']) is True:
                indicator_type_data['casePreference'] = itd['casePreference']
                indicator_type_data['value1Label'] = itd['value1Label']
                if 'value2Label' in itd:
                    indicator_type_data['value2Label'] = itd['value2Label']
                if 'value3Label' in itd:
                    indicator_type_data['value3Label'] = itd['value3Label']

            indicator_types[indicator_type] = indicator_type_data

        return indicator_types

    def retrieve_indicators_by_type(self, indicator_type, result_limit=10000):
        """Download Indicators from ThreatConnect API"""
        indicator_type_data = self.tcs.request.indicator_types_data.get(indicator_type)

        if not indicator_type_data:
            self.error_exit(None, message=f'Invalid type {indicator_type} provided.')

        if self.od.last_run is None:
            # NOTE: only on first run use the filter query params. on subsequent runs all
            #       indicators are required to delete existing indicator in KV store.
            if self.od.filter_confidence is not None and self.od.filter_confidence not in [-1, 0]:
                confidence = int(self.od.filter_confidence) - 1
                self.tcs.request.filters.add('confidence', '>', str(confidence))
            if self.od.filter_rating is not None and self.od.filter_rating not in [-1, 0]:
                rating = int(self.od.filter_rating) - 1
                self.tcs.request.filters.add('rating', '>', str(rating))
            if self.od.filter_false_positive is not None and self.od.filter_false_positive not in [
                -1
            ]:
                false_positive = int(self.od.filter_false_positive) + 1
                self.tcs.request.filters.add('falsePositive', '<', str(false_positive))
            if (
                self.od.filter_threat_assess_score is not None
                and self.od.filter_threat_assess_score not in [-1]
            ):
                ta_score = self.od.filter_threat_assess_score - 1
                self.tcs.request.filters.add('threatAssessScore', '>', str(ta_score))

        params = {
            'includes': ['additional', 'attributes', 'tags'],
            'owner': self.od.name,
            'resultLimit': result_limit,
        }
        if self.od.last_run is not None:
            params['modifiedSince'] = self.od.last_run
            params['owner'] = self.od.name

        api_branch = indicator_type_data.get('apiBranch')
        api_entity = indicator_type_data.get('apiEntity')
        for indicator_data in self.tcs.request.iterate(
            f'v2/indicators/{api_branch}', params, api_entity
        ):
            yield indicator_data

    def retrieve_inactive_indicators(self, result_limit=10000):
        """Download Indicators from ThreatConnect API that have been marked as inactive."""
        params = {'owner': self.od.name, 'resultLimit': result_limit}
        self.tcs.request.filters.add('active', '=', 'false')
        if self.od.last_run is not None:
            params['modifiedSince'] = self.od.last_run

        for indicator_data in self.tcs.request.iterate('v2/indicators', params, 'indicator'):
            self.logger.debug(
                '''filter=inactive, reason=indicator is inactive, '''
                f'''check=failed, indicator={indicator_data.get('summary')}'''
            )
            yield indicator_data
        self.tcs.request.filters.reset()

    @property
    def stats_filtered(self):
        """Return stats filtered."""
        if self.od.last_run is None:
            # NOTE: on first run the difference between total api indicators and added indicators
            #       is the filtered count.
            self.stats['filtered'] = self.indicator_count_api - int(self.stats.get('added', 0))
        return self.stats.get('filtered', 0)

    @property
    def stats_total(self):
        """Return stats total."""
        total = 0
        for k, v in self.stats.items():
            v = v or 0
            if k in ['added', 'deleted', 'filtered', 'unaltered', 'updated']:
                total += int(v)
        return total

    def update_indicator_data(self, indicator_data):
        """Update indicators in KV Store"""
        indicator = indicator_data.get('indicator')
        api_indicator_lm = indicator_data.get('lastModified')
        kvs_indicator_lm = self.ioc_data.get(indicator).get('lastModifed')
        if api_indicator_lm == kvs_indicator_lm:
            del self.ioc_data[indicator]
            return False
        return True

    def update_owner_data(self):
        """Update Owner Collection"""
        self.indicator_count += int(self.stats.get('added', 0))
        self.indicator_count -= int(self.stats.get('deleted', 0))

        self.od['indicatorCount'] = self.indicator_count
        self.od['indicatorCountApi'] = self.indicator_count_api
        self.od['lastRun'] = self.md
        self.tcs.collections.owners.update(self.od._key, self.od)
        self.logger.info(f'action=update-owner, owner=\"{self.od.name}\"')

    def update_stats_data(self):
        """Update Stats Collection"""
        # update stats
        self.stats['filtered'] = self.stats_filtered
        self.stats['total'] = self.stats_total
        self.tcs.collections.download_stats.insert(self.stats)
        self.logger.info(f'action=update-stats, owner=\"{self.od.name}\"')


if __name__ == '__main__':
    dispatch(IndicatorDownloadService, sys.argv, sys.stdin, sys.stdout, __name__)
