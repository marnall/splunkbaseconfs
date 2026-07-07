import os
import sys
import time
import datetime
import json
import splunk.appserver.mrsparkle.lib.util as util

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    def get_api_version(ip, api_key):
        import re

        headers = {'PVX-Authorization': api_key}
        response = helper.send_http_request('https://{}/api/get-api-version'.format(ip), 'GET', headers=headers, verify=False, timeout=60, use_proxy=True)
        version = response.json()["result"]["version"]

        return float(re.match("...", version).group(0))

    pvx_ip_address = helper.get_global_setting('ip_address')
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

    if verify == 'false':
        verify = False
    else:
        verify = True
    
    api_version = get_api_version(pvx_ip_address, pvx_api_key)
    if api_version >= 0.5:
        url = 'https://{}/api/query?expr=server.zone.name, client.zone.name, server.rt, server.dtt, client.dtt, server.dtt.count, server.rt.count, client.dtt.count FROM citrix BY time(), server.ip, client.ip, server.port, client.port, domain, citrix.application, layer, uuid, application.name, capture.id SINCE @now-{} UNTIL @now-{}'.format(pvx_ip_address,420,360)
    else:
        url = 'https://{}/api/query?expr=server.zone, client.zone, server.rt, server.dtt, client.dtt, server.dtt.count, server.rt.count, client.dtt.count FROM citrix BY time(), server.ip, client.ip, server.port, client.port, domain, citrix.application, layer, uuid, application, capture.id SINCE @now-{} UNTIL @now-{}'.format(pvx_ip_address,420,360)

    headers = {'PVX-Authorization': pvx_api_key}
    method = 'GET'
    timeout = 45.0
    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=headers, cookies=None, verify=False,
                                        timeout=timeout, use_proxy=True)
    r_json = response.json()

    if 'data' in r_json['result']:
        for res in r_json['result']['data']:
            timestamp =int(float(res['key'][0]['value']))
            dest_ip = res['key'][1].get('value')
            src_ip = res['key'][2].get('value')
            dest_port = res['key'][3].get('value')
            src_port = res['key'][4].get('value')
            domain = res['key'][5].get('value')
            citrix_application = res['key'][6].get('value')
            layer = res['key'][7].get('value')
            uuid = res['key'][8].get('value')
            app = res['key'][9].get('value')
            capture = res['key'][10].get('value')
            server_zone = res['values'][0]['value'][0]
            client_zone = res['values'][1]['value'][0]
            server_rt = res['values'][2]['value']
            server_dtt = res['values'][3]['value']
            client_dtt = res['values'][4]['value']
            server_dtt_count = res['values'][5]['value']
            server_rt_count = res['values'][6]['value']
            client_dtt_count = res['values'][7]['value']
            
            if server_dtt:
                server_dtt = round(server_dtt, 3)
            if client_dtt:
                client_dtt = round(client_dtt, 3)
            if server_rt:
                server_rt = round(server_rt, 3)
            
            data = {
                    'action': 'allowed',
                    'time': timestamp,
                    'dest_ip': dest_ip,
                    'src_ip': src_ip,
                    'dest_port': dest_port,
                    'src_port': src_port,
                    'layer': layer,
                    'server_zone': server_zone,
                    'client_zone': client_zone,
                    'uuid': uuid,
                    'app': app,
                    'server_dtt': server_dtt,
                    'server_rt': server_rt,
                    'client_dtt': client_dtt,
                    'server_dtt_count': server_dtt_count,
                    'server_rt_count': server_rt_count,
                    'client_dtt_count': client_dtt_count,
                    'capture': capture
                }

            event = helper.new_event(time=timestamp,
                            data=json.dumps(data),
                            index=helper.get_output_index(),
                            source=helper.get_input_type(),
                            sourcetype=helper.get_sourcetype(),
                            done=True,
                            unbroken=True)
            ew.write_event(event)
