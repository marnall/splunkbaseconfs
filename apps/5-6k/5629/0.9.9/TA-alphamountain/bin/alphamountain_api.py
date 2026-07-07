#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import sys
import os
import requests
import re
import logging
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

from splunk.clilib import cli_common as cli
import splunklib.client as client
import splunk
from common import category_name_mapping

@Configuration(distributed=False)
class alphaMountainCommand(GeneratingCommand):
    search_term = Option(require=True)
    hard_refresh = Option(require=False)
    api_key = Option(require=False)

    __DOMAIN_NAME_REGEX = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]")

    def generate(self):
        api_config = self._get_application_config("alphamountain.conf", "alphamountain")
        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA-alphamountain")
        except Exception as e:
            self.logger.error("An error occurred connecting to splunkd: " + str(e))
            exit(1)

        if self.api_key and len(self.api_key) > 0:
            api_config['api_key'] = self.api_key
        else:
            for storage_password in service.storage_passwords:
                if storage_password.username == 'admin' and storage_password.realm == 'api_key':
                    api_config['api_key'] = storage_password.clear_password
                    self.logger.error(storage_password.clear_password)
                    break

        api_config['threat_url'] = 'https://api.alphamountain.ai/threat/uri/'
        api_config['categories_url'] = 'https://api.alphamountain.ai/category/uri/'
        api_config['impersonate_url'] = 'https://api.alphamountain.ai/impersonate/uri/'

        _terms = str(self.search_term).split(',')

        _terms = [t.strip(' \n\r') for t in _terms]

        _hosts = [alphaMountainCommand._validate_term(t) for t in _terms]

        _hosts = list(filter(lambda item: item is not None, _hosts))

        _refresh = self.hard_refresh if self.hard_refresh is not None \
            and self.hard_refresh in [0, 1] else 0

        if len(_hosts) <= 0:
            self.logger.error('Given search terms are invalid')
            exit(2)

        for host in _hosts:
            threat_response = ''
            categories_response = ''
            impersonate_response = ''
            try:
                # api_response = self._lookup_filter(p, api_config)
                threat_response = self._call_API (host, api_config, 'threat_url')
                categories_response = self._call_API (host, api_config, 'categories_url')
                impersonate_response = self._call_API (host, api_config, 'impersonate_url')
            except requests.exceptions.RequestException as e:
                self.logger.error(e)
                exit(3)

            data = alphaMountainCommand._prepare_response(host, threat_response, categories_response, impersonate_response)

            yield data

    @staticmethod
    def _get_application_config_value(file, stanza, key):
        stanza_value = alphaMountainCommand._get_application_config(file, stanza)
        if stanza_value and key in stanza_value:
            return stanza_value[key]
        else:
            return ''

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

        if stanza in config:
            return config[stanza]
        else:
            return None

    @staticmethod
    def _update_application_config_value(file, stanza, key, value):
        app_dir = os.path.dirname(__file__)
        local_config_path = os.path.join(app_dir, "../local", file)
        key_value = {key:value}

        if os.path.exists(local_config_path):
            local_config = cli.readConfFile(local_config_path)
            if stanza in local_config:
                local_config[stanza].update(key_value)
            else:
                local_config[stanza] = key_value
            cli.writeConfFile(local_config_path, local_config)
            # self.logger.error("error here")
            # exit(7)            

    @staticmethod
    def _prepare_response(site, threat_response, categories_response, impersonate_response):

        if threat_response == 401:
            risk_score = 'Valid license required'
        elif threat_response == 429:
            risk_score = 'Quota exhausted'
            # Set "time out" so won't continue to hit API
            alphaMountainCommand._set_quota_exhausted_timeout('threat_url')
        elif str(threat_response).isnumeric():
            risk_score = 'Error requesting data'            
        else:
            risk_score = "{:.3}".format(float(threat_response['threat']['score'])) if threat_response['status']['threat'] == "Success" else '-'

        if categories_response == 401:
            categories_names = 'Valid license required'
        elif categories_response == 429:
            categories_names = 'Quota exhausted'
            # Set "time out" so won't continue to hit API
            alphaMountainCommand._set_quota_exhausted_timeout('categories_url')
        elif str(categories_response).isnumeric():
            categories_names = 'Error requesting data'            
        else:
            separator = ''
            categories_names = ''
            if categories_response['status']['category'] == "Success":
                for catID in categories_response['category']['categories']:               
                    categories_names = categories_names + separator + category_name_mapping[catID]
                    separator = ', '
            else:
                categories_names = 'Unrated'

        if impersonate_response == 401:
            impersonate_domain = 'Valid license required'
        elif impersonate_response == 429:
            impersonate_domain = 'Quota exhausted'
            # Set "time out" so won't continue to hit API
            alphaMountainCommand._set_quota_exhausted_timeout('impersonate_url')
        elif str(impersonate_response).isnumeric():
            impersonate_domain = 'Error requesting data'            
        else:
            impersonate_domain = impersonate_response['impersonate'] if impersonate_response['status']['impersonate'] == "Success" and impersonate_response['impersonate'] else '-'

        result = {
            "host": site,
            "categories": categories_names,
            "risk_score": risk_score,
            "possible_typo": impersonate_domain
        }

        return result

    @staticmethod
    def _call_API(site, api_config, endpoint):

        if alphaMountainCommand._is_quota_exhausted_timeout(endpoint) == True:
            return 429

        url = 'http://' + site
        headers = { 'Content-Type': 'application/json' }
        data = { 'version': 1, 'license': api_config['api_key'], 'type': 'partner.info', 'uri': url }
        r = requests.post(api_config[endpoint], headers=headers, data=json.dumps(data))

        if r.status_code == 200:
            j = r.json()
            return j
        elif r.status_code > 0:
            return r.status_code
        else:
            self.logger.error(r.status_code)
            self.logger.error(r.text)
            exit(6)


    @staticmethod
    def _is_quota_exhausted_timeout(endpoint):
        # check config file for timeout value for endpoint
        timeout = alphaMountainCommand._get_application_config_value("app.conf", "timeout", endpoint)
        # if not exists, return false
        if not timeout:
            return False
        # if exits and expired, clear value and return false
        elif (time.time() - float(timeout) > 60*60):
            alphaMountainCommand._update_application_config_value("app.conf", "timeout", endpoint, '')
            return False
        # if exists and still in timeout, return true
        else:
            return True

    @staticmethod
    def _set_quota_exhausted_timeout(endpoint):
        timeout = alphaMountainCommand._get_application_config_value("app.conf", "timeout", endpoint)
        # only set if not currently set (or will never expire)
        if not timeout:
            # set timeout value (1 hour) in config for endpoint
            alphaMountainCommand._update_application_config_value("app.conf", "timeout", endpoint, time.time() + 60*60)

    @staticmethod
    def _validate_term(term):
        if alphaMountainCommand.__DOMAIN_NAME_REGEX.search(term):
            return term
        return None

dispatch(alphaMountainCommand, sys.argv, sys.stdin, sys.stdout, None)