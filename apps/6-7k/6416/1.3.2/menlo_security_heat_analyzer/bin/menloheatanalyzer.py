#!/usr/bin/env python

import json
import requests
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option, validators


@Configuration()
class MenloHeatAnalyzerCommand(EventingCommand):
    """ Enriches records with information from the Menlo HEAT API.

    ##Syntax
    .. code-block::
        menloheatanalyzer field=<domain field>

    ##Description

    %(description)

    """

    field = Option(doc='''
        **Syntax:** **field=***<domain field>*
        **Description:** Specify which field contains the domain name of interest.  Defaults to domain.
        ''',
        require=True,
        validate=validators.Fieldname())



    def prepare(self):
        self.oemid = self.service.storage_passwords['menlo_security_heat_realm:oemid'].clear_password
        self.deviceid = self.service.storage_passwords['menlo_security_heat_realm:deviceid'].clear_password
        self.uid = self.service.storage_passwords['menlo_security_heat_realm:uid'].clear_password

        proxy_enabled_val = self.service.confs['menlo_security_heat_analyzer_settings']['heat_proxy']['proxy_enabled']
        if proxy_enabled_val.lower() in [ "1", "true", "yes" ] :
            self.proxy_enabled = True
            self.proxy_host_port = self.service.confs['menlo_security_heat_analyzer_settings']['heat_proxy']['proxy_host']
            self.proxy_url = f'http://{self.proxy_host_port}'
            proxy_auth_enabled_val = self.service.confs['menlo_security_heat_analyzer_settings']['heat_proxy']['proxy_auth_enabled']
            if proxy_auth_enabled_val.lower() in [ "1", "true", "yes" ] :
                self.proxy_auth_enabled = True
                self.proxy_username = self.service.confs['menlo_security_heat_analyzer_settings']['heat_proxy']['proxy_username']
                if self.proxy_username :
                    self.proxy_url = self.proxy_url.replace('http://', f'http://{ self.proxy_username}@')
                    self.proxy_password = self.service.storage_passwords['menlo_security_heat_realm:proxy_password'].clear_password
                    if self.proxy_password :
                        self.proxy_url = self.proxy_url = self.proxy_url.replace('@', f":{self.proxy_password}@")
            
            self.proxies = { 'https': self.proxy_url }
        else :
            self.proxy_enabled = False
            self.proxies = None



    def transform(self, events):
        log_proxy_info = False
        new_events = list()
        domains = set()
        for event in events:
            new_events.append(event)
            domains.add(event[self.field])
        domain_categories = self.call_heat_api(domains)
        for event in new_events:
            domain = event[self.field]
            if domain in domain_categories:
                event['category_id'] = domain_categories[domain]
            else:
                event['category_id'] = '-1'

            if (log_proxy_info and self.proxy_enabled) :
                event['proxy_host_port'] = self.proxy_host_port
                event['proxy_auth_enabled'] = self.proxy_auth_enabled
                event['proxy_username'] = self.proxy_username
                event['proxy_password'] = self.proxy_password
                event['proxy_url'] = self.proxy_url

        return new_events



    def call_heat_api(self, domains):
        api_headers = { 'Content-Type': 'application/json' }
        result = dict()
        # API will only take 100 domains in a call, so split up the calls
        domain_list = list(domains)
        for x in range(0, len(domain_list), 100):
            response = requests.post(
                url='https://api.bcti.brightcloud.com/1.0/url',
                headers={ 'Content-Type': 'application/json' },
                proxies=self.proxies,
                json=self.create_payload(domain_list[x:100+x])
            )
            result.update(self.process_response(response))

        return result



    def create_payload(self, domains):
        payload = {
            'requestid': '12345',
            'oemid': self.oemid,
            'deviceid': self.deviceid,
            'uid': self.uid,
            'queries': ['Getinfo'],
            'a1cat': 1,
            'reputation': 1,
            'xml': 0
        }

        payload['urls'] = list(domains)

        return payload



    def process_response(self, response):
        domain_categories = dict()

        answer = json.loads(response.text)
        if 'errormsg' in answer:
            raise RuntimeError(answer['errormsg'])

        for result in answer['results']:
            category_ids = list()
            for category in result['queries']['getinfo']['cats']:
                category_ids.append(category['catid'])
            domain_categories[result['url']] = category_ids
        return domain_categories


dispatch(MenloHeatAnalyzerCommand, sys.argv, sys.stdin, sys.stdout, __name__)
