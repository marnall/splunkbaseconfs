# coding=utf-8
# Skurio.py
# Copyright 2019-22 Skurio Ltd

import sys
import os
import re
import string
import json
from datetime import date, time, datetime, timedelta, timezone
import csv
import requests
from skurioclient import SkurioClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

import splunklib.client as client
from splunklib.modularinput import *

class Skurio(Script):

    BASE_URL = 'https://api.skurio.com/breachalert/v1/'

    def __init__(self):
        self.session_key = ''
        self.checkpoint_dir = ''
        self.folder_regex = None
        self.alert_regex = None
        self.timeframe = None
        self.ew = None
        self.input_name = ''
        self.bac = None

    def get_scheme(self):
        scheme = Scheme('Skurio Threat Intelligence')
        scheme.description = 'Define the results you want to fetch from the Skurio DRP platform'
        scheme.use_external_validation = True

        symbol_argument = Argument('api_key')
        symbol_argument.data_type = Argument.data_type_string
        symbol_argument.description = 'Your X-Auth-Skurio-Key (36 characters, contains hyphens) from support@skurio.com'
        symbol_argument.required_on_create = True
        scheme.add_argument(symbol_argument)

        symbol_argument = Argument('app_key')
        symbol_argument.data_type = Argument.data_type_string
        symbol_argument.description = 'Your app-specific key from api.skurio.com (56 characters, no hyphens)'
        symbol_argument.required_on_create = True
        scheme.add_argument(symbol_argument)

        symbol_argument = Argument('folder_search')
        symbol_argument.data_type = Argument.data_type_string
        symbol_argument.description = 'Regex to match folders. Blank matches all. Example: .*company.*'
        symbol_argument.required_on_create = False
        scheme.add_argument(symbol_argument)

        symbol_argument = Argument('alert_search')
        symbol_argument.data_type = Argument.data_type_string
        symbol_argument.description = 'Regex to match alerts. Blank matches all. Example: .*emails'
        symbol_argument.required_on_create = False
        scheme.add_argument(symbol_argument)

        symbol_argument = Argument('override_range')
        symbol_argument.data_type = Argument.data_type_string
        symbol_argument.description = 'Force timeframe of next fetch. This will revert to blank when complete. Example: 2019-09-01 2019-09-30'
        symbol_argument.required_on_create = False
        scheme.add_argument(symbol_argument)

        return scheme

    def validate_input(self, validation_definition):
        pass

    def stream_events(self, inputs, ew):
        self.session_key = self._input_definition.metadata['session_key']
        self.checkpoint_dir = inputs.metadata.get('checkpoint_dir')
        self.ew = ew

        try:
            for input_name, input_item in inputs.inputs.items():
                self.folder_regex = None
                self.alert_regex = None
                self.timeframe = None
                self.input_name = input_name

                if 'folder_search' in input_item:
                    self.folder_regex = str(input_item['folder_search'])
                    if self.folder_regex == 'None':
                        self.folder_regex = None
                if 'alert_search' in input_item:
                    self.alert_regex = str(input_item['alert_search'])
                    if self.alert_regex == 'None':
                        self.alert_regex = None
                if 'override_range' in input_item:
                    self.timeframe = str(input_item['override_range'])
                    if self.timeframe == 'None':
                        self.timeframe = None

                # If the keys aren't masked, mask them
                if 'api_key' in input_item:
                    if str(input_item['api_key']) != '••••••':
                        self.encrypt_apikey('skurio_apikey_'+self.get_instance_postfix(), str(input_item['api_key']))
                        self.mask_apikey('api_key')
                
                if 'app_key' in input_item:
                    if str(input_item['app_key']) != '••••••':
                        self.encrypt_apikey('skurio_appkey_'+self.get_instance_postfix(), str(input_item['app_key']))
                        self.mask_apikey('app_key')
                
                api_key, app_key = self.get_apikeys()
                
                exit_on_error = True
                if self.timeframe is not None:
                    exit_on_error = False

                self.bac = SkurioClient(api_key=api_key, app_key=app_key, logger_obj=self, exit_on_error=exit_on_error)
                self.get_data()
        except Exception as e:
            ew.log(EventWriter.ERROR, 'stream_events caught exception: %s' % str(e))

    def encrypt_apikey(self, key_name, api_key):
        args = {'token':self.session_key}
        service = client.connect(**args)
        
        try:
            # If the credential already exists, delete it.
            for storage_password in service.storage_passwords:
                if storage_password.username == key_name:
                    service.storage_passwords.delete(username=storage_password.username)

            # Create the credential.
            service.storage_passwords.create(api_key, key_name)

        except Exception as e:
            raise Exception('An error occurred updating credentials. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: %s' % str(e))

    def mask_apikey(self, key_name):
        try:
            args = {'token':self.session_key}
            service = client.connect(**args)
            kind, input_name = self.input_name.split('://')
            item = service.inputs.__getitem__((input_name, kind))
            
            kwargs = {
                key_name: '••••••'
            }
            item.update(**kwargs).refresh()
            
        except Exception as e:
            raise Exception('Error updating inputs.conf: %s' % str(e))

    def get_apikeys(self):
        args = {'token':self.session_key}
        service = client.connect(**args)
        api_key = ''
        app_key = ''

        # Retrieve the password from the storage/passwords endpoint 
        for storage_password in service.storage_passwords:
            if storage_password.username == ('skurio_apikey_'+self.get_instance_postfix()):
                api_key = storage_password.content.clear_password
            if storage_password.username == ('skurio_appkey_'+self.get_instance_postfix()):
                app_key = storage_password.content.clear_password

        if len(api_key) == 0 or len(app_key) == 0:
            # Check previous storage location
            for storage_password in service.storage_passwords:
                if storage_password.username == 'skurio_apikey':
                    api_key = storage_password.content.clear_password
                if storage_password.username == 'skurio_appkey':
                    app_key = storage_password.content.clear_password

        return api_key, app_key

    def create_event_data(self, alert, result, match_type, match):
        ret_data = ''
        if result['created'][-1:] != 'Z':
            createdTime = result['created'] + 'Z'
        else:
            createdTime = result['created']
        created = datetime.strptime(createdTime, '%Y-%m-%d %H:%M:%S%z')

        published = None
        if result['published'] != 'Unknown':
            # Timezones on the API are all UTC
            if result['published'][-1:] != 'Z':
                publishedTime = result['published'] + 'Z'
            else:
                publishedTime = result['published']
            published = datetime.strptime(publishedTime, '%Y-%m-%d %H:%M:%S%z')

        ret_data = ret_data + 'created=' + created.strftime('%Y-%m-%dT%H:%M:%S%z') + ' '

        if published != None:
            ret_data = ret_data + 'published=' + published.strftime('%Y-%m-%dT%H:%M:%S%z') + ' '
        else:
            ret_data = ret_data + 'published=Unknown '

        #result['duplicateCount']
        ret_data = ret_data + 'alertId=' + alert['alertId'] + ' '
        ret_data = ret_data + 'alertName="' + alert['alertName'] + '" '
        if 'folderId' in result and result['folderId'] is not None:
            ret_data = ret_data + 'folderId=' + alert['folderId'] + ' '
        ret_data = ret_data + 'folderName="' + alert['folderName'] + '" '
        ret_data = ret_data + 'alertType=' + alert['alertType'] + ' '
        ret_data = ret_data + 'resultId=' + result['resultId'] + ' '
        ret_data = ret_data + 'appUrl=' + result['appUrl'] + ' '
        ret_data = ret_data + 'author="' + result['author'] + '" '
        #result['content'],
        ret_data = ret_data + 'emailsChecksum=' + result['emailsChecksum'] + ' '

        if result['includesPassword'] != None:
            ret_data = ret_data + 'includesPassword=' + str(result['includesPassword']) + ' '

        ret_data = ret_data + 'messageId=' + result['messageId'] + ' '
        ret_data = ret_data + 'matchCount=' + str(match_type['matchCount']) + ' '

        if result['sensitivityScore'] != None:
            ret_data = ret_data + 'sensitivityScore=' + str(result['sensitivityScore']) + ' '

        ret_data = ret_data + 'siteName="' + result['siteName'] + '" '
        ret_data = ret_data + 'siteDescription="' + result['siteDescription'] + '" '
        # source is a reserved name
        ret_data = ret_data + 'postSource="' + result['source'] + '" '
        ret_data = ret_data + 'postSourceUrl=' + result['sourceUrl'] + ' '

        ret_data = ret_data + 'totalInPost=' + str(match_type['totalInPost']) + ' '
        ret_data = ret_data + 'matchType=' + match_type['matchType'] + ' '

        match_field_dict = {
            "keywords": "keyword",
            "emails" : "email",
            "ips" : "ip",
            "domains": "domain",
            "cards": "card"
        }
        if match_type['matchType'] in match_field_dict:
            match_field = match_field_dict[match_type['matchType']]
            ret_data = ret_data + 'matchedValue="' + match[match_field] + '" '

        if 'redactedPassword' in match:
            ret_data = ret_data + 'redactedPassword=' + match['redactedPassword'] + ' '

        if 'hashedPassword' in match:
            ret_data = ret_data + 'hashedPassword=' + match['hashedPassword'] + ' '

        return ret_data

    def write_event(self, alert, result, match_type, match):
        event = Event()
        event.stanza = self.input_name
        event.data = self.create_event_data(alert, result, match_type, match)
        self.ew.write_event(event)

    def generate_events(self, start_date, end_date):
        alerts = self.bac.get_alerts()
        if alerts is not None:
            #self.ew.log(EventWriter.INFO, 'Got {} alerts. folder_regex:{}, alert_regex:{}'.format(len(alerts), self.folder_regex, self.alert_regex))
            for alert in alerts:
                #EventWriter.log(ew, EventWriter.INFO, 'Checking folder "{}", alert "{}"'.format(alert['folderName'], alert['alertName']))
                if(self.folder_regex is None or len(self.folder_regex) == 0 or re.search(self.folder_regex, alert['folderName']) != None):
                    if(self.alert_regex is None or len(self.alert_regex) == 0 or re.search(self.alert_regex, alert['alertName']) != None):
                        self.ew.log(EventWriter.INFO, 'Fetching results for {}'.format(alert['alertName']))
                        results = self.bac.get_results(alert['alertId'], start_date, end_date)
                        if len(results) != 0:
                            self.ew.log(EventWriter.INFO, 'Got {} results'.format(len(results)))
                            for result in results:
                                self.ew.log(EventWriter.INFO, '{} - {}'.format(alert['alertName'], result['created']))
                                result_details = self.bac.get_result_details(alert['alertName'], alert['alertId'], result['resultId'])
                                if self.bac.check_api_response(result_details):
                                    if 'matches' in result_details['data']['items']:
                                        for match_type in result_details['data']['items']['matches']:
                                            for match in match_type['matchedValues']:
                                                self.write_event(alert, result_details['data']['items'], match_type, match)
                            self.ew.log(EventWriter.INFO, 'generate_events finished writing {} results'.format(len(results)))


    def get_instance_postfix(self):
        kind, input_name = self.input_name.split('://')
        postfix = input_name.lower()
        valid_chars = '-_'+string.ascii_letters+string.digits
        postfix = ''.join([x if x in valid_chars else '_' for x in postfix])
        return postfix

    def get_state_value(self, key):
        val = None
        try:
            if self.checkpoint_dir is not None and len(self.checkpoint_dir) > 0:
                file_name =  self.checkpoint_dir + '/state_' + self.get_instance_postfix()+'.json'
                with open(file_name) as json_file:
                    data = json.load(json_file)
                    if key in data:
                        val = data[key]
        except Exception as e:
            self.ew.log(EventWriter.ERROR, 'get_state_value file error: %s' % str(e))

        return val

    def set_state_value(self, key, val):
        try:
            if self.checkpoint_dir is not None and len(self.checkpoint_dir) > 0:
                file_name =  self.checkpoint_dir + '/state_' + self.get_instance_postfix()+'.json'
                data = {}
                try:
                    with open(file_name, 'r') as json_file:
                        try:
                            data = json.load(json_file)
                        except ValueError:
                            data = {}
                except Exception as e:
                    self.ew.log(EventWriter.ERROR, 'Caught set_state_value read file error: %s' % str(e))

                data[key] = val

                with open(file_name, 'w') as json_file:
                    json.dump(data, json_file)

        except Exception as e:
            self.ew.log(EventWriter.ERROR, 'set_state_value error: %s' % str(e))

    def get_start_and_end_date(self):
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(minutes=5)
        override_timeframe = False

        if self.timeframe is not None and len(self.timeframe) > 0:
            try:
                start_str, end_str = self.timeframe.split(' ')
                self.ew.log(EventWriter.INFO, 'Got start "{}", end "{}"'.format(start_str, end_str))
                start_date = datetime.strptime(start_str+'Z', '%Y-%m-%d%z')
                end_date = datetime.strptime(end_str+'Z', '%Y-%m-%d%z')
                override_timeframe = True
            except Exception as e:
                self.ew.log(EventWriter.ERROR, 'Caught exception parsing timeframe: {} - {}'.format(timeframe, str(e)))

        if override_timeframe == False:
            last_fetch = self.get_state_value('last_fetch')
            if last_fetch is not None:
                start_date = datetime.strptime(last_fetch, '%Y-%m-%dT%H:%M:%S%z')

        return start_date, end_date

    def clear_timeframe(self):
        try:
            args = {'token':self.session_key}
            service = client.connect(**args)
            kind, input_name = self.input_name.split('://')
            item = service.inputs.__getitem__((input_name, kind))
            
            kwargs = {
                'override_range': ''
            }
            item.update(**kwargs).refresh()
        
        except Exception as e:
            raise Exception('clear_timeframe: error updating inputs.conf: %s' % str(e))

    def get_data(self):
        try:
            checkpoint_date = datetime.now(timezone.utc)
            start_date,end_date = self.get_start_and_end_date()

            self.ew.log(EventWriter.INFO, '{} : start_date {} - end_date {}'.format(
                self.input_name, 
                datetime.strftime(start_date, '%Y-%m-%dT%H:%M:%S'), 
                datetime.strftime(end_date, '%Y-%m-%dT%H:%M:%S')
                ))
             
            self.generate_events(start_date, end_date)

            #Save last fetch (note this is 'now' not the end date of the fetch)
            self.ew.log(EventWriter.INFO, 'get_data Finished generate_events, saving state value last_fetch')
            self.set_state_value('last_fetch', datetime.strftime(checkpoint_date, '%Y-%m-%dT%H:%M:%S%z'))

            #Set timeframe override back to nothing - this will cause a new fetch
            if self.timeframe is not None and len(self.timeframe) > 0:
                self.clear_timeframe()

        except Exception as e:
            self.ew.log(EventWriter.ERROR, '{} : get_data uncaught exception: {}'.format(self.input_name, str(e)))
            raise e

    # Required if using 'self' as the logger_obj for SkurioClient
    def write_ba_log(self, level, str):
        ew_log_level = EventWriter.INFO
        if level == SkurioClient.ERROR:
            ew_log_level = EventWriter.ERROR
        elif level == SkurioClient.WARNING:
            ew_log_level = EventWriter.WARNING
        self.ew.log(ew_log_level, str)

if __name__ == '__main__':
    sys.exit(Skurio().run(sys.argv))