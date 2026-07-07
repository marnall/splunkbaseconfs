
# encoding = utf-8
import json
from time import sleep as sleep
import splunklib.results as results
import splunklib.client as client
import logging
import sys
import requests
import urllib.parse as urllib

def validate_input(helper, definition):
    index = definition.parameters.get('index', None)
    usenonavalonindex=definition.parameters.get('usenonavalonindex', None)
    if not int(usenonavalonindex):
        if  index == 'avalon':
            pass
        else:
            raise ValueError("Index named `avalon` must be created and selected here, or select the checkbox at the end to use a different Index")
            return False

def collect_events(helper, ew):
    avalon_api_key = helper.get_global_setting("avalon_api_key")
    session_key=helper.context_meta['session_key']
    server_uri = helper.context_meta['server_uri']
    
    if avalon_api_key == None:
        raise_web_message(server_uri, session_key, response="api_key")
    
    try:
        http_info = urllib.urlparse(server_uri)
    except Exception:
        raise ValueError(str(server_uri) + " is not in http(s)://hostname:port format")

    if not http_info.scheme or not http_info.hostname or not http_info.port:
        raise ValueError(
            http_url + " is not in http(s)://hostname:port format")
    logging.info("HTTP URL is :"+server_uri)
    service = client.connect(host=http_info.hostname,port=http_info.port,token=session_key, app='Splunk_TA-Avalon', owner='nobody', autologin=True)
    searchquery_normal = '| pullworkspaces | table id Title | rename Title AS title | dedup id title | sort + id | outputlookup workspaces.csv'
    kwargs_normalsearch = {"exec_mode": "normal"}
    job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)

    # A normal search returns the job's SID right away, so we need to poll for completion
    while True:
        while not job.is_ready():
            pass
        stats = {"isDone": job["isDone"],
                 "doneProgress": float(job["doneProgress"])*100,
                  "scanCount": int(job["scanCount"]),
                  "eventCount": int(job["eventCount"]),
                  "resultCount": int(job["resultCount"])}
        
        status = ("\r%(doneProgress)03.1f%%   %(scanCount)d scanned   "
                  "%(eventCount)d matched   %(resultCount)d results") % stats
        if stats["isDone"] == "1":
            break
        sleep(2)
    #outputlookup into workspace will be done as search is compleded. closing job.
    job.cancel()

def raise_web_message(server_uri, session_key, response=None):
    
    if response == "api_key":
        msg = 'Connecting to Avalon API failed. ' \
              'Please configure API key in Configurations Tab --> Add-on setup parameters ' \
              'inside the Avalon Add-on'
    else:
        msg = 'Connecting to Avalon API failed ' \
              'Please check internet connectivity to Avalon API. ' \
              'Other Possible Issues: Wrong API key or Invalid Proxy settings.'
    try:
        uri = server_uri + '/services/messages/new'
        headers = {'Authorization': 'Splunk ' + session_key}
        data = {
            'name': 'Custom message from Avalon Add-on',
            'value': msg,
            'severity': 'warn'
        }
        requests.post(uri, headers=headers, data=data, verify=False)
    except Exception as e:
        logging.info('---error in raise_web_message---')
        logging.info(e)
    sys.exit(msg)

