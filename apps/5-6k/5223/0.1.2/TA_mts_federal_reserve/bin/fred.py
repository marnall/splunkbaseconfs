#!/usr/bin/env python
# coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals

import os,sys
import time
import json
import requests
import urllib
from re import search

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'TA_mts_federal_reserve', 'bin/ta_mts_federal_reserve/aob_py3'))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


def prep_fred_data(start_date, series_id, result):
    all_records = []
    for rc in result['observations']:
        if rc['date'] > start_date:
            fred_series_data = {
                "Date": rc['date'],
                "SeriesID": series_id,
                "Value": rc['value']
            }
            all_records.append(fred_series_data)

    if all_records:
        return all_records
    else:
        return 0

@Configuration()
class fred(GeneratingCommand):

    series_id = Option(require=True)
    start_date = Option(require=True)
    end_date = Option(require=True)
    
    def generate(self):

        self.logger.debug("Retrieving FRED Events - {}".format(self.series_id))

        storage_passwords=self.service.storage_passwords
        for credential in storage_passwords:
            usercreds = {'password':credential.content.get('clear_password')}
            if search('fred_api_key', usercreds['password']):
                passwd = json.loads(usercreds['password'])
                fred_api_key = passwd['fred_api_key']

        url = "https://api.stlouisfed.org/fred/series/observations?series_id={}&api_key={}&file_type=json&observation_start={}&observation_end={}".format(self.series_id, fred_api_key, self.start_date, self.end_date)
        sourcetype = "economic:fred:command"

        # Request data

        # The following examples send rest requests to some endpoint.
        response = requests.request('GET', url)

        r_json = response.json()
        
        # get response status code
        r_status = response.status_code

        # check the response status, if the status is not sucessful, raise requests.HTTPError
        if r_status > 200:
            evt_data = {'Message':'HTTP Error {}'.format(r_status)}
            evt_json = json.dumps(evt_data)
            event_time = str(round(time.time(), 3))
            yield {'_time': event_time, 'sourcetype': sourcetype, 'Message': evt_data['Message'], '_raw': evt_json}

        else:
            fred_series_data = prep_fred_data(self.start_date,self.series_id,r_json)
            
            if fred_series_data:
                for rc in fred_series_data:
                    event_time = int(time.mktime(time.strptime(str(rc['Date']), "%Y-%m-%d")))
            
                    # To create a splunk event
                    evt_json = json.dumps(rc)                
                    yield {'_time': event_time, 'sourcetype': sourcetype, 'Date': rc['Date'], 'SeriesID': rc['SeriesID'], 'Value': rc['Value'], '_raw': evt_json}

dispatch(fred, sys.argv, sys.stdin, sys.stdout, __name__)
