
# encoding = utf-8

import os
import json
import logging
import re
import socket
import configparser

from socprime_attack_detective import SOCPrime_AD_api as socprime_ad_api
from splunk_attack_detective import Splunk_AD as splunk_ad
app = __file__.split(os.sep)[-3]

def get_proxy(proxy_dict):
    if proxy_dict.get('proxy_type') == "http":
        proto = ''
    elif proxy_dict.get('proxy_type') == "socks4":
        proto = 'socks4://'
    elif proxy_dict.get('proxy_type') == "socks5":
        proto = 'socks5://'
    else:
        proto = ''

    proxy_user_password = f"{proxy_dict.get('proxy_username')}:{proxy_dict.get('proxy_password')}@" if proxy_dict.get('proxy_username') and proxy_dict.get('proxy_password') else ''
    proxy_result = {
        "http": proto + proxy_user_password + proxy_dict.get('proxy_url') + ":" + proxy_dict.get('proxy_port'),
        "https": proto + proxy_user_password + proxy_dict.get('proxy_url') + ":" + proxy_dict.get('proxy_port')
    }
    return proxy_result

def validate_input(helper, definition):

    def check_array_validation(param_name):
        if param_name in definition.parameters:
            if definition.parameters[param_name] is not None:
                try:
                    ist_obj = json.loads(definition.parameters[param_name])
                    if not isinstance(ist_obj,list):
                        raise ValueError(f'Error during validation process. Error message: Please specify {param_name} in array format.')
                except:
                    raise ValueError(f'Error during validation process. Error message: {param_name} is not in array format.')
    
    def check_for_integer(param_name):
        if param_name in definition.parameters:
            if definition.parameters[param_name] is not None:
                try:
                    int(definition.parameters[param_name])
                except:
                    raise ValueError(f'{param_name} parameter must be an integer.')

    def check_host_port_validation(param_name):
        if definition.parameters[param_name] is not None and definition.parameters[param_name] != '':
                ist_obj = json.loads(definition.parameters[param_name])
                for elem in ist_obj:
                    try:
                        re.fullmatch(re.compile(r'^(.*?)(?::(\d+))?$'), elem)
                        host,port = re.search(r'^(.*?)(?::(\d+))?$', elem).groups()
                        try:
                            int(port)
                        except:
                            raise ValueError(f'Port value is not integer: {elem}.')
                    except Exception as err:
                        raise ValueError(f'Format for host:port value is not right: {elem}.')
   
    def check_splunk_host_port_availability(param_name):
        if definition.parameters[param_name] is not None and definition.parameters[param_name] != '':
                ist_obj = json.loads(definition.parameters[param_name])
                for elem in ist_obj:
                    host,port = re.search(r'^(.*?)(?::(\d+))?$', elem).groups()
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(2)
                    try:
                        s.connect((host, int(port)))
                    except:
                        raise ValueError(f'Can`t open connection to host:port. Check {elem} value.')
                
    for param in ["splunk_rest_api_host_and_port"]:
        check_array_validation(param)
        check_host_port_validation(param)
        check_splunk_host_port_availability(param)
    
    for param in ["parallel_jobs_count"]:
        check_for_integer(param)

def get_splunk_config_from_input_param(splunk_host_port, session_key, app, 
                                       splunk_rest_api_username, splunk_rest_api_password, 
                                       splunk_rest_api_token):
    splunk_host, splunk_port = re.search(r'^(.*?)(?::(\d+))?$', splunk_host_port).groups()
    if splunk_host == 'localhost':
        return {"host": "localhost", "port": int(splunk_port), "token": session_key, "app": app}
    elif splunk_rest_api_username and splunk_rest_api_password:
        return {"host": splunk_host, "port": int(splunk_port), "username": splunk_rest_api_username, "password": splunk_rest_api_password, "app": app}
    elif splunk_rest_api_token:
        return {"host": splunk_host, "port": int(splunk_port), "splunkToken": splunk_rest_api_token, "app": app}
    else:
        logging.info({"host": splunk_host, "port": int(splunk_port), "splunkToken": splunk_rest_api_token, "app": app})
        raise ValueError("Insufficient credentials provided for Splunk configuration.")

def get_app_version():
    app_path = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', app)
    app_conf_path = os.path.join(app_path, 'default', 'app.conf')
    if not os.path.exists(app_conf_path):
        return app, "NA"

    config = configparser.ConfigParser()
    config.read(app_conf_path)
    try:
        app_version = config['launcher']['version']
        app_name = config['ui']['label']
        return app_name, app_version
    except KeyError:
        return app, "NA"


def collect_events(helper, ew):
    session_key = helper._input_definition.metadata["session_key"]
    app_name,app_version = get_app_version()
    input_name = helper.get_input_stanza_names()
    parallel_jobs_count = int(helper.get_arg('parallel_jobs_count') or 1)
    socprime_ad_input = socprime_ad_api(parallel_jobs_count,app_name,app_version)
    socprime_ad_input.input_name = input_name

    logging.info(f'Starting Attack Detective input script')
    logging.info(f'Start Input processing: {input_name}')

    attack_detective_api_key = helper.get_arg('attack_detective_api_key')
    socprime_ad_input.api_token = attack_detective_api_key

    attack_detective_api_url = helper.get_arg('attack_detective_api_url')
    socprime_ad_input.base_url = attack_detective_api_url
    
    splunk_rest_api_host_and_port = json.loads(helper.get_arg('splunk_rest_api_host_and_port') or '["localhost:8089"]')
    splunk_rest_api_username = helper.get_arg('splunk_rest_api_username')
    splunk_rest_api_password = helper.get_arg('splunk_rest_api_password')
    splunk_rest_api_token = helper.get_arg('splunk_rest_api_token')
    proxy_settings = helper.get_proxy()

    socprime_ad_input.proxy_server = get_proxy(proxy_settings) if proxy_settings else {}
    logging.debug(f'Using proxy server: {socprime_ad_input.proxy_server}' if proxy_settings else 'No proxy server configured.')
        
    for splunk_host_port in splunk_rest_api_host_and_port:
        logging.info(f'Starting Attack Detective querying in the Splunk instance: {splunk_host_port}. Input name: {input_name}')
        conf = get_splunk_config_from_input_param(splunk_host_port,session_key,app,splunk_rest_api_username,splunk_rest_api_password,splunk_rest_api_token)
        socprime_ad_input.conf = conf
        socprime_ad_input.start_processing_tasks()
        logging.info(f'Script execution completed for the instance: {splunk_host_port}. Input name: {input_name}')
        