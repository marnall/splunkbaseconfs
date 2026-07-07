#!/usr/bin/env python

import splunk.rest as rest
import splunk.Intersplunk
import datetime
import requests
import json
import urllib

results,dummy,settings = splunk.Intersplunk.getOrganizedResults()

sessionKey = settings.get("sessionKey")
keywords, argvals = splunk.Intersplunk.getKeywordsAndOptions()

if 'owner' in argvals:
    owner = argvals.get("owner", None)

if 'app' in argvals:
    app = argvals.get("app", None)

if 'name' in argvals:
    name = argvals.get("name", None)
    name = name.replace('#', ' ')

if 'schedule' in argvals:
    schedule = argvals.get('schedule', None)
    schedule = schedule.replace('#', ' ')

try:
    if owner!='none':
        job = {
                '_time': datetime.datetime.utcnow().isoformat()
                }

        serviceaddr = urllib.quote('/servicesNS/'+owner+'/'+app+'/saved/searches/'+name)
        
        server_response, server_content = rest.simpleRequest(serviceaddr, sessionKey=sessionKey, postargs={'cron_schedule':schedule,'is_scheduled':1}, method='POST', raiseAllErrors=True)
        job['status'] = server_response.status
        if server_response.status == 200:
            job['content'] = (server_content)
        else:
            print(server_content)
        splunk.Intersplunk.outputResults([job])
except Exception, e:
        print(e)
