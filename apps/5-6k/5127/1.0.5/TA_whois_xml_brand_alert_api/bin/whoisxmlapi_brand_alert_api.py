#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import sys
import os
import requests

from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

from splunk.clilib import cli_common as cli
import splunklib.client as client


@Configuration(distributed=False)
class WXABrandAlertCommand(GeneratingCommand):
    include_term1 = Option(require=True)
    include_term2 = Option(require=False)
    include_term3 = Option(require=False)
    include_term4 = Option(require=False)
    exclude_term1 = Option(require=False)
    exclude_term2 = Option(require=False)
    exclude_term3 = Option(require=False)
    exclude_term4 = Option(require=False)
    since_date = Option(require=False)

    api_key = Option(require=False)

    __MODE_PURCHASE = 'purchase'
    __MAX_DATE_DELTA = 14

    def generate(self):
        api_config = self._get_application_config(
            "whoisxmlapi_brand_alert.conf", "whoisxmlapi_brand_alert")

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA_whois_xml_brand_alert_api")
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

        include_terms = WXABrandAlertCommand._prepare_search_terms(
            self.include_term1, self.include_term2, self.include_term3, self.include_term4)

        exclude_terms = WXABrandAlertCommand._prepare_search_terms(
            self.exclude_term1, self.exclude_term2, self.exclude_term3, self.exclude_term4)

        if not len(include_terms) > 0:
            self.logger.error('Given search terms are invalid or missing')
            exit(1)

        since_date = (date.today() - timedelta(days=1))

        if self.since_date and len(self.since_date) > 0:
            try:
                since_date = WXABrandAlertCommand._parse_since_date(self.since_date)
            except ValueError as e:
                self.logger.error(e)
                exit(1)
            except Exception as e:
                self.logger.error(e)
                exit(1)

        api_response = ''

        try:
            api_response = self._send_api_request(
                include_terms,
                exclude_terms,
                since_date,
                api_config
            )
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

        if 'domainsList' not in parsed_response:
            self.logger.error('The domainList field missed')
            exit(1)

        domain_list = parsed_response['domainsList']

        for item in domain_list:
            yield {'domain_name': item['domainName'], 'action': item['action']}

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
    def _send_api_request(_include_terms, _exclude_terms, _date, _api_config):
        payload = {
            'apiKey': _api_config['api_key'],
            'sinceDate': _date.strftime('%Y-%m-%d'),
            'responseFormat': 'JSON',
            'mode': WXABrandAlertCommand.__MODE_PURCHASE,
            'includeSearchTerms': _include_terms,
            'excludeSearchTerms': _exclude_terms
        }

        response = requests.post(
            _api_config['api_url'],
            data=json.dumps(payload)
        )

        return response.content

    @staticmethod
    def _prepare_search_terms(_term1, _term2, _term3, _term4):
        r = []
        for term in [_term1, _term2, _term3, _term4]:
            if term and len(term) > 2:
                r.append(term)
            else:
                continue
        return r

    @staticmethod
    def _parse_since_date(_since_date):
        today = date.today()
        given_date = datetime.strptime(_since_date, '%Y-%m-%d').date()

        if given_date >= today:
            raise ValueError('The "since date" should be in the Past.')
        if (today - given_date).days > WXABrandAlertCommand.__MAX_DATE_DELTA:
            raise ValueError('The "since date" should be in (Today - 14 days] interval.')
        return given_date


dispatch(WXABrandAlertCommand, sys.argv, sys.stdin, sys.stdout, None)
