######################################
# File: osc_query.py                 #
# Author: OSC                        #
# Version: 1.3                       #
# Date: 29AUG2019                    #
# Purpose: Connect Splunk to OSC API #
######################################

import oscq_b
import requests
import json

class oscq_q:

    def __init__(self):
        pass

class query:

    def __init__(self, obj):
        self.q = obj
        self.api_uri = 'https://api.oscontext.com/api/v1/domainsquery'
        self.headers = { \
                'content-type': "application/x-www-form-urlencoded",\
                'referer': "Splunk SPL"
        }
        self.payload = ''
        self = query.qString(self)

    def qString(self):
        self.querystring = {}
        self.querystring['token'] = self.q.token
        self.querystring['size'] = self.q.args.n
        self.querystring['sort'] = self.q.args.o
        self.querystring['q'] = self.q.q
        if self.q.args.t != 'ANY':
            self.querystring['type'] = self.q.args.t
        return self

class execute:

    def __init__(self, obj):
        self.query = obj
        

    def query(self):
        self.resp = requests.request("GET", self.query.api_uri, data=\
                self.query.payload, params=self.query.querystring)
        jsonResp = json.loads(self.resp.text)
        self.jsonResp = jsonResp["results"]
        return self




