"""
Written by Raymond McCullagh for Avocado Consulting Pty. Ltd.
Copyright (C) 2022 Avocado Consulting Pty. Ltd.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import os, sys
import requests
import json
import csv
import certifi
from classes.modinput import ModInput

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib import six

class modinput_splunkbase(ModInput):
    def __init__(self, modinput, scheme):
        super().__init__(modinput, scheme)

    def stream_events(self, inputs, ew):
        # Splunk Enterprise calls the modular input, 
        # streams XML describing the inputs to stdin,
        # and waits for data on stdout describing events.
        self.log.debug('Initializing modular input for {}.py...'.format(self.modinput))

        # Iterates through each modinput configured
        for input_name, input_item in six.iteritems(inputs.inputs):
            
            # Locate lookup based on provided Splunk App and lookup.csv name
            csv_file = os.path.join(os.environ["SPLUNK_HOME"],'etc','apps',input_item['lookup_located_app'],'lookups',input_item['apps_lookup'])
            unique_apps = self.get_unique_applist(csv_file)
            ingested_events = 0
            # For each app in unique list of apps, get support details and print
            for app in unique_apps:
                event = self.get_support_details(app)
                if event['event_valid']:
                    print(json.dumps(event['event_content']))
                    self.log.debug('Completed {}\'th result'.format(str(ingested_events)))
                    ingested_events+=1
            self.log.info('Ingesting {} events into Splunk from input: {} completed'.format(str(ingested_events), input_name))

    def get_unique_applist(self, csv_file):
        apps_list = []
        # Reads the content of the csv file using Dict Reader, and ensures the 'app' key exists
        with open(csv_file) as file:
            reader = csv.DictReader(file)
            for row in reader:
                app = row['app']
                if app is not None:
                    apps_list.append(app)
                else:
                    self.log.error('Unable to find suitable app folder name. Check that lookup: {} exists and has a column with header \'app\'!'.format(csv_file))
        file.close()
        # Removes duplicates of apps (as default applist csv may contain dupes for different versions in env)
        dedup_dict = dict.fromkeys(apps_list)
        app_list = list(dedup_dict)

        return app_list

    def get_support_details(self, app):
        url_path = "https://splunkbase.splunk.com/api/v1/app/"
        url_args = {
            'appid': app,   # filters response by app folder-name, e.g. 'TA_admin_ninja'
            'order': 'latest',
            'limit': '1',   # only retrieves 1 event
            'include': 'support,created_by,releases.splunk_compatibility,releases'  # this is mandatory for returning required info from API
        }
        self.log.debug('Preparing to call {} for {}'.format(url_path, app))
        response_dict = requests.get(url=url_path, params=url_args, verify=certifi.where()).json()
        event = {
            'event_valid': True,
            'event_content': None
        }
        if response_dict['total'] >=1 :
            releases_list = response_dict['results'][0]['releases'] # clean response to just release info
            clean_release_list = []
            for release in releases_list:   # includes only select fields from release dict in response
                release_detail = {
                    'version': release['title'], 
                    'splunk_compatability': release['splunk_compatibility'],
                    'platform_support': release['product_compatibility']
                }
                clean_release_list.append(release_detail)

            final_supp_details = {  # build final dict for printing
                'app_id': response_dict['results'][0]['uid'],
                'app': response_dict['results'][0]['appid'],
                'support_type': response_dict['results'][0]['support'],
                'release_detail': clean_release_list
            }
            event['event_content'] = final_supp_details
        else:
            self.log.error('No results found for {}!'.format(app))
            event['event_valid'] = False
        return event

    def validate_input(self, definition):
        """Alternate way, using splunk.rest:
        import splunk.rest as rest
        response = rest.simpleRequest('data/lookup-table-files/{}'.format(provided_csv), sessionKey=sessionkey, getargs={'output_mode': 'json'}).status_code
        raise ValueError(response)
        """
        provided_app = definition.parameters['lookup_located_app']
        provided_csv = definition.parameters['apps_lookup']
        session = definition.metadata['session_key']

        # Validate that there is a Splunk Lookup that exists in the specified location with specified name.
        req_status = self.req.simple_get(endpoint='data/lookup-table-files/{}'.format(provided_csv), app=provided_app, sessionkey=session).status_code
        if req_status is not 200:
            raise ValueError('Unable to find the lookup: \'{}\' within Splunk app: \'{}\''.format(provided_csv, provided_app))

        # Validate that there's a key for 'app' in the provided lookup
        csv_file = os.path.join(os.environ["SPLUNK_HOME"],'etc','apps',provided_app,'lookups',provided_csv)
        try:
            self.get_unique_applist(csv_file)
        except:
            raise ValueError('Unable to find suitable lookup content. Check that lookup: {} exists and has a column with header \'app\'!'.format(csv_file))