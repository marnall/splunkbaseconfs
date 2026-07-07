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
class WXAGeoipCommand(GeneratingCommand):
    search_term = Option(require=True)
    api_key = Option(require=False)

    __DOMAIN_NAME_REGEX = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]")
    __IPV4_REGEX = re.compile(
        r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$")
    __IPV6_REGEX = re.compile(r'^(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}$', re.IGNORECASE)
    __EMAIL_REGEX = re.compile(
        r'^(?:[a-z0-9]+[a-z0-9-\.\+]{2,64})\@(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]',
        re.IGNORECASE)

    __IP_ADDRESS_PARAMETER = 'ipAddress'
    __DOMAIN_PARAMETER = 'domain'
    __EMAIL_PARAMETER = 'email'

    def generate(self):
        api_config = self._get_application_config("whoisxmlapi_geoip.conf", "whoisxmlapi_geoip")

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA_whois_xml_geoip_api")
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

        _parameters = [WXAGeoipCommand._guess_type(t) for t in _terms]

        _parameters = list(filter(lambda item: item is not None, _parameters))

        if len(_parameters) <= 0:
            self.logger.error('Given search terms are invalid')
            exit(1)

        for p in _parameters:
            api_response = ''
            try:
                api_response = self._send_api_request(p['term'], p['type'], api_config)
            except requests.exceptions.RequestException as e:
                self.logger.error(e)
                exit(1)

            parsed_response = json.loads(api_response)

            if "code" in parsed_response and "messages" in parsed_response:
                self.logger.error(parsed_response['messages'])
                exit(1)

            if 'ip' not in parsed_response:
                self.logger.error('Result missed')
                exit(1)

            data = WXAGeoipCommand._flat_response(parsed_response)

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
    def _flat_response(response_dict):
        flat_result = {}
        for k, v in response_dict.items():
            if type(v) is dict:
                flat_result.update(WXAGeoipCommand._flat_response(v))
            else:
                (_k, _v) = WXAGeoipCommand._get_leaf(k, v)
                flat_result[_k] = _v

        return flat_result

    @staticmethod
    def _get_leaf(key, value):
        if type(value) is list:
            return key, ', '.join(value)
        return key, value

    @staticmethod
    def _send_api_request(_search_term, _type, _api_config):
        payload = {
            'apiKey': _api_config['api_key'],
            _type: _search_term
        }

        response = requests.get(
            _api_config['api_url'],
            params=payload
        )

        return response.content

    @staticmethod
    def _guess_type(term):
        if WXAGeoipCommand.__DOMAIN_NAME_REGEX.search(term):
            return {'term': term, 'type': WXAGeoipCommand.__DOMAIN_PARAMETER}
        if WXAGeoipCommand.__IPV4_REGEX.search(term) \
                or WXAGeoipCommand.__IPV6_REGEX.search(term):
            return {'term': term, 'type': WXAGeoipCommand.__IP_ADDRESS_PARAMETER}
        if WXAGeoipCommand.__EMAIL_REGEX.search(term):
            return {'term': term, 'type': WXAGeoipCommand.__EMAIL_PARAMETER}
        return None


dispatch(WXAGeoipCommand, sys.argv, sys.stdin, sys.stdout, None)
