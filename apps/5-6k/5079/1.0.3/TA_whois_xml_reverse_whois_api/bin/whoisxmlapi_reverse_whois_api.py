#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

from splunk.clilib import cli_common as cli
import splunklib.client as client


@Configuration(distributed=False)
class WXAReverseWhoisCommand(GeneratingCommand):
    include_term = Option(require=True)

    api_key = Option(require=False)
    search_type = Option(require=False)

    __MODE_PREVIEW = 'preview'
    __MODE_PURCHASE = 'purchase'
    __SEARCH_TYPE = 'current'

    def generate(self):
        api_config = self._get_application_config("whoisxmlapi_reverse_whois.conf", "whoisxmlapi_reverse_whois")

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA_whois_xml_reverse_whois_api")
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

        if not self.search_type or len(self.search_type) == 0:
            self.search_type = WXAReverseWhoisCommand.__SEARCH_TYPE

        api_response = ''

        try:
            api_response = self._send_api_request(self.include_term, self.search_type, api_config, self.__MODE_PURCHASE)
        except requests.exceptions.RequestException as e:
            self.logger.error(e)
            exit(1)

        parsed_response = json.loads(api_response)

        if "code" in parsed_response and "messages" in parsed_response:
            self.logger.error(parsed_response['messages'])
            exit(1)

        if 'domainsList' not in parsed_response:
            self.logger.error('Domains list missed')
            exit(1)

        domains_list = parsed_response['domainsList']
        for domain in domains_list:
            yield {'domain_name': domain}

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
    def _send_api_request(_include_term, _search_type, _api_config, mode):
        payload = {
            'apiKey': _api_config['api_key'],
            'outputFormat': 'JSON',
            'searchType': _search_type,
            'mode': mode,
            'basicSearchTerms': {
                'include': [_include_term]
            }
        }

        response = requests.post(
            _api_config['api_url'],
            data=json.dumps(payload)
        )

        return response.content


dispatch(WXAReverseWhoisCommand, sys.argv, sys.stdin, sys.stdout, None)
