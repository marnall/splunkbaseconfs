#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author: info@vuldb.com

import requests
import json
import datetime

def request_error_handler(func):
    def request_handler(self, **kwargs):
        try:
            response = func(self, **kwargs)
    
            if response.status_code in [200, 204]:
                if response.json()['response']['status'] in ['200', '204']:
                    return response
                else:
                    raise APIError(f"API status code: {response.json()['response']['status']}. API error message: {response.json()['response']['error']}")
            elif response.status_code in [401, 403, 405]:
                raise APIError(f'HTTP Response status code: {response.status_code}')
            else:
                raise APIError(f'func: {func.__name__} HTTP status code: {response.status_code} response: {response.content}')
        except Exception as e:
            raise VulDBError(e)

    return request_handler

class VulDBError(Exception):
    def __init__(self, status):
        self.status = status

    def __str__(self):
        return f"VulDB error: {self.status}"

class APIError(VulDBError):
    def __init__(self, status):
        self.status = status

    def __str__(self):
        return f"APIError: {self.status}"
  

class VulDBClient():
    
    def __init__(self, api_key, proxies, vuldb_lang='en', verify=True):
        
        self.verify = verify
        
        if vuldb_lang.lower() in ['de', 'es', 'fr', 'it', 'pt', 'zh', 'ja', 'ko', 'ru', 'ar', 'sv', 'nl', 'da', 'no', 'fi', 'is', 'hr', 'bs', 'sr', 'mk', 'sq', 'sl', 'be', 'tr', 'ro', 'cs', 'uk', 'bg', 'pl', 'hu', 'et', 'lv', 'lt', 'he', 'fa', 'ku', 'ug', 'el', 'ka', 'kk', 'az', 'tg', 'hi', 'ne', 'si', 'ps', 'mn', 'vi', 'th', 'lo', 'km', 'my', 'id', 'ms', 'am', 'sw', 'zu', 'xh', 'ti', 'ig', 'yo', 'so', 'sd', 'uz', 'tl', 'ur', 'bn', 'tk', 'ht', 'ha', 'sn', 'qu', 'gn', 'pa', 'mr', 'ta', 'gu', 'kn', 'te', 'ml', 'ch', 'rm', 'fy', 'lb', 'mt', 'ga', 'cy', 'br', 'gv', 'rw', 'rn', 'ny', 'ff', 'bm', 'wo', 'tn', 'st', 'ay', 'mi', 'sm', 'or', 'ak', 'ln', 'kg', 'ee', 'hy', 'ky', 'ks', 'bo', 'co', 'oc', 'ca', 'gl', 'fj', 'to', 'bi', 'kr', 'ng', 'nd', 'nr', 'dz', 'mh', 'lg', 'nv', 'iu', 'kl', 'eo', 'xk']:
            self.vuldb_lang = vuldb_lang.lower()
            self.url = f'https://vuldb.com/{self.vuldb_lang}/?api'
        else:
            self.vuldb_lang = 'en'
            self.url = 'https://vuldb.com/?api'
        
        self.api_key = api_key
        self.headers = {'X-VulDB-ApiKey' : self.api_key,
                        'User-Agent'     : 'VulDB Splunk App 5.3.1'}
        self.proxies = proxies
        self.timeout = (30, 120)

    @request_error_handler
    def get_cursorinit(self, mode='recent'):
        
        post_data = {'format'  : 'json',
                     'cursorinit' : mode}
        
        return requests.post(self.url, data=post_data, headers=self.headers, proxies=self.proxies, verify=self.verify, timeout=self.timeout)
    
    @request_error_handler
    def get_latest_entries(self, latest=1000, details=0):
        
        post_data = {'format'  : 'json',
                     'recent'  : str(latest),
                     'details' : str(details)}
        
        return requests.post(self.url, data=post_data, headers=self.headers, proxies=self.proxies, verify=self.verify, timeout=self.timeout)

    @request_error_handler
    def get_latest_updates(self, updates=1000, details=0):
        
        post_data = {'format'  : 'json',
                     'updates' : str(updates),
                     'details' : str(details)}
        
        return requests.post(self.url, data=post_data, headers=self.headers, proxies=self.proxies, verify=self.verify, timeout=self.timeout)
    
    @request_error_handler
    def get_entry_by_id(self, ids=None, details=0):
        
        assert not isinstance(ids, str), 'Argument must be a list.'
        idstr = ', '.join(map(str, ids))
        
        post_data = {'format'  : 'json',
                     'id'      : idstr,
                     'details' : str(details)}
        
        return requests.post(self.url, data=post_data, headers=self.headers, proxies=self.proxies, verify=self.verify, timeout=self.timeout)
    
    @request_error_handler
    def get_entries_by_date(self, date=None, adv_date=False, cdate=True, mdate=False, details=0, limit=None):
        
        try:
            date = int(date)
        except ValueError:
            raise ValueError("Incorrect date format, should be a UNIX time stamp")

        if mdate:
            qstr = 'entry_timestamp_change_start'
        elif cdate:
            qstr = 'entry_timestamp_create_start'
        else:
            qstr = 'advisory_date_start'
         
        post_data = {'format'  : 'json',
                     qstr      : date,
                     'limit'   : limit,
                     'details' : str(details)}
        
        return requests.post(self.url, data=post_data, headers=self.headers, proxies=self.proxies, verify=self.verify, timeout=self.timeout)