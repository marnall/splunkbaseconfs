import requests
from pprint import pprint
import json
import time
from datetime import datetime
from splunklib.client import Service
current_milli_time = lambda: int(round(time.time() * 1000))
from pytz import timezone


headers={
    'User-Agent': 'iBabyFeedTimer/718 (iPhone; iOS 12.2; Scale/3.00)',
    'Accept': 'application/json',
    'Accept-Language': 'en-GB;q=1'
}

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # login = definition.parameters.get('login', None)
    pass


def collect_events(helper, ew):

    token=helper.context_meta['session_key']

    service = Service(token=token)
    service.namespace['owner'] = 'Nobody'

#    helper.log_warning("KV Store Collections:")
#    for collection in service.kvstore:
#        helper.log_warning("  %s" % collection.name)

    # Let's delete a collection if it already exists, and then create it
    collection_name = "babytimer_state"
    checkpoint_key  = "checkpoint"
    if collection_name not in service.kvstore:
        service.kvstore.create(collection_name)

    collection = service.kvstore[collection_name]
    current_time = time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    current_time = datetime.now(timezone('UTC')).strftime("%Y-%m-%dT%H:%M:%S.000Z")
#    current_time = '2019-04-27T15:00:13.000Z'
    #current_time = '2019-06-08T15:49:43.790Z'
    #try:

    #except:
    #    helper.log_warning("{} didnt exist".format(checkpoint_key))
        
    try:
        checkpoint_info = collection.data.query_by_id(checkpoint_key)
        last_sync = checkpoint_info['value']
        helper.log_info("Checkpoint found - value={}".format(last_sync))
        try:
            collection.data.update(checkpoint_key, json.dumps({"_key": checkpoint_key, "value": current_time}))
        except:
            helper.log_warning("Could not update key with current time... ({})".format(current_time))
        
    except:
        helper.log_info("No checkpoint found - setting to current time")
        last_sync = ""
        collection.data.insert(json.dumps({"_key": checkpoint_key, "value": current_time}))
        #2019-04-26T22:44:28.879Z
        
    helper.log_warning("Should return checkpoint value: %s" % collection.data.query_by_id(checkpoint_key)['value'])
    #proxies = {
    #    'http': 'http://192.168.0.204:8888',
    #    'https': 'http://192.168.0.204:8888',
    #}
    proxies = {}

    response = requests.get(
        'https://syncserver1.fehnerssoftware.com:6000/account',
        params={
            'nocache': current_milli_time(),
            'password': helper.get_arg('password'),
            'username': helper.get_arg('login')
        },
        proxies=proxies,
        verify=False,
        headers=headers
    )
    helper.log_info(response.content)
    login_resp = json.loads(response.content)
    secret = login_resp['secret']
    account_id = login_resp['_id']

    response = requests.get(
        'https://syncserver1.fehnerssoftware.com:6000/sync',
        params={
            'accountID': account_id,
            'secret': secret,
            'nocache': current_milli_time(),
            'lastSync' :last_sync
        },
        headers=headers
    )
    #pprint(response.content)
    helper.log_info(response.content)
    
    events=json.loads(response.content)
    for event in events:
        splunk_event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="babytimer:sync", data=json.dumps(event))
        ew.write_event(splunk_event)
