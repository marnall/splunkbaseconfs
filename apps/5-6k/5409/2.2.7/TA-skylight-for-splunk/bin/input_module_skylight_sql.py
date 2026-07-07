# encoding = utf-8
import os
import splunk.appserver.mrsparkle.lib.util as util
import os
import sys
import time
import datetime
import json

SQLCOMMAND = {
    256: 'SELECT',
    512: 'INSERT',
    768: 'UPDATE',
    1024: 'DELETE',
    1280: 'CREATE',
    1281: 'CREATE TABLE',
    1282: 'CREATE INDEX',
    1283: 'CREATE VIEW',
    1536: 'DROP',
    1537: 'DROP TABLE',
    1538: 'DROP INDEX',
    1539: 'DROP VIEW',
    1792: 'ALTER',
    1793: 'ALTER TABLE',
    2048: 'PREPARE',
    2304: 'EXECUTE',
    61440: 'BEGIN',
    61696: 'COMMIT',
    61952: 'ROLLBACK'
}

SQLSYSTEM = {
    'DRDA': 'DB2 (DRDA)',
    'MySQL': 'MySQL / MariaDB',
    'PostgreSQL': 'PostgreSQL',
    'TDS(msg)': 'Microsoft SQL Server / Sybase',
    'TNS': 'Oracle'
}

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
    pvx_address = helper.get_global_setting("ip_address")
    verify = helper.get_arg('verify')

    if pvx_address == "none":
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

    api_version = get_api_version(pvx_address, pvx_api_key)
    if api_version >= 0.5:
        url = 'https://{}/api/query?expr=query.payload%2C%20response.payload%2C%20server.rt%20FROM%20databases%20BY%20time%28%29%2C%20server.ip%2C%20client.ip%2C%20server.port%2C%20client.port%2C%20user%2C%20system%2C%20query%2C%20database%2C%20command%2C%20application.name%2C%20layer%2C%20capture.id%20SINCE @now-{} UNTIL @now-{}'.format(pvx_address, 420, 360)
    else:
        url = 'https://{}/api/query?expr=query.payload%2C%20response.payload%2C%20server.rt%20FROM%20databases%20BY%20time%28%29%2C%20server.ip%2C%20client.ip%2C%20server.port%2C%20client.port%2C%20user%2C%20system%2C%20query%2C%20database%2C%20command%2C%20application%2C%20layer%2C%20capture.id%20SINCE @now-{} UNTIL @now-{}'.format(pvx_address, 420, 360)
    
    headers = {'PVX-Authorization': pvx_api_key}
    method = 'GET'
    timeout = 45.0
    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=headers, cookies=None, verify=verify,
                                        timeout=timeout, use_proxy=True)
    r_json = response.json()

    if 'data' in r_json['result']:
        for res in r_json['result']['data']:
            timestamp = int(float(res['key'][0]['value']))
            dest_ip = res['key'][1].get('value')
            src_ip = res['key'][2].get('value')
            dest_port = res['key'][3].get('value')
            src_port = res['key'][4].get('value')
            user = res['key'][5].get('value')
            vendor_product = SQLSYSTEM[res['key'][6].get('value')]
            query = res['key'][7].get('value')
            database = res['key'][8].get('value')
            command = SQLCOMMAND.get(int(res['key'][9].get('value', -1)))
            app = res['key'][10].get('value', -1)
            layer = res['key'][11].get('value')
            capture = res['key'][12].get('value')
            bytes_out = int(res['values'][1].get('value'))
            bytes_in = int(res['values'][0].get('value'))
            bytes_total = bytes_out + bytes_in
            server_rt = res['values'][2].get('value')
            if server_rt:
                server_rt = round(server_rt, 3)
            data = {
                'action': 'allowed',
                'time': timestamp,
                'dest_ip': dest_ip,
                'src_ip': src_ip,
                'dest_port': dest_port,
                'src_port': src_port,
                'user': user,
                'vendor_product': vendor_product,
                'query': query,
                'database': database,
                'command': command,
                'app': app,
                'layer': layer,
                'bytes': bytes_total,
                'bytes_out': bytes_out,
                'bytes_in': bytes_in,
                'server_rt': server_rt,
                'capture': capture
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
