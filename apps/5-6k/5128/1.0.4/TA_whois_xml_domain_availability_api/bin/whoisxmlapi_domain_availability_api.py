#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import sys
import os
import requests
import re

import ipaddress
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

from splunk.clilib import cli_common as cli
import splunklib.client as client


@Configuration(distributed=False)
class WXADomainAvailabilityCommand(GeneratingCommand):
    domain_name = Option(require=True)
    mode = Option(require=False)

    api_key = Option(require=False)

    __DOMAIN_NAME_REGEX = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]")

    __MODE_DNS_AND_WHOIS = 'DNS_AND_WHOIS'
    __MODE_DNS_ONLY = 'DNS_ONLY'

    def generate(self):
        api_config = self._get_application_config(
            "whoisxmlapi_domain_availability.conf", "whoisxmlapi_domain_availability")

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA_whois_xml_domain_availability_api")
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

        if self.mode and len(self.mode) > 0:
            mode = self.mode
        else:
            mode = WXADomainAvailabilityCommand.__MODE_DNS_AND_WHOIS

        domains = WXADomainAvailabilityCommand._parse_domain_names(self.domain_name)

        if not len(domains) > 0:
            self.logger.error('Given domain names are invalid')
            exit(1)

        api_response = ''

        for domain in domains:
            try:
                api_response = self._send_api_request(domain, mode, api_config)
            except requests.exceptions.RequestException as e:
                self.logger.error(e)
                exit(1)

            try:
                parsed_response = json.loads(api_response)
            except json.JSONDecodeError as e:
                self.logger.error(e)
                exit(1)

            if "code" in parsed_response and "messages" in parsed_response:
                self.logger.error(parsed_response['messages'])
                exit(1)

            if 'DomainInfo' not in parsed_response:
                self.logger.error('The DomainInfo field missed')
                exit(1)

            if 'domainAvailability' not in parsed_response['DomainInfo']:
                self.logger.error('Domain availability status missed')
                exit(1)

            domain_availability = parsed_response['DomainInfo']['domainAvailability']

            yield {'domain_availability': domain_availability, 'domain_name': domain}

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
    def _send_api_request(_domain_name, _mode, _api_config):
        payload = {
            'apiKey': _api_config['api_key'],
            'domainName': _domain_name,
            'outputFormat': 'JSON'
        }

        if _mode and len(_mode) > 0:
            payload['mode'] = _mode

        response = requests.get(
            _api_config['api_url'],
            params=payload
        )

        return response.content

    @staticmethod
    def _validate_domain_name(_domain_name):
        match = WXADomainAvailabilityCommand.__DOMAIN_NAME_REGEX.search(_domain_name)
        if not match:
            return False

        return True

    @staticmethod
    def _parse_domain_names(_domain_names):
        if _domain_names and len(_domain_names) > 0:
            domain_list = []
            domain_candidates = str(_domain_names).split(',')
            for candidate in domain_candidates:
                cleared = str(candidate).strip()
                if WXADomainAvailabilityCommand._validate_domain_name(cleared):
                    domain_list.append(cleared)
            return domain_list
        else:
            return []


dispatch(WXADomainAvailabilityCommand, sys.argv, sys.stdin, sys.stdout, None)
