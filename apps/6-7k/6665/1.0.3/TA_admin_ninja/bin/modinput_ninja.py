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
import re
import logging
import requests
import json
from classes.modinput import ModInput

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib import six
from jsonpath_ng.ext import parse

class modinput_ninja(ModInput):
    def __init__(self, modinput, scheme, script_vars):
        super().__init__(modinput, scheme)
        self.script_vars = script_vars

    def stream_events(self, inputs, ew):
        # Splunk Enterprise calls the modular input, 
        # streams XML describing the inputs to stdin,
        # and waits for XML on stdout describing events.

        self.log.debug('Initializing modular input for {}.py...'.format(self.modinput))
        from requests.packages.urllib3.exceptions import InsecureRequestWarning
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        # Iterates through each modinput configured
        for input_name, input_item in six.iteritems(inputs.inputs):

            # All variables below are being used to construct the API request URL;
            # Example: https://127.0.0.1:8089/servicesNS/-/-/admin/macros?output_mode=json&f=definition&f=disabled&count=0

            url_params = self.script_vars['uri_query']
            url_params.update({'count': input_item['maximum_entries']})
            req_url = 'https://{}:{}{}'.format(self.script_vars['target_host'], str(self.script_vars['target_port']), self.script_vars['uri_path'])
            req_headers = {'Authorization': 'Bearer {}'.format(inputs.metadata['session_key'])}
            response = requests.get(url=req_url, verify=False, headers=req_headers, params=url_params).json()

            self.check_gotevents(response)
            
            ingested_events = 0
            parsed_dict = self.apply_json_paths(response, self.script_vars['path_list'])
            for parsed_json in parsed_dict:
                print(json.dumps(parsed_json))
                ingested_events+=1

            self.log.info('Ingesting {} events into Splunk from input: {} completed'.format(str(ingested_events), input_name))

    def check_gotevents(self, response):
        try:
            if len(response['entry']) == 0:
                self.log.error("No data to retrieve! Likely no config item exists in Splunk for this endpoint type.")
                exit(2)
            else:
                self.log.debug("Number of returned events: {}".format(str(len(response['entry']))))
        except:
            self.log.debug('Entry field not found in response dict')
            self.log.error("No data to retrieve! Likely no config item exists in Splunk for this endpoint type.")
            exit(2)

    def rex_path_key(self, json_path): #returns a subset of the json path query string, for grouping in final results. e.g.: "entry[*].acl.perms" -> "acl.perms"
        key = re.search("([\w]+)$", json_path).group()

        return key

    def parse_json_path(self, json_path, body): #returns a list of successful JSON path matches based on specified json_path
        entry_list = []
        json_key = self.rex_path_key(json_path)
        json_match = parse(json_path)
        for match in json_match.find(body):
            entry_list.append({json_key : match.value})

        return entry_list

    def join_json_fields(self, json_multilist):
        """ At the start of this func, json_multilist looks something like the below. 
        The idea is to smash it all together (JSON keys allowing) into a single dict object, which can then be printed as JSON.
        results = [ 
            [ {"name" : name1}, {"name" : name2} ], 
            [ {"content" : content1}, {"content" : content2} ], 
            [ {"perms" : perms1}, {"perms" : perms2} ] 
            ] 
        """
        joined_json_list = []   # highest level of list

        for json_entry in range(len(json_multilist[0])):    #iterates through entries within first 2nd-dimensional list
            joined_json = {}

            for json_segment in range(len(json_multilist)):     #iterates through selected json key-groups (i.e. results for entry[*].name vs entry[*].acl.perms)
                joined_json.update(json_multilist[json_segment][json_entry])    #Adds as many key-groups to joined_json dict as possible
            
            joined_json_list.append(joined_json)    #appends joined_json dict to joined_json_list

        return joined_json_list

    def apply_json_paths(self, json_dict, json_pathlist): # 'main' func, to call other methods with just json_dict and json_pathlist
        results = []
        for path in json_pathlist:
            parsed_json = self.parse_json_path(path, json_dict)
            results.append(parsed_json)

        applied_json_dict = self.join_json_fields(results)

        return applied_json_dict