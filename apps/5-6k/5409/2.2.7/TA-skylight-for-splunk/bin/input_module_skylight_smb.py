# encoding = utf-8
import os
import splunk.appserver.mrsparkle.lib.util as util
import os
import sys
import time
import datetime
import json

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    def get_api_version(ip, api_key):
        import re

        headers = {'PVX-Authorization': api_key}
        response = helper.send_http_request('https://{}/api/get-api-version'.format(ip), 'GET', headers=headers, verify=False, timeout=60, use_proxy=True)
        version = response.json()["result"]["version"]

        return float(re.match("...", version).group(0))

    ip_address = helper.get_global_setting("ip_address")
    verify = helper.get_arg('verify')
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)

    if ip_address == "none":
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
    elif verify == 'true':
        verify = True

    api_version = get_api_version(ip_address, pvx_api_key)
    if api_version >= 0.5:
        url = 'https://{}/api/query?expr=query.payload, response.payload FROM smb by time(), server.ip, client.ip, server.port, client.port, file, file.id, user, domain, tree, tree.id, smb.command, smb.status, smb.version, application.name, layer, capture.id, uuid, file.id SINCE @now-{} UNTIL @now-{}'.format(ip_address, 420, 360)
    else:
        url = 'https://{}/api/query?expr=query.payload, response.payload FROM smb by time(), server.ip, client.ip, server.port, client.port, file, file.id, user, domain, tree, tree.id, smb.command, smb.status, smb.version, application, layer, capture.id, uuid, file.id SINCE @now-{} UNTIL @now-{}'.format(ip_address, 420, 360)

    headers = {'PVX-Authorization': pvx_api_key}
    method = 'GET'
    timeout = 45.0

    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=headers, cookies=None, verify=False,
                                        timeout=timeout, use_proxy=True)
    r_json = response.json()

    if 'result' in r_json and 'data' in r_json['result']:
        for res in r_json['result']['data']:
            timestamp = int(float(res['key'][0]['value']))
            dest_ip = res['key'][1].get('value')
            src_ip = res['key'][2].get('value')
            dest_port = res['key'][3].get('value')
            src_port = res['key'][4].get('value')
            file_name = res['key'][5].get('value')
            file_id = res['key'][6].get('value')
            user = res['key'][7].get('value')
            dest_nt_domain = res['key'][8].get('value')
            tree = res['key'][9].get('value')
            # tree_id = res['key'][10]['value']
            smb_command = ":".join(str(i) for i in res['key'][11].get('value'))
            smb_status = res['key'][12].get('value')
            smb_version = res['key'][13].get('value')
            app = res['key'][14].get('value')
            layer = res['key'][15].get('value')
            capture = res['key'][16].get('value')
            uuid = res['key'][17].get('value')
            bytes_out = int(res['values'][0].get('value'))
            bytes_in = int(res['values'][1].get('value'))
            bytes_total = bytes_out + bytes_in
            data = {
                # action set to allowed, because PVX is a passive network
                # monitoring appliance and all the traffic it received is
                # assumed to be allowed.
                'action': 'allowed',
                'time': timestamp,
                'dest_ip': dest_ip,
                'src_ip': src_ip,
                'dest_port': dest_port,
                'src_port': src_port,
                'file_name': file_name,
                'user': user,
                'dest_nt_domain': dest_nt_domain,
                'tree': tree,
                'smb_command': smb_command,
                'smb_status': smb_status,
                'smb_version': smb_version,
                'layer': layer,
                'app': app,
                'bytes': bytes_total,
                'bytes_out': bytes_out,
                'bytes_in': bytes_in,
                'capture': capture,
                'uuid': uuid,
                'file_id': file_id
            }
            event = helper.new_event(
                time=timestamp,
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=helper.get_sourcetype(),
                data=json.dumps(data),
                done=True,
                unbroken=True)
            ew.write_event(event)
