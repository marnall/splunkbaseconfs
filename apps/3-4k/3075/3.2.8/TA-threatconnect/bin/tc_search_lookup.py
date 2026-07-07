#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Indicator Lookup Command."""
import os
from collections import OrderedDict
import sys
import urllib.parse

# import urllib3

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand
from splunklib.searchcommands import (
    dispatch,
    Configuration,
    Option,
)


@Configuration()
class LookupSearchCommand(BaseGeneratingCommand):
    """Command to retrieve details about a Indicator

    Used in the tc_view_ioc_lookup to view the details of a indicator and in
    Indicator Collection Review to retrieve additional details upon expanse.

    Usage:
    | tclookup indicator=<Indicator Value>
               indicator_type=<Indicator Type Comma delimited|Default=Any>

    e.g.,
    | tclookup indicator=3.33.33.4 indicator_type=Address,Host
    """

    indicator = Option(require=True, doc='The Indicator value you wish to lookup')
    indicator_type = Option(
        require=False, doc='The Type of Indicator. Defaults to Any', default='Any'
    )
    include_additional = Option(
        require=False,
        doc='If additional information should be retrieved. Defaults to false',
        default='false',
    )
    owner = Option(require=False, doc='The Owner name for the indicator.', default='')

    filename = os.path.basename(__file__)
    safe_indicator = None

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return
        self.include_additional = self.tcs.utils.to_bool(self.include_additional)
        self.indicator_type = self.tcs.request.indicator_types
        if self.indicator_type in ['Any']:
            self.indicator_type = [self.indicator_type]
        self.owner = [{'name': self.owner}] if self.owner else []
        self.safe_indicator = urllib.parse.quote(self.indicator, safe='')

    def generate(self):
        """Implement generate command for looking up details on a indicator."""
        # indicator data
        if not self.owner:
            # Figure out indicator type
            for indicator_type in self.indicator_type:
                self.logger.debug(f'indicator_type={indicator_type}')

                api_branch = self.tcs.request.indicator_type_branch(indicator_type)
                url = f'/v2/indicators/{api_branch}/{self.safe_indicator}/owners'
                r = self.tcs.session.get(f'{url}')
                self.logger.debug(f'url={r.request.url}')
                if not r.ok:
                    self.error_exit(None, f'Search Lookup Failure for indicator {self.indicator}')
                self.owner = r.json().get('data', {}).get('owner')
                if self.owner:
                    self.logger.info(f'action=lookup, type={indicator_type}')
                    break

            # Nothing found
            if not self.owner:
                yield {'ThreatConnect Results': 'Indicator not found in ThreatConnect.'}
                sys.exit()

        # Process owners
        for o in self.owner:
            self.logger.debug(f"owner_name={o.get('name')}")

            # get indicator resource
            for indicator_type in self.indicator_type:
                api_branch = self.tcs.request.indicator_type_branch(indicator_type)
                params = {
                    'owner': o.get('name'),
                    'includeTags': True,
                    'includeAttributes': True,
                }
                if self.include_additional:
                    params['includeAdditional'] = True
                url = f'/v2/indicators/{api_branch}/{self.safe_indicator}'
                r = self.tcs.session.get(f'{url}', params=params)
                self.logger.debug(f'url={r.request.url}')
                if not r.ok:
                    continue

                api_entity = self.tcs.request.indicator_types_data.get(indicator_type, {}).get(
                    'apiEntity'
                )
                indicator_data = r.json().get('data').get(api_entity)

                result_data = OrderedDict()
                result_data['indicator'] = self.indicator
                result_data['type'] = indicator_type
                result_data['owner'] = indicator_data.get('owner', {}).get('name')
                result_data['rating'] = indicator_data.get('rating')
                result_data['confidence'] = indicator_data.get('confidence')
                result_data['dateAdded'] = indicator_data.get('dateAdded')
                result_data['lastModified'] = indicator_data.get('lastModified')
                result_data['groups'] = ''

                result_data['description'] = 'N/A'
                # add descritpion to result if Available
                for description in [
                    attr.get('value', '')
                    for attr in indicator_data.get('attribute', [])
                    if 'type' in attr and attr.get('type', '') == 'Description'
                ]:
                    result_data['description'] = description

                # include extra data from includeAdditional if enabled
                if self.include_additional:
                    result_data['observationCount'] = indicator_data.get('observationCount', '0')
                    result_data['falsePositiveCount'] = indicator_data.get(
                        'falsePositiveCount', '0'
                    )

                tags = [t.get('name') for t in indicator_data.get('tag', [])]
                if tags:
                    result_data['tags'] = tags
                else:
                    result_data['tags'] = ''
                result_data['webLink'] = indicator_data.get('webLink')

                try:
                    groups = self.tcs.request.get_group_associations(
                        {'indicator': self.indicator, 'type': indicator_type}
                    )
                except Exception:  # nosec
                    # best effort on getting group associations
                    groups = []
                groups = [t.get('name') for t in groups]
                if groups:
                    result_data['groups'] = groups

                self.logger.info(f'result_data={result_data}')

                self.results.append(result_data)

        for result in self.results:
            yield result


if __name__ == '__main__':
    dispatch(LookupSearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
