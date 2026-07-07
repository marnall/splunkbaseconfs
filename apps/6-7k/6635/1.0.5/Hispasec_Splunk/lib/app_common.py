import base64
import json
import os
import hashlib
import datetime
from configparser import ConfigParser
import requests
import time
from time import sleep

helper = None

def set_helper(hlp):
    global helper
    helper = hlp

def get_version():
    VERSION_DIR = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','Hispasec_Splunk','default','app.conf')
    if not os.path.exists(VERSION_DIR):
        return 0
    app_config = ConfigParser()
    app_config.read(VERSION_DIR, encoding='UTF-8')
    return app_config['launcher']['version']

def set_input_setting(section, key, value):
    local_path = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','Hispasec_Splunk','local')
    if not os.path.exists(local_path):
        os.makedirs(local_path,0o755)

    setting_path = os.path.join(local_path,'inputs.conf')
    input_config = ConfigParser()
    input_config.read(setting_path, encoding='UTF-8')
    if not input_config.has_section(section):
        input_config.add_section(section)
    input_config.set(section, key, value)
    with open(setting_path, 'w') as file:
        input_config.write(file)

def gen_context_path(input_name):
    encode_str = base64.b64encode(bytes(input_name,'utf-8'))
    suffix = hashlib.sha1(encode_str).hexdigest()
    return(os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'Hispasec_Splunk', 'data'), 'status-{}.json'.format(suffix))

def fetch_context(input_name, init_val={}):
    ck_path, file_name = gen_context_path(input_name)
    status_file = os.path.join(ck_path, file_name)
    if not os.path.exists(ck_path):
        os.makedirs(ck_path, 0o755)
    if not os.path.exists(status_file):
        with open(status_file,'w') as json_file:
            json.dump(init_val, json_file)
    else:
        try:
            with open(status_file) as json_file:
                status = json.load(json_file)
        except json.decoder.JSONDecodeError:
            helper.log_error(f'JSONDecodeError@{status_file} when fetch_context, INPUT: {input_name}')
            status = {}
        return status
    return init_val

def update_context(input_name, key, value):
    ck_path, file_name = gen_context_path(input_name)
    status_file = os.path.join(ck_path, file_name)
    if not os.path.exists(ck_path):
        os.makedirs(ck_path,0o755)
    if not os.path.exists(status_file):
        with open(status_file,'w') as json_file:
            status = {key:value}
            json.dump(status, json_file)
    else:
        try:
            with open(status_file) as json_file:
                status = json.load(json_file)
        except json.decoder.JSONDecodeError:
            helper.log_error(f'JSONDecodeError@{status_file} when update_context, INPUT: {input_name}')
            status = {}
        status[key] = value
        with open(status_file, 'w') as json_file:
            json.dump(status, json_file)
    return True

class RetryException(Exception):
    pass

class UnRetryException(Exception):
    pass

def raise_for_status(response):
    if isinstance(response.reason, bytes):
        try:
            reason = response.reason.decode('utf-8')
        except UnicodeDecodeError:
            reason = response.reason.decode('iso-8859-1')
    else:
        reason = response.reason

        if 400 <= response.status_code < 500:
            http_error_msg = u'%s Client Error: %s for url: %s'%(response.status_code, reason, response.url)
            raise UnRetryException(http_error_msg)
        elif 500 <= response.status_code < 600:
            http_error_msg = u'%s Server Error: %s for url: %s'%(response.status_code, reason, response.url)
            raise RetryException(http_error_msg)

def request_help(max_retries, backoff_sec):
    def send_request(url, method, parameters=None, payload=None,headers=None, timeout=55, proxies=None):
        attempt_times, attempt_delay = max_retries, backoff_sec
        response = None
        while attempt_times >= 0:
            try:
                response = requests.request(method, url, params=parameters, headers=headers, json=payload, timeout=timeout, proxies=proxies)
                raise_for_status(response)
                return response
            except RetryException as e:
                pass
            except UnRetryException as e:
                break
            attempt_times -= 1
            if attempt_times != 0:
                sleep(attempt_delay)
        return response
    return send_request