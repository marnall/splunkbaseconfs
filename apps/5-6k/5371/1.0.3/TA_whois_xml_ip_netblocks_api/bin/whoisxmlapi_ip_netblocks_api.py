#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import sys
import os
import requests
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

from splunk.clilib import cli_common as cli
import splunklib.client as client


def _gvn(data, key):
    if data is None:
        return None
    if type(data) is not dict:
        return data
    if key not in data:
        return None
    return data[key]


@Configuration(distributed=False)
class WXAIPNetblocksCommand(GeneratingCommand):
    search_terms = Option(require=True)
    mask = Option(require=False)
    term_type = Option(require=True)
    api_key = Option(require=False)

    __ALLOWED_TERMS_TYPES = ['ip', 'org', 'asn']
    __IP_TYPE = 'ip'
    __ORG_TYPE = 'org'
    __ASN_TYPE = 'asn'
    __IPV4_REGEX = re.compile(
        r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$")
    __IPV6_REGEX = re.compile(r'^(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}$', re.IGNORECASE)
    __ASN_AND_MASK_REGEX = re.compile(r'^\d+$')

    def generate(self):
        api_config = self._get_application_config("whoisxmlapi_ip_netblocks.conf",
                                                  "whoisxmlapi_ip_netblocks")

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA_whois_xml_ip_netblocks_api")
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

        self._validate_terms()

        api_response = ''
        try:
            api_response = self._send_api_request(self.search_terms, self.mask, self.term_type, api_config)
        except requests.exceptions.RequestException as e:
            self.logger.error(e)
            exit(6)

        parsed_response = json.loads(api_response)

        if "code" in parsed_response and "messages" in parsed_response:
            self.logger.error(parsed_response['messages'])
            exit(7)

        if 'result' not in parsed_response or 'count' not in parsed_response['result']:
            self.logger.error('Result missed')
            exit(8)

        for i in WXAIPNetblocksCommand._build_flat_output(parsed_response['result']['inetnums']):
            yield i

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
    def _build_flat_output(result):
        for block in result:
            yield WXAIPNetblocksCommand._get_flat_row(block)

    @staticmethod
    def _get_flat_row(data):
        out = {
            'inetnum': data['inetnum'],
            'inetnumFirst': data['inetnumFirst'],
            'inetnumLast': data['inetnumLast'],
            'parent': _gvn(data, 'parent'),
            'netname': data['netname'],
            'nethandle': data['nethandle'],
            'description': data['description'],
            'modified': _gvn(data, 'modified'),
            'country': _gvn(data, 'country'),
            'city': _gvn(data, 'city'),
            'address': ' '.join(data['address']),
            'abuseContact.id': [_gvn(x, 'id') for x in data['abuseContact']],
            'abuseContact.person': [_gvn(x, 'person') for x in data['abuseContact']],
            'abuseContact.role': [_gvn(x, 'role') for x in data['abuseContact']],
            'abuseContact.phone': [_gvn(x, 'phone') for x in data['abuseContact']],
            'abuseContact.email': [_gvn(x, 'email') for x in data['abuseContact']],
            'abuseContact.country': [_gvn(x, 'country') for x in data['abuseContact']],
            'abuseContact.city': [_gvn(x, 'city') for x in data['abuseContact']],
            'abuseContact.address': [' '.join(x['address']) for x in data['abuseContact']],
            'adminContact.id': [_gvn(x, 'id') for x in data['adminContact']],
            'adminContact.person': [_gvn(x, 'person') for x in data['adminContact']],
            'adminContact.role': [_gvn(x, 'role') for x in data['adminContact']],
            'adminContact.phone': [_gvn(x, 'phone') for x in data['adminContact']],
            'adminContact.email': [_gvn(x, 'email') for x in data['adminContact']],
            'adminContact.country': [_gvn(x, 'country') for x in data['adminContact']],
            'adminContact.city': [_gvn(x, 'city') for x in data['adminContact']],
            'adminContact.address': [' '.join(x['address']) for x in data['adminContact']],
            'techContact.id': [_gvn(x, 'id') for x in data['techContact']],
            'techContact.person': [_gvn(x, 'person') for x in data['techContact']],
            'techContact.role': [_gvn(x, 'role') for x in data['techContact']],
            'techContact.phone': [_gvn(x, 'phone') for x in data['techContact']],
            'techContact.email': [_gvn(x, 'email') for x in data['techContact']],
            'techContact.country': [_gvn(x, 'country') for x in data['techContact']],
            'techContact.city': [_gvn(x, 'city') for x in data['techContact']],
            'techContact.address': [' '.join(x['address']) for x in data['techContact']],
            'mntBy.mntner': [x['mntner'] for x in data['mntBy']],
            'mntBy.email': [x['email'] for x in data['mntBy']],
            'mntLower.mntner': [x['mntner'] for x in data['mntLower']],
            'mntLower.email': [x['email'] for x in data['mntLower']],
            'mntDomains.mntner': [x['mntner'] for x in data['mntDomains']],
            'mntDomains.email': [x['email'] for x in data['mntDomains']],
            'mntRoutes.mntner': [x['mntner'] for x in data['mntRoutes']],
            'mntRoutes.email': [x['email'] for x in data['mntRoutes']],
            'remarks': ' '.join(data['remarks']) if 'remarks' in data else None,
            'source': data['source']
        }
        if data['as'] is not None:
            out['as.asn'] = _gvn(data['as'], 'asn')
            out['as.name'] = _gvn(data['as'], 'name')
            out['as.type'] = _gvn(data['as'], 'type')
            out['as.route'] = _gvn(data['as'], 'route')
            out['as.domain'] = _gvn(data['as'], 'domain')
        if data['org'] is not None:
            data['org.org'] = _gvn(data['org'], 'org')
            data['org.name'] = _gvn(data['org'], 'name')
            data['org.phone'] = _gvn(data['org'], 'phone')
            data['org.email'] = _gvn(data['org'], 'email')
            data['org.country'] = _gvn(data['org'], 'country')
            data['org.city'] = _gvn(data['org'], 'city')
            data['org.postalCode'] = _gvn(data['org'], 'postalCode')
            data['org.address'] = ' '.join(data['org']['address']) if 'address' in data['org'] else []

        return out

    def _validate_terms(self):
        if self.term_type not in WXAIPNetblocksCommand.__ALLOWED_TERMS_TYPES:
            self.logger.error('Terms type is invalid')
            exit(2)

        _term = None

        if self.term_type == WXAIPNetblocksCommand.__IP_TYPE:
            _terms = str(self.search_terms).split(',')
            for i in _terms:
                if WXAIPNetblocksCommand.__IPV4_REGEX.match(i) or WXAIPNetblocksCommand.__IPV6_REGEX.match(i):
                    _term = i
                    break

            if _term is None:
                self.logger.error('Could not find a valid IP')
                exit(3)

            if self.mask is not None and len(str(self.mask)) > 0:
                if not WXAIPNetblocksCommand.__ASN_AND_MASK_REGEX.match(self.mask) \
                        and (int(self.mask) <= 128 or int(self.mask) >= 0):
                    self.logger.error('Mask is invalid')
                    exit(4)

        elif self.term_type == WXAIPNetblocksCommand.__ORG_TYPE:
            _terms = str(self.search_terms).split(',')
            _term = [str(x).strip() for x in _terms]

        else:
            if str(self.search_terms).lower().find('asn') is not -1:
                _term = str(self.search_terms).lower().replace('asn', '')
            else:
                _term = self.search_terms

            if not WXAIPNetblocksCommand.__ASN_AND_MASK_REGEX.match(_term):
                self.logger.error('Invalid AS number')
                exit(5)

        self.search_terms = _term

    @staticmethod
    def _send_api_request(_term, _mask, _type, _api_config):
        payload = {
            'apiKey': _api_config['api_key'],
            'limit': 1000
        }

        if _type == WXAIPNetblocksCommand.__IP_TYPE:
            payload['ip'] = _term
            if _mask is not None and len(str(_mask)) > 0:
                payload['mask'] = _mask

        if _type == WXAIPNetblocksCommand.__ORG_TYPE:
            payload['org[]'] = _term

        if _type == WXAIPNetblocksCommand.__ASN_TYPE:
            payload['asn'] = _term

        response = requests.get(
            _api_config['api_url'],
            params=payload
        )

        return response.content


dispatch(WXAIPNetblocksCommand, sys.argv, sys.stdin, sys.stdout, None)
