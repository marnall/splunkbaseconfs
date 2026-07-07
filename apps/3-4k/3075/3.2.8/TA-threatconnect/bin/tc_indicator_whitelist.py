#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Download Indicator Whitelist Command"""
import sys
import os
import ipaddress
import re

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class IndicatorWhitelistCommand(BaseGeneratingCommand):
    """Download Tag Data from ThreatConnect.

    Used in Configure -> Indicator Whitelist -> List/Configure pages and Configure -> Indicator
    Downloads -> Edit.

    Usage:
    | tciw key=<indicator whitelist key>

    e.g.,
    | tciw key=abc123
    """

    # args
    key = Option(doc='The **indicator whitelist key** from the KV Store.', require=False)

    # properties
    fetch_size = 50000
    filename = os.path.basename(__file__)

    def filter_indicators_whitelist_by_type(self, indicator_type, filter_type):
        """Filter the indicator whitelist by type."""
        if filter_type not in ['CIDR', 'Regex', 'String']:
            return

        for indicator in self.tcs.collections.indicators.paginate(
            fields='_key,indicator', query={'type': indicator_type}
        ):
            if filter_type == 'CIDR':
                should_delete = self.filter_indicator_whitelist_cidr(indicator.get('indicator', ''))
            elif filter_type == 'Regex':
                should_delete = self.filter_indicator_whitelist_regex(
                    indicator.get('indicator', '')
                )
            else:
                should_delete = self.filter_indicator_whitelist_string(
                    indicator.get('indicator', '')
                )

            if should_delete:
                self.results.append(indicator)
                self.tcs.collections.indicators.delete_by_id(indicator.get('_key'))

    def filter_indicators_whitelist(self):
        """Filter indicator whitelist."""
        for indicator_type in self.indicator_whitelist_data.get('filterIndicatorTypes', []):
            self.filter_indicators_whitelist_by_type(
                indicator_type, self.indicator_whitelist_data.get('filterType', '')
            )

    def filter_indicator_whitelist_cidr(self, indicator):
        """Compare indicator using CIDR whitelist."""
        try:
            ip = ipaddress.ip_address(indicator)
        except ValueError:
            return False

        for cidr in self.indicator_whitelist_data.get('filterValue', []):
            try:
                cidr_network = ipaddress.ip_network(cidr)
            except Exception:
                self.logger.warning(
                    f'action: skipped-cidr, reason: invalid cidr "{cidr}" in indicator filter.'
                )
                continue

            if ip in cidr_network:
                self.logger.debug(
                    f'filter: whitelist-cidr, indicator: {indicator}, filter: {cidr}, check: failed'
                )
                return True
        return False

    def filter_indicator_whitelist_regex(self, indicator):
        """Compare indicator using regex whitelist."""
        for rex in self.indicator_whitelist_data.get('filterValue', []):
            try:
                rex_compiled = re.compile(r'{}'.format(rex))
            except re.error:
                self.logger.warning(
                    f'action: skipped-regex, reason: invalid regex "{rex}" in indicator filter.'
                )
                continue

            if re.match(rex_compiled, indicator):
                self.logger.debug(
                    f'filter: whitelist-regex, indicator: {indicator}, filter: {rex}, check: failed'
                )
                return True
        return False

    def filter_indicator_whitelist_string(self, indicator):
        """Compare indicator using string whitelist."""
        if indicator in self.indicator_whitelist_data.get('filterValue', []):
            self.logger.debug(
                f'filter: whitelist-string, indicator: {indicator}, '
                f'filter: {self.indicator_whitelist_data.get("filterValue", [])}, check: failed'
            )
            return True
        return False

    def generate(self):
        """Implement generate method for demo data and results."""
        self.filter_indicators_whitelist()

        # display results
        for r in self.results:
            yield r

    @property
    def indicator_whitelist_data(self):
        """Return the indicator whitelist data."""
        try:
            return self.tcs.collections.indicator_whitelist.query_by_id(self.key)
        except Exception:
            self.error_exit(None, 'Indicator whitelist could not be found.')

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return


if __name__ == '__main__':
    dispatch(IndicatorWhitelistCommand, sys.argv, sys.stdin, sys.stdout, __name__)
