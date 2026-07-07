import os
import sys
import time
import datetime
import json

from datetime import datetime, timedelta
def validate_input(helper, definition):
    pass
def collect_events(helper, ew):
    opt_api_key = helper.get_arg('api_key')
    threatfeed_collection_dict = { "0cb06558728b4dc296019c93b78360d1": "SOCRadar-APT-Recommended-Block-Hash","e89ab3b58e174b8c82767088d8e66cae": "SOCRadar-Attackers-Recommended-Block-IP", "03cc11380b5d4a77a0d0cc2a7c568230": "SOCRadar-Recommended-Phishing-Global", "606a83358bbe466d8c3885e37fa595b7": "SOCRadar-Attackers-Recommended-Block-Domain", "8742cab86cc4414092217f87298e94a1": "SOCRadar-Recommended-Block-Hash","4d7a69ce6e7c49ff8c916da5d7343916": "SOCRadar-APT-Recommended-Block-IP", "9079dcc2f96e4835bb807026d4cdcc86": "SOCRadar-APT-Recommended-Block-Domain"}
    
    for threatfeed_uuid, threatfeed_name in threatfeed_collection_dict.items():
        url =f"https://platform.socradar.com/api/threat/intelligence/feed_list/{threatfeed_uuid}.json?key={opt_api_key}&v=2"
        response = helper.send_http_request(url, 'GET', parameters=None, payload=None,headers=None, cookies=None, verify=True, cert=None,timeout=None, use_proxy=True)
       # feedlist=[]
       # for feed in response.json():
        #    f={}
         #   f['feed']=feed['feed']
          #  f['maintainer_name']=threatfeed_name
           # f['latest_seen_date']=feed['latest_seen_date']
            #feedlist.append(f)
       # event = helper.new_event(json.dumps(feedlist), time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
        f=""
        for feed in response.json():
            f=feed['feed'] +","+threatfeed_name+","+feed['latest_seen_date']
            event = helper.new_event(f, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
            ew.write_event(event)
        time.sleep(1)
        #helper.delete_check_point(str(alarm["id"]))    