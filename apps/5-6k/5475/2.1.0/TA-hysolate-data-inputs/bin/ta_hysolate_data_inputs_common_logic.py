import base64
import json
import sys

HMC_DOMAIN = 'hysolate.com'

PY3 = sys.version_info[0] >= 3

def base64ify(bytes_or_str):
    if PY3 and isinstance(bytes_or_str, str):
        input_bytes = bytes_or_str.encode('utf8')
    else:
        input_bytes = bytes_or_str

    output_bytes = base64.b64encode(input_bytes)
    if PY3:
        return output_bytes.decode('ascii')
    return output_bytes

def get_access_token(helper):
    account = helper.get_arg('service_account')
    client_id = account['username']
    client_secret = account['password']
    url = 'https://auth.%s/oauth2/token' % (HMC_DOMAIN,)
    auth_value = ('Basic ' +
        base64ify('%s:%s' % (client_id, client_secret)).strip())
    headers = {
        'Authorization':auth_value,
        'Content-Type':'application/x-www-form-urlencoded',
    }
    response = helper.send_http_request(
        url, 'POST',
        payload='grant_type=client_credentials',
        headers=headers)
    response.raise_for_status()
    return response.json()['access_token']

def hysolate_collect_events(helper, event_writer, api_path):
    headers = dict(Authorization='Bearer ' + get_access_token(helper))
    source = helper.get_input_type()
    index = helper.get_output_index()
    sourcetype = helper.get_sourcetype()
    url = 'https://console.%s/api/%s' % (HMC_DOMAIN, api_path)
    key = '%s-%s-%s' % (helper.get_input_stanza_names(), HMC_DOMAIN, api_path)
    page_token = helper.get_check_point(key)
    while True:
        parameters = None
        if page_token:
            parameters = dict(pageToken=page_token)
        response = helper.send_http_request(
            url, 'GET', parameters=parameters, headers=headers)
        response.raise_for_status()
        body = response.json()
        page_token = body.get('nextPageToken', None)
        helper.save_check_point(key, page_token)
        items = body['items']
        for item in items:
            event = helper.new_event(
                source=source, index=index, sourcetype=sourcetype,
                data=json.dumps(item, separators=[',', ':']))
            event_writer.write_event(event)
        if not items:
            break
