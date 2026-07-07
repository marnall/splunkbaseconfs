#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import re
import sys
from collections import OrderedDict

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

from splunk.clilib import cli_common as cli
import splunklib.client as client

import csv


@Configuration(distributed=False)
class WXAWhoisHistoryCommand(GeneratingCommand):
    domain_name = Option(require=True)
    api_key = Option(require=False)
    fields = Option(require=False)

    __DOMAIN_NAME_REGEX = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]")

    __MODE_PREVIEW = 'preview'
    __MODE_PURCHASE = 'purchase'

    fields_allowed = OrderedDict([
        ("DomainName", "domainName"),
        ("Status", "status"),
        ("CreatedDate", "createdDateISO8601"),
        ("UpdatedDate", "updatedDateISO8601"),
        ("ExpiresDate", "expiresDateISO8601"),

        ("AuditCreatedDate", "audit_createdDate"),
        ("AuditUpdatedDate", "audit_updatedDate"),

        ("RegistrantName", "registrantContact_name"),
        ("RegistrantOrganization", "registrantContact_organization"),
        ("RegistrantEmail", "registrantContact_email"),
        ("RegistrantTelephone", "registrantContact_telephone"),
        ("RegistrantFax", "registrantContact_fax"),
        ("RegistrantCountry", "registrantContact_country"),
        ("RegistrantState", "registrantContact_state"),
        ("RegistrantCity", "registrantContact_city"),
        ("RegistrantPostalCode", "registrantContact_postalCode"),
        ("RegistrantStreet", "registrantContact_street"),

        ("AdministrativeContactName", "administrativeContact_name"),
        ("AdministrativeContactOrganization", "administrativeContact_organization"),
        ("AdministrativeContactEmail", "administrativeContact_email"),
        ("AdministrativeContactTelephone", "administrativeContact_telephone"),
        ("AdministrativeContactFax", "administrativeContact_fax"),
        ("AdministrativeContactCountry", "administrativeContact_country"),
        ("AdministrativeContactState", "administrativeContact_state"),
        ("AdministrativeContactCity", "administrativeContact_city"),
        ("AdministrativeContactPostalCode", "administrativeContact_postalCode"),
        ("AdministrativeContactStreet", "administrativeContact_street"),

        ("TechnicalContactName", "technicalContact_name"),
        ("TechnicalContactOrganization", "technicalContact_organization"),
        ("TechnicalContactEmail", "technicalContact_email"),
        ("TechnicalContactTelephone", "technicalContact_telephone"),
        ("TechnicalContactFax", "technicalContact_fax"),
        ("TechnicalContactCountry", "technicalContact_country"),
        ("TechnicalContactState", "technicalContact_state"),
        ("TechnicalContactCity", "technicalContact_city"),
        ("TechnicalContactPostalCode", "technicalContact_postalCode"),
        ("TechnicalContactStreet", "technicalContact_street"),

        ("BillingContactName", "billingContact_name"),
        ("BillingContactOrganization", "billingContact_organization"),
        ("BillingContactEmail", "billingContact_email"),
        ("BillingContactTelephone", "billingContact_telephone"),
        ("BillingContactFax", "billingContact_fax"),
        ("BillingContactCountry", "billingContact_country"),
        ("BillingContactState", "billingContact_state"),
        ("BillingContactCity", "billingContact_city"),
        ("BillingContactPostalCode", "billingContact_postalCode"),
        ("BillingContactStreet", "billingContact_street"),

        ("RegistrarName", "registrarName"),
        ("WhoisServer", "whoisServer"),
        ("CleanText", "cleanText"),
    ])

    def generate(self):
        api_config = self._get_application_config("whoisxmlapi_hist.conf", "whoisxmlapi_hist")

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA-whois_xml_history_api")
        except Exception as e:
            self.logger.error("An error occurred connecting to splunkd: " + str(e))
            exit(1)

        for storage_password in service.storage_passwords:
            if storage_password.username == 'admin' and storage_password.realm == 'api_key':
                api_config['api_key'] = storage_password.clear_password
                break

        domain_name = self._validate_domain_name(self.domain_name)

        if not domain_name:
            self.logger.error('bad domain name: ' + self.domain_name)
            exit(1)

        api_response = ''

        if domain_name:
            try:
                api_response = self._send_api_request(domain_name, api_config, self.__MODE_PURCHASE)
            except requests.exceptions.RequestException as e:
                self.logger.error(e)
                exit(1)

        parsed_response = json.loads(api_response)

        if "code" in parsed_response and "messages" in parsed_response:
            self.logger.error(parsed_response['messages'])
            exit(1)

        for whois in parsed_response["records"]:
            norm_whois = self._normalize_whois(whois, self.fields)
            yield norm_whois

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
    def _send_api_request(_value, _api_config, mode):
        payload = {
            'apiKey': _api_config['api_key'],
            'outputFormat': 'JSON',
            'mode': mode,
            'domainName': _value
        }

        response = requests.get(
            _api_config['api_url'],
            params=payload
        )

        return response.content

    @staticmethod
    def _flatten_json(y):
        out = {}

        def flatten(x, name=''):
            if type(x) is dict:
                for a in x:
                    flatten(x[a], name + a + '_')
            elif type(x) is list:
                i = 0
                for a in x:
                    flatten(a, name + str(i) + '_')
                    i += 1
            else:
                out[name[:-1]] = x

        flatten(y)
        return out

    @staticmethod
    def _validate_domain_name(_domain_name):
        match = WXAWhoisHistoryCommand.__DOMAIN_NAME_REGEX.search(_domain_name)

        return match.group(0) if match else None

    @staticmethod
    def _normalize_whois(_source_whois, fields=None):

        _source_whois = WXAWhoisHistoryCommand._flatten_json(_source_whois)

        result_whois = OrderedDict()

        if fields is not None:
            fields = next(csv.reader([str(fields)]))

            for userField in fields:
                if userField in WXAWhoisHistoryCommand.fields_allowed:
                    source_field = WXAWhoisHistoryCommand.fields_allowed[userField]
                    if source_field in _source_whois:
                        result_whois[userField] = _source_whois[source_field]
                    else:
                        result_whois[userField] = None
                else:
                    result_whois[userField] = None
        else:
            for result_field, source_field in WXAWhoisHistoryCommand.fields_allowed.items():
                if source_field in _source_whois:
                    result_whois[result_field] = _source_whois[source_field]
                else:
                    result_whois[result_field] = None

        return result_whois


dispatch(WXAWhoisHistoryCommand, sys.argv, sys.stdin, sys.stdout, None)
