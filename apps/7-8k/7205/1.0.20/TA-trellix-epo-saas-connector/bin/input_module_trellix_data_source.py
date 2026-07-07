# encoding = utf-8

import os
import sys

from pathlib import Path
import time
import base64
import logging
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import json
import splunklib.client as client
from splunklib.modularinput import Argument, Script, Scheme, Event
import dateutil.parser
import dateutil.tz
import requests
import re
from splunk.clilib import cli_common as cli
from datetime import datetime, timedelta
from splunktaucclib.splunk_aoblib.rest_helper import TARestHelper
from collections import OrderedDict
from datetime import timezone

if sys.version_info[0] < 3:
    import urllib
else:
    import urllib.parse as urllib


'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''

'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

"After adding input in UI,the call will go for pull the ePO SaaS events and Insights events(if insights checkbox is checked) "

_APPNAME = 'TA-trellix-epo-saas-connector'


client_scope_device = "epo.device.r epo.device.w "                        # ePO DeviceScopes
client_scope_epo = "epo.evt.r "                        # ePO SaaS Threat Events Scopes
client_scope_insight = "ins.ms.r ins.suser ins.user "     # Insight Scopes
client_scope_audit = "audit.svc.r "                       # Trellix Audit Log Scopes (IAM/ePO SaaS /EDR)
client_scope_dlp = "dpim.api.r udlp.im.vf udlp.im.vm "   #Trellix DLP Incidents Scopes
client_scope_edr = "soc.act.tg "                          #Trellix EDR Threats
client_scope_tag = "epo.tags.r epo.tags.w"                # ePo TagScopes

uam_client_scope_device = "epo.device.r "                        # ePO DeviceScopes
uam_client_scope_epo = "epo.evt.r "              # ePO SaaS Threat Events Scopes
uam_client_scope_insight = "ins.ms.r ins.suser ins.user "     # Insight Scopes
uam_client_scope_audit = "audit.svc.r "                     # Trellix Audit Log Scopes (IAM/ePO SaaS /EDR)
uam_client_scope_dlp = "dpim.api.r udlp.im.vf udlp.im.vm "   #Trellix DLP Incidents Scopes
uam_client_scope_edr = "soc.act.tg "                          #Trellix EDR Threats Scopes

cached_token = None
token_expires_at = None

dlp_cached_token = None
dlp_token_expires_at = None

no_record_sleep_period_in_seconds = 60


def setup_logger(level):
    """
    Setup a logger for the REST handler.
    """

    logger = logging.getLogger('splunk.appserver.%s.controllers.trellix_saas_datasource_controller' % _APPNAME)
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler( make_splunkhome_path(['var', 'log', 'splunk', 'trellix_saas_datasource_controller.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


logger = setup_logger(logging.DEBUG)
rest_helper = TARestHelper(logger)

def get_trelliX_headers(api_Key, token):
    HEADERS = {
        'Authorization': 'Bearer ' + str(token),
        'Content-Type': 'application/vnd.api+json',
        'x-api-key': api_Key
    }
    return HEADERS


def obtain_bearer_token(helper, token_url, client_id, client_secret, scope, proxy_settings):
    global cached_token
    global token_expires_at

    #if cached_token is not None and token_expires_at > time.time():
        # use the cached token.
        #helper.log_debug("Trellix: Using cached token")
        #return cached_token

    helper.log_debug("Trellix: requesting new token")
    res_token = get_api_token(helper, token_url, client_id, client_secret, scope, proxy_settings)
    #helper.log_info("Trellix: After requesting new token="+str(res_token))


    if hasattr(res_token, 'status_code') and res_token.status_code == 200:
        token_json = json.loads(res_token.text)
        auth_token = token_json['access_token']

        #expires_in = (10*60) # 9 minutes
        #if 'expires_in' in token_json:
        #    expires_in = token_json['expires_in']

        # Subtract 1 minute to ensure it doesn't expire
        #expires_in -= (1*60)
        #token_expires_at = time.time() + expires_in
        #cached_token = auth_token
        #return cached_token
        return auth_token
    elif (hasattr(res_token, 'status_code') and res_token.status_code == 401) or ("ALTER_IAM"==res_token):
        if "realms" in token_url:
            temp_url = "https://iam.cloud.trellix.com/iam/v1.1/token"
        else:
            temp_url = "https://auth.trellix.com/auth/realms/IAM/protocol/openid-connect/token"

        res_token = get_api_token(helper, temp_url, client_id, client_secret, scope, proxy_settings)
        helper.log_info("Trellix: requesting dual IAM token="+str(res_token))

        if hasattr(res_token, 'status_code') and res_token.status_code == 200:
            token_json = json.loads(res_token.text)
            auth_token = token_json['access_token']
            return auth_token

        else:
            #cached_token = None
            auth_token = None
            raise Exception(f"Trellix: Error obtain dual IAM Credentials for the input {str(helper.input_name)} ")
    else:
        #cached_token = None
        auth_token = None
        raise Exception(f"Trellix: Error obtain Credentials for the input {str(helper.input_name)} ")



def get_api_token(helper, token_url, client_id, client_secret, scope, proxy_settings):
    response = ''
    try:
        data_string = str(client_id) + ":" + str(client_secret)
        data_bytes = data_string.encode("utf-8")
        encoded_value = base64.b64encode(data_bytes)
        HEADERS = {
            'Authorization': 'Basic ' + encoded_value.decode('utf-8'),
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        parameters="grant_type=client_credentials&scope="+scope
        #helper.log_info("###TOKEN TOKEN TOKEN TOKEN###=URL="+str(token_url)+"   EV="+str(HEADERS))
        if proxy_settings:
            #helper.log_info("###TOKEN TOKEN TOKEN TOKEN###=PROXY")
            response = helper.send_http_request(token_url, 'POST', parameters=None, payload=parameters,
                                                headers=HEADERS, cookies=None, verify=True, cert=None,
                                                timeout=10, use_proxy=True)
        else:
            #helper.log_info("###TOKEN TOKEN TOKEN TOKEN###=NOT PROXY")
            response = helper.send_http_request(token_url, 'POST', parameters=None, payload=parameters,
                                                headers=HEADERS, cookies=None, verify=True, cert=None,
                                                timeout=10, use_proxy=False)


        return response

    except requests.ReadTimeout as ex:
        helper.log_info("Trellix :get_api_token() MESSAGE : Read Timeout = " + str(ex))
        return "ALTER_IAM"
    except Exception as ex:
        helper.log_info("Trellix :get_api_token() MESSAGE : Error Occurred = " + str(ex))
        #return ex

def dlp_obtain_bearer_token(helper, token_url, client_id, client_secret, scope, proxy_settings):
    global dlp_cached_token
    global dlp_token_expires_at

    #if dlp_cached_token is not None and dlp_token_expires_at > time.time():
        # use the cached token.
    #    helper.log_debug("Trellix: Using cached token")
    #    return dlp_cached_token

    helper.log_debug("Trellix: DLP requesting new token")
    res_token = dlp_get_api_token(helper, token_url, client_id, client_secret, scope, proxy_settings)
    #helper.log_info("Trellix: DLP After requesting new token="+str(res_token))


    if hasattr(res_token, 'status_code') and res_token.status_code == 200:
        token_json = json.loads(res_token.text)
        auth_token = token_json['access_token']

        #expires_in = (10*60) # 9 minutes
        #if 'expires_in' in token_json:
        #    expires_in = token_json['expires_in']

        # Subtract 1 minute to ensure it doesn't expire
        #expires_in -= (1*60)
        #token_expires_at = time.time() + expires_in
        #cached_token = auth_token
        #return cached_token
        return auth_token
    elif (hasattr(res_token, 'status_code') and res_token.status_code == 401) or ("ALTER_IAM"==res_token):
        if "realms" in token_url:
            temp_url = "https://iam.cloud.trellix.com/iam/v1.1/token"
        else:
            temp_url = "https://auth.trellix.com/auth/realms/IAM/protocol/openid-connect/token"

        res_token = dlp_get_api_token(helper, temp_url, client_id, client_secret, scope, proxy_settings)
        #helper.log_info("Trellix: requesting dual IAM token="+str(res_token))

        if hasattr(res_token, 'status_code') and res_token.status_code == 200:
            token_json = json.loads(res_token.text)
            auth_token = token_json['access_token']
            return auth_token

        else:
            #cached_token = None
            auth_token = None
            raise Exception(f"Trellix: DLP Error obtain dual IAM Credentials for the input {str(helper.input_name)} ")
    else:
        #cached_token = None
        auth_token = None
        raise Exception(f"Trellix: DLP Error obtain Credentials for the input {str(helper.input_name)} ")



def dlp_get_api_token(helper, token_url, client_id, client_secret, scope, proxy_settings):
    response = ''
    try:
        data_string = str(client_id) + ":" + str(client_secret)
        data_bytes = data_string.encode("utf-8")
        encoded_value = base64.b64encode(data_bytes)
        HEADERS = {
            'Authorization': 'Basic ' + encoded_value.decode('utf-8'),
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        parameters="audience=trellix&grant_type=client_credentials&scope="+scope
        helper.log_info("###TOKEN TOKEN TOKEN TOKEN###=URL="+str(token_url)+"   EV="+str(HEADERS))
        if proxy_settings:
            helper.log_info("###TOKEN TOKEN TOKEN TOKEN###=PROXY")
            response = helper.send_http_request(token_url, 'POST', parameters=None, payload=parameters,
                                                headers=HEADERS, cookies=None, verify=True, cert=None,
                                                timeout=None, use_proxy=True)
        else:
            helper.log_info("###TOKEN TOKEN TOKEN TOKEN###=NOT PROXY")
            response = helper.send_http_request(token_url, 'POST', parameters=None, payload=parameters,
                                                headers=HEADERS, cookies=None, verify=True, cert=None,
                                                timeout=None, use_proxy=False)


        return response

    except requests.ReadTimeout as ex:
        helper.log_info("Trellix :DLP get_api_token() MESSAGE : Read Timeout = " + str(ex))
        return "ALTER_IAM"
    except Exception as ex:
        helper.log_info("Trellix :DLP get_api_token() MESSAGE : Error Occurred = " + str(ex))
        #return ex

def get_event_list(helper, token, events_url, apiKey, proxy_settings):
    try:

        HEADERS = {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/vnd.api+json',
            'x-api-key': apiKey
        }

        if proxy_settings:
            response = helper.send_http_request(events_url, 'GET', parameters=None, payload=None,
                                                headers=HEADERS, cookies=None, verify=True, cert=None,
                                                timeout=None, use_proxy=True)
        else:
            response = helper.send_http_request(events_url, 'GET', parameters=None, payload=None,
                                                headers=HEADERS, cookies=None, verify=True, cert=None,
                                                timeout=None, use_proxy=True)

        return response

    except Exception as ex:
        helper.log_info("Trellix :get_event_list() : Error Occurred = "+str(ex))
        return ex


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # api_gateway_url = definition.parameters.get('apigateway_url', None)
    # client_id = definition.parameters.get('client_id', None)
    # client_secret = definition.parameters.get('client_secret', None)
    # api_key = definition.parameters.get('api_key', None)
    #interval = helper.get_arg('interval')
    interval = definition.parameters.get('interval', None)

    if int(interval) < 300 :
        raise ValueError('The data pull interval should be greater than 300 sec')
    #response = check_mvision_server_status(helper, definition)
    response = True
    if (response):
        pass
    else:
        raise ValueError('check the Trellix SaaS server Status')


    check_epo_events = definition.parameters.get('trellix_epo_events')
    check_audit_events = definition.parameters.get('trellix_audit_events')
    check_insights_events = definition.parameters.get('trellix_insights_events')
    check_dlp_incidents = definition.parameters.get('trellix_dlp_incidents')
    check_edr_events = definition.parameters.get('trellix_edr_events')

    #if ( check_epo_events is None and check_audit_events is None and check_insights_events is None and check_dlp_incidents is None and check_edr_events is None):
    #    raise ValueError('Atleast select one of the checkbox')
        #raise ValueError({
        #    "messages": [{"type": "ERROR", "text": "Please select at least one checkbox."}]
        #})
    #else:
    #    pass

def check_mvision_server_status(helper, definition):

    client_id = definition.parameters.get('client_id', None)
    client_secret = definition.parameters.get('client_secret', None)
    api_gateway_url = definition.parameters.get('api_gateway_url', None)
    api_key = definition.parameters.get('api_key', None)

    data_name = helper.get_arg('name')+"``splunk_cred_sep``"+"1"

    CLEAR_PASSWORD = get_password(helper, data_name)
    JSON_obj = json.loads(CLEAR_PASSWORD)

    opt_client_secret = helper.get_arg('client_secret')
    opt_api_key = helper.get_arg('api_key')

    api_key = ''

    client_secret = ''
    proxy_settings = definition.parameters.get('proxy',None)

    proxy_enabled = False
    proxy_url =None
    input_conf_file_path = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', _APPNAME,"local", "ta_trellix_epo_saas_connector_settings.conf")
    if os.path.exists(input_conf_file_path):
        input_conf = cli.readConfFile(input_conf_file_path)
        for name, content in input_conf.items():
            if "proxy" in name and content["proxy_enabled"] != "0":
                proxy_enabled = True
                proxy_url = content["proxy_type"]+"://"+content["proxy_url"]+":"+content["proxy_port"]

    data_string = str(client_id) + ":" + str(client_secret)
    data_bytes = data_string.encode("utf-8")
    encoded_value = base64.b64encode(data_bytes)

    HEADERS = {
        'Authorization': 'Basic ' + encoded_value.decode('utf-8'),
        'Content-Type': 'application/vnd.api+json'
    }

    iam_url = definition.parameters.get('iam_url', None) + "scope=" + client_scope_device
    url = api_gateway_url + '/epo/v2/tags'

    if proxy_enabled:
        response =  rest_helper.send_http_request(
            url=iam_url,
            method="GET",
            headers=HEADERS,
            timeout=30,
            proxy_uri=proxy_url
        )
    else:
        response =  rest_helper.send_http_request(
            url=iam_url,
            method="GET",
            headers=HEADERS,
            timeout=30
        )

    if response.status_code == 200:
        pass
    else:
        return False

    token_json = json.loads(response.text)
    auth_token = token_json['access_token']

    HEADERS = {
        'Authorization': 'Bearer ' + str(auth_token),
        'Content-Type': 'application/vnd.api+json',
        'x-api-key': api_key
    }

    if proxy_enabled:
        response =  rest_helper.send_http_request(
            url=url,
            method="GET",
            headers=HEADERS,
            timeout=30,
            proxy_uri=proxy_url
        )
    else:
        response = rest_helper.send_http_request(
            url=url,
            method="GET",
            headers=HEADERS,
            timeout=30
        )

    if response.status_code == 200:
        return True
    else:
        return False

def credentials_validation(helper,ew):
    try:
        APP = helper.get_app_name()
        helper.collection_name = APP
        session_key = helper.context_meta['session_key']
        helper.USERNAME = helper.get_arg('client_id')
        helper.ew = ew
        helper.max_past = _utcnow() - timedelta(hours=11, minutes=59)
        # The following examples get the arguments of this input.
        # Note, for single instance mod input, args will be returned as a dict.
        # For multi instance mod input, args will be returned as a single value.

        helper.nobody_client = client.connect(token=session_key, owner='nobody', app=APP, autologin=True)
        helper.admin_client = client.connect(token=session_key, autologin=True)

        iam_url = helper.get_arg('iam_url')
        opt_client_id = helper.get_arg('client_id')
        data_name = helper.input_name.split('://')[1]+"``splunk_cred_sep``"+"1"

        CLEAR_PASSWORD = get_password(helper, data_name)
        JSON_obj = json.loads(CLEAR_PASSWORD)
        proxy_settings = helper.get_proxy()
        scope = client_scope_device.strip()

        auth_token = obtain_bearer_token(helper, iam_url, opt_client_id,
                                         JSON_obj['client_secret'], scope, proxy_settings)

        if hasattr(auth_token, 'status_code') and auth_token.status_code != 200:
            helper.log_info("###credentials is invalid###")
        else:
            helper.log_info("###credentials is valid###")
    except Exception as ex:
        helper.log_info(ex)

def collect_events(helper, ew):
    final_time_dt = _utcnow()
    final_time_dt = fmtdate(final_time_dt)

    credentials_validation(helper,ew)

    saas_flag = helper.get_arg('trellix_epo_events')
    audit_flag = helper.get_arg('trellix_audit_events')
    insights_flag = helper.get_arg('trellix_insights_events')
    dlp_flag = helper.get_arg('trellix_dlp_incidents')
    edr_flag = helper.get_arg('trellix_edr_events')

    if saas_flag:
        collect_saas_events(helper, ew,final_time_dt)

    if audit_flag:
        collect_saas_audits(helper, ew,final_time_dt)

    if insights_flag:
        collect_insights_events(helper, ew,final_time_dt)

    if dlp_flag:
        collect_dlp_events(helper, ew,final_time_dt)

    if edr_flag:
        collect_edr_events(helper, ew,final_time_dt)

    if saas_flag or audit_flag or insights_flag or dlp_flag or edr_flag:
        update_saas_last_poll_time(helper,final_time_dt)
    else:
        helper.log_info("This indicates a configuration issue where Trellix data sources have not been selected to send events to Splunk. \n Action is required to select the Trellix data sources to enable event flow into Splunk.")

def collect_saas_events(helper, ew,final_time_dt):

    # step 1
    APP = helper.get_app_name()
    CLEAR_PASSWORD = None
    PROXY_PASSWORD = None
    PROXY_USERNAME = helper.get_arg('proxy_username', None)
    helper.collection_name = APP
    proxy_password = helper.get_arg('proxy_password', None)
    uri =helper.context_meta["server_uri"]
    session_key = helper.context_meta['session_key']
    helper.USERNAME = helper.get_arg('client_id')
    helper.ew = ew
    helper.max_past = _utcnow() - timedelta(hours=11, minutes=59)
    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.

    helper.nobody_client = client.connect(token=session_key, owner='nobody', app=APP, autologin=True)
    helper.admin_client = client.connect(token=session_key, autologin=True)
    iam_url = helper.get_arg('iam_url')
    opt_api_gateway_url = helper.get_arg('api_gateway_url')
    opt_client_id = helper.get_arg('client_id')

    opt_client_secret = helper.get_arg('client_secret')
    opt_api_key = helper.get_arg('api_key')

    data_name = helper.input_name.split('://')[1]+"``splunk_cred_sep``"+"1"

    CLEAR_PASSWORD = get_password(helper, data_name)
    JSON_obj = json.loads(CLEAR_PASSWORD)

    helper.get_input_type()
    loglevel = helper.get_log_level()
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()

    initial_time_dt = retrieve_saas_last_poll_time(helper)
    #final_time_dt = _utcnow()
    initial_time_dt = fmtdate(initial_time_dt)
    helper.log_debug("@@@ SAAS events from initial_time_dt ===" + str(initial_time_dt))
    helper.log_debug("@@@ SAAS events from final_time_dt ===" + str(final_time_dt))

    time_le = "filter[timestamp][le]="+final_time_dt
    time_le = time_le.replace(':', '%3A')
    time_gt = "filter[timestamp][ge]="+initial_time_dt
    time_gt = time_gt.replace(':', '%3A')

    #time_le = "filter[timestamp][le]=2025-04-10T00:00:00.652Z"
    #time_le = time_le.replace(':', '%3A')
    #time_gt = "filter[timestamp][ge]=2025-09-28T10:23:00.652Z"
    #time_gt = time_gt.replace(':', '%3A')

    next_page_link = "page[limit]=1000"
    param = next_page_link + "&" + time_gt + "&" + time_le
    #param = next_page_link
    url = opt_api_gateway_url + '/epo/v2/events'
    count = 0
    helper.log_info("###POLLING STARTED SAAS###")
    while True:
        try:

            scope = client_scope_epo.strip()


            auth_token = obtain_bearer_token(helper, iam_url, opt_client_id,
                                             JSON_obj['client_secret'], scope, proxy_settings)

            if hasattr(auth_token, 'status_code') and auth_token.status_code != 200:
                helper.log_info("###Credentials is invalid###")
            head = get_trelliX_headers(JSON_obj['api_key'], auth_token)
            helper.log_info("Trellix: SaaS from FLITER ==="+str(param))
            if proxy_settings:
                helper.log_info("###POLLING STARTED SAAS###PROXY")
                response = helper.send_http_request(url, 'GET', parameters=param, payload=None,
                                                    headers=head, cookies=None, verify=True, cert=None,
                                                    timeout=None, use_proxy=True)
            else:
                helper.log_info("###POLLING STARTED SAAS###NO PROXY")
                response = helper.send_http_request(url, 'GET', parameters=param, payload=None,
                                                    headers=head, cookies=None, verify=True, cert=None,
                                                    timeout=None, use_proxy=False)

            if hasattr(response, 'status_code') and response.status_code == 200:
                my_data = response.json()
                #my_data = {"data":[{"id":"123456789","attributes":{
                 #   "sourceipv4":"172.16.214.33","agentguid":"0F835DF8-A139-4A6B-9DA3-6CF98FC8884B"}}]}
                result = json.dumps(my_data)
                if result is None:
                    helper.log_info("Error occurred while fetching threat events from MVISION ePO.")
                    raise Exception("Error occurred while fetching threat events from MVISION ePO.")
                else:
                    result_json = ''
                    try:
                        if not validateJSON(helper, result):
                            raise Exception("invalid json")

                        result_json = json.loads(result)
                        response = result_json["data"]

                        for event in response:
                            '''Push Threat Events pulled from MVISION ePO to Splunk Syslog'''
                            saas_event=''
                            count = count + 1
                            saas_event= event["attributes"]
                            saas_event.update({'id':event['id']})

                            if "sourceipv6" in saas_event:
                                sourceipv6 = saas_event["sourceipv6"]
                                #helper.log_info("Before cleaning: " + str(sourceipv6))
                                saas_event["sourceipv6"] = clean_ip(sourceipv6)
                                #helper.log_info("After cleaning: " + str(saas_event["sourceipv6"]))


                            if hasattr(saas_event, 'extendedattributes'):
                                extended_att = saas_event["extendedattributes"]
                                if hasattr(extended_att, 'EPExtendedEvent'):
                                    ep_extended_att = extended_att["EPExtendedEvent"]
                                    #helper.log_info("###EPExtendedEvent EPExtendedEvent EPExtendedEvent###")
                                    saas_event.pop("extendedattributes",None)
                                    #helper.log_info("###EPExtendedEvent###="+str(saas_event))
                                    saas_event.update({'TargetModifyTime':ep_extended_att['TargetModifyTime'],
                                                       'SecondActionStatus':ep_extended_att['SecondActionStatus'],
                                                       'DurationBeforeDetection':ep_extended_att['DurationBeforeDetection'],
                                                       'TargetPath':ep_extended_att['TargetPath'],
                                                       'TargetFileSize':ep_extended_att['TargetFileSize'],
                                                       'AttackVectorType':ep_extended_att['AttackVectorType'],
                                                       'TargetName':ep_extended_att['TargetName'],
                                                       'TargetAccessTime':ep_extended_att['TargetAccessTime'],
                                                       'AMCoreContentVersion':ep_extended_att['AMCoreContentVersion'],
                                                       'NaturalLangDescription':ep_extended_att['NaturalLangDescription'],
                                                       'TaskName':ep_extended_att['TaskName'],
                                                       'AnalyzerGTIQuery':ep_extended_att['AnalyzerGTIQuery'],
                                                       'SecondAttemptedAction':ep_extended_att['SecondAttemptedAction'],
                                                       'AnalyzerContentCreationDate':ep_extended_att['AnalyzerContentCreationDate'],
                                                       'BladeName':ep_extended_att['BladeName'],
                                                       'ThreatDetectedOnCreation':ep_extended_att['ThreatDetectedOnCreation'],
                                                       'TargetCreateTime':ep_extended_att['TargetCreateTime'],
                                                       'FirstAttemptedAction':ep_extended_att['FirstAttemptedAction'],
                                                       'Cleanable':ep_extended_att['Cleanable'],
                                                       'FirstActionStatus':ep_extended_att['FirstActionStatus']})

                            #helper.log_info("###EPExtendedEvent WRITE###="+str(saas_event))
                            evt = helper.new_event(json.dumps(
                                saas_event), time=None, host=None, index=None, source=None, sourcetype="TrellixDataSource", done=True, unbroken=True)
                            ew.write_event(evt)


                        '''Get the link to next page if pagination is present'''
                        next_page = result_json["links"]["next"]
                        param = next_page.split("?")[1]
                    except Exception as ex:
                        helper.log_info("###POLLING ENDED###")
                        helper.log_info("@@@@@@@ EVENT SAAS COUNT="+str(count))
                        helper.log_info("while parsing events from ePO for the input="+str(helper.input_name))
                        break

            else:
                helper.log_info("### Required(SaaS) scope is not present for this Input="+str(response.text))
                break

        except Exception as ex:
            helper.log_info(ex)
            break

def clean_ip(ip):
    if ip and ip.startswith("/"):
        return ip[1:]
    return ip

def collect_saas_audits(helper, ew,final_time_dt):
    # step 1
    APP = helper.get_app_name()
    PROXY_USERNAME = helper.get_arg('proxy_username', None)
    helper.collection_name = APP
    proxy_password = helper.get_arg('proxy_password', None)
    uri = helper.context_meta["server_uri"]
    session_key = helper.context_meta['session_key']
    helper.USERNAME = helper.get_arg('client_id')
    helper.ew = ew
    helper.max_past = _utcnow() - timedelta(hours=11, minutes=59)
    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.

    helper.nobody_client = client.connect(token=session_key, owner='nobody', app=APP, autologin=True)
    helper.admin_client = client.connect(token=session_key, autologin=True)
    opt_api_gateway_url = helper.get_arg('api_gateway_url')
    opt_client_id = helper.get_arg('client_id')

    opt_client_secret = helper.get_arg('client_secret')
    opt_api_key = helper.get_arg('api_key')
    iam_url = helper.get_arg('iam_url')

    audit_source = helper.get_arg('audit_source')

    # download_intervals(helper)

    kind, input_name = helper.input_name.split('://')
    proxy_password_storage_key = '_'.join([kind, input_name, str(PROXY_USERNAME)])

    data_name = helper.input_name.split('://')[1] + "``splunk_cred_sep``" + "1"

    CLEAR_PASSWORD = get_password(helper, data_name)
    JSON_obj = json.loads(CLEAR_PASSWORD)

    helper.get_input_type()
    # get the loglevel from the setup page
    loglevel = helper.get_log_level()
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()

    initial_time_dt = fmtdate(retrieve_saas_last_poll_time(helper))
    helper.log_debug("Trellix: auditLogs from initial_time_dt ===" + str(initial_time_dt))
    helper.log_debug("Trellix: auditlogs from final_time_dt ===" + str(final_time_dt))

    time_le = "filter[startTime][le]=" + final_time_dt
    time_le = time_le.replace(':', '%3A')
    time_gt = "filter[startTime][ge]=" + initial_time_dt
    time_gt = time_gt.replace(':', '%3A')

    next_page_link = "page[limit]=1000"
    param = next_page_link + "&" + time_gt + "&" + time_le
    url = opt_api_gateway_url + '/epo/v2/auditLogs'

    count = 0
    helper.log_info("Trellix: POLLING Started for Audit Events")
    while True:
        try:
            scope = client_scope_audit.strip()

            auth_token = obtain_bearer_token(helper, iam_url, opt_client_id,
                                             JSON_obj['client_secret'], scope, proxy_settings)


            if hasattr(auth_token, 'status_code') and auth_token.status_code != 200:
                helper.log_info("###Credentials is invalid###")

            #helper.log_info("JSON JSON JSON###="+str(JSON_obj))
            #check_apikey =""
            #if hasattr(JSON_obj, 'api_key') :
            #    check_apikey = JSON_obj['api_key']


            head = get_trelliX_headers(JSON_obj['api_key'], auth_token)

            #head = get_trelliX_headers(check_apikey, auth_token)
            # The following examples send rest requests to some endpoint.
            helper.log_info("Trellix: Audit from FLITER ==="+str(param))
            if proxy_settings:
                helper.log_info(f"Trellix: using proxy for {url} ")
                response = helper.send_http_request(url, 'GET', parameters=param, payload=None,
                                                    headers=head, cookies=None, verify=True, cert=None,
                                                    timeout=None, use_proxy=True)
            else:
                helper.log_info(f"Trellix: invoking {url} ")
                response = helper.send_http_request(url, 'GET', parameters=param, payload=None,
                                                    headers=head, cookies=None, verify=True, cert=None,
                                                    timeout=None, use_proxy=False)

            if hasattr(response, 'status_code') and response.status_code == 200:
                my_data = response.json()
                result = json.dumps(my_data)
                if result is None:
                    helper.log_info("Trellix: Error occurred while fetching from {url}")
                    raise Exception("Error occurred while fetching from {url}")
                else:
                    result_json = ''
                    try:
                        if not validateJSON(helper, result):
                            raise Exception("invalid json received from ")

                        result_json = json.loads(result)
                        response = result_json["data"]
                        for user_audit in response:
                            count = count + 1

                            audit_elog = user_audit["attributes"]
                            audit_elog.update({'id':user_audit['id']})
                            audit_elog.update({'auditSource':audit_source})
                            data = helper.new_event(json.dumps(
                                audit_elog), time=None, host=None, index=None, source=None,
                                sourcetype="TrellixAuditLogs", done=True, unbroken=True)
                            ew.write_event(data)

                        '''Get the link to next page if pagination is present'''
                        next_page = result_json["links"]["next"]
                        param = next_page.split("?")[1]

                        #if len(response) == 0:
                        #    helper.log_info("Trellix: Sleeping to save API key usage for {url}")
                        # We have no items, so s
                        #    time.sleep(no_record_sleep_period_in_seconds)

                    except Exception as ex:
                        helper.log_info("###POLLING ENDED###")
                        helper.log_info("@@@@@@@ EVENT AUDIT COUNT=" + str(count))
                        helper.log_info("while parsing events from AuditLogs for the input=" + str(helper.input_name))
                        break
            else:
                helper.log_info("### Required(Audit) scope is not present for this Input="+str(response.text))
                break
        except Exception as ex:
            helper.log_info(ex)
            break

def collect_insights_events(helper, ew,final_time_dt):

    # step 1
    APP = helper.get_app_name()
    CLEAR_PASSWORD = None
    PROXY_PASSWORD = None
    PROXY_USERNAME = helper.get_arg('proxy_username', None)
    helper.collection_name = APP
    proxy_password = helper.get_arg('proxy_password', None)
    uri =helper.context_meta["server_uri"]
    session_key = helper.context_meta['session_key']
    helper.USERNAME = helper.get_arg('client_id')
    helper.ew = ew
    helper.max_past = _utcnow() - timedelta(hours=11, minutes=59)
    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.

    helper.nobody_client = client.connect(token=session_key, owner='nobody', app=APP, autologin=True)
    helper.admin_client = client.connect(token=session_key, autologin=True)
    opt_api_gateway_url = helper.get_arg('api_gateway_url')
    opt_client_id = helper.get_arg('client_id')
    opt_client_secret = helper.get_arg('client_secret')
    opt_api_key = helper.get_arg('api_key')
    iam_url = helper.get_arg('iam_url')

    data_name = helper.input_name.split('://')[1]+"``splunk_cred_sep``"+"1"

    CLEAR_PASSWORD = get_password(helper, data_name)
    JSON_obj = json.loads(CLEAR_PASSWORD)

    helper.get_input_type()
    loglevel = helper.get_log_level()
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()

    initial_time_dt = retrieve_insights_last_poll_time(helper)
    initial_time_dt = fmtdate(initial_time_dt)
    helper.log_debug("collect_insights_events @@@ INSIGHTS events from initial_time_dt ===" + str(initial_time_dt))
    helper.log_debug("collect_insights_events @@@ INSIGHTS events from final_time_dt ===" + str(final_time_dt))

    #time_le = "filter[to_date][eq]="+final_time_dt
    time_le = "filter.to_date.eq="+final_time_dt
    time_le = time_le.replace(':', '%3A')
    time_le = time_le.replace('Z', '.000Z')
    #time_gt = "filter[from_date][eq]="+initial_time_dt
    time_gt = "filter.from_date.eq="+initial_time_dt
    time_gt = time_gt.replace(':', '%3A')
    time_gt = time_gt.replace('Z', '.000Z')

    #time_gt="filter[from_date][eq]=2023-08-15T05:09:29.000Z"
    #time_gt = time_gt.replace(':', '%3A')
    #time_le="filter[to_date][eq]=2023-08-25T13:09:29.000Z"
    #time_le = time_le.replace(':', '%3A')

    next_page_link = "page[limit]=1000"

    param = next_page_link +"&" + time_gt + "&" + time_le
    #params = next_page_link + "&" + eventFields
    url = opt_api_gateway_url + '/insights/v2/events?'

    count = 0
    helper.log_info("###POLLING STARTED INSIGHTS###")
    while True:

        try:

            scope = client_scope_insight.strip()

            helper.log_info("###INSIGHTS SCOPE###="+str(scope))

            auth_token = obtain_bearer_token(helper, iam_url, opt_client_id,
                                             JSON_obj['client_secret'], scope, proxy_settings)

            if hasattr(auth_token, 'status_code') and auth_token.status_code != 200:
                helper.log_info("###Credentials is invalid###")
            head = get_trelliX_headers(JSON_obj['api_key'], auth_token)
            # The following examples send rest requests to some endpoint.
            helper.log_info("Trellix: Insights from FLITER ==="+str(param))
            if proxy_settings:
                helper.log_info("###POLLING STARTED INSIGHTS###PROXY")
                response = helper.send_http_request(url, 'GET', parameters=param, payload=None,
                                                headers=head, cookies=None, verify=True, cert=None,
                                                timeout=None, use_proxy=True)
            else:
                helper.log_info("###POLLING STARTED INSIGHTS###NO PROXY")
                response = helper.send_http_request(url, 'GET', parameters=param, payload=None,
                                                    headers=head, cookies=None, verify=True, cert=None,
                                                    timeout=None, use_proxy=False)

            #helper.log_info("Trellix: Insights RESPONSE ==="+str(response.text))
            if hasattr(response, 'status_code') and response.status_code == 200:
                my_data = response.json()
                result = json.dumps(my_data)
                #helper.log_info("HELP collect_insights_events=" + str(result))
                if result is None:
                    helper.log_info("Error occurred while fetching threat events from collect_insights_events.")
                    raise Exception("Error occurred while fetching threat events from collect_insights_events.")
                else:
                    try:
                        if not validateJSON(helper, result):
                            raise Exception("invalid json")

                        result_json = json.loads(result)
                        #helper.log_info("###INSIGHTS=" + str(result_json))
                        response = result_json["events"]
                        #helper.log_info("INSIGHTS Events="+str(response))
                        for event in response:
                            '''Push Threat Events pulled from MVISION ePO to Splunk Syslog'''

                            insight_att = event
                            insgihs_cus_det = insight_att["customer_details"]
                            ma_id = insgihs_cus_det["ma_id"]
                            agent_guid = convert_ma_id_to_guidformat(ma_id)
                            iocs_att = insight_att["iocs"]

                            md5_value = None
                            sha256_value = None

                            for ioc in iocs_att:
                                type = ioc["type"]
                                if type == "md5":
                                    md5_value = ioc["value"]
                                if type == "sha1":
                                    sha1_value = ioc["value"]
                                if type == "sha256":
                                    sha256_value = ioc["value"]

                            insight_json = {'insights_splunkcategory': 'Trellix Insights Event', 'agentGuid': agent_guid,
                                            'timestamp': insight_att['timestamp'], 'md5': md5_value, 'sha256': sha256_value,
                                            'campaign-id': insight_att['campaign_id'], 'analyzerId': 'Trellix Insights',
                                            'analyzerName': 'Trellix Insights'}
                            #helper.log_info("dev_response before=")
                            dev_response = get_device_details_using_keyvalue(iam_url,opt_api_gateway_url, opt_client_id,
                                                                             JSON_obj['client_secret'], JSON_obj['api_key'], proxy_settings,
                                                                             helper, "agentGuid", agent_guid)

                            #helper.log_info("dev_response after="+str(dev_response.text))
                            dev_details = json.loads(dev_response.text)
                            if len(dev_details['data']) != 0:
                                #helper.log_info("dev_response IF="+str(dev_details))
                                dev_list = dev_details['data']
                                for device in dev_list:

                                    dev_att = device['attributes']
                                    mac_old = dev_att['macAddress']
                                    mac_format = ':'.join(mac_old[i:i + 2] for i in range(0, 12, 2))
                                    insight_json.update(
                                        {'computerName': dev_att['computerName'], 'userName': dev_att['userName'],
                                         'macAddress': mac_format, 'ipAddress': dev_att['ipAddress'],
                                         'domainName': dev_att['domainName'], 'osType': dev_att['osType'],
                                         'eventId': 'Trellix Insights Event'})

                                count = count + 1

                                evt = helper.new_event(json.dumps(
                                    insight_json), time=None, host=None, index=None, source=None, sourcetype="TrellixDataSource", done=True, unbroken=True)
                                ew.write_event(evt)

                        '''Get the link to next page if pagination is present'''
                        next_page = result_json["links"]["next"]
                        param = next_page.split("?")[1]
                    except Exception as ex:
                        helper.log_info("###INSIGHTS POLLING ENDED###")
                        helper.log_info("@@@@@@@ EVENT INSIGHTS COUNT="+str(count))
                        helper.log_info("while parsing INSIGHTS from ePO for the input="+str(helper.input_name))
                        break
            else:
                helper.log_info("### Required(Insights) scope is not present for this Input="+str(response.text))
                break
        except Exception as ex:
            helper.log_info(ex)
            break


def collect_dlp_events(helper, ew,final_time_dt):
    # step 1
    APP = helper.get_app_name()
    PROXY_USERNAME = helper.get_arg('proxy_username', None)
    helper.collection_name = APP
    proxy_password = helper.get_arg('proxy_password', None)
    uri = helper.context_meta["server_uri"]
    session_key = helper.context_meta['session_key']
    helper.USERNAME = helper.get_arg('client_id')
    helper.ew = ew
    helper.max_past = _utcnow() - timedelta(hours=11, minutes=59)
    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.

    helper.nobody_client = client.connect(token=session_key, owner='nobody', app=APP, autologin=True)
    helper.admin_client = client.connect(token=session_key, autologin=True)
    opt_api_gateway_url = helper.get_arg('api_gateway_url')
    opt_client_id = helper.get_arg('client_id')

    opt_client_secret = helper.get_arg('client_secret')
    opt_api_key = helper.get_arg('api_key')
    iam_url = helper.get_arg('iam_url')
    audit_source = helper.get_arg('audit_source')

    # download_intervals(helper)

    kind, input_name = helper.input_name.split('://')
    proxy_password_storage_key = '_'.join([kind, input_name, str(PROXY_USERNAME)])

    data_name = helper.input_name.split('://')[1] + "``splunk_cred_sep``" + "1"

    CLEAR_PASSWORD = get_password(helper, data_name)
    JSON_obj = json.loads(CLEAR_PASSWORD)

    helper.get_input_type()
    # get the loglevel from the setup page
    loglevel = helper.get_log_level()
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()

    initial_time_dt = fmtdate(retrieve_saas_last_poll_time(helper))
    helper.log_debug("Trellix: DLP from initial_time_dt ===" + str(initial_time_dt))
    helper.log_debug("Trellix: DLP from final_time_dt ===" + str(final_time_dt))

    time_le = " and insertionTime<=" + final_time_dt +")"
    #time_le = " and utcTime<= 2025-08-13T05:02:08Z)"
    #time_le = time_le.replace(':', '%3A')
    time_gt = "filter=(insertionTime>=" + initial_time_dt
    #time_gt = "filter=(utcTime>= 2025-08-12T17:03:08Z"
    #time_gt = time_gt.replace(':', '%3A')

    attr_list = 'include=application,classificationMatches.classification,clipboard,cloud,collaboration,comments,device,email,endpoint,eventUser,evidence,iamRoleReviewer,iamUserReviewer,ndlpAppliance,networkComm,networkShare,policy,print,removableStorage,resolution,rules.ruleset,scan,status,webPost,justification'
    next_page_link = "page[limit]=500"
    filter="sort=insertionTime&"+ time_gt + time_le
    param = attr_list+ "&" +next_page_link + "&" + filter
    #param = attr_list+ "&" +next_page_link

    helper.log_info("Trellix: DLP from FLITER ===" + str(param))


    url = opt_api_gateway_url + '/dpim/v2/incident'

    count = 0
    helper.log_info("Trellix: POLLING Started for DLP Events")
    while True:
        try:
            scope = client_scope_dlp.strip()

            auth_token = dlp_obtain_bearer_token(helper, iam_url, opt_client_id,
                                                 JSON_obj['client_secret'], scope, proxy_settings)

            if hasattr(auth_token, 'status_code') and auth_token.status_code != 200:
                helper.log_info("###Credentials is invalid###")

            #decoded = jwt.decode(auth_token, options={"verify_signature": False})
            #helper.log_info("DECODED TENANT ID="+str(decoded))
            #tenant_id = decoded["tenant_id"]


            head = get_trelliX_headers(JSON_obj['api_key'], auth_token)
            # The following examples send rest requests to some endpoint.
            if proxy_settings:
                helper.log_info(f"Trellix: using proxy for {url} ")
                response = helper.send_http_request(url, 'GET', parameters=param, payload=None,
                                                    headers=head, cookies=None, verify=True, cert=None,
                                                    timeout=None, use_proxy=True)
            else:
                helper.log_info(f"Trellix: invoking {url} ")
                response = helper.send_http_request(url, 'GET', parameters=param, payload=None,
                                                    headers=head, cookies=None, verify=True, cert=None,
                                                    timeout=None, use_proxy=False)

            #helper.log_info(f"Trellix: DLP invoking {str(response)} ")
            if hasattr(response, 'status_code') and response.status_code == 200:
                my_data = response.json()
                result = json.dumps(my_data)
                if result is None:
                    helper.log_info("Trellix: DLP Error occurred while fetching from {url}")
                    raise Exception("Error occurred while fetching from {url}")
                else:
                    result_json = ''
                    try:
                        if not validateJSON(helper, result):
                            raise Exception("invalid json received from ")

                        result_json = json.loads(result)

                        data_json =''
                        #current_path_obj = "C:\\Program Files\\Splunk\\etc\\apps\\TA-trellix-epo-saas-connector\\bin\\dlp.json"
                        #with open(current_path_obj, "r", encoding="utf-8") as f:
                            #data_json = json.load(f)
                        #input = data_json["data"]
                        #helper.log_info("###POLLING DLP before ###size="+str(len(input)))
                        output = simplify_relationships(helper,result_json)
                        #helper.log_info("###POLLING DLP after###size="+str(len(output)))
                        # response = result_json["data"]
                        # response_inc = result_json["included"]
                        #
                        # for dlp_json in response:
                        #     count = count + 1
                        #
                        #     dlp_elog = dlp_json["attributes"]
                        #     dlp_elog.update({'id':dlp_json['id']})
                        #     helper.log_info("Trellix: DLP FINAL="+str(dlp_elog))
                        for dlp_json in output:
                            count = count + 1
                            data = helper.new_event(json.dumps(
                                dlp_json), time=None, host=None, index=None, source=None,
                                sourcetype="TrellixDLPIncident", done=True, unbroken=True)
                            ew.write_event(data)

                        '''Get the link to next page if pagination is present'''
                        next_page = result_json["links"]["next"]
                        param = next_page.split("?")[1]

                        #if len(response) == 0:
                        #    helper.log_info("Trellix: Sleeping to save API key usage for {url}")
                        # We have no items, so s
                        #    time.sleep(no_record_sleep_period_in_seconds)

                    except Exception as ex:
                        helper.log_info("###POLLING DLP ENDED###")
                        helper.log_info("Splunk Ingested count=" + str(count))
                        helper.log_info("while parsing events from DLP logs for the input=" + str(helper.input_name))
                        break
            else:
                helper.log_info("### Required(DLP) scope is not present for this Input="+str(response.text))
                break
        except Exception as ex:
            helper.log_info(ex)
            break

def simplify_relationships(helper,data_json):
    # Create lookup for included items

    try:

        #current_path_obj = "C:\\Program Files\\Splunk\\etc\\apps\\TA-trellix-epo-saas-connector\\bin\\dlp.json"
        #with open(current_path_obj, "r", encoding="utf-8") as f:
            #data_json = json.load(f)

        #helper.log_info("FILE==="+str(data_json))
        input = data_json["data"]
        helper.log_info("API Received count="+str(len(input)))
        included_lookup = {
            (item["id"], item["type"]): item
            for item in data_json.get("included", [])
        }

        # Map classificationMatch ID to classification attributes
        classification_match_to_classification = {}

        # Map rule ID to ruleset attributes
        rule_to_ruleset = {}

        for item in included_lookup.values():
            try:
                if item["type"] == "classificationMatch":
                    classification_rel = item.get("relationships", {}).get("classification", {}).get("data")
                    if classification_rel:
                        classification_id = classification_rel.get("id")
                        classification_type = classification_rel.get("type")
                        classification = included_lookup.get((classification_id, classification_type))
                        if classification:
                            classification_match_to_classification[item["id"]] = classification.get("attributes", {})

                if item["type"] == "rule":
                    ruleset_rel = item.get("relationships", {}).get("ruleset", {}).get("data")
                    if ruleset_rel:
                        ruleset_id = ruleset_rel.get("id")
                        ruleset_type = ruleset_rel.get("type")
                        ruleset = included_lookup.get((ruleset_id, ruleset_type))
                        if ruleset:
                            rule_to_ruleset[item["id"]] = ruleset.get("attributes", {})

            except Exception as ex:
                helper.log_info("ITEM="+str(item))
                helper.log_info(ex)

        # Process each data item
        simplified_data = []

        for item in data_json.get("data", []):
            try:
                simplified_item = {"id": item["id"]}

                for key, value in item.get("attributes", {}).items():
                    if value is not None:
                        simplified_item[key] = value

                relationships = item.get("relationships", {})
                for rel_key, rel_value in relationships.items():
                    rel_data = rel_value.get("data")

                    if not rel_data:
                        continue

                    if isinstance(rel_data, dict):
                        ref_id = rel_data.get("id")
                        ref_type = rel_data.get("type")
                        ref = included_lookup.get((ref_id, ref_type))
                        if ref:
                            for k, v in ref.get("attributes", {}).items():
                                if v is not None:
                                    simplified_item[f"{rel_key}_{k}"] = v

                    elif isinstance(rel_data, list):
                        for idx, rel_obj in enumerate(rel_data):
                            ref_id = rel_obj.get("id")
                            ref_type = rel_obj.get("type")
                            ref = included_lookup.get((ref_id, ref_type))
                            if ref:
                                for k, v in ref.get("attributes", {}).items():
                                    if v is not None:
                                        simplified_item[f"{rel_key}_{idx}_{k}"] = v

                            # Handle classificationMatch → classification
                            if rel_key == "classificationMatches" and ref_type == "classificationMatch":
                                classification_attrs = classification_match_to_classification.get(ref_id)
                                if classification_attrs:
                                    for k, v in classification_attrs.items():
                                        if v is not None:
                                            simplified_item[f"classification_{idx}_{k}"] = v

                            # Handle rule → ruleset
                            if rel_key == "rules" and ref_type == "rule":
                                ruleset_attrs = rule_to_ruleset.get(ref_id)
                                if ruleset_attrs:
                                    for k, v in ruleset_attrs.items():
                                        simplified_item[f"ruleset_{idx}_{k}"] = v

                simplified_data.append(simplified_item)
            except Exception as ex:
                helper.log_info("WORFLOW="+str(item["attributes"]["workflowId"]))
                helper.log_info(ex)

        helper.log_info("Processed Event count="+str(len(simplified_data)))
        return simplified_data

    except Exception as ex:
        helper.log_info(ex)

def collect_edr_events(helper, ew, final_time_dt):
    APP = helper.get_app_name()
    PROXY_USERNAME = helper.get_arg('proxy_username', None)
    helper.collection_name = APP
    proxy_password = helper.get_arg('proxy_password', None)
    uri = helper.context_meta["server_uri"]
    session_key = helper.context_meta['session_key']
    helper.USERNAME = helper.get_arg('client_id')
    helper.ew = ew
    helper.max_past = _utcnow() - timedelta(hours=11, minutes=59)

    helper.nobody_client = client.connect(token=session_key, owner='nobody', app=APP, autologin=True)
    helper.admin_client = client.connect(token=session_key, autologin=True)
    opt_api_gateway_url = helper.get_arg('api_gateway_url')
    opt_client_id = helper.get_arg('client_id')
    opt_client_secret = helper.get_arg('client_secret')
    opt_api_key = helper.get_arg('api_key')
    iam_url = helper.get_arg('iam_url')
    audit_source = helper.get_arg('audit_source')

    kind, input_name = helper.input_name.split('://')
    data_name = helper.input_name.split('://')[1] + "``splunk_cred_sep``" + "1"
    CLEAR_PASSWORD = get_password(helper, data_name)
    JSON_obj = json.loads(CLEAR_PASSWORD)

    helper.get_input_type()
    loglevel = helper.get_log_level()
    proxy_settings = helper.get_proxy()

    initial_time_dt = fmtdate(retrieve_saas_last_poll_time(helper))
    helper.log_debug("Trellix: EDR from initial_time_dt ===" + str(initial_time_dt))
    helper.log_debug("Trellix: EDR from final_time_dt ===" + str(final_time_dt))

    obj = datetime.strptime(final_time_dt, "%Y-%m-%dT%H:%M:%SZ")
    final_time_dt = obj.replace(tzinfo=timezone.utc)
    to_millis = int(final_time_dt.timestamp()) * 1000
    time_le = "&to=" + str(to_millis)

    obj = datetime.strptime(initial_time_dt, "%Y-%m-%dT%H:%M:%SZ")
    initial_time_dt = obj.replace(tzinfo=timezone.utc)
    from_millis = int(initial_time_dt.timestamp()) * 1000
    time_gt = "from=" + str(from_millis)

    filter_str = time_gt + time_le
    url = opt_api_gateway_url + '/edr/v2/threats'

    count = 0
    helper.log_info("Trellix: POLLING Started for EDR Events")
    page_limits = [20000]
    limit_index = 0

    while True:
        try:
            scope = client_scope_edr.strip()
            auth_token = obtain_bearer_token(helper, iam_url, opt_client_id,
                                             JSON_obj['client_secret'], scope, proxy_settings)

            if hasattr(auth_token, 'status_code') and auth_token.status_code != 200:
                helper.log_info("###Credentials is invalid###")

            head = get_trelliX_headers(JSON_obj['api_key'], auth_token)
            current_limit = page_limits[limit_index]
            param = f"page[limit]={current_limit}&{filter_str}"
            helper.log_info(f"Trellix: calling {url} with params={param}")

            if proxy_settings:
                response = helper.send_http_request(url, 'GET', parameters=param, payload=None,
                                                    headers=head, cookies=None, verify=True, cert=None,
                                                    timeout=15.0, use_proxy=True)
            else:
                response = helper.send_http_request(url, 'GET', parameters=param, payload=None,
                                                    headers=head, cookies=None, verify=True, cert=None,
                                                    timeout=15.0, use_proxy=False)

            if not hasattr(response, 'status_code') or response.status_code != 200:
                helper.log_info(f"Trellix: API returned {getattr(response, 'status_code','?')} {getattr(response, 'text','')}")
                limit_index += 1
                if limit_index >= len(page_limits):
                    helper.log_info("Trellix: All page limits failed. Stopping.")
                    break
                continue

            try:
                my_data = response.json()
            except Exception:
                helper.log_info("Trellix: Non-JSON response, stopping.")
                break

            if isinstance(my_data, dict) and my_data.get("message"):
                helper.log_info(f"Trellix: API error message: {my_data.get('message')}")
                limit_index += 1
                if limit_index >= len(page_limits):
                    break
                continue

            result_json = my_data
            for edr_json in result_json.get("data", []):
                count += 1
                threat_id = edr_json.get("id")
                aff_url = f"{opt_api_gateway_url}/edr/v2/threats/{threat_id}/detections"
                aff_param = "page[limit]=5000&"+filter_str

                try:
                    if proxy_settings:
                        response_aff = helper.send_http_request(aff_url, 'GET', parameters=aff_param, payload=None,
                                                                headers=head, cookies=None, verify=True, cert=None,
                                                                timeout=15.0, use_proxy=True)
                    else:
                        response_aff = helper.send_http_request(aff_url, 'GET', parameters=aff_param, payload=None,
                                                                headers=head, cookies=None, verify=True, cert=None,
                                                                timeout=15.0, use_proxy=False)
                    my_data_aff = response_aff.json()
                except Exception as ex:
                    helper.log_info(f"Trellix: Error fetching detections for {threat_id}: {ex}")
                    continue

                detection_data = my_data_aff.get("data", [])
                relationships = edr_json.get("relationships", {}).copy()
                relationships["detections"] = {"data": detection_data}
                threat_with_aff = edr_json.copy()
                threat_with_aff["relationships"] = relationships

                try:
                    simplified = edr_simplify_relationships({"data": [threat_with_aff]})
                    #helper.log_info("### Simplified EDR threat ###=" + str(simplified))
                    data = helper.new_event(json.dumps(simplified), time=None, host=None, index=None, source=None,
                                            sourcetype="TrellixEDRThreats", done=True, unbroken=True)
                    ew.write_event(data)
                except Exception as ex:
                    helper.log_info(f"Trellix: Error simplifying threat {threat_id}: {ex}")
                    continue

            helper.log_info("@@@@@@@ PROCESSED EDR COUNT=" + str(count))
            next_page = result_json.get("links", {}).get("next")
            if not next_page:
                break
            param = next_page.split("?")[1] if "?" in next_page else next_page

        except Exception as ex:
            helper.log_info(f"Trellix: Fatal error: {ex}")
            break


def edr_simplify_relationships(edr_data):
    """
    Simplify one threat object (expects {"data":[threat]}).
    Returns a single flattened dict, not an array.
    """
    threats = edr_data.get("data", [])
    if not threats:
        return {}

    threat = threats[0]
    base = {
        "id": threat.get("id"),
        **threat.get("attributes", {})
    }

    # Flatten top-level hashes
    hashes_obj = base.pop("hashes", {})
    for hk, hv in hashes_obj.items():
        base[f"hashes_{hk}"] = hv

    # Process detections
    detections = threat.get("relationships", {}).get("detections", {}).get("data", [])

    flattened_list = []
    edr_ui_url = base.get("edrUiUrl")

    for det_idx, detection in enumerate(detections):
        attributes = detection.get("attributes", {}) or {}
        trace_id = attributes.get("traceId")
        if edr_ui_url and trace_id:
            url = f"{edr_ui_url}?traceId={trace_id}"
        else:
            url = None  # or ""

        flat = {
            "id": detection.get("id"),
            "type": detection.get("type"),
            "url": url
        }


        # Flatten detection attributes
        for k, v in attributes.items():
            if k != "host":
                flat[k] = v

        # Flatten host info
        host = attributes.get("host", {}) or {}
        for hk, hv in host.items():
            if hk not in ("os", "netInterfaces"):
                flat[f"host_{hk}"] = hv

        # Flatten host OS info
        os_info = host.get("os", {}) or {}
        for ok, ov in os_info.items():
            flat[f"host_os_{ok}"] = ov

        # Flatten network interfaces
        net_interfaces = host.get("netInterfaces", []) or []
        for ni_idx, ni in enumerate(net_interfaces):
            for nk, nv in ni.items():
                flat[f"host_netInterface_{ni_idx}_{nk}"] = nv

        flattened_list.append(flat)


    for idx, flat in enumerate(flattened_list):
        for k, v in flat.items():
            base[f"detection_{idx}_{k}"] = v

    return base

    # # Process affectedhosts
    # affected_hosts = threat.get("relationships", {}).get("affectedhosts", {}).get("data", [])
    # for idx, host in enumerate(affected_hosts):
    #     host_attrs = host.get("attributes", {}) or {}
    #     for k, v in host_attrs.items():
    #         if k not in ("host", "hashes"):
    #             base[f"affected_host_{idx}_{k}"] = v
    #
    #     host_hashes = host_attrs.get("hashes", {}) or {}
    #     for hk, hv in host_hashes.items():
    #         base[f"hashes_{hk}"] = hv
    #
    #     host_obj = host_attrs.get("host", {}) or {}
    #     for hk, hv in host_obj.items():
    #         if hk not in ("os", "netInterfaces"):
    #             base[f"affected_host_{idx}_host_{hk}"] = hv
    #
    #     os_obj = host_obj.get("os", {}) or {}
    #     for ok, ov in os_obj.items():
    #         base[f"affected_host_{idx}_host_os_{ok}"] = ov
    #
    #     net_interfaces = host_obj.get("netInterfaces", []) or []
    #     for ni_idx, ni in enumerate(net_interfaces):
    #         for nk, nv in ni.items():
    #             base[f"affected_host_{idx}_netInterface_{ni_idx}_{nk}"] = nv
    #
    # return base

def get_device_details_using_keyvalue(iam_url,gateway_url,client_id,client_secret,api_key,proxy_settings,helper,key,value):
    try:

        scope = client_scope_device.strip()

        res_token = obtain_bearer_token(helper, iam_url, client_id,
                                        client_secret, scope, proxy_settings)

        #helper.log_info("Device details scope="+str(res_token))
        if hasattr(res_token, 'status_code') and res_token.status_code != 200:
            helper.log_info("###Credentials is invalid###")

        HEADERS = get_trelliX_headers(api_key, res_token)

        url = gateway_url+'/epo/v2/devices?filter['+key+']='+value

        if proxy_settings:
            #helper.log_info("INSIGHT PROXY TRUE=")
            response = helper.send_http_request(url, 'GET', parameters=None, payload=None,
                                                    headers=HEADERS, cookies=None, verify=True, cert=None,
                                                    timeout=None, use_proxy=True)
        else:
            #helper.log_info("INSIGHT PROXY FALSE")
            response = helper.send_http_request(url, 'GET', parameters=None, payload=None,
                                                    headers=HEADERS, cookies=None, verify=True, cert=None,
                                                    timeout=None, use_proxy=False)

        #helper.log_info("Device details response="+str(res_token.text))
        return response

    except Exception as ex:
        helper.log_info("Trellix :get_device_details_using_keyvalue : Error Occurred = "+str(ex))
        return ex

def validateJSON(helper,jsonData):
    try:
        json.loads(jsonData)
    except Exception as ex:
        helper.log_info("validateJSON="+str(jsonData))
        return False
    return True

def convert_ma_id_to_guidformat(gid):
    guid = gid[: 8] + "-" + gid[8:]
    guid = guid[: 13] + "-" + guid[13:]
    guid = guid[: 18] + "-" + guid[18:]
    guid = guid[: 23] + "-" + guid[23:]
    return guid


####### new code #############
def _utcnow():
    """
    Helper method which allows us to mock datetime.utcnow() responses in our test suite.
    Datetime is written in C code and apparently can't be mocked as a result. Who knew?

    :return datetime:
    """
    return datetime.now(dateutil.tz.tzutc())

def encrypt_password(self, username, password):
        """
        Saves a cleartext password into Splunk's secure password storage service

        :param str username: the username associated with the password
        :param str password: the cleartext password to encrypt
        :raise Exception: if any issue is encountered while communicating with the storage passwords service
        """
        try:
            for storage_password in self.admin_client.storage_passwords:
                if storage_password.username == username:
                    self.admin_client.storage_passwords.delete(
                        username=storage_password.username)
                    break
            self.admin_client.storage_passwords.create(password, username)
        except Exception as e:
            raise Exception(
                "{}: An error occurred updating credentials. Please ensure your user account has admin_all_objects"
                " and/or list_storage_passwords capabilities. Details: {}".format(self.input_name, e))

def mask_password(self, location):
    """
    Replaces a password configuration item with a masked version and re-saves the input definition

    :param str location:  the location of the password configuration item
    :raise Exception: if any error is encountered while saving inputs.conf
    """
    unsupported_keys = ['disabled', 'host_resolved', 'python.version']
    try:
        kind, input_name = self.input_name.split('://')
        for input_def in self.admin_client.inputs.list(kind):
            if input_def.name != input_name:
                continue
            new_input_content = input_def.content.copy()
            new_input_content[location] = self.MASK
            #new_input_content['start_by_shell'] = False
            for key in unsupported_keys:
                if key in new_input_content:
                    del new_input_content[key]
            new_input = input_def.update(**new_input_content)
            new_input.refresh()
            break
    except Exception as e:
        raise Exception('{}: Error updating inputs.conf: {}'.format(self.input_name, e))

def get_password(self, username):
    """
    Retrieves the cleartext password from Splunk's password storage service

    :param str username: the username corresponding to the password we want to retrieve
    :return str: the cleartext password
    :raise ValueError: if the username is not found in the password storage service
    """
    for storage_password in self.admin_client.storage_passwords:
        if storage_password.username == username:
            return storage_password.content.clear_password
    raise ValueError('{}: get_password/Could not find user record for {} in storage_passwords'.format(self.input_name, username))
def set_siem_url(self):
    """
    builds the appropriate URL and turns on or off SSL validation, based on settings,

    :return None:
    """
    self.VALIDATE_SSL = True if (self.SIEM_URL_HOST == self.SIEM_URL_DEFAULT_HOST) else False
    self.SIEM_URL = self.SIEM_URL_PROTOCOL + self.SIEM_URL_HOST + self.SIEM_URL_PATH + self.SIEM_URL_QUERY_PARAMS

def get_headers(self):
    """
    called when building the SIEM request, to set version information in the request header

    :return dict: contains the User-Agent string to user
    """
    ta_version = self.admin_client.apps[self.APP]['version']
    ta_user_agent = '{}/{}'.format(self.APP, ta_version)
    return {'User-Agent': ta_user_agent}

def retrieve_saas_last_poll_time(self):
    """
    Returns the last successful poll time from the Splunk KV store

    :return datetime: either the last poll time or the maximum time into the past which can be successfully queried
    """
    kv = self.nobody_client.kvstore[self.collection_name]
    self.log_debug("retrieve_last_poll_time="+str(self.input_name))
    query_args = {'query': '{{"input_name":"{}"}}'.format(self.input_name)}
    results = kv.data.query(**query_args)
    if len(results) == 0:
        self.log_debug("retrieve_last_poll_time IFIFIFIF")
        return retrieve_saas_old_poll_time(self)
    if len(results) > 1:
        raise ValueError(
            'retrieve_last_poll_time/When trying to retrieve the last poll time, '
            'multiple kvstore records were found which match {}'.format(self.input_name))
    self.input_kv_key = results[0]['_key']
    last_poll_time_s = results[0]['last_poll_time']
    last_poll_time_dt = dateutil.parser.parse(last_poll_time_s)
    if last_poll_time_dt < self.max_past:
        self.ew.log(self.ew.INFO, 'retrieve_last_poll_time/Previous poll time is too far in the past.'
                                    ' Returning maximum data available.')
        return self.max_past
    return last_poll_time_dt

def retrieve_saas_old_poll_time(self):
    """
    Older versions of the script stored the last poll time inside the collection schema, instead of the
    actual kv data store. Try to find the old poll value and delete the old collection, if found.

    :return datetime: either the last poll time or the maximum time into the past which can be successfully queried
    """

    import time
    if sys.version_info[0] < 3:
        import md5
        credhash = md5.new(self.USERNAME).hexdigest()
    else:
        import hashlib
        credhash = hashlib.md5(self.USERNAME.encode('utf-8')).hexdigest()

    field_name = 'field.{}'.format(credhash)
    old_collection_name = 'trellix_data_source'
    try:
        collection = self.nobody_client.kvstore[old_collection_name]
        self.ew.log(self.ew.INFO,"retrieve_old_poll_time=field_name="+str(field_name))
        self.ew.log(self.ew.INFO,"retrieve_old_poll_time=collection="+str(collection))
        self.ew.log(self.ew.INFO,"retrieve_old_poll_time="+str(field_name))
        last_poll_time_s = collection[field_name]
        last_poll_time_dt = dateutil.parser.parse(last_poll_time_s)
        if last_poll_time_dt.tzinfo is None:
            # The first statement attaches the local timezone to the naive date. The second converts to UTC.
            last_poll_time_dt = last_poll_time_dt.replace(tzinfo=dateutil.tz.tzoffset('', time.timezone * -1))
            last_poll_time_dt = last_poll_time_dt.astimezone(dateutil.tz.tzutc())
        collection.delete()
        if last_poll_time_dt < self.max_past:
            self.ew.log(self.ew.INFO, '{}: retrieve_last_poll_time/Previous poll time is too far in the past.'
                                        ' Returning maximum data available.'.format(self.input_name))
            return self.max_past
        return last_poll_time_dt
    except Exception as e:
        self.ew.log(self.ew.INFO, '{}: retrieve_last_poll_time/No previous poll results found: "{}"'
                                    ' Retrieving maximum data available.'.format(self.input_name, e))
        return self.max_past

def update_saas_last_poll_time(self, last_poll_time):
    """
    Updates the last successful poll time in the Splunk KV store.

    :param str last_poll_time: A string containing the last successful poll time
    """
    self.log_debug("update_last_poll_time="+str(self.input_name))
    self.log_debug("update_last_poll_time=input_kv_key="+str(self.input_kv_key))
    self.log_debug("update_last_poll_time=collection_name="+str(self.collection_name))
    data = json.dumps({'input_name': self.input_name, 'last_poll_time': last_poll_time})
    kv = self.nobody_client.kvstore[self.collection_name]
    if self.input_kv_key is None:
        result = kv.data.insert(data)
        self.input_kv_key = result['_key']
    else:
        kv.data.update(self.input_kv_key, data)

def retrieve_insights_last_poll_time(self):
    """
    Returns the last successful poll time from the Splunk KV store

    :return datetime: either the last poll time or the maximum time into the past which can be successfully queried
    """
    kv = self.nobody_client.kvstore[self.collection_name]
    self.log_debug("retrieve_last_poll_time="+str(self.input_name))
    query_args = {'query': '{{"input_name":"{}"}}'.format(self.input_name)}
    results = kv.data.query(**query_args)
    if len(results) == 0:
        self.log_debug("retrieve_last_poll_time IFIFIFIF")
        return retrieve_insights_old_poll_time(self)
    if len(results) > 1:
        raise ValueError(
            'retrieve_last_poll_time/When trying to retrieve the last poll time, '
            'multiple kvstore records were found which match {}'.format(self.input_name))
    self.input_kv_key = results[0]['_key']
    last_poll_time_s = results[0]['last_poll_time']
    last_poll_time_dt = dateutil.parser.parse(last_poll_time_s)
    if last_poll_time_dt < self.max_past:
        self.ew.log(self.ew.INFO, 'retrieve_last_poll_time/Previous poll time is too far in the past.'
                                  ' Returning maximum data available.')
        return self.max_past
    return last_poll_time_dt

def retrieve_insights_old_poll_time(self):
    """
    Older versions of the script stored the last poll time inside the collection schema, instead of the
    actual kv data store. Try to find the old poll value and delete the old collection, if found.

    :return datetime: either the last poll time or the maximum time into the past which can be successfully queried
    """

    import time
    if sys.version_info[0] < 3:
        import md5
        credhash = md5.new(self.USERNAME).hexdigest()
    else:
        import hashlib
        credhash = hashlib.md5(self.USERNAME.encode('utf-8')).hexdigest()

    field_name = 'field.{}'.format(credhash)
    old_collection_name = 'trellix_data_source'
    try:
        collection = self.nobody_client.kvstore[old_collection_name]
        self.log_debug("retrieve_old_poll_time="+str(field_name))
        last_poll_time_s = collection[field_name]
        last_poll_time_dt = dateutil.parser.parse(last_poll_time_s)
        if last_poll_time_dt.tzinfo is None:
            # The first statement attaches the local timezone to the naive date. The second converts to UTC.
            last_poll_time_dt = last_poll_time_dt.replace(tzinfo=dateutil.tz.tzoffset('', time.timezone * -1))
            last_poll_time_dt = last_poll_time_dt.astimezone(dateutil.tz.tzutc())
        collection.delete()
        if last_poll_time_dt < self.max_past:
            self.ew.log(self.ew.INFO, '{}: retrieve_last_poll_time/Previous poll time is too far in the past.'
                                      ' Returning maximum data available.'.format(self.input_name))
            return self.max_past
        return last_poll_time_dt
    except Exception as e:
        self.ew.log(self.ew.INFO, '{}: retrieve_last_poll_time/No previous poll results found: "{}"'
                                  ' Retrieving maximum data available.'.format(self.input_name, e))
        return self.max_past

def update_insights_last_poll_time(self, last_poll_time):
    """
    Updates the last successful poll time in the Splunk KV store.

    :param str last_poll_time: A string containing the last successful poll time
    """
    self.log_debug("update_last_poll_time="+str(self.input_name))
    self.log_debug("update_last_poll_time=input_kv_key="+str(self.input_kv_key))
    data = json.dumps({'input_name': self.input_name, 'last_poll_time': last_poll_time})
    kv = self.nobody_client.kvstore[self.collection_name]
    if self.input_kv_key is None:
        result = kv.data.insert(data)
        self.input_kv_key = result['_key']
    else:
        kv.data.update(self.input_kv_key, data)

'''def query_and_save(self, start_time_s, end_time_s):
    """
    Performs a single request to the TAP SIEM API, using any configured proxy. After a successful query, it updates
    the last successful poll time.

    :param datetime start_time_s: the start of the query interval (inclusive)
    :param datetime end_time_s: the end of the query interval (exclusive)
    """
    args = urllib.urlencode({'interval': '{}/{}'.format(start_time_s, end_time_s)})
    url = '{}&{}'.format(self.SIEM_URL, args)
    try:
        auth = (self.USERNAME, self.CLEAR_PASSWORD)
        proxies = self.get_proxies(self.PROXY_SERVER, self.PROXY_PORT, self.PROXY_USERNAME, self.PROXY_PASSWORD)
        headers = self.get_headers()
        resp = requests.get(url, auth=auth, proxies=proxies, headers=headers, verify=self.VALIDATE_SSL)
        if resp.status_code == 204:
            self.ew.log(self.ew.INFO,
                        '{}: query_and_save/Empty content returned from {} to {}'.format(self.input_name,
                                                                                            start_time_s, end_time_s))
        elif resp.status_code != 200:
            self.ew.log(self.ew.ERROR, '{}: query_and_save/Querying from {} to {}, but SIEM server returned: {} {}'
                        .format(self.input_name, start_time_s, end_time_s, resp.status_code, resp.reason))
            return
        self.ew.log(self.ew.INFO,
                    '{}: query_and_save/Successful query from {} to {}'.format(self.input_name, start_time_s,
                                                                                end_time_s))
        self.save_events(resp.json())
        update_last_poll_time(last_poll_time=end_time_s)
    except Exception as e:
        self.ew.log(self.ew.ERROR,
                    '{}: query_and_save/Could not query TAP URL- {} ({})'.format(self.input_name, url, e))
        sys.exit(1)'''

def save_events(self, data):
    """
    Processes a single content query's return value. Adds the eventType attribute to each event before logging it.

    :param dict data: a dictionary containing events to be logged
    """
    # Python's default isoformat uses +00:00 instead of Z, so replace it for consistency.
    default_event_time = re.sub('(?<=[0-9]{3})([0-9]{3})?\+00:00', 'Z', _utcnow().isoformat())
    for key in data.keys():
        if key in ['clicksBlocked', 'clicksPermitted', 'messagesBlocked',
                    'messagesDelivered']:
            evdata = data[key]
            for row in evdata:
                if 'eventType' not in row:
                    row.update({'eventType': key})
                if 'eventTime' not in row:
                    row.update({'eventTime': default_event_time})
                event = Event()
                event.stanza = self.input_name
                event.data = json.dumps(row)
                self.ew.write_event(event)


def download_intervals(self):
    """
    Sequentially initiates downloads of SIEM logs in tranches of one hour at a time.

    :return: None
    :raise ValueError: if the interval is too long, too short, or if the end is before the start
    """
    initial_time_dt ="" #retrieve_last_poll_time(self)
    final_time_dt = _utcnow()

    self.log_info("== *** initial Time date  == " + str(initial_time_dt))
    self.log_info("== *** final_time_dt Time date  == " + str(final_time_dt))

    if final_time_dt <= initial_time_dt:
        raise ValueError(
            '{}: download_intervals/End of interval must be after start of interval'.format(self.input_name))
    if (final_time_dt - initial_time_dt) > timedelta(hours=12):
        raise ValueError('{}: download_intervals/Interval cannot be greater than 12 hours'.format(self.input_name))
    hours, seconds = divmod(
        int((final_time_dt - initial_time_dt).total_seconds()), 3600)

    for hour in range(hours):
        start_secs_offset = (3600 * hour) + 1
        start_time_dt = initial_time_dt + timedelta(seconds=start_secs_offset)
        start_time_s = fmtdate(start_time_dt)
        end_secs_offset = start_secs_offset + 3599
        end_time_dt = initial_time_dt + timedelta(seconds=end_secs_offset)
        end_time_s = fmtdate(end_time_dt)
        #query_and_save(start_time_s, end_time_s)
        self.log_info("== *** Start Time == " + str(start_time_s))
        self.log_info("== *** End Time Time == " + str(end_time_s))
    # This is cheating, but if we have exactly one second left over, we'll end up having the same
    # start and end times, which the SIEM service will throw an error on. So, we'll tack on an
    # extra second, why not?
    if seconds > 0:
        if seconds == 1:
            seconds = 2
        start_secs_offset = (3600 * hours) + 1
        start_time_dt = initial_time_dt + timedelta(seconds=start_secs_offset)
        start_time_s = fmtdate(start_time_dt)
        end_secs_offset = start_secs_offset + seconds - 1
        end_time_dt = initial_time_dt + timedelta(seconds=end_secs_offset)
        end_time_s = fmtdate(end_time_dt)
        # The previous cheat should make this exception unreachable, but I'll leave it here for
        # when we solve the problem which makes the cheat necessary.
        if start_time_s == end_time_s:
            raise ValueError('{}: download_intervals/Cannot download a single second.'.format(self.input_name))
        #query_and_save(start_time_s, end_time_s)
        self.log_info("== *** Start Time == " + str(start_time_s))
        self.log_info("== *** End Time Time == " + str(end_time_s))


def fmtdate(ts):
    """
    Utility method to return UTC timestamps in ISO8601 format.

    :param ts datetime: a ``datetime`` object
    :return str: a string containing the ISO8601 formatted time in UTC
    """
    return ts.strftime('%Y-%m-%dT%H:%M:%SZ')

    # noinspection PyMethodMayBeStatic


def get_proxies(self, proxy_server=None, proxy_port=None, proxy_username=None, proxy_password=None):
    auth = ''
    port = ''
    if proxy_server is None:
        return {}
    if proxy_username is not None:
        auth = urllib.quote(proxy_username)
    if proxy_password is not None and auth != '':
        auth += ':' + urllib.quote(proxy_password)
    if auth != '':
        auth += '@'
    if proxy_port is not None:
        port = ':' + str(proxy_port)
    return {'https': 'https://' + auth + proxy_server + port}
