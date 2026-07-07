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
class WXAWebsiteContactsCommand(GeneratingCommand):
    search_term = Option(require=True)
    from_scratch = Option(require=False)
    api_key = Option(require=False)

    __DOMAIN_NAME_REGEX = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]")

    def generate(self):
        api_config = self._get_application_config("whoisxmlapi_website_contacts.conf", "whoisxmlapi_website_contacts")

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA_whois_xml_website_contacts_api")
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

        _parameters = [WXAWebsiteContactsCommand._validate_term(t) for t in _terms]

        _parameters = list(filter(lambda item: item is not None, _parameters))

        _from = self.from_scratch if self.from_scratch is not None \
            and self.from_scratch in [0, 1] else 0

        if len(_parameters) <= 0:
            self.logger.error('Given search terms are invalid')
            exit(1)

        for p in _parameters:
            api_response = ''
            try:
                api_response = self._send_api_request(p, _from, api_config)
            except requests.exceptions.RequestException as e:
                self.logger.error(e)
                exit(1)

            parsed_response = json.loads(api_response)

            if "code" in parsed_response and "messages" in parsed_response:
                self.logger.error(parsed_response['messages'])
                exit(1)

            if 'websiteResponded' not in parsed_response:
                self.logger.error('Result missed')
                exit(1)

            data = WXAWebsiteContactsCommand._prepare_response(parsed_response)

            yield data

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
    def _prepare_response(response_dict):
        result = {
            "domain_name": response_dict['domainName'],
            "company_names": response_dict['companyNames'],
            "country_code": response_dict['countryCode'],
            "emails_description": [x['description'] for x in response_dict['emails']],
            "emails_address": [x['email'] for x in response_dict['emails']],
            "meta_description": response_dict['meta']['description'] if 'description' in response_dict['meta'] else '',
            "meta_title": response_dict['meta']['title'] if 'title' in response_dict['meta'] else '',
            "phones_call_hours": [x['callHours'] for x in response_dict['phones']],
            "phones_description": [x['description'] for x in response_dict['phones']],
            "phones_number": [x['phoneNumber'] for x in response_dict['phones']],
            "postal_addresses": response_dict['postalAddresses'],
            "social_links_facebook": response_dict['socialLinks']['facebook'],
            "social_links_instagram": response_dict['socialLinks']['instagram'],
            "social_links_linkedIn": response_dict['socialLinks']['linkedIn'],
            "social_links_twitter": response_dict['socialLinks']['twitter'],
            "website_responded": response_dict['websiteResponded']
        }

        return result

    @staticmethod
    def _send_api_request(_search_term, _from, _api_config):
        payload = {
            'apiKey': _api_config['api_key'],
            'domainName': _search_term,
            'from': _from
        }

        response = requests.get(
            _api_config['api_url'],
            params=payload
        )

        return response.content

    @staticmethod
    def _validate_term(term):
        if WXAWebsiteContactsCommand.__DOMAIN_NAME_REGEX.search(term):
            return term
        return None


dispatch(WXAWebsiteContactsCommand, sys.argv, sys.stdin, sys.stdout, None)
