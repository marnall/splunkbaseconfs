from future.moves.urllib import parse as urllib_parse
import json
import requests

def access_token(base_url, username, password):
    access_token_url = base_url + '/1/authorization'
    access_token_data = '[{"privilege":"write","resourceType":"stream","resource":"default/proxy_tle/RawLogInput"}]'
    access_token_request = requests.post(access_token_url, auth=(username, password), data=access_token_data)
    access_token_request.raise_for_status()
    access_token_payload = access_token_request.json()
    if isinstance(access_token_payload, list) and len(access_token_payload)>0:
        return access_token_payload[0].get('sws-token')
    return None

def authorization_header(token):
     return 'SWS-Token "sws-token"="%s"' % token

def send_event(base_url, token, data):
    port = urllib_parse.urlparse(base_url).port
    log_event_url = base_url + '/1/workspaces/default/projects/proxy_tle/streams/RawLogInput'
    headers = {'Authorization': authorization_header(token)}
    body = [
        {
            "data":data
        }
    ]
    log_event_request = requests.post(log_event_url, headers=headers, data=json.dumps(body))
    log_event_request.raise_for_status()
    return log_event_request.text

#Example

"""
base_url = 'http://3.122.47.12:9093'
username = 'USER'
password = 'PASSWORD'
event = "123123 Baz"

token = access_token(base_url, username, password)
status = send_event(base_url, token, event)
"""
