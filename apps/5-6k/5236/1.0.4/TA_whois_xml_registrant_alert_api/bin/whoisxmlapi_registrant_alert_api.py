#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import sys
import os
import requests

import logging
from datetime import date, datetime, timedelta
import api

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

from splunk.clilib import cli_common as cli
import splunklib.client as client
import splunk


@Configuration(distributed=False)
class WXARegAlertCommand(GeneratingCommand):
    term1 = Option(require=False)
    term2 = Option(require=False)
    term3 = Option(require=False)
    term4 = Option(require=False)
    exclude_term1 = Option(require=False)
    exclude_term2 = Option(require=False)
    exclude_term3 = Option(require=False)
    exclude_term4 = Option(require=False)
    advanced_term1 = Option(require=False)
    advanced_field1 = Option(require=False)
    advanced_term2 = Option(require=False)
    advanced_field2 = Option(require=False)
    advanced_term3 = Option(require=False)
    advanced_field3 = Option(require=False)
    advanced_term4 = Option(require=False)
    advanced_field4 = Option(require=False)
    api_key = Option(require=False)
    since_date = Option(require=False)

    advanced_mode = False

    __MAX_DATE_DELTA = 14

    def generate(self):

        api_config = self._get_application_config("whoisxmlapi_registrant_alert.conf", "whoisxmlapi_registrant_alert")

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA_whois_xml_registrant_alert_api")
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

        _basic_terms = WXARegAlertCommand._validate_terms(self.term1,
            self.term2, self.term3, self.term4)

        _exclude_terms = WXARegAlertCommand._validate_terms(self.exclude_term1,
            self.exclude_term2, self.exclude_term3, self.exclude_term4)

        _advanced_terms = WXARegAlertCommand._validate_terms(
            {'field': self.advanced_field1, 'term': self.advanced_term1},
            {'field': self.advanced_field2, 'term': self.advanced_term2},
            {'field': self.advanced_field3, 'term': self.advanced_term3},
            {'field': self.advanced_field4, 'term': self.advanced_term4},
        )

        if not self._determine_mode(_basic_terms, _advanced_terms):
            self.logger.error('Received invalid data. Please check the API documentation.')
            exit(1)

        api_config['advanced_mode'] = self.advanced_mode

        since_date = (date.today() - timedelta(days=1))

        if self.since_date and len(self.since_date) > 0:
            try:
                since_date = WXARegAlertCommand._get_since_date(self.since_date)
            except ValueError as e:
                self.logger.error(e)
                exit(1)
            except Exception as e:
                self.logger.error(e)
                exit(1)

        api_response = ''
        try:
            if self.advanced_mode:
                api_response = self._send_api_request(_advanced_terms, [], since_date, api_config)
            else:
                api_response = self._send_api_request(_basic_terms, _exclude_terms, since_date, api_config)
        except requests.exceptions.RequestException as e:
            self.logger.error(e)
            exit(1)

        parsed_response = json.loads(api_response)

        if 'code' in parsed_response:
            self.logger.error('API response: {}'.format(api_response))
            exit(1)

        if 'domainsList' not in parsed_response:
            self.logger.error('The domainList is missed in response')
            exit(1)

        domains_list = parsed_response['domainsList']

        for row in domains_list:
            yield {'domain_name': row['domainName'],
                   'action': row['action'],
                   'date': row['date']}

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
    def _send_api_request(_search_terms, _exclude_terms, _since_date, _api_config):
        payload = {
            'apiKey': _api_config['api_key'],
            'mode': 'purchase',
            'sinceDate': _since_date.strftime('%Y-%m-%d')
        }

        if _api_config['advanced_mode']:
            payload['advancedSearchTerms'] = _search_terms
        else:
            payload['basicSearchTerms'] = {
                'include': _search_terms,
                'exclude': _exclude_terms
            }

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

                        if arg['field'] not in api.advanced_field_list:
                            continue

                        _terms.append(arg)
                else:
                    if len(str(arg)) > 0:
                        _terms.append(arg)

        return _terms

    @staticmethod
    def _get_since_date(raw_date):
        today = date.today()
        given_date = datetime.strptime(str(raw_date).strip('\'"'), '%Y-%m-%d').date()

        if given_date >= today:
            raise ValueError('The "since date" should be in the Past.')
        if (today - given_date).days > WXARegAlertCommand.__MAX_DATE_DELTA:
            raise ValueError('The "since date" should be between yesterday and today - 14 days.'
                             .format(WXARegAlertCommand.__MAX_DATE_DELTA))
        return given_date

    def _determine_mode(self, _basic_terms, _advanced_terms):
        """
        Determine if there are parameters for advanced mode
        and set up the value if self.advanced_mode

        :return: bool - False if the first terms (basic or advanced) are missing, True otherwise
        """
        if len(_advanced_terms) > 0:
            self.advanced_mode = True
        else:
            if len(_basic_terms) > 0:
                self.advanced_mode = False
            else:
                return False

        return True


dispatch(WXARegAlertCommand, sys.argv, sys.stdin, sys.stdout, None)
