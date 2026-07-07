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
class WXAReverseDnsCommand(GeneratingCommand):
    ip_address = Option(require=True)

    api_key = Option(require=False)

    __IP_REGEX = re.compile(
        r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$")

    __MODE_PREVIEW = 'preview'
    __MODE_PURCHASE = 'purchase'
    __MAX_ITERATIONS = 20

    def generate(self):
        api_config = self._get_application_config("whoisxmlapi_reverse_dns.conf", "whoisxmlapi_reverse_dns")

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA_whois_xml_reverse_dns_api")
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

        if not WXAReverseDnsCommand._validate_ip_address(self.ip_address):
            self.logger.error('Given IP address is invalid')
            exit(1)

        latest_name = ''

        for i in range(WXAReverseDnsCommand.__MAX_ITERATIONS):
            api_response = ''
            try:
                api_response = self._send_api_request(self.ip_address, latest_name, api_config)
            except requests.exceptions.RequestException as e:
                self.logger.error(e)
                exit(1)

            parsed_response = json.loads(api_response)

            if "code" in parsed_response and "messages" in parsed_response:
                self.logger.error(parsed_response['messages'])
                exit(1)

            if 'size' not in parsed_response:
                self.logger.error('The size field missed')
                exit(1)

            if 'result' not in parsed_response:
                self.logger.error('Domains list missed')
                exit(1)

            domains_list = parsed_response['result']
            latest_name = domains_list[-1]['name']

            for row in domains_list:
                yield {'domain_name': row['name'],
                       'first_seen': datetime.utcfromtimestamp(row['first_seen']).isoformat(' '),
                       'last_visit': datetime.utcfromtimestamp(row['last_visit']).isoformat(' ')}

            if parsed_response['size'] < 300:
                break

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
    def _send_api_request(_ip_address, _latest_name, _api_config):
        payload = {
            'apiKey': _api_config['api_key'],
            'ip': _ip_address
        }

        if _latest_name and len(_latest_name) > 0:
            payload['from'] = _latest_name

        response = requests.get(
            _api_config['api_url'],
            params=payload
        )

        return response.content

    @staticmethod
    def _validate_ip_address(ip):
        match = WXAReverseDnsCommand.__IP_REGEX.search(ip)
        if not match:
            return False

        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            pass

        return False


dispatch(WXAReverseDnsCommand, sys.argv, sys.stdin, sys.stdout, None)
