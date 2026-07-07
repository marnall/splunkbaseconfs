#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import ipaddress
import json
import os
import re
import sys
from collections import OrderedDict

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators

from splunk.clilib import cli_common as cli
import splunklib.client as client


@Configuration(distributed=False)
class WXAWhoisCommand(StreamingCommand):
    domain_field = Option(require=True)
    api_key = Option(require=False)

    __WHOISXMLAPI_SETUP_CONFIG_FILE = "whoisxmlapi_setup.conf"
    __WHOISXMLAPI_API_STANZA = "whoisxmlapi_config"
    __DOMAIN_NAME_REGEX = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]")
    __IPV4_REGEX = re.compile(
        r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$")

    fields_allowed = OrderedDict([
        ("Status", "status"),
        ("CreatedDate", "createdDateNormalized"),
        ("UpdatedDate", "updatedDateNormalized"),
        ("ExpiresDate", "expiresDateNormalized"),

        ("AuditCreatedDate", "audit_createdDate"),
        ("AuditUpdatedDate", "audit_updatedDate"),

        ("RegistrantName", "registrant_name"),
        ("RegistrantOrganization", "registrant_organization"),
        ("RegistrantEmail", "registrant_email"),
        ("RegistrantTelephone", "registrant_telephone"),
        ("RegistrantFax", "registrant_fax"),
        ("RegistrantCountry", "registrant_country"),
        ("RegistrantCountryCode", "registrant_countryCode"),
        ("RegistrantState", "registrant_state"),
        ("RegistrantCity", "registrant_city"),
        ("RegistrantPostalCode", "registrant_postalCode"),
        ("RegistrantStreet1", "registrant_street1"),

        ("AdministrativeContactName", "administrativeContact_name"),
        ("AdministrativeContactOrganization", "administrativeContact_organization"),
        ("AdministrativeContactEmail", "administrativeContact_email"),
        ("AdministrativeContactTelephone", "administrativeContact_telephone"),
        ("AdministrativeContactFax", "administrativeContact_fax"),
        ("AdministrativeContactCountry", "administrativeContact_country"),
        ("AdministrativeContactCountryCode", "administrativeContact_countryCode"),
        ("AdministrativeContactState", "administrativeContact_state"),
        ("AdministrativeContactCity", "administrativeContact_city"),
        ("AdministrativeContactPostalCode", "administrativeContact_postalCode"),
        ("AdministrativeContactStreet1", "administrativeContact_street1"),

        ("TechnicalContactName", "technicalContact_name"),
        ("TechnicalContactOrganization", "technicalContact_organization"),
        ("TechnicalContactEmail", "technicalContact_email"),
        ("TechnicalContactFax", "technicalContact_fax"),
        ("TechnicalContactTelephone", "technicalContact_telephone"),
        ("TechnicalContactCountry", "technicalContact_country"),
        ("TechnicalContactCountryCode", "technicalContact_countryCode"),
        ("TechnicalContactState", "technicalContact_state"),
        ("TechnicalContactCity", "technicalContact_city"),
        ("TechnicalContactPostalCode", "technicalContact_postalCode"),
        ("TechnicalContactStreet1", "technicalContact_street1"),

        ("BillingContactName", "billingContact_name"),
        ("BillingContactOrganization", "billingContact_organization"),
        ("BillingContactEmail", "billingContact_email"),
        ("BillingContactTelephone", "billingContact_telephone"),
        ("BillingContactFax", "billingContact_fax"),
        ("BillingContactCountry", "billingContact_country"),
        ("BillingContactCountryCode", "billingContact_countryCode"),
        ("BillingContactState", "billingContact_state"),
        ("BillingContactCity", "billingContact_city"),
        ("BillingContactPostalCode", "billingContact_postalCode"),
        ("BillingContactStreet1", "billingContact_street1"),

        ("EstimatedDomainAge", "estimatedDomainAge"),
        ("RegistrarName", "registrarName"),
        ("RegistrarIANAID", "registrarIANAID"),
        ("ContactEmail", "contactEmail"),
        ("WhoisServer", "whoisServer"),
        ("StrippedText", "strippedText"),
    ])

    def stream(self, records):

        api_config = WXAWhoisCommand._get_application_config(
            WXAWhoisCommand.__WHOISXMLAPI_SETUP_CONFIG_FILE,
            WXAWhoisCommand.__WHOISXMLAPI_API_STANZA,
        )

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA-whois_xml_api")
        except Exception as e:
            self.logger.error("An error occurred connecting to splunkd: " + str(e))
            exit(1)

        for storage_password in service.storage_passwords:
            if storage_password.username == 'admin' and storage_password.realm == 'api_key':
                api_config['api_key'] = storage_password.clear_password
                break

        domain_name_field = self.domain_field

        cache = dict()

        for event in records:
            result = OrderedDict()
            domain_name = WXAWhoisCommand._validate_domain_name(event[domain_name_field])

            if not domain_name:
                result['IsValid'] = False
            elif domain_name in cache:
                event.update(cache[domain_name])
            else:
                try:
                    api_response = WXAWhoisCommand._send_api_request(domain_name, api_config)
                except requests.exceptions.RequestException as e:
                    self.logger.error(str(e))
                    yield event
                    continue

                normalize_whois = WXAWhoisCommand._normalize_whois(json.loads(api_response))
                result.update(normalize_whois)
                cache[domain_name] = result
                event.update(result)

            yield event

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
    def _send_api_request(_value, _api_config):
        payload = {
            'apiKey': _api_config['api_key'],
            'outputFormat': 'JSON',
            'preferFresh': 1,
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

        if 'WhoisRecord' in y:
            wr = y['WhoisRecord']
            if 'subRecords' in wr and isinstance(wr['subRecords'], list) and len(wr['subRecords']) > 0:
                y['WhoisRecord'] = wr['subRecords'][0]

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
        match = WXAWhoisCommand.__DOMAIN_NAME_REGEX.search(_domain_name) \
                or WXAWhoisCommand.__IPV4_REGEX.search(_domain_name)
        if match:
            return match.group(0)

        try:
            ipaddress.ip_address(_domain_name)
            return _domain_name
        except ValueError:
            pass

        return None

    @staticmethod
    def _normalize_whois(_source_whois):
        prefixes = (
            "WhoisRecord_",
            "WhoisRecord_registryData_",
        )

        _source_whois = WXAWhoisCommand._flatten_json(_source_whois)

        if "WhoisRecord_parseCode" in _source_whois and _source_whois["WhoisRecord_parseCode"] == 0:
            return {}

        result_whois = OrderedDict()

        for result_field, source_field in WXAWhoisCommand.fields_allowed.items():
            for prefix in prefixes:
                source_key = '{}{}'.format(prefix, source_field)
                if source_key in _source_whois:
                    if result_field not in result_whois:
                        result_whois[result_field] = _source_whois[source_key]
                    break
            else:
                result_whois[result_field] = None

        return result_whois


dispatch(WXAWhoisCommand, sys.argv, sys.stdin, sys.stdout, None)
