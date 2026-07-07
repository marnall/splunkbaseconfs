#!/usr/bin/env python

'''
Splunk APP Lookup Script by AnChain.AI.
'''

__author__ = 'Tianyi Zhang, Wei Quan'
__copyright__ = 'Copyright 2020, AnChain.AI'
__credits__ = ['Tianyi Zhang', 'Wei Quan']

import csv
import json
import sys
import logging
import requests
import itertools
from multiprocessing_wrapper import multiprocessor

class BEI_Query():
    def __init__(self):
        # initialize vars here for external calling
        self.resp = None
        self.category = None
        self.entity_name = None
        self.risk_score = None
        self.risk_level = None
        self.suspicious_activity = None
        self.activeness = None
        self.balance = None
        self.balance_usd = None
        self.first_txn = None
        self.last_txn = None
        self.total_received = None
        self.total_sent = None
        self.url = None
        self.default_api_key = 'e_F38WHb38ABv2yZfPE5lJlesq4ImFuY2hhaW4tc3BsdW5rLWZyZWUi.7Yvuue6EVj7U6vxeb6-4hGhSaSg'

    def safe_requests(self,method,url,payload=None):
        if not url.startswith(('https', 'http')):
            url = url.lstrip(':/')
            url = "https://{}".format(url)
        try:
            user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
            headers = {'User-Agent': user_agent}
            if method == 'POST':
                url = 'https://bei.anchainai.com/api/bulk/address_info_v4'
                self.resp = requests.post(url, headers=headers, json=payload)
            else:
                self.resp = requests.get(url, headers=headers, timeout=30)
            print("request to {} used {} seconds".format(url, self.resp.elapsed.total_seconds()))
        except Exception:
            print("failed to safe_requests on url: {}".format(url))
            self.resp = None
        return self.resp

    def lookup(self,address,api_key,method='GET'):
        self.category = None # clear prev result when calling lookup
        self.entity_name = None
        self.risk_score = None
        self.risk_level = None
        self.suspicious_activity = None
        self.activeness = None
        self.balance = None
        self.balance_usd = None
        self.first_txn = None
        self.last_txn = None
        self.total_received = None
        self.total_sent = None
        # used when method is POST
        payload = {
            "apikey": api_key,
            "proto": "btc",
            "address": [
                address
            ]
        }
        try:
            if address.startswith('0x'): # check eth address
                payload["proto"] = 'eth'
                url = 'https://bei.anchainai.com/api/address_info_v4?proto=eth&address={}&apikey={}'.format(address, api_key)
            else:
                url = 'https://bei.anchainai.com/api/address_info_v4?proto=btc&address={}&apikey={}'.format(address, api_key)
            ret = self.safe_requests(method,url,payload) # get response data
            if ret == None:
                return [itertools.repeat(None, 12)]
            if ret.json()['status'] != 200:
                return [itertools.repeat(None, 12)]
            if 'data' not in ret.json():
                return [itertools.repeat(None, 12)]
            data = ret.json()['data']
            if address not in data:
                return [itertools.repeat(None, 12)]
            if not data[address]['is_address_valid']:
                return [itertools.repeat(None, 12)]
            self.category = ','.join(data[address]['self']['category']) # process response data into categories
            entity_name = ','.join(data[address]['self']['detail'])
            self.entity_name = 'Upgrade to advanced API to see entity' if api_key == self.default_api_key else entity_name
            self.risk_score = data[address]['risk']['score']
            self.risk_level = data[address]['risk']['level']
            self.suspicious_activity = json.dumps({'suspicious_activity': data[address]['activity']['suspicious_activity']})
            self.activeness = data[address]['stats']['activeness']
            self.balance = data[address]['stats']['balance']
            self.balance_usd = data[address]['stats']['balance_usd']
            self.first_txn = data[address]['stats']['first_txn']
            self.last_txn = data[address]['stats']['last_txn']
            self.total_received = data[address]['stats']['total_received']
            self.total_sent = data[address]['stats']['total_sent']
            # return classified data into a list
            return [self.category, self.entity_name, self.risk_score, self.risk_level, self.suspicious_activity, self.activeness, self.balance, self.balance_usd, self.first_txn, self.last_txn, self.total_received, self.total_sent]
        except:
            return [itertools.repeat(None, 12)]

    def lookup_spa(self,address,api_key):
        try:
            proto = 'eth' if address.startswith('0x') else 'btc'
            url = 'https://bei.anchainai.com/api/spa?proto={}&address={}&apikey={}'.format(proto,address,api_key)
            ret = self.safe_requests('GET', url)
            if ret.json()['status'] != 200:
                return None
            if 'data' not in ret.json():
                return None
            data = ret.json()['data']
            if address not in data:
                return None
            if 'spa' not in data[address]:
                return None
            return data[address]['spa']
        except:
            return None

    def lookup_suspicious_activity(self,address,api_key):
        try:
            proto = 'eth' if address.startswith('0x') else 'btc'
            url = 'https://bei.anchainai.com/api/address_suspicious_activity?proto={}&address={}&apikey={}'.format(proto,address,api_key)
            ret = self.safe_requests('GET',url)
            if ret.json()['status'] != 200:
                return None
            if 'data' not in ret.json():
                return None
            data = ret.json()['data']
            if address not in data:
                return None
            if not data[address]['is_address_valid']:
                return None
            suspicious_activity = json.dumps({'suspicious_activity': data[address]['activity']['suspicious_activity']})
            return suspicious_activity
        except:
            return None
    
    def lookup_suspicious_addr(self,start_epoch,end_epoch,api_key,proto):
        try:
            url = 'https://bei.anchainai.com/api/active/suspicious_address?proto={}&from={}&to={}&apikey={}'.format(proto,start_epoch,end_epoch,api_key)
            self.url = url
            ret = self.safe_requests('GET', url)
            if ret.json()['status'] != 200:
                return None
            if 'data' not in ret.json():
                return None
            data = ret.json()['data']
            return data
        except:
            return None
