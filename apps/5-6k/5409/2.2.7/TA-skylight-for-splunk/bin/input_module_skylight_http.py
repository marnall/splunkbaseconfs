import sys
import os
import splunk.appserver.mrsparkle.lib.util as util
import json
import time
import datetime
import urllib
import httplib2
from xml.dom import minidom
import splunk.rest as rest
import re

HTTP_METHODS = {
    0: 'GET',
    1: 'HEAD',
    2: 'POST',
    3: 'CONNECT',
    4: 'PUT',
    5: 'OPTIONS',
    6: 'TRACE',
    7: 'DELETE'
}

input_name = "http"
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

    pvx_address = helper.get_global_setting("ip_address")
    verify = helper.get_arg('verify')
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)

    if pvx_address == "none":
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

    api_version = get_api_version(pvx_address, pvx_api_key)
    if api_version == 0.5:
        url = 'https://{}/api/query?expr=traffic, response.traffic, request.traffic, request.payload, response.payload, request.payload.md5, response.payload.md5 FROM http BY time(), server.ip, client.ip, server.port, client.port, host, method, response.category, response.status, software, url, url.path, response.content_type, user_agent, is_ajax, application.name, layer, capture.id, capture.hostname, uuid, domain.primary, begin, end SINCE @now-{} UNTIL @now-{}'.format(pvx_address, 420, 360)
    elif api_version == 0.6:
        url = 'https://{}/api/query?expr=traffic, response.traffic, request.traffic, request.payload, response.payload, request.payload.sha256, response.payload.sha256 FROM http BY time(), server.ip, client.ip, server.port, client.port, host, method, response.category, response.status, software, url, url.path, response.content_type, user_agent, is_ajax, application.name, layer, capture.id, capture.hostname, uuid, domain.primary, begin, end SINCE @now-{} UNTIL @now-{}'.format(pvx_address, 420, 360)
    elif api_version == 0.7:
        url = 'https://{}/api/query?expr=traffic, response.traffic, request.traffic, request.payload, response.payload, request.payload.sha256, response.payload.sha256, begin, end FROM http BY time(), server.ip, client.ip, server.port, client.port, host, method, response.category, response.status, software, url, url.path, response.content_type, user_agent, is_ajax, application.name, layer, capture.id, capture.hostname, uuid, domain.primary SINCE @now-{} UNTIL @now-{}'.format(pvx_address, 420, 360)
    else:
        url = 'https://{}/api/query?expr=traffic, response.traffic, request.traffic, request.payload, response.payload FROM http BY time(), server.ip, client.ip, server.port, client.port, host, method, response.category, response.status, software, url, url.path, response.content_type, user_agent, is_ajax, application, layer, capture.id, capture.hostname, uuid, begin, end SINCE @now-{} UNTIL @now-{}'.format(pvx_address, 420, 360)
    
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
            site = res['key'][5].get('value')
            http_method = HTTP_METHODS.get(int(res['key'][6].get('value', -1)))
            category =res['key'][7].get('value')
            status = res['key'][8].get('value')
            if status:
                status = int(status)
            software =res['key'][9].get('value')
            url = res['key'][10].get('value')
            url_length = len(url) if url else None
            uri_path = res['key'][11].get('value')
            uri_query = url[url.index('?'):] if '?' in url else None
            response_content_type = res['key'][12].get('value')
            user_agent = res['key'][13].get('value')
            http_user_agent_length = len(user_agent) if user_agent else None
            is_ajax = res['key'][14].get('value')
            app = res['key'][15].get('value')
            layer = res['key'][16].get('value')
            capture = res['key'][17].get('value')
            capture_hostname = res['key'][18].get('value')
            uuid = res['key'][19].get('value')

            bytes_total = int(res['values'][0]['value'])
            bytes_in = int(res['values'][1]['value'])
            bytes_out = int(res['values'][2]['value'])
            request_payload = res['values'][3].get('value')
            response_payload = res['values'][4].get('value')

            data = {
                'action': 'allowed',
                'time': timestamp,
                'dest_ip': dest_ip,
                'src_ip': src_ip,
                'dest_port': dest_port,
                'src_port': src_port,
                'site': site,
                'http_method': http_method,
                'category': category,
                'software': software,
                'url': url,
                'url_length': url_length,
                'uri_path': uri_path,
                'uri_query': uri_query,
                'http_content_type': response_content_type,
                'http_user_agent': user_agent,
                'http_user_agent_length': http_user_agent_length,
                'is_ajax': is_ajax,
                'app': app,
                'layer': layer,
                'bytes': bytes_total,
                'bytes_out': bytes_out,
                'bytes_in': bytes_in,
                'capture': capture,
                'request_payload' : request_payload,
                'response_payload' : response_payload,
                'uuid' : uuid
            }
            if api_version == 0.5 or api_version == 0.6:
                request_hash = res['values'][5].get('value')
                response_hash = res['values'][6].get('value')

                data['request_hash'] = str(request_hash[0]) if request_hash else None
                data['response_hash'] = str(response_hash[0]) if response_hash else None
                data['domain_primary'] = res['key'][21].get('value')
                data["begin"] = res['key'][22].get('value')
                data["end"] = res['key'][23].get('value')
            elif api_version == 0.7:
                request_hash = res['values'][5].get('value')
                response_hash = res['values'][6].get('value')
                data['request_hash'] = str(request_hash[0]) if request_hash else None
                data['response_hash'] = str(response_hash[0]) if response_hash else None

                data["begin"] = res['values'][7].get('value')
                data["end"] = res['values'][8].get('value')
            else:
                data["begin"] = res['key'][20].get('value')
                data["end"] = res['key'][21].get('value')

            if status:
                data['status'] = status
            if checkExceptions(capture_hostname, app, dest_port):
                event = helper.new_event(time=timestamp,
                                data=json.dumps(data),
                                index=helper.get_output_index(),
                                source=helper.get_input_type(),
                                sourcetype=helper.get_sourcetype(),
                                done=True,
                                unbroken=True)
                ew.write_event(event)
