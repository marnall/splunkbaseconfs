import os
import sys
import time
import datetime
import json
import splunk.appserver.mrsparkle.lib.util as util

OS = {
    0 : 'Unknown',
    1 : 'Linux:3.x',
    2 : 'Linux:2.6.x',
    3 : 'Linux:2.4.x',
    4 : 'Linux:2.2.x',
    5 : 'Linux:2.0',
    6 : 'Linux:3.x (loopback)',
    7 : 'Linux:2.6.x (loopback)',
    8 : 'Linux:2.4.x (loopback)',
    9 : 'Linux:2.2.x (loopback)',
    10 : 'Linux:2.6.x (google crawler)',
    11 : 'Linux:Android',
    12 : 'Linux:3.x (generic)',
    13 : 'Linux:2.4.x-2.6.x (generic)',
    14 : 'Linux:2.2.x-3.x (generic)',
    15 : 'Linux:2.2.x-3.x (generic, no ts)',
    16 : 'Linux:2.2.x-3.x (generic, barebone)',
    17 : 'Windows:XP',
    18 : 'Windows:7 or 8',
    19 : 'Windows:7 (Websense crawler)',
    20 : 'Windows:NT kernel 5.x (generic)',
    21 : 'Windows:NT kernel 6.x (generic)',
    22 : 'Windows:NT kernel (generic)',
    23 : 'Mac OS X:10.x',
    24 : 'iOS:iPhone or iPad',
    25 : 'Mac OS X (generic)',
    26 : 'FreeBSD:9.x',
    27 : 'FreeBSD:8.x',
    28 : 'FreeBSD (generic)',
    29 : 'OpenBSD:3.x',
    30 : 'OpenBSD:4.x-5.x',
    31 : 'Solaris:8',
    32 : 'Solaris:10',
    33 : 'OpenVMS:8.x',
    34 : 'OpenVMS:7.x',
    35 : 'NeXTSTEP',
    36 : 'Tru64:4.x',
    37 : 'NMap:SYN scan',
    38 : 'NMap:OS detection',
    39 : 'p0f:sendsyn utility',
    40 : 'Blackberry',
    41 : 'Nintendo:3DS',
    42 : 'Nintendo:Wii',
    43 : 'BaiduSpider',
    44 : 'Linux:3.x (syn+ack)',
    45 : 'Linux:2.4-2.6 (syn+ack)',
    46 : 'Linux:2.4.x (syn+ack)',
    47 : 'Linux:2.6.x (syn+ack)',
    48 : 'Windows:XP (syn+ack)',
    49 : 'Windows:7 or 8 (syn+ack)',
    50 : 'FreeBSD:9.x (syn+ack)',
    51 : 'FreeBSD:8.x (syn+ack)',
    52 : 'FreeBSD:8.x-9.x (syn+ack)',
    53 : 'OpenBSD:5.x (syn+ack)',
    54 : 'Mac OS X:10.x (syn+ack)',
    55 : 'Solaris:6 (syn+ack)',
    56 : 'Solaris:8 (syn+ack)',
    57 : 'Solaris:10 (syn+ack)',
    58 : 'HP-UX:11.x (syn+ack)',
    59 : 'OpenVMS:7.x (syn+ack)',
    60 : 'Tru64:4.x (syn+ack)'
    }

input_name = "tcp"
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

    pvx_ip_address = helper.get_global_setting("ip_address")
    verify = helper.get_arg('verify')
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)
    
    if pvx_ip_address == "none":
        return None

    pvx_api_key = ""
    try:
        cwd = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','pvx_api_key.txt')
        with open(cwd, 'r') as file:
            pvx_api_key = file.read().splitlines()[0]
    except:
        return None

    if verify == "false":
        verify = False
    elif verify == "true":
        verify = True
    
    lambda_function = lambda x: x[0] if len(x)>0 else None

    api_version = get_api_version(pvx_ip_address, pvx_api_key)

    if api_version == 0.7:
        url = 'https://{}/api/query?expr=client.traffic, server.traffic, traffic, server.os, client.os, server.mac, client.mac, client.vlan, server.vlan, syns, begin, end FROM tcp BY time(), server.ip, client.ip, server.port, client.port, application.name, layer, ip.family, capture.id, capture.hostname, uuid, dcerpc SINCE @now-{} UNTIL @now-{}'.format(pvx_ip_address, 420, 360)
    elif api_version >= 0.5:
        url = 'https://{}/api/query?expr=client.traffic, server.traffic, traffic, server.os, client.os, server.mac, client.mac, client.vlan, server.vlan, syns FROM tcp BY time(), server.ip, client.ip, server.port, client.port, application.name, layer, ip.family, capture.id, capture.hostname, uuid, dcerpc, begin, end SINCE @now-{} UNTIL @now-{}'.format(pvx_ip_address, 420, 360)
    else:
        url = 'https://{}/api/query?expr=client.traffic, server.traffic, traffic, server.os, client.os, server.mac, client.mac, client.vlan, server.vlan, syns FROM tcp BY time(), server.ip, client.ip, server.port, client.port, application, layer, ip.family, capture.id, capture.hostname, uuid, dcerpc, begin, end SINCE @now-{} UNTIL @now-{}'.format(pvx_ip_address, 420, 360)

    headers = {'PVX-Authorization': pvx_api_key}
    method = 'GET'
    timeout = 45.0
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
            app = res['key'][5].get('value', -1)
            layer = res['key'][6].get('value')
            ip_protocol = res['key'][7].get('value')
            capture = res['key'][8].get('value')
            capture_hostname = res['key'][9].get('value')
            uuid = res['key'][10].get('value')
            dcerpc = res['key'][11].get('value')

            bytes_out = res['values'][0].get('value')
            bytes_in = res['values'][1].get('value')
            bytes_all = res['values'][2].get('value')
            server_os = OS.get(res['values'][3].get('value')[0])
            client_os = OS.get(res['values'][4].get('value')[0])
            server_mac = res['values'][5].get('value')[0]
            client_mac = res['values'][6].get('value')[0]
            client_vlan = lambda_function(res['values'][7].get('value'))
            server_vlan = lambda_function(res['values'][8].get('value'))
            syns = res['values'][9].get('value')
            
            data = {
                    'action': 'allowed',
                    'time': timestamp,
                    'bytes_in' : bytes_in,
                    'bytes_out' : bytes_out,
                    'bytes': bytes_all,
                    'dest_ip': dest_ip,
                    'src_ip': src_ip,
                    'dest_port': dest_port,
                    'src_port': src_port,
                    'app': app,
                    'layer': layer,
                    'syns': syns,
                    'server_os': server_os,
                    'client_os': client_os,
                    'server_mac': server_mac,
                    'client_mac': client_mac,
                    'client_vlan': client_vlan,
                    'server_vlan': server_vlan,
                    'ip_protocol': ip_protocol,
                    'capture': capture,
                    'uuid' : uuid,
                    'dcerpc' : dcerpc
            }

            if api_version == 0.7:
                data["begin"] = res['values'][10].get('value')
                data["end"] = res['values'][11].get('value')
            else:
                data["begin"] = res['key'][12].get('value')
                data["end"] = res['key'][13].get('value')


            if checkExceptions(capture_hostname, app, dest_port):
                event = helper.new_event(time=timestamp,
                                data=json.dumps(data),
                                index=helper.get_output_index(),
                                source=helper.get_input_type(),
                                sourcetype=helper.get_sourcetype(),
                                done=True,
                                unbroken=True)
                ew.write_event(event)
