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

def setup_logging():
    logger = logging.getLogger('splunk.whoisxmlapi')    
    SPLUNK_HOME = os.environ['SPLUNK_HOME']

    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "whoisxmlapi.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a') 
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger

@Configuration(distributed=False)
class WXAWebsiteCategorizationCommand(GeneratingCommand):
    search_term = Option(require=True)
    hard_refresh = Option(require=False)
    api_key = Option(require=False)
    logger = setup_logging()

    __DOMAIN_NAME_REGEX = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]")

    def generate(self):
        api_config = self._get_application_config("whoisxmlapi_website_categorization.conf", "whoisxmlapi_website_categorization")

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA_whois_xml_website_categorization_api")
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

        _parameters = [WXAWebsiteCategorizationCommand._validate_term(t) for t in _terms]

        _parameters = list(filter(lambda item: item is not None, _parameters))

        _refresh = self.hard_refresh if self.hard_refresh is not None \
            and self.hard_refresh in [0, 1] else 0

        if len(_parameters) <= 0:
            self.logger.error('Given search terms are invalid')
            exit(1)

        for p in _parameters:
            api_response = ''
            try:
                api_response = self._send_api_request(p, _refresh, api_config)
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

            data = WXAWebsiteCategorizationCommand._prepare_response(parsed_response)

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
            "as": response_dict['as'],
            "domain": response_dict['domainName'],
            "categories": response_dict['categories'],
            "createdDate": response_dict['createdDate'],
            "responded": 'yes' if response_dict['websiteResponded'] else 'no'
        }

        return result

    @staticmethod
    def _send_api_request(_search_term, _refresh, _api_config):
        payload = {
            'apiKey': _api_config['api_key'],
            'domainName': _search_term,
            'hardRefresh': _refresh
        }

        response = requests.get(
            _api_config['api_url'],
            params=payload
        )

        return response.content

    @staticmethod
    def _validate_term(term):
        if WXAWebsiteCategorizationCommand.__DOMAIN_NAME_REGEX.search(term):
            return term
        return None


dispatch(WXAWebsiteCategorizationCommand, sys.argv, sys.stdin, sys.stdout, None)
