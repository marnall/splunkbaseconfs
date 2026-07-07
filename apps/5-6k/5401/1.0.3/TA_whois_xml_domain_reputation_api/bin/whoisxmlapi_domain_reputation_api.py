#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import sys
import os
import requests
import re

from ipaddress import IPv4Address, IPv6Address, AddressValueError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

from splunk.clilib import cli_common as cli
import splunklib.client as client
import splunk


@Configuration(distributed=False)
class WXADomainReputationCommand(GeneratingCommand):
    search_term = Option(require=True)
    mode = Option(require=False)
    api_key = Option(require=False)

    __DOMAIN_NAME_REGEX = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]")

    def generate(self):
        api_config = self._get_application_config("whoisxmlapi_domain_reputation.conf", "whoisxmlapi_domain_reputation")

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA_whois_xml_domain_reputation_api")
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

        _terms = str(self.search_term).split(',')

        _terms = [t.strip(' \n\r') for t in _terms]

        _parameters = [WXADomainReputationCommand._validate_term(t) for t in _terms]

        _parameters = list(filter(lambda item: item is not None, _parameters))

        _mode = self.mode if self.mode is not None \
            and self.mode in ['fast', 'full'] else 'fast'

        if len(_parameters) <= 0:
            self.logger.error('Given search terms are invalid')
            exit(1)

        for p in _parameters:
            api_response = ''
            try:
                api_response = self._send_api_request(p, _mode, api_config)
            except requests.exceptions.RequestException as e:
                self.logger.error(e)
                exit(1)

            parsed_response = json.loads(api_response)

            if "code" in parsed_response and "messages" in parsed_response:
                self.logger.error(parsed_response['messages'])
                exit(1)

            if 'reputationScore' not in parsed_response:
                self.logger.error('Result missed')
                exit(1)
            for row in WXADomainReputationCommand._prepare_response(parsed_response, p):
                yield row

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
    def _prepare_response(response_dict, term):
        for test in response_dict['testResults']:
            result = {
                "term": term,
                "mode": response_dict['mode'],
                "score": response_dict['reputationScore'],
                "test": test['test'],
                "test_code": test['testCode'],
                "warnings": test["warnings"],
                "warning_codes": test["warningCodes"]
            }
            yield result

        return

    @staticmethod
    def _send_api_request(_search_term, _mode, _api_config):
        payload = {
            'apiKey': _api_config['api_key'],
            'domainName': _search_term,
            'mode': _mode
        }

        response = requests.get(
            _api_config['api_url'],
            params=payload
        )

        return response.content

    @staticmethod
    def _validate_term(term):
        if WXADomainReputationCommand.__DOMAIN_NAME_REGEX.search(term):
            return term
        else:
            try:
                IPv4Address(term)
                return term
            except AddressValueError:
                pass
        return None


dispatch(WXADomainReputationCommand, sys.argv, sys.stdin, sys.stdout, None)
