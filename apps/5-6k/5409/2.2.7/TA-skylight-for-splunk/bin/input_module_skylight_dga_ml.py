# encoding = utf-8
import os, sys
import splunk.appserver.mrsparkle.lib.util as util
import json
import re
import time
import subprocess

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    pvx_address = helper.get_global_setting('ip_address')
    pvx_api_key = ""
    try:
        cwd = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','pvx_api_key.txt')
        with open(cwd, 'r') as file:
            pvx_api_key = file.read().splitlines()[0]
    except:
        return None

    url = 'https://{}/api/query?expr=client.traffic, server.traffic FROM dns BY time(), client.ip, query.name, capture.hostname, capture.id SINCE @now-420 UNTIL @now-360'.format(pvx_address)
    headers = {'PVX-Authorization': pvx_api_key}
    response = helper.send_http_request(url, "GET", headers=headers, verify=False, timeout=50, use_proxy=True)
    r_json = response.json()
    safe_status = True
    if 'data' in r_json['result']:
        for res in r_json['result']['data']:
            timestamp = int(float(res['key'][0]['value']))
            query = res[
                'key'][2].get('value')

            os.environ['PYTHONPATH'] = os.path.join(util.get_apps_dir(), 'Splunk_SA_Scientific_Python_linux_x86_64','bin','linux_x86_64', 'bin', 'python3')

            my_process = os.path.join(os.getcwd(), os.path.dirname(os.path.abspath(__file__))+'/dga_ml_predict.py')

            p = subprocess.Popen([
                os.environ['PYTHONPATH'],
                '-W', 'ignore',
                my_process, 
                query
            ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            output = p.communicate()[0]

            if "dga" in str(output) and len(query)>6:
                safe_status = False
                data = {
                    'time': timestamp,
                    'status': 'warning',
                    'src_ip': res['key'][1].get('value'),
                    'query': query,
                    'bytes_out': res['values'][0].get('value'),
                    'bytes_in': res['values'][1].get('value'),
                    'capture_hostname': res['key'][3].get('value'),
                    'capture_id': res['key'][4].get('value')
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
    if safe_status:
        timestamp = round(time.time())
        data = {
            'time': timestamp,
            'status': 'safe'
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
