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
class WXASubdomainsCommand(GeneratingCommand):
    search_term = Option(require=True)
    api_key = Option(require=False)

    __DOMAIN_NAME_REGEX = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]")

    def generate(self):

        api_config = self._get_application_config("whoisxmlapi_subdomains.conf", "whoisxmlapi_subdomains")

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA_whois_xml_subdomains_api")
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

        if not WXASubdomainsCommand._validate_search_term(self.search_term):
            self.logger.error('Given search term is invalid')
            exit(1)

        api_response = ''
        try:
            api_response = self._send_api_request(self.search_term, api_config)
        except requests.exceptions.RequestException as e:
            self.logger.error(e)
            exit(1)

        parsed_response = json.loads(api_response)

        if "code" in parsed_response and "messages" in parsed_response:
            self.logger.error(parsed_response['messages'])
            exit(1)

        if 'result' not in parsed_response:
            self.logger.error('Result missed')
            exit(1)

        parsed_response = parsed_response['result']

        if 'count' not in parsed_response:
            self.logger.error('The size field missed')
            exit(1)

        size = int(parsed_response['count'])
        if size < 1:
            return

        if 'records' not in parsed_response:
            self.logger.error('Domains list missed')
            exit(1)

        domains_list = parsed_response['records']

        for row in domains_list:
            yield {'domain_name': row['domain'],
                   'first_seen': datetime.utcfromtimestamp(int(row['firstSeen'])).isoformat(' '),
                   'last_visit': datetime.utcfromtimestamp(int(row['lastSeen'])).isoformat(' ')}

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
    def _send_api_request(_search_term, _api_config):
        payload = {
            'apiKey': _api_config['api_key'],
            'domainName': _search_term
        }

        response = requests.get(
            _api_config['api_url'],
            params=payload
        )

        return response.content

    @staticmethod
    def _validate_search_term(term):
        match_domain = WXASubdomainsCommand.__DOMAIN_NAME_REGEX.search(term)

        return True if match_domain else False


dispatch(WXASubdomainsCommand, sys.argv, sys.stdin, sys.stdout, None)
