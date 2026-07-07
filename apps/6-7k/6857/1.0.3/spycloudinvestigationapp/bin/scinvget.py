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

import os, sys
import time
import logging, logging.handlers
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import requests as requests
import re
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import splunklib.client as client
import hashlib
from datetime import datetime
import math
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

app = "spycloudinvestigationapp"
owner = "nobody"

## endpoint dictionary - keys must match the 'endpoint' dropdown values in dashboard
endpoints = {
    'email': 'https://api.spycloud.io/investigations-v2/breach/data/emails/' , 
    'username' : 'https://api.spycloud.io/investigations-v2/breach/data/usernames/',
    'domain' : 'https://api.spycloud.io/investigations-v2/breach/data/domains/',
    'breach' : 'https://api.spycloud.io/investigations-v2/breach/catalog/',
    'ip' : 'https://api.spycloud.io/investigations-v2/breach/data/ips/',
    'password' : 'https://api.spycloud.io/investigations-v2/breach/data/passwords/',
    'machine_id' : 'https://api.spycloud.io/investigations-v2/breach/data/infected-machine-ids/',
    'phone_number' : 'https://api.spycloud.io/investigations-v2/breach/data/phone-numbers/',
    'email_username' : 'https://api.spycloud.io/investigations-v2/breach/data/email-usernames/',
    'social_handle' : 'https://api.spycloud.io/investigations-v2/breach/data/social-handles/',
    'bank_number' : 'https://api.spycloud.io/investigations-v2/breach/data/bank-numbers/',
    'cc_number' : 'https://api.spycloud.io/investigations-v2/breach/data/cc-numbers/',
    'drivers_license' : 'https://api.spycloud.io/investigations-v2/breach/data/drivers-licenses/',
    'national_id' : 'https://api.spycloud.io/investigations-v2/breach/data/national-ids/',
    'passport' : 'https://api.spycloud.io/investigations-v2/breach/data/passport-numbers/',
    'ssn' : 'https://api.spycloud.io/investigations-v2/breach/data/social-security-numbers/'
    }

email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
domain_regex = r"^(?=.{1,255}$)(?!-)[A-Za-z0-9\-]{1,63}(\.[A-Za-z0-9\-]{1,63})*\.?(?<!-)$"

APIKEY = ''
PROXYPWD = ''
configParser = configparser.RawConfigParser()   
def setup_logging(level):
    
    logger = logging.getLogger('splunk.foo')
    logger.setLevel(level)
    SPLUNK_HOME = os.environ['SPLUNK_HOME'] 
    LOGGING_FILE_NAME = app + ".log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d PID=%(process)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a', maxBytes=10000000,backupCount=5) 
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    return logger




@Configuration()
class scinvget(GeneratingCommand):
    endpoint = Option(require=True)
    field = Option(require=True)
    update = Option(require=False, validate=validators.Boolean(), default=False)
    quota_check = Option(require=False, validate=validators.Boolean(), default=False)
    fuzzy = Option(require=False, validate=validators.Boolean(), default=False)
    source_id = Option(require=False, default=False)
    severity = Option(require=False, default=False)
        
    
    def generate(self):

        #create service instance for python SDK
        service = self.service
        
        log_level = str(service.confs['settings']['logging']['level'])
        logger = setup_logging(log_level)
        
        logger.info('stage="Command start"')
        
        #collect search times
        search_info = self.search_results_info
        
        dateFormat = "%Y-%m-%d"

        #function converting to
        def convertDate() :
            splunk_earliest = ''
            splunk_latest = ''

            try :
                splunk_earliest = search_info.search_et
            except :
                splunk_earliest is None
            
            try :
                splunk_latest = search_info.search_lt
            except :
                splunk_latest is None
            
            global earliest_converted
            global latest_converted
            
            if splunk_earliest :
                
                earliest_converted = time.strftime(dateFormat, time.localtime(splunk_earliest))
            else:
                earliest_converted = ''
            
            if splunk_latest :
                latest_converted = time.strftime(dateFormat, time.localtime(splunk_latest))
            else:
                latest_converted = ''

        # access session to extract hashed API Key
        storage_passwords = service.storage_passwords
        logger.debug('stage="retrieving stored passwords"')
        
        # Store passwords
        for password in storage_passwords:
            if password.name == app +':API_Key:':
                global APIKEY
                APIKEY = password.clear_password
                logger.debug('stage="API_Key retrieved"')
            elif password.name == app +':proxy_pass:':
                global PROXYPWD
                PROXYPWD = password.clear_password
                logger.debug('stage="proxy_pass retrieved"')
            
        
        

        # set vars
        quota_limit = int(service.confs['settings']['quotas']['quota_limit'])
        endpoint = str(self.endpoint)
        source_id = str(self.source_id)
        severity = str(self.severity)
        field = str(self.field)
        quota_check = self.quota_check
        
        SHA1 = r"(?:[a-fA-F\d]{40})"
        SHA1_PATTERN = re.compile("^" + SHA1 + "$")

        # counters
        cursor_iteration = 0
        
        #Collect App details
        app_info = service.apps[app].state
        app_version= app_info.content['version']

        # Collect Splunk Env details
        info = service.info
        splunk_product = info['product_type']
        splunk_version = info['version']

        user_agent = 'Splunk-INV/'+ app_version + ' Splunk-'+ splunk_product + '/' + splunk_version  
        logger.debug('stage="user agent created" user_agent="'+user_agent+'"')
        # Set request headers
        headers = {
            'X-Api-Key': APIKEY,
            'User-Agent': user_agent,
        }
       
        #set proxy information
        proxy = {}
        proxy_url = ''
        proxy_user = ''
        proxy_enabled = ''

        # Gather Proxy details
        try:
            proxy_enabled=str(service.confs['settings']['proxy']['enabled'])
            proxy_url=str(service.confs['settings']['proxy']['proxy_url'])
            if proxy_enabled == '1' and proxy_url is not None :
                logger.debug('stage="Proxy enabled"')
                proxy = {
                    'https': proxy_url,
                }
                logger.debug('stage="created proxy" proxy=' + str(proxy))
                try:
                    proxy_user = str(service.confs['settings']['proxy']['user'])
                except:
                    logger.debug('stage="validating proxy user" state="No proxy user defined"')
                if proxy_user != 'None' :
                    logger.debug('proxy_user='+proxy_user)
                    if PROXYPWD is not None:
                        logger.debug('stage="validating proxy authentication" state="Using authentication for proxy"')
                        o = urlparse(proxy_url)
                        scheme=o.scheme + '://'
                        netloc=o.netloc 
                        auth = proxy_user +':'+ PROXYPWD +'@'
                        pURL = scheme + auth + netloc
                        
                        proxy = {
                        'https': pURL
                        }
                    else:
                        logger.debug('stage="validating proxy authentication" state="missing password for authentication, proceeding without auth"')
                else:
                    logger.debug('stage="validating proxy authentication" state="NOT using authentication for proxy"')
                    proxy_user =''
                    PROXYPWD = ''
            elif (proxy_enabled == '0') :
                proxy = {}
                logger.info('stage="validating proxy status" status="Proxy not enabled"')
        except :
            logger.info('stage="validating proxy status" status="Proxy is not configured"')


        # request timeout (aws LBs timeout @ 30sec)
        TIMEOUT = 25
        logger.debug('request_timeout='+ str(TIMEOUT))

        #function to cleanup strings
        def cleanValue(value, style):
            value = str(value)
            logger.debug('stage="formatting" value="'+value+'"')
            if style == 'alphanumeric':
                stripped_value = re.sub('\W+','', value)
            elif style == 'number':
                stripped_value = re.sub('\D+','', value)
            logger.debug('stage="formatting" formatted_value="'+stripped_value+'"')
            return stripped_value
        
        #function to create the API URL
        def buildURL(query):
            convertDate()
            base_url = endpoints.get(endpoint) + query
            variables = '/?fuzzy=' + str(self.fuzzy) +'&since=' + earliest_converted + '&until=' + latest_converted +'&severity='+ severity + '&source_id='+ source_id + '&salt='
            builtURL = base_url + variables
            logger.debug('stage="Building query URL" url="' + builtURL +'"' )
            return builtURL

        def isSha1(s):
            return SHA1_PATTERN.match(s) is not None


        logger.debug('stage="performing input validations"')
        ## Bank Number
        if endpoint == 'bank_number' :
            field=cleanValue(field,'alphanumeric')
            if field.isalnum() : 
                url = buildURL(field)
            else:
                logger.error('Invalid Bank Number')
                raise ValueError('Invalid Bank Number')         
        ## Natl ID
        elif endpoint == 'national_id' :
            if isSha1(field) is False:
                field=cleanValue(field,'alphanumeric')
                if field.isalnum() : 
                    field = field.upper()
                    field = hashlib.sha1(field.encode('utf-8')).hexdigest()
                    logger.debug('stage="create SHA1 Hash" hash="'+field+'"')
                else:
                    logger.error('Invalid National ID')
                    raise ValueError('Invalid National ID') 
            else:
                logger.debug('Using provided SHA1 hash "'+field+'"')
            url = buildURL(field)
        ## Passport
        elif endpoint == 'passport' :
            if isSha1(field) is False:
                field=cleanValue(field,'alphanumeric')
                if field.isalnum() : 
                    field = field.upper()
                    field = hashlib.sha1(field.encode('utf-8')).hexdigest()
                    logger.debug('stage="create SHA1 Hash" hash="'+field+'"')
                else:
                    logger.error('Invalid Passport Number')
                    raise ValueError('Invalid Passport Number')
            else:
                logger.debug('Using provided SHA1 hash "'+field+'"')
            url = buildURL(field)  
        ## DL
        elif endpoint == 'drivers_license':
            if isSha1(field) is False:
                field = cleanValue(field,'alphanumeric')
                if field.isalnum() :
                    field = field.upper()
                    field = hashlib.sha1(field.encode('utf-8')).hexdigest()
                    logger.debug('stage="create SHA1 Hash" hash="'+field+'"')
                else:
                    logger.error('Invalid Drivers License Number')
                    raise ValueError('Invalid Drivers License Number')
            else:
                logger.debug('Using provided SHA1 hash "'+field+'"')
            url = buildURL(field)
        ## SSN
        elif endpoint == 'ssn':
            if isSha1(field) is False:
                field = cleanValue(field,'number')
                if len(field) == 9 and field.isnumeric() :
                    field = hashlib.sha1(field.encode('utf-8')).hexdigest()
                    logger.debug('stage="create SHA1 Hash" hash="'+field+'"')
                else:
                    logger.error('Invalid SSN')
                    raise ValueError('Invalid SSN ')
            else:
                logger.debug('Using provided SHA1 hash "'+field+'"')
            url = buildURL(field)
        ## CC
        elif endpoint == 'cc_number':
            if isSha1(field) is False:
                field = cleanValue(field,'number')
                if (len(field) >= 12 and len(field) <=19) and field.isnumeric() :
                    field = hashlib.sha1(field.encode('utf-8')).hexdigest()
                    logger.debug('stage="create SHA1 Hash" hash="'+field+'"')
                else:
                    logger.error('Invalid CC Number')
                    raise ValueError('Invalid CC Number')
            else:
                logger.debug('Using provided SHA1 hash "'+field+'"')
            url = buildURL(field)
        ## breach
        elif endpoint == 'breach' :
            url = endpoints.get('breach')
            logger.info('stage="Utilizing breach endpoint" url="' + url +'"')
        ## IP (supports single IPs and CIDR ranges like 103.127.185.0/24)
        elif endpoint == 'ip' :
            field = field.replace('/', '%2F')
            url = buildURL(field)
        ## Other Endpoints
        elif endpoint in endpoints :
            url = buildURL(field)

        logger.debug('stage="finished input validations"')

        #retry counter
        retries = 0
        #first retry wait value
        retry_wait = 3 
        # No. of retries allowed
        RETRY_LIMIT = 2
        # list of status codes that are valid for a retry
        retry_status_codes = [429,500]

        #function performing the GET request to the API 
        def getRequest():
            try:
                logger.info('stage="performing GET request"')
                r = requests.get(url, headers=headers , proxies=proxy ,  timeout=TIMEOUT)
            except requests.exceptions.RequestException as e:
                logger.error(e)
                raise Exception(e)
            return r

        # Gather API results
        if endpoint != "":
            r = getRequest()
            response_status = r.status_code
            logger.info('stage="retrieving GET Request status code" status_code="' + str(response_status)+ '"')

            # Exponential backoff API retry when conditions met
            while (response_status in retry_status_codes) and (retries != RETRY_LIMIT) :
                retries += 1
                logger.warn('status_code="' + str(response_status) + '" status="retrying" retry_attempt="' + str(retries)+'"')
                logger.warn('Waiting for ' + str(retry_wait) + ' seconds...')
                time.sleep(retry_wait)
                retry_wait *= 3
                getRequest()

            
            if r.status_code == 200:
                query_count = 1
                global hits
                hits = str(r.json()['hits'])

                if quota_check is True:
                    logger.info('stage="Performing Quota Check"')
                    nQueries = math.ceil((int(hits) / 1000))
                    qString = 'query' if nQueries == 1 else 'queries'
                    splunk_record = {'_time': time.time(),'result':'The query above will return a total of '+hits+' records. This will require '+str(nQueries)+ ' ' + qString +' to pull down all records.'}
                    yield splunk_record
                
                # check quota limit for all endpoints except for the endpoint
                elif (r.json()['hits'] > quota_limit) and (endpoint!= 'breach'):
                    logger.error('stage="enforcing quota limit"  hits="' + str(r.json()['hits']) + '" quota_limit="' + str(quota_limit) + '"')
                    raise Exception("This query returns \"" + str(r.json()['hits']) + "\" records and the configured quota limit is \"" + str(quota_limit) + "\" records")

                elif r.json()['cursor'] is "" : 
                    logger.info('stage="Retrieving results" hits="'+ hits +'"')
                    logger.debug('stage="Retrieving results" state="No pagination required"')
                    
                    page_records = 0
                    for result in r.json()['results']:
                        splunk_record = {'_time': time.time(),'_raw': result}
                        page_records +=1
                        yield splunk_record
                    logger.debug('stage="Retrieving results"  splunk_results_yielded="' + str(page_records)+'"')

                else:
                    logger.info('stage="Retrieving results" hits="'+ hits +'"')
                    
                    page_records = 0
                    for result in r.json()['results']:
                        splunk_record = {'_time': time.time(),'_raw': result}
                        page_records +=1
                        yield splunk_record
                    logger.debug('stage="Retrieving results"  splunk_results_yielded="' + str(page_records)+'"')
                    
                    cursor = r.json()['cursor']
                    while cursor != "" :
                        try:
                            page_records = 0
                            
                            if endpoint == 'breach':
                                cursorVar = '?cursor='
                            else:
                                cursorVar = '&cursor='
                            cursor_url = url + cursorVar + cursor
                            cursor_iteration += 1
                            logger.debug('stage="Pagination" cursor_iteration="' + str(cursor_iteration) + '" cursor="' + str(cursor) + '" url="' + cursor_url +'"')
                            r = requests.get(cursor_url, headers=headers, proxies=proxy)
                            
                            for result in r.json()['results']:
                                splunk_record = {'_time': time.time(),'_raw': result}
                                page_records +=1
                                yield splunk_record
                            logger.debug('stage="Pagination"  splunk_results_yielded="' + str(page_records)+'"')
                            cursor = r.json()['cursor']
                            
                        except :
                            logger.error('stage="Pagination" status="failed" cursor_iteration="' + str(cursor_iteration) + '" cursor="' + str(cursor) + '" url="' + url+'"')
                            raise Exception('Failed on Pagination, please see internal logs for more details')
                            
                query_count = query_count + cursor_iteration
                logger.info('queries_performed='+str(query_count))
                logger.info('stage="Command Finished"')               
            else:
                
                logger.error('stage="Exiting on non 200 status" status_code="' + str(r.status_code) + '" reason="' + str(r.reason) + '" url="' + str(r.url)+'"')
                try:
                    message = str(r.json()['message'])
                    logger.error('API_Message="' + message +'"')
                except:
                    try: 
                        message = str(r.json()['Message'])
                        logger.error('API_Message="' + message +'"')
                    except:
                        logger.error('API_Message="no message provided by the API"')
                        message="N/A"
                logger.info('stage="Command Finished"')
                raise Exception('API_Message="'+ message + '" status_code="' + str(r.status_code) + '" reason="' + str(r.reason) + '" url="' + str(r.url) + '"')
                
dispatch(scinvget, sys.argv, sys.stdin, sys.stdout, __name__)