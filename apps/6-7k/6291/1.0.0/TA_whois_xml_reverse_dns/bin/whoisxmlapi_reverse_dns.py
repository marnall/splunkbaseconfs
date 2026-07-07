#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import sys
import os
import requests

from datetime import datetime
import api

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option

from splunk.clilib import cli_common as cli
import splunklib.client as client


@Configuration(distributed=False)
class WXAReverseDnsApiCommand(GeneratingCommand):
    term1 = Option(require=False)
    term2 = Option(require=False)
    term3 = Option(require=False)
    term4 = Option(require=False)
    field1 = Option(require=False)
    field2 = Option(require=False)
    field3 = Option(require=False)
    field4 = Option(require=False)
    exclude1 = Option(require=False)
    exclude2 = Option(require=False)
    exclude3 = Option(require=False)
    exclude4 = Option(require=False)
    record_type = Option(require=False)
    api_key = Option(require=False)

    __RECORD_TYPE = 'soa'

    def generate(self):

        api_config = self._get_application_config(
            'whoisxmlapi_reverse_dns_api.conf',
            'whoisxmlapi_reverse_dns_api'
        )

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key,
                                     app='TA_whois_xml_reverse_dns')
        except Exception as e:
            self.logger.error(
                'An error occurred connecting to splunkd: ' + str(e)
            )
            exit(1)

        if self.api_key and len(self.api_key) > 0:
            api_config['api_key'] = self.api_key
        else:
            for storage_password in service.storage_passwords:
                if storage_password.username == 'admin' \
                        and storage_password.realm == 'api_key':
                    api_config['api_key'] = storage_password.clear_password
                    break

        if not self.record_type \
                or len(self.record_type) == 0 \
                or self.record_type not in api.record_type_list:
            self.record_type = WXAReverseDnsApiCommand.__RECORD_TYPE

        _terms = WXAReverseDnsApiCommand._validate_terms(
            {'field': self.field1, 'term': self.term1, 'exclude': self.exclude1},
            {'field': self.field2, 'term': self.term2, 'exclude': self.exclude2},
            {'field': self.field3, 'term': self.term3, 'exclude': self.exclude3},
            {'field': self.field4, 'term': self.term4, 'exclude': self.exclude4},
        )

        if len(_terms) == 0:
            self.logger.error(
                'Invalid search terms. Please check the API documentation.')
            exit(1)

        api_response = ''
        try:
            api_response = self._send_api_request(_terms, self.record_type, api_config)
        except (requests.exceptions.RequestException,
                requests.exceptions.InvalidSchema) as e:
            self.logger.error(e)
            exit(1)

        parsed_response = json.loads(api_response)

        if 'code' in parsed_response:
            self.logger.error('API response: {}'.format(api_response))
            exit(1)

        if 'result' not in parsed_response:
            self.logger.error('The result is missing in response')
            exit(1)

        record_list = parsed_response['result']

        for row in record_list:
            yield {
                'dns_record': row['value'],
                'domain_name': row['name'],
                'first_seen': datetime.utcfromtimestamp(row['first_seen']).isoformat(' '),
                'last_visit': datetime.utcfromtimestamp(row['last_visit']).isoformat(' ')
            }

    @staticmethod
    def _get_application_config(file, stanza):
        app_dir = os.path.dirname(__file__)
        config_path = os.path.join(app_dir, '../default', file)
        config = cli.readConfFile(config_path)
        local_config_path = os.path.join(app_dir, '../local', file)

        if os.path.exists(local_config_path):
            local_config = cli.readConfFile(local_config_path)
            for name, content in local_config.items():
                if name in config:
                    config[name].update(content)
                else:
                    config[name] = content

        return config[stanza]

    @staticmethod
    def _send_api_request(_search_terms, _record_type, _api_config):
        payload = {
            'apiKey': _api_config['api_key'],
            'recordType': _record_type,
            'terms': _search_terms
        }

        url = _api_config['api_url']

        if not url.startswith('https://'):
            raise requests.exceptions.InvalidSchema(
                'Possible insecure network communication')

        response = requests.post(
            _api_config['api_url'],
            data=json.dumps(payload)
        )

        return response.content

    @staticmethod
    def _validate_terms(*args):
        _terms = []
        for arg in args:
            if arg is not None:
                if type(arg) is dict:
                    if (arg['field'] is not None and len(str(arg['field'])) > 0
                            and arg['term'] is not None and len(str(arg['term'])) > 0):

                        if arg['field'] not in api.field_list:
                            continue

                        if arg['exclude'] is not None \
                                and len(str(arg['exclude'])) > 0:
                            arg['exclude'] = bool(int(arg['exclude']))
                        else:
                            arg['exclude'] = False

                        _terms.append(arg)

        return _terms


dispatch(WXAReverseDnsApiCommand, sys.argv, sys.stdin, sys.stdout, None)
