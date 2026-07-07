import sys
import os
from abc import abstractmethod

app_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
lib_path = os.path.join(app_root, 'lib')
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

import datetime
from dateutil import parser
import logging
import requests

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import splunklib.client as client

logger = logging.getLogger('splunk.VaronisReportApiSearch')
logger.setLevel(logging.DEBUG)

from six.moves import urllib
import getpass
import argparse

try:
    from ntlm3 import HTTPNtlmAuthHandler
except ImportError:
    from bin.ntlm3 import HTTPNtlmAuthHandler



AUTH_TOKEN = None

datetime_format = '%Y-%m-%d %H:%M:%S'
date_format = '%Y-%m-%d'

def validate_date(value):
    for fmt in (date_format, datetime_format):
        try:
            datetime.datetime.strptime(value, fmt)
            return value
        except ValueError:
            pass
    raise ValueError("Invalid date format. Please use 'YYYY-MM-DD' or 'YYYY-MM-DD hh:mm:ss' format.")

class VaronisSearchBase(StreamingCommand):
    def get_settings(self):
        logger.debug('------------------------------get_settings start------------------------------')
        
        if self._metadata:
            app_name = 'varonisreportapisearch_realm'
            service = client.connect(token=self._metadata.searchinfo.session_key, app=self._metadata.searchinfo.app)
            storage_passwords = service.storage_passwords
            for credential in storage_passwords:
                
                if credential.content.get('realm') == app_name and credential.content.get('username') == 'varonis_user':
                    password = credential.content.get('clear_password')

            for conf in service.confs['app'].list():
                if conf.name == 'api':
                    api_url = conf.content['api_url']
                    user = conf.content['varonis_user']
                    break
        else:
            api_url = self.api_url
            user = self.varonis_user
            password = self.password

        domain = user.split('\\')[0]
        username = user.split('\\')[1]
        logger.debug('------------------------------get_settings end------------------------------')

        return {
                'domain': domain,
                'username': username,
                'password': password,
                'api_url': api_url
            }

    def get_auth_token(self):
        logger.debug('------------------------------get_auth_token start------------------------------')

        global AUTH_TOKEN

        self.settings = self.get_settings()
        logger.debug("retrieved settings ")
        logger.debug(self.settings['username'])
        #logger.debug(self.settings['password'])
        logger.debug(self.settings['domain'])
        logger.debug(self.settings['api_url'])

        # Build Auth Request
        headers = {'Content-type': 'application/json'}

        #############################################
        passman = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password(None,  self.settings['api_url'] + 'login', self.settings['domain'] + '\\' + self.settings['username'], self.settings['password'])

        # create the NTLM authentication handler
        auth_NTLM = HTTPNtlmAuthHandler.HTTPNtlmAuthHandler(passman)

        opener = urllib.request.build_opener(auth_NTLM)

        auth_response = opener.open(self.settings['api_url'] + 'login')
        
        #############################################
        #auth_response = requests.get(self.settings['api_url'] + 'login',
        #                             auth=HttpNtlmAuth(self.settings['domain'] + '\\' + self.settings['username'], password=self.settings['password']),
        #                             headers=headers)
        
        logger.debug('------------------------------get_auth_token end------------------------------')

        if auth_response.code == 200:
            content = auth_response.read()
            auth_t = content.decode()
            AUTH_TOKEN = auth_t.strip('\"')
            return True
        else:
            raise Exception('Auth Failed: ' + auth_response.text)

    def execute_search_query(self):

        headers = {'Authorization': 'Bearer ' + AUTH_TOKEN, 'Content-type': 'application/json'}
        search_query_param = self.get_query()
        logger.debug("running search query: " + search_query_param)
        search_query_body = {"Query": search_query_param}

        search_query = requests.post(self.settings['api_url'] + 'search', json=search_query_body, headers=headers)

        if search_query.status_code == 201:
            logger.debug('search query location: ' + search_query.headers['Location'])
            return search_query.headers['Location']
        else:
            raise Exception('Search query failed: ' + search_query.text)

    @abstractmethod
    def get_query(self):
        pass

    def get_search_results(self, location):
        next_page = True
        headers = {'Authorization': 'Bearer ' + AUTH_TOKEN, 'Content-type': 'application/json'}
        columns = []

        while next_page:
            search_query_results = requests.get(location, headers=headers)
            if search_query_results.status_code == 200:
                result = search_query_results.json()
                if result['QuerySearchResult']['ItemCount'] != 0:
                    columns = result['QuerySearchResult']['Columns']
                    for item in result['QuerySearchResult']['Items']:
                        yield {key: value for key, value in zip(columns, item)}
                    if result['NextResultsUrl'] is not None:
                        logger.debug('got into next results url: ' + result['NextResultsUrl'])
                        location = result['NextResultsUrl']
                    else:
                        logger.debug('next page is false')
                        next_page = False
                else:
                    logger.debug('Result size: 0')
                    next_page = False

    def main(self):

        auth_result = self.get_auth_token()
        if auth_result is True:
            results_url = self.execute_search_query()
            results = self.get_search_results(results_url)

            for item in results:
                yield item

    def stream(self, records):
        logger.debug('------------------------------stream start')

        try:
            results = self.main()
            for item in results:
                # Calculate unix_timestamp for the _time field
                date_object = parser.parse(item['Time'])
                unix_timestamp = int(date_object.timestamp())
    
                # Create a summary for the _raw field
                raw_summary = ", ".join([f"{key}: {value}" for key, value in item.items()])
    
                # Include the _time and _raw fields in the output dictionary
                output_item = {'_time': unix_timestamp, '_raw': raw_summary, **item}
    
                yield output_item
                
        except Exception as e: 
            print(e)
            raise
        
        

