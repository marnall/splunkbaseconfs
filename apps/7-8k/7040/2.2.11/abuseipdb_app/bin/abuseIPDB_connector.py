import service_retrieval as service

import sys
import os

# So that we can use our own libs as packaged deps
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

from requests import request, exceptions

#make_request is the general use wrapper function for the API, which will be called by the below functions
def make_request(splunk_service, endpoint, params):
    base_url = "https://api.abuseipdb.com/api/v2/"
    endpoints = {
        'check':'get',
        'reports': 'get',
        'blacklist': 'get',
        'report': 'post',
        'account': 'get',
        'check-block': 'get'
    }

    if endpoint in endpoints:
        request_method = endpoints[endpoint]
    else:
        raise ValueError('Provided endpoint name for request is invalid.')

    hasProxy = service.get_proxy_settings(splunk_service)
    
    headers = {
        'Key': service.get_api_key(splunk_service),
        "Accept": "application/json",
        "User-Agent": "Splunk/2.2.11",
        "X-Request-Source": "Splunk_" + '.'.join(map(str, splunk_service.splunk_version)) + ';Splunk_2.2.11;'
    }

    try:
        response = request(request_method, base_url+endpoint, headers=headers, params=params) if hasProxy is None else request(request_method, base_url+endpoint, headers=headers, params=params, proxies=hasProxy)
        return response
    except exceptions.ConnectionError as e:
        raise Exception('An unexpected error occurred while reaching AbuseIPDB.' + str(e))
    except exceptions.ReadTimeout:
        raise Exception('Request exceeded timeout limit while reaching AbuseIPDB.')
    except exceptions.HTTPError as e:
        raise Exception('Unexpected HTTP error occurred while making request to AbuseIPDB.' + str(e))
    except exceptions.TooManyRedirects:
        raise Exception('Too many redirects occurred while reaching AbuseIPDB.')
    except Exception as e:
        raise Exception('An unexpected error occurred while reaching AbuseIPDB.' + str(e))

#----------------------------------------------------------------------------------------------

#these functions are general use wrapper functions for each endpoint being requested

def make_check_request(splunk_service, params):
    return make_request(splunk_service, 'check', params)

def make_reports_request(splunk_service, params):
    return make_request(splunk_service, 'reports', params)

def make_report_request(splunk_service, params):
    return make_request(splunk_service, 'report', params)

def make_blacklist_request(splunk_service, params):
    return make_request(splunk_service, 'blacklist', params)

def make_account_request(splunk_service, params):
    return make_request(splunk_service, 'account', params)

def make_checkblock_request(splunk_service, params):
    return make_request(splunk_service, 'check-block', params)


#------------------------------------------------------------------------------------------
