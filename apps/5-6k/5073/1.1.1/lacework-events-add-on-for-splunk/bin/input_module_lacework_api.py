
# encoding = utf-8

import os
import sys
import json
import time
from datetime import datetime, timedelta

TOKEN_URL = "https://{}.lacework.net/api/v1/access/tokens"
EVENTS_URL = 'https://{}.lacework.net/api/v1/external/events/GetEventsForDateRange?START_TIME={}&END_TIME={}'
EVENT_DETAILS_URL = 'https://{}.lacework.net/api/v1/external/events/GetEventDetails?EVENT_ID={}'

# Built in Splunk method to validate user input.
def validate_input(helper, definition):
    try:
        token_expr = int(definition.parameters.get('bearer_token_expiration'))
    except ValueError:
        raise ValueError('Token expiration must be an integer.')
    if token_expr <= 0:
        raise Exception('Token expiration must be greater than 0.')
        
    sub_domain = definition.parameters.get('sub_domain')


# Built-in Splunk method that kicks off collecting Lacework events.
def collect_events(helper, ew):
    sub_domain = helper.get_arg('sub_domain')
    token_expr = int(helper.get_arg('bearer_token_expiration'))
    
    helper.log_info('Collecting events for ' + sub_domain)
    cred = helper.get_user_credential_by_id(sub_domain)
    if cred:
        access_key = cred['username']
        secret = cred['password']
        
        args = (access_key, token_expr, secret, sub_domain)
        response = retrieve_bearer(helper, *args)
        if response.status_code == 201:
            data = json.loads(response.text).get('data')
            if data:
                token = data[0].get('token')
                process_lacework_events(helper, ew, *(token, sub_domain))


# Utilize API to retrieve events that took place over the past day.
def process_lacework_events(helper, ew, *args):
    token = args[0]
    sub_domain = args[1]
    
    today_utc = datetime.utcnow()
    yest_utc = datetime.utcnow() - timedelta(days=1)
        
    url = EVENTS_URL.format(
        sub_domain, 
        dt_format(yest_utc), 
        dt_format(today_utc))
    
    now = time.time()
    headers = {"Authorization": token}
    response = helper.send_http_request(url, 'GET', headers=headers,
                use_proxy=False)
    events = json.loads(response.text).get('data')
    if events:
        unique_ids = set()
        for event in events:
            event_id = event.get('EVENT_ID')
            if event_id not in unique_ids:
                args = (event_id, event, sub_domain, headers)
                get_event_details(helper, *args)
                # Write events
                event = helper.new_event(json.dumps(event))
                ew.write_event(event)
            unique_ids.add(event_id)
            
    helper.log_info('Processed {} events in {} seconds for subdomain {}.'
        .format(len(events), time.time() - now, sub_domain))


# Get supplementaru Lacework event data.
def get_event_details(helper, *args):
    event_id = args[0] 
    event = args[1] 
    sub_domain = args[2]
    headers = args[3]
    
    url = EVENT_DETAILS_URL.format(sub_domain, str(event_id))
    response = helper.send_http_request(url, 'GET', headers=headers,
            use_proxy=False)
    data = json.loads(response.text)['data'][0]['ENTITY_MAP']

    if data.get('CT_User'):
        event['USERNAME'] = data['CT_User'][0]['USERNAME']
        event['ACCOUNT_ID'] = data['CT_User'][0]['ACCOUNT_ID']
    else:
        event['USERNAME'] = ''
        event['ACCOUNT_ID'] = ''

    if data.get('Region'):
        event['REGION'] = data['Region'][0]['REGION']
    else:
        event['REGION'] = ''

    if data.get('NewViolation'):
        event['REASON'] = data['NewViolation'][0]['REASON']
    elif data.get('ViolationReason'):
        event['REASON'] = data['ViolationReason'][0]['REASON']
    else:
        event['REASON'] = ''
                    

# Retrieves Lacework API bearer token
def retrieve_bearer(helper, *args):
    access_key = args[0]
    token_expr = args[1]
    secret = args[2]
    sub_domain = args[3]
    
    post = {"keyId": access_key, "expiry_Time": token_expr}
    headers = {"X-LW-UAKS": secret, "Content-Type": "application/json"}
    response = helper.send_http_request(
        TOKEN_URL.format(sub_domain), 
        'POST', 
        payload=json.dumps(post), 
        headers=headers,
        use_proxy=False)
    return response
    

# Converts a datetime object into string format
def dt_format(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    