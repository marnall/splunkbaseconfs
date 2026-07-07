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

# from __future__ import absolute_import, division, print_function, unicode_literals
# import app
import os, sys
import time
import json

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from splunklib.six.moves import range
import splunklib.client as client
from splunk import rest

from domaintools import API
from domaintools import __version__ as dt_api_version
from Utils.app_env import AppEnv


@Configuration(type='events', retainsevents=True, streaming=False)
class ImportPhisheyeResultsCommand(GeneratingCommand):

    def splunk_service(self, token):
        return client.connect(
            host="localhost",
            port="8089",
            verify=False,
            owner="nobody",
            app="TA-domaintools",
            token=token
        )

    def domaintools_api(self, token):
        headers, response = rest.simpleRequest(
            '/services/domaintools_credentials',
            method='POST',
            sessionKey=token,
            postargs={}
        )

        credentials = json.loads(response)

        app_env = AppEnv()
        return API(
            credentials['username'],
            credentials['password'],
            app_partner='splunk',
            app_name=app_env.package_id,
            app_version=app_env.integration_version,
            api_version=dt_api_version
        )

    def generate(self):
        self.logger.debug("ImportPhishEyeCommand: Starting import_phisheye_results.py")
        token = self.metadata.searchinfo.session_key
        service = self.splunk_service(token)
        api = self.domaintools_api(token)

        self.logger.debug("ImportPhishEyeCommand: Connecting to phisheye_monitors kvstore API")
        phisheye_monitors = service.kvstore['phisheye_monitors']
        self.logger.debug("ImportPhishEyeCommand: Querying enabled PhishEye monitors")
        enabled_monitors = phisheye_monitors.data.query(query=json.dumps({"enabled": 1}))

        self.logger.debug("ImportPhishEyeCommand: Querying phisheye results")
        for monitor in enabled_monitors:
            try:
                self.logger.debug("ImportPhishEyeCommand: Querying phisheye results for term {0}"
                                  .format(monitor['term']))
                api_results = api.phisheye(monitor['term'])
            except Exception, e:
                self.logger.warning("ImportPhishEyeCommand: Error requesting PhishEye results: {0}"
                                    .format(e.reason['error']['message']))
                continue

            for result in api_results:
                yield {'imported': int(time.time()),
                   'domain': result['domain'],
                   'monitor': monitor['term'],
                   'risk_score': result["risk_score"] if "risk_score" in result else "",
                   '_key': result['domain'],
                   '_raw': json.dumps(result)
                   }

dispatch(ImportPhisheyeResultsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
