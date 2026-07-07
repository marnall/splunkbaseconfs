#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Connectivity Test"""
import os
import re
import socket
import sys
from collections import OrderedDict
from urllib.parse import urlparse

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from requests.exceptions import ProxyError
from splunklib.searchcommands import dispatch, Configuration


@Configuration()
class PreflightChecksCommand(BaseGeneratingCommand):
    """Command to check basic setup and connectivity.

    This command is run from the Support -> Connectivity Test link
    in the App menu.

    Usage:
    | tcpreflightchecks

    e.g.,
    | tcpreflightchecks
    """

    # properties
    exception = None
    filename = os.path.basename(__file__)

    def add_result(self, category, item, status, info):
        """Add result entry for Splunk search output"""
        result_data = OrderedDict()
        result_data['Category'] = category
        result_data['Item'] = item
        result_data['Status'] = status
        result_data['Info'] = info
        self.results.append(result_data)

    def _validate_config_found(self, item, config_value):
        """Validate the config item was found."""
        status = 'FOUND'
        if config_value is None:
            status = 'MISSING'
        self.add_result('Config', item=item, status=status, info=config_value)

    def add_config_values(self):
        """Add configuration to results."""
        self._validate_config_found('App Name', self.tcs.config.app_name)
        self._validate_config_found('App Access Id', self.tcs.config.api_access_id)
        self._validate_config_found(
            'App Secret Key',
            f'{self.tcs.config.api_secret_key[:1]}***{self.tcs.config.api_secret_key[-1:]}',
        )
        self._validate_config_found('App API Url', self.tcs.config.api_base_url)
        self._validate_config_found('Logging Level', self.tcs.config.logging_level)
        self._validate_config_found('Search Max Chunk Size', self.tcs.config.max_chunk_size)
        self._validate_config_found(
            'ThreatConnect Migration Version', self.tcs.config.tc_migration_version
        )
        self._validate_config_found(
            'Playbook Adaptive Response Filter', self.tcs.config.pb_adaptive_response_filter
        )
        self._validate_config_found(
            'Playbook Event Triage Filter', self.tcs.config.pb_event_triage_filter
        )
        self._validate_config_found('Playbook Label Filter', self.tcs.config.pb_label_filter)
        self._validate_config_found(
            'Playbook Workflow Action Filter', self.tcs.config.pb_workflow_action_filter
        )
        self._validate_config_found('Proxy Enabled', str(self.tcs.config.proxy_enabled))
        if self.tcs.config.proxy_enabled:
            self._validate_config_found('Proxy Host', self.tcs.config.proxy_host)
            self._validate_config_found('Proxy Port', self.tcs.config.proxy_port)
            self._validate_config_found('Proxy User', self.tcs.config.proxy_user)
            proxy_pass = ''  # nosec
            if self.tcs.config.proxy_pass:
                proxy_pass = f'{self.tcs.config.proxy_pass[:1]}***{self.tcs.config.proxy_pass[-1:]}'
            self._validate_config_found('Proxy Pass', proxy_pass)
        self._validate_config_found('Search Sleep', self.tcs.config.search_sleep)
        self._validate_config_found(
            'ThreatConnect API Verify SSL', str(self.tcs.config.tc_verify_ssl)
        )

    def generate(self):
        """Implement generate command for connectivity test."""
        if self.exception is not None:
            self.add_result('Config', 'Setup', 'FAILED', self.exception)
        else:
            # Add config data
            self.add_config_values()

            # Test DNS
            self.test_dns()

            # Test Proxy Connectivity
            self.test_proxy()

            # Test Private Cloud Connectivity
            self.test_threatconnect_api()

            # Splunk API Test
            self.test_splunk_api()

        # display the results
        for r in self.results:
            yield r

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        try:
            if not super().prepare():
                return
        except Exception as e:
            self.exception = e.args

    def test_dns(self):
        """Test DNS is working properly."""
        status = None
        domain = 'api.threatconnect.com'
        info = '-'
        try:
            ip = socket.gethostbyname(domain)
            status = 'FAILED'
            info = f'Domain "{domain}" resolved to {ip}'
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                status = 'PASSED'
                info = f'Domain "{domain}" resolved to {ip}'
        except Exception as e:
            status = 'FAILED'
            info = f'Error when resolving domain "{domain}" ({e})'

        # add results
        self.add_result('Network', 'DNS Test', status, info)

    def test_threatconnect_api(self):
        """Test ThreatConnect API connectivity."""
        domain = None
        info = '-'
        ip = None
        status = 'FAILED'
        try:
            domain = urlparse(self.tcs.config.api_base_url).netloc
            ip = socket.gethostbyname(domain)
        except Exception as e:
            info = f'Failed to resolve host {domain} ({e})'

        if ip and domain:
            status = 'FAILED'
            info = f'Domain "{domain}" resolved to {ip}'
            try:
                r = self.tcs.session.get('/v2/owners')
                data = r.json()
                if data.get('status') == 'Success':
                    status = 'PASSED'
                result_count = data.get('data', {}).get('resultCount', 0)

                info = f'Retrieved {result_count} Owners from ThreatConnect API'
            except Exception as e:
                info = f'Failed ThreatConnect API request ({e})'
        self.add_result('Network', 'ThreatConnect API Connectivity', status, info)

    def test_proxy(self):
        """Test Proxy is working properly."""
        if self.tcs.config.proxy_enabled and self.tcs.config.proxy_host:
            info = 'Invalid Proxy Configuration'
            status = 'FAILED'
            try:
                self.tcs.session.get('/v2/owners')
                status = 'PASSED'
                info = (
                    f'Connection to proxy host "{self.tcs.config.proxy_host}" '
                    f'and port {self.tcs.config.proxy_port} succeeded'
                )
            except ProxyError as e:
                info = f'Proxy connection test failed ({e})'
            except Exception:
                info = 'Proxy connection test failed'
            self.add_result('Network', 'Proxy Connectivity', status, info)

    def test_splunk_api(self):
        """Test Proxy is working properly."""
        info = 'Indexes "tc_app_log" and "tc_event_data" could not found'
        status = 'FAILED'
        try:
            self.service.indexes['tc_app_logs']  # pylint: disable=pointless-statement
            self.service.indexes['tc_event_data']  # pylint: disable=pointless-statement
            status = 'PASSED'
            info = 'Found indexes "tc_app_log" and "tc_event_data"'
        except Exception as e:
            info = f'Failed to retrieve indexes from Splunk API ({e})'
        self.add_result('Network', 'Splunk API Check', status, info)


if __name__ == '__main__':
    dispatch(PreflightChecksCommand, sys.argv, sys.stdin, sys.stdout, __name__)
