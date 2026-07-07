#!/usr/bin/env python

###########
# Author: Lukas Utz <lutz@splunk.com>
# Date: 10 January 2022
###########

###########
# No guarantee is given for the used endpoint https://ipapi.co
# It does not require an API key or registration and is free but limited to 30k requests per month
# See https://ipapi.co/terms/ for the Terms of Service
###########

import sys
import os
import requests
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import splunklib.results as results

@Configuration()
class IpExtrainfoCommand(StreamingCommand):

    opt_ip = Option(
        doc='''
        **Syntax:** **ip=***<fieldname>*
        **Description:** Fieldname containing IP info."
        **Default:** ip*''',
        name='ip',
        require=False,
        default='ip',
        validate=validators.Fieldname())

    def stream(self, events):

        ## get current i.e. most recent apikey from ipapikey collection
        service = self.service
        kwargs_oneshot = {"output_mode": 'json'}
        searchquery_oneshot = "| inputlookup ipapikey | sort - savetime | head 1 | table apikey"
        oneshotsearch_results = service.jobs.oneshot(searchquery_oneshot, **kwargs_oneshot)
        reader = results.JSONResultsReader(oneshotsearch_results)
        current_apikey = ""
        for item in reader:
             if len(item["apikey"]) > 0:
                current_apikey = "&key="  + item["apikey"]

        base_url_1 = "https://ipapi.co/"
        base_url_2 = "/json/?appid=5064&extapp=splunk" + current_apikey
        for event in events:
            r = requests.get(base_url_1 + event[self.opt_ip] + base_url_2).json()
            for k in r:
                event[k] = r[k]
            yield event

dispatch(IpExtrainfoCommand, sys.argv, sys.stdin, sys.stdout, __name__)
