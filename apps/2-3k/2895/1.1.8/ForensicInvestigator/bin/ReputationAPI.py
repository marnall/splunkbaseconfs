#!/usr/bin/env python

"""ReputationAPI.py:  Collection of classes and methods for interacting with
various online analysis APIs"""

import httplib
import os
import ssl
import hmac
from hashlib import sha256
import json

__author__ = 'Josh Tornetta'
__maintainer__ = 'Josh Tornetta'
__email__ = "tornettaj@gmail.com"
__status__ = "Production"

metascan_url = "metascan-online.com"
metascan_type = {
        "hash": "hashlookup.",
        "ip": "ipscan.",
        "url": "ipscan."
        }
metascan_endpoint = {
        "hash": "/v2/hash/",
        "ip": "/v1/scan/",
        "url": "/v1/scan/"
        }
totalhash_query = {
        "hash": "hash:",
        "ip": "ip:",
        "url": "url:"
        }
totalhash_endpoint = {
        "hash": "/search/",
        "ip": "/search/",
        "url": "/search/",
        "analysis": "/analysis/"
}
totalhash_url = "api.totalhash.com"


class MetascanAPI:

    api_key = ""

    def __init__(self,api_key,scan_type):
        self.api_key = api_key
        self.scan_type = scan_type
        self.url = metascan_type[scan_type] + metascan_url
        self.api_endpoint = metascan_endpoint[scan_type]

    def hashLookup(self,hash):
        r = self.makeRequest(hash)
        return r

    def ipLookup(self,ip):
        r = self.makeRequest(ip)
        return r

    def urlLookup(self,url):
        r = self.makeRequest(url)
        return r

    def makeRequest(self,query):
        headers = { "apikey": self.api_key }

        r = httplib.HTTPSConnection(self.url,443)
        r.request("GET",self.api_endpoint + query,headers=headers)
        res = r.getresponse()

        if not res.status == 200:
            err_resp = {}
            err_resp['Error'] = str(res.reason)
            return json.dumps(err_resp)
        else:
            return res.read()

class TotalHashAPI:
    api_key = ""

    def __init__(self,api_key,userid,scan_type,query):
        self.api_key = api_key
        self.userid = userid
        self.query = query
        self.scan_type = scan_type

    def hashLookup(self,hash):
        query = totalhash_query[self.scan_type] + hash
        r = self.makeRequest(query)
        return r

    def urlLookup(self,url):
        pass

    def useragentLookup(self,useragent):
        pass

    def ipLookup(self,ip):
        pass

    def mutexLookup(self,mutex):
        pass

    def hashAnalysis(self,sha1_hash):
        query = sha1_hash
        r = self.makeRequest(query)
        return r

    def makeRequest(self,query):
        query_string = query + "&id=" + self.userid + "&sign=" + self.get_signature(query)
        r = httplib.HTTPSConnection(totalhash_url,context=ssl.create_default_context())
        r.request("GET",totalhash_endpoint[self.scan_type] + query_string)
        res = r.getresponse()
        return res.read()

    def get_signature(self,query):
        return hmac.new(self.api_key,msg=query,digestmod=sha256).hexdigest()
