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
import os, sys
from pupdb.core import PupDB
import requests as requests
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators


splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'searchcommands_app', '../lib'))
db = PupDB("apiquery.db")

@Configuration()
class ApiQuery(StreamingCommand):
    endpoint = Option(require=True)
    update = Option(require=False, validate=validators.Boolean(), default=False)
    def stream(self, records):
        for record in records:
            # First check to see if we want to query the endpoint regardless if the data is already cached
            if self.update:
                try:
                    r = requests.get(record[self.endpoint])
                    db.set(record[self.endpoint], r.json())
                    self.logger.debug("Cache miss for %s" % record[self.endpoint])
                    record['api_data'] = r.json()
                    yield record
                except Exception as e:
                    record['api_data'] = {'error': str(e)}
                    yield record

            # Otherwise, check local cache first
            else:
                if db.get(record[self.endpoint]) is not None:
                    record['api_data'] = db.get(record[self.endpoint])
                    yield record
                else:
                    try:
                        r = requests.get(record[self.endpoint])
                        db.set(record[self.endpoint], r.json())
                        self.logger.debug("Cache miss for %s" % record[self.endpoint])
                        record['api_data'] = r.json()
                        yield record
                    except Exception as e:
                        record['api_data'] = {'error': str(e)}
                        yield record


dispatch(ApiQuery, sys.argv, sys.stdin, sys.stdout, __name__)
