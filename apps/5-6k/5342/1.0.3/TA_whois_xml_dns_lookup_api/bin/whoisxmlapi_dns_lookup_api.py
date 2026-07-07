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
class WXADNSLookupCommand(GeneratingCommand):
    search_term = Option(require=True)
    record_types = Option(require=True)
    api_key = Option(require=False)

    __DOMAIN_NAME_REGEX = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]")
    __DNS_RECORD_TYPES = ["A", "NS", "MD", "MF", "CNAME", "SOA", "MB", "MG", "MR", "NULL", "WKS", "PTR", "HINFO",
                          "MINFO", "MX", "TXT", "RP", "AFSDB", "ISDN", "RT", "NSAP", "NSAP_PTR", "SIG", "KEY", "PX",
                          "GPOS", "AAAA", "LOC", "NXT", "EID", "NIMLOC", "SRV", "ATMA", "NAPTR", "KX", "CERT", "DNAME",
                          "APL", "DS", "SSHFP", "IPSECKEY", "RRSIG", "NSEC", "DNSKEY", "DHCID", "TLSA", "ANY", "DLV"]

    def generate(self):
        api_config = self._get_application_config("whoisxmlapi_dns_lookup.conf", "whoisxmlapi_dns_lookup")

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA_whois_xml_dns_lookup_api")
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

        _parameters = [WXADNSLookupCommand._validate_term(t) for t in _terms]

        _parameters = list(filter(lambda item: item is not None, _parameters))

        _types = [(t.upper() if t.upper() in WXADNSLookupCommand.__DNS_RECORD_TYPES else None)
                  for t in self.record_types.split(',')]

        _types = list(filter(lambda item: item is not None, _types))

        if len(_parameters) <= 0:
            self.logger.error('Given search terms are invalid')
            exit(1)

        if len(_types) <= 0:
            self.logger.error('Given DNS records list is invalid')
            exit(1)

        for p in _parameters:
            api_response = ''
            try:
                api_response = self._send_api_request(p, _types, api_config)
            except requests.exceptions.RequestException as e:
                self.logger.error(e)
                exit(1)

            parsed_response = json.loads(api_response)

            if "code" in parsed_response and "messages" in parsed_response:
                self.logger.error(parsed_response['messages'])
                exit(1)

            if 'DNSData' not in parsed_response:
                self.logger.error('Result missed')
                exit(1)

            if 'dnsTypes' not in parsed_response['DNSData']:
                self.logger.error('Result missed')
                exit(1)

            for r in WXADNSLookupCommand._prepare_response(parsed_response):
                yield r

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
        dns_data = response_dict['DNSData']
        for d in dns_data['dnsRecords']:
            row = {
                'domain_name': dns_data['domainName'],
                'dns_types': d['dnsType'],
                'audit_updated_date': dns_data['audit']['updatedDate'],
                'audit_created_date': dns_data['audit']['createdDate'],
                'record_fields': [],
                'values': []
            }

            for key, value in d.items():
                if key in ['dnsType', 'rawText']:
                    continue

                row['record_fields'].append(key)
                row['values'].append(",".join(['"' + str(f) + '"' for f in value]) if type(value) is list else value)

            yield row

    @staticmethod
    def _send_api_request(_search_term, _types, _api_config):
        payload = {
            'apiKey': _api_config['api_key'],
            'domainName': _search_term,
            'type': ','.join(_types),
            'outputFormat': 'JSON'
        }

        response = requests.get(
            _api_config['api_url'],
            params=payload
        )

        return response.content

    @staticmethod
    def _validate_term(term):
        if WXADNSLookupCommand.__DOMAIN_NAME_REGEX.search(term):
            return term
        return None


dispatch(WXADNSLookupCommand, sys.argv, sys.stdin, sys.stdout, None)
