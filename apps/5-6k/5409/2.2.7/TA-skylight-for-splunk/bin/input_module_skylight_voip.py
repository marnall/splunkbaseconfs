import os
import sys
import time
import datetime
import json
import splunk.appserver.mrsparkle.lib.util as util

input_name = "voip"
def checkExceptions(host, application, server_port):
    json_path = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','exceptions.json')
    with open(json_path, "r") as f:
        json_data = json.loads(f.read())['filter']

        if len(json_data) > 0:
            for captures in json_data:
                if captures['capture'] == host:
                    for inputs in captures['inputs']:
                        if inputs['name'] == input_name:
                            capture_filter = inputs['exceptions']
                            if len(capture_filter) > 0:
                                for app in capture_filter:
                                    try:
                                        if int(app) == int(server_port):
                                            return False
                                    except:
                                        if str(app) == str(application):
                                            return False
                            else:
                                return True
        else:
            return True
    return True

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    def get_api_version(ip, api_key):
        import re

        headers = {'PVX-Authorization': api_key}
        response = helper.send_http_request('https://{}/api/get-api-version'.format(ip), 'GET', headers=headers, verify=False, timeout=60, use_proxy=True)
        version = response.json()["result"]["version"]

        return float(re.match("...", version).group(0))

    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)
    pvx_ip_address = helper.get_global_setting('ip_address')
    verify = helper.get_arg('verify')

    if pvx_ip_address == "none":
        return None

    pvx_api_key = ""
    try:
        cwd = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','pvx_api_key.txt')
        with open(cwd, 'r') as file:
            pvx_api_key = file.read().splitlines()[0]
    except:
        return None

    if verify == 'false':
        verify = False
    else:
        verify = True


    api_version = get_api_version(pvx_ip_address, pvx_api_key)
    if api_version >= 0.7:
        url = 'https://{}/api/query?expr=traffic, client.traffic, server.traffic, server.zone.name, client.zone.name FROM voip BY time(), server.ip, client.ip, server.port, client.port, call, caller, layer, uuid, capture.id, capture.hostname SINCE @now-{} UNTIL @now-{}'.format(pvx_ip_address, 420, 360)
    elif api_version >= 0.5:
        url = 'https://{}/api/query?expr=traffic, client.traffic, server.traffic, server.zone.name, client.zone.name FROM voip BY time(), server.ip, client.ip, server.port, client.port, call, caller.name, layer, uuid, capture.id, capture.hostname SINCE @now-{} UNTIL @now-{}'.format(pvx_ip_address, 420, 360)
    else:
        url = 'https://{}/api/query?expr=traffic, client.traffic, server.traffic, server.zone, client.zone FROM voip BY time(), server.ip, client.ip, server.port, client.port, call, caller, layer, uuid, capture.id, capture.hostname SINCE @now-{} UNTIL @now-{}'.format(pvx_ip_address, 420, 360)
    
    headers = {'PVX-Authorization': pvx_api_key}
    method = 'GET'
    timeout = 5.0
    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=headers, cookies=None, verify=verify,
                                        timeout=timeout, use_proxy=True)
    r_json = response.json()

    if 'data' in r_json['result']:
        for res in r_json['result']['data']:
            timestamp =int(float(res['key'][0]['value']))
            dest_ip = res['key'][1].get('value')
            src_ip = res['key'][2].get('value')
            dest_port = res['key'][3].get('value')
            src_port = res['key'][4].get('value')
            call = res['key'][5].get('value')
            caller = res['key'][6].get('value', -1)
            layer =res['key'][7].get('value')
            uuid = res['key'][8].get('value')
            capture = res['key'][9].get('value')
            capture_hostname = res['key'][10].get('value')
            bytes_total = int(res['values'][0]['value'])
            bytes_out = int(res['values'][1]['value'])
            bytes_in = int(res['values'][2]['value'])
            server_zone = res['values'][3]['value'][0]
            client_zone = res['values'][4]['value'][0]
            data = {
                    'action': 'allowed',
                    'time': timestamp,
                    'dest_ip': dest_ip,
                    'src_ip': src_ip,
                    'dest_port': dest_port,
                    'src_port': src_port,
                    'layer': layer,
                    'bytes': bytes_total,
                    'bytes_out': bytes_out,
                    'bytes_in': bytes_in,
                    'call': call,
                    'caller': caller,
                    'server_zone': server_zone,
                    'client_zone': client_zone,
                    'uuid': uuid,
                    'capture': capture
                }

            if checkExceptions(capture_hostname, app, dest_port):
                event = helper.new_event(time=timestamp,
                                data=json.dumps(data),
                                index=helper.get_output_index(),
                                source=helper.get_input_type(),
                                sourcetype=helper.get_sourcetype(),
                                done=True,
                                unbroken=True)
                ew.write_event(event)
