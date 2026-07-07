#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import sys
import os
import requests
import re

import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

from splunk.clilib import cli_common as cli
import splunklib.client as client
import splunk


@Configuration(distributed=False)
class WXADomainsSubdomainsDiscoveryCommand(GeneratingCommand):
    include_terms = Option(require=False)
    exclude_terms = Option(require=False)
    include_domains = Option(require=False)
    exclude_domains = Option(require=False)
    include_subdomains = Option(require=False)
    exclude_subdomains = Option(require=False)
    since_date = Option(require=False)
    term_type = Option(require=False)
    api_key = Option(require=False)

    __ALLOWED_TERMS_TYPES = ['domains', 'subdomains']

    def generate(self):
        api_config = self._get_application_config("whoisxmlapi_domains_and_subdomains_discovery.conf",
                                                  "whoisxmlapi_domains_and_subdomains_discovery")

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA_whois_xml_domains_and_subdomains_discovery_api")
        except Exception as e:
            self.logger.error("An error occurred connecting to splunkd: " + str(e))
            exit(1)

        if self.api_key and len(self.api_key) > 0:
            api_config['api_key'] = self.api_key
        else:
            for storage_password in service.storage_passwords:
                if storage_password.username == 'admin' and storage_password.realm == 'api_key':
                    api_config['api_key'] = storage_password.clear_password
                    break

        if self.term_type is not None and self.term_type in WXADomainsSubdomainsDiscoveryCommand.__ALLOWED_TERMS_TYPES:
            if self.term_type == 'domains':
                self.include_domains = self.include_terms
                self.exclude_domains = self.exclude_terms
            else:
                self.include_subdomains = self.include_terms
                self.exclude_subdomains = self.exclude_terms

        _include_domains = str(self.include_domains).split(',') \
            if self.include_domains is not None and len(self.include_domains) > 0 else []
        _include_domains = [t.strip(' \n\r') for t in _include_domains]

        _exclude_domains = str(self.exclude_domains).split(',') \
            if self.exclude_domains is not None and len(self.exclude_domains) > 0 else []
        _exclude_domains = [t.strip(' \n\r') for t in _exclude_domains]

        _include_subdomains = str(self.include_subdomains).split(',') \
            if self.include_subdomains is not None and len(self.include_subdomains) > 0 else []
        _include_subdomains = [t.strip(' \n\r') for t in _include_subdomains]

        _exclude_subdomains = str(self.exclude_subdomains).split(',') \
            if self.exclude_subdomains is not None and len(self.exclude_subdomains) > 0 else []
        _exclude_subdomains = [t.strip(' \n\r') for t in _exclude_subdomains]

        if len(_include_domains) + len(_include_subdomains) <= 0:
            self.logger.error('Given search terms are invalid')
            exit(2)

        domains = {}
        if len(_include_domains) > 0 or len(_exclude_domains) > 0:
            domains['include'] = _include_domains
            domains['exclude'] = _exclude_domains

        subdomains = {}
        if len(_exclude_subdomains) > 0 or len(_include_subdomains) > 0:
            subdomains['include'] = _include_subdomains
            subdomains['exclude'] = _exclude_subdomains

        _since_date = None

        try:
            _since_date = datetime.strptime(self.since_date, "%Y-%m-%d")\
                .strftime("%Y-%m-%d") if self.since_date is not None else None
        except ValueError as e:
            self.logger.error(e)
            exit(3)

        api_response = ''
        try:
            api_response = self._send_api_request(domains, subdomains, _since_date, api_config)
        except requests.exceptions.RequestException as e:
            self.logger.error(e)
            exit(4)

        parsed_response = json.loads(api_response)

        if "code" in parsed_response and "messages" in parsed_response:
            self.logger.error(parsed_response['messages'])
            exit(5)

        if 'domainsCount' not in parsed_response:
            self.logger.error('Result missed')
            exit(6)

        for domain in parsed_response['domainsList']:
            yield {"domain_name": domain}

    @staticmethod
    def _get_application_config(file, stanza):
        app_dir = os.path.dirname(__file__)
        config_path = os.path.join(app_dir, "../default", file)
        config = cli.readConfFile(config_path)
        local_config_path = os.path.join(app_dir, "../local", file)

        if os.path.exists(local_config_path):
            local_config = cli.readConfFile(local_config_path)
            for name, content in local_config.items():
                if name in config:
                    config[name].update(content)
                else:
                    config[name] = content

        return config[stanza]

    @staticmethod
    def _send_api_request(_domains, _subdomains, _since_date, _api_config):
        payload = {
            'apiKey': _api_config['api_key'],
        }

        if len(_domains.keys()) > 0:
            payload['domains'] = _domains

        if len(_subdomains.keys()) > 0:
            payload['subdomains'] = _subdomains

        if _since_date is not None:
            payload['sinceDate'] = _since_date

        response = requests.post(
            _api_config['api_url'],
            json=payload
        )

        return response.content


dispatch(WXADomainsSubdomainsDiscoveryCommand, sys.argv, sys.stdin, sys.stdout, None)
