#!/usr/bin/python
from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
import json
import requests
import time
import sys


def main():
    #get json ouptut from splunk modular alert - See alert_actions.conf.spec
    payload = json.loads(sys.stdin.read())
    config = payload.get('configuration', dict())
    base_url =  config.get('base_url').rstrip('/')
    splunkServer = payload.get('server_host')
    splunkURI = payload.get('server_uri')
    splunkApp = payload.get('app')
    splunkSearch = payload.get('search_name')
    resultsLink = payload.get('results_link')
    result = payload.get('result', dict())
    details = result.get('_raw')
    details = json.dumps(details)
    message = config.get('message')
    severity = config.get('severity')
    mc_object = config.get('object')
    hostname = config.get('hostname')
    sid = payload.get('sid')
    url = "%s/events-service/api/v1.0/events" % (
      base_url
    )
    loginurl = "%s/ims/api/v1/access_keys/login" % (
      base_url
    )
    loginhdr={"Content-Type": "application/json"}
    #body = json.dumps(dict(
    #    class='EVENT',
    #    _source_hostname=config.get('hostname'),
    #    severity=config.get('severity'),
    #    message=config.get('message'),
    #    object=config.get('object'),
    #    tags=splunkSearch
    #))
    body = '[{ "source_hostname": "'+splunkServer+'","class":"SPLUNK_EV","severity":"'+severity+'","tags":"['+splunkSearch+']","msg": "'+message+'","splunk_results_link":"\''+resultsLink+'\'","splunk_log_detail":'+details+',"source_identifier": "'+sid+'","object":"'+mc_object+'"}]'
    #print(body, file=sys.stderr)
    eventbody = json.loads(body)
    loginbody = json.dumps(dict(
        access_key = config.get('access_key'),
        access_secret_key = config.get('secret_key'),
        tenant_id = config.get('tenant_id')
    ))

    login = requests.post( loginurl, loginbody, headers=loginhdr)
    jwt = json.loads(login.text)['json_web_token']

    print("Login response status: %s reason %s" % (login.status_code,login.reason), file=sys.stderr)
    #print("Login response: %s" % login.text, file=sys.stderr)


    eventheader={"Content-Type": "application/json", "Authorization": "Bearer %s" % (jwt)}
    eventsend = requests.post( url, json=eventbody, headers=eventheader)
    print("Event send status: %s reason %s" % (eventsend.status_code,eventsend.reason), file=sys.stderr)
    print("Event send response: %s" % eventsend.text, file=sys.stderr)

        
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
         print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
         sys.exit(1)
    
    main()