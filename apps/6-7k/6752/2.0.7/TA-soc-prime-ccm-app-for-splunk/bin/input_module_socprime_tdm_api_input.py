# encoding = utf-8

import os
import sys
import time
import datetime

import json
import requests
import ccm_module
import splunk_module
import logging
import configparser

app = __file__.split(os.sep)[-3]

def get_job_list_from_tdm(client_secret_id, BASE_URL, proxy_server, app_name, app_version):
    URL_PREFIX = "/v1/ccm/jobs"
    headers = {
            'client_secret_id': client_secret_id,
            'User-Agent': f'{app_name}/{app_version}'
    }
    try:
        response = requests.get(url=f'{BASE_URL}{URL_PREFIX}/', headers=headers, proxies=proxy_server)
    except Exception as e:
        raise ValueError(f'Error while validation session. Error message: {e}')
    if response.ok:
        return response.json()
    else:
        raise ValueError(f'Error during validation process. Response status code: {response.status_code}. Error message: {response.text}.')

def get_id_from_name(job_names_list, get_job_list_from_tdm):
    id_list = []
    for a in job_names_list:
        for b in get_job_list_from_tdm:
            if a == b['name']:
                id_list.append(b['id'])
    return id_list

def get_proxy(proxy_dict):
    if proxy_dict.get('proxy_type') == "http":
        proto = ''
    elif proxy_dict.get('proxy_type') == "socks4":
        proto = 'socks4://'
    elif proxy_dict.get('proxy_type') == "socks5":
        proto = 'socks5://'
    if proxy_dict.get('proxy_username') != '' and proxy_dict.get('proxy_password') != '':
        proxy_user_password = proxy_dict.get('proxy_username') + ':' + proxy_dict.get('proxy_password') + '@'
    else:
        proxy_user_password = ''
    proxy_result = {
                    "http": proto + proxy_user_password + proxy_dict.get('proxy_url') + ":" + proxy_dict.get('proxy_port'),
                    "https:": proto + proxy_user_password + proxy_dict.get('proxy_url') + ":" + proxy_dict.get('proxy_port')
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
    for elem in ["rule_exceptions", "splunk_default_host_port_list", "job_names_list"]:
        check_array_validation(elem)

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
    logging.info(f'Starting input script. All saved searches will be installed in to the {app} application.')
    logging.info(f'Start Input processing: {input_name}')

    client_secret_id = helper.get_arg('client_secret_id')
    job_names_list = helper.get_arg('job_names_list')
    rule_exception_list = helper.get_arg('rule_exceptions')
    splunk_default_host_port_list = helper.get_arg('splunk_default_host_port_list')
    splunk_default_restapi_user = helper.get_arg('splunk_default_restapi_user')
    splunk_default_restapi_password = helper.get_arg('splunk_default_restapi_password')
    force_updating_rules = helper.get_arg('force_updating_rules')
    proxy_settings = helper.get_proxy()
    rules_owner = helper.get_arg('splunk_default_rules_owner')
    BASE_URL = helper.get_arg('ccm_api_url')

    if len(proxy_settings) == 0:
        proxy_server = {}
    else:
        proxy_server = get_proxy(proxy_settings)
    logging.info(f'Using proxy server: {proxy_server}')

    if splunk_default_host_port_list is not None:
        splunk_default_host_port_list = json.loads(splunk_default_host_port_list)
    else:
        splunk_default_host_port_list = ["localhost:8089"]

    if rule_exception_list is not None:
        rule_exception_list = json.loads(rule_exception_list)
    else:
        rule_exception_list = []

    if job_names_list is not None:
        job_names_list = json.loads(job_names_list)

    else:
        job_names_list = []

    if force_updating_rules == "false":
        force_updating_rules = False
    else:
        force_updating_rules = True

    if rules_owner is not None:
        rules_owner = str(rules_owner)
    else:
        rules_owner = 'nobody'

    logging.info(f'Input Name: {input_name}. Start processing all Jobs.')
    job_list_from_tdm = get_job_list_from_tdm(client_secret_id, BASE_URL, proxy_server, app_name, app_version)
    results = []
    if len(job_names_list) > 0 and len(job_list_from_tdm) > 0:
        id_list = get_id_from_name(job_names_list, job_list_from_tdm)
        if len(id_list) == 0:
            logging.info(f'Input Name: {input_name}. Jobs ID list is empty. Check your Jobs List parameter.')
            exit(0)
        elif len(id_list) > 0:
            logging.info(f'Input Name: {input_name}. Jobs ID list: {id_list}.')
            for job_id in id_list:
                cntnt = ccm_module.InputCCM(client_secret_id, job_id, BASE_URL, proxy_server, app_name, app_version)
                result = cntnt.get_data_from_ccm()
                if result is not None:
                    logging.info(f'Input Name: {input_name}. Processing Job ID:{job_id}. Results count: {len(result)}.')
                    logging.debug(f'{job_id}|{result}')
                    if len(result) > 0:
                        results += result
                else:
                    logging.info(f'Input Name: {input_name}. Processing Job ID:{job_id}. No results. Check your job.')
    logging.debug(f'{job_names_list}|{results}')
    if len(results) > 0:
        for savedsearch in results:
                if savedsearch["case"]["name"] in rule_exception_list:
                    logging.info(f'The savedsearch \"{savedsearch["case"]["name"]}\" will be deleted from results because this rule in the Exception List.')
                    results.remove(savedsearch)
    logging.info(f'Input Name: {input_name}. The total number of savedsearches for this input according to your Job Lists: {len(results)}')
    if len(results) < 0:
        exit(0)
    successfully_installed_rules = []
    for splunk_host_port in splunk_default_host_port_list:
        if splunk_host_port in ["localhost:8089", "127.0.0.1:8089"]:
            conf = {
                    "host": "localhost",
                    "port": 8089,
                    "token": session_key,
                    "app": app
                    }
            splout = splunk_module.OutputSplunk(conf,force_updating_rules,rules_owner)
        else:
            splunk_default_hostname, splunk_default_port = splunk_host_port.split(":")
            if splunk_default_restapi_user is None or splunk_default_restapi_password is None:
                raise ValueError(f'Error. Splunk API User or Password is not set.')
            conf = {
                    "host": splunk_default_hostname,
                    "port": int(splunk_default_port),
                    "username": splunk_default_restapi_user,
                    "password": splunk_default_restapi_password,
                    "app": app
                    }
            splout = splunk_module.OutputSplunk(conf,force_updating_rules,rules_owner)
        splout.bulk_create_saved_search(results)
        if len(splout.successfully_installed_rules) > 0 and splout.successfully_installed_rules not in successfully_installed_rules:
            successfully_installed_rules += splout.successfully_installed_rules
        if len(successfully_installed_rules) > 0:
            cntnt.post_ccm_stat_gen_chunks(successfully_installed_rules)
