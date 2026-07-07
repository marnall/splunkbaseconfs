
# encoding = utf-8

import os
import sys
import time
import datetime
import splunk.version as ver
import requests
import json
import traceback
import splunk.rest as rest
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

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # crits = definition.parameters.get('crits', None)
    # global_account = definition.parameters.get('global_account', None)
    # start_time = definition.parameters.get('start_time', None)
    pass

def collect_events(helper, ew):
    input_name = helper.get_input_stanza_names()
    dc_starting_time = time.time()
    helper.log_info(
        "Starting data collection for input {} at {}".format(
            input_name, dc_starting_time
        )
    )
    global_account = helper.get_arg("global_account")
    crits = helper.get_arg("crits")
    if not global_account:
        helper.log_error("Invalid global_account for input '{}'.".format(input_name))
        return

    username = global_account.get("username")
    password = global_account.get("password")
    url = global_account.get("url").rstrip("/")
    stanza_name = str(helper.get_input_stanza_names())
    # Data dictionary
    splunk_version = ver.__version__
    if not splunk_version:
        helper.log_error(
            "Evolven Error: unable to fetch splunk version."
        )
        return
    # To obtain session key
    session_key = helper.context_meta['session_key']
    proxy_settings = get_proxy(helper, session_key)
    sourcetype = "evolven:"+crits
    source = helper.get_input_type()

    headers = {
        'user': username,
        'pass': password
    }
    try:
        # Calling method for token generation.
        crits = helper.get_arg("crits")
        scope = helper.get_arg("scope")
        # helper.log_info("=============")
        # helper.log_info(f"{crits}")
        # helper.delete_check_point(crits)
        # helper.log_info("=============")
        if helper.get_check_point(crits):
            start_time = helper.get_check_point(crits).split("-----")[0]
            current_id = helper.get_check_point(crits).split("-----")[1]
        else:
            start_time = helper.get_arg("start_time")
            current_id = 0
        c_time = round(time.time() * 1000)
        if crits == "Certificates":
            endpoint = url + "/" + f"enlight.server/html/scripts/api/assets.jsp?action=table&globalCrit={crits}%20where%20Until%20%3E%20{start_time}%20AND%20Until%20%3C%20{c_time}&previousmaxId={current_id}&simple=true&json=true&envId={scope}"
        else:
            endpoint = url + "/" + f"enlight.server/html/scripts/api/assets.jsp?action=table&globalCrit=Evolven.{crits}%20where%20time%3E{start_time}%20AND%20time%20%3C%20{c_time}&previousmaxId={current_id}&simple=true&json=true&envId={scope}"
        helper.log_info(f"endpoint {endpoint}")
        response = requests.get(endpoint, headers=headers, proxies=proxy_settings)
        r = response.json()
        if "Table" in r.get("Next").keys():
            events = r.get("Next").get("Table").get("Rows").get("Row")
            if isinstance(events, list):
                for event in events:
                    current_id = event["AssetID"]
                    dumps_event = json.dumps(event, ensure_ascii=False)
                    final_event = helper.new_event(index=helper.get_output_index(),
                                sourcetype=sourcetype,
                                source=source,
                                data=dumps_event)
                    ew.write_event(final_event)
                    helper.save_check_point(crits, str(start_time)+"-----"+str(current_id))
            else:
                current_id = events["AssetID"]
                dumps_event = json.dumps(events, ensure_ascii=False)
                final_event = helper.new_event(index=helper.get_output_index(),
                            sourcetype=sourcetype,
                            source=source,
                            data=dumps_event)
                ew.write_event(final_event)
                helper.save_check_point(crits, str(start_time)+"-----"+str(current_id))
            previousmaxId = r.get("Next").get("MaxId")
            while r.get("Next").get("HasMore") == "true":
                if crits == "Certificates":
                    endpoint = url + "/" + f"enlight.server/html/scripts/api/assets.jsp?action=table&globalCrit={crits}%20where%20Until%20%3E%20{start_time}%20AND%20Until%20%3C%20{c_time}&previousmaxId={current_id}&simple=true&json=true&envId={scope}"
                else:
                    endpoint = url + "/" + f"enlight.server/html/scripts/api/assets.jsp?action=table&globalCrit=Evolven.{crits}%20where%20time%3E{start_time}%20AND%20time%20%3C%20{c_time}&previousmaxId={current_id}&simple=true&json=true&envId={scope}"
                helper.log_info(f"endpoint {endpoint}")
                response = requests.get(endpoint, headers=headers, proxies=proxy_settings)
                r = response.json()
                if "Table" in r.get("Next").keys():
                    events = r.get("Next").get("Table").get("Rows").get("Row")
                    if isinstance(events, list):
                        for event in events:
                            current_id = event["AssetID"]
                            dumps_event = json.dumps(event, ensure_ascii=False)
                            final_event = helper.new_event(index=helper.get_output_index(),
                                        sourcetype=sourcetype,
                                        source=source,
                                        data=dumps_event)
                            ew.write_event(final_event)
                            helper.save_check_point(crits, str(start_time)+"-----"+str(current_id))
                    else:
                        current_id = events["AssetID"]
                        dumps_event = json.dumps(events, ensure_ascii=False)
                        final_event = helper.new_event(index=helper.get_output_index(),
                                    sourcetype=sourcetype,
                                    source=source,
                                    data=dumps_event)
                        ew.write_event(final_event)
                        helper.save_check_point(crits, str(start_time)+"-----"+str(current_id))
                    previousmaxId = r.get("Next").get("MaxId")
            
            helper.save_check_point(crits, str(c_time)+"-----"+str(current_id))
        helper.log_info(
                "Data collection process is completed for input {}".format(input_name)
            )
        helper.log_info("Total time taken in data collection for input {} is {}".format(input_name, (time.time() - dc_starting_time)))
        return True
    except requests.exceptions.SSLError as e:
        helper.log_error("SSL certificate verification failed. Please add a valid "\
                         "SSL Certificate or Change VERIFY_SSL flag to False "\
                         "Error: {}".format(str(e)))
        helper.log_debug("Error Trace: {}".format(traceback.format_exc()))
        return False
    except requests.exceptions.ProxyError as e:
        helper.log_error("Please verify Proxy Configurations. "\
                         "Error: {}".format(str(e)))
        helper.log_debug("Error Trace: {}".format(traceback.format_exc()))
        return False
    except Exception as e:
        helper.log_error(
            "Evolven Error: Terminating the data collection unsuccessfully. "\
            "Error: {}".format(str(e)))
        helper.log_info("Error Trace: {}".format(traceback.format_exc()))
        return False

def get_proxy(helper,session_key):
    """
    Gives information of proxy if proxy is enable.
    :return: dictionary having proxy information
    """
    proxy_settings = None

    _, response_content = rest.simpleRequest(
        "/servicesNS/nobody/{}/configs/conf-ta_evolven_app_for_splunk_settings/proxy"
        .format("TA-evolven-app-for-splunk"),
        sessionKey=session_key,
        getargs={"output_mode": "json"},
        raiseAllErrors=True)
    proxy_info = json.loads(response_content)['entry'][0]['content']
    if int(proxy_info.get("proxy_enabled", 0)) == 0:
        return proxy_settings

    proxy_port = proxy_info.get('proxy_port')
    proxy_url = proxy_info.get('proxy_url')
    proxy_type = proxy_info.get('proxy_type')
    proxy_username = proxy_info.get('proxy_username', '')
    proxy_password = ''

    if proxy_username:
        try:
            __URL_FORMAT = "__REST_CREDENTIAL__#TA-evolven-app-for-splunk"\
                       "#configs/conf-ta_evolven_app_for_splunk_settings"\
                       ":proxy``splunk_cred_sep``1:"
            __URL_ENCODE = requests.compat.quote_plus(__URL_FORMAT)
            _, response_content = rest.simpleRequest(
                "/servicesNS/nobody/{}/storage/passwords/".format("TA-evolven-app-for-splunk") + __URL_ENCODE,
                sessionKey=session_key,
                getargs={"output_mode": "json"},
                raiseAllErrors=True)
            response_dict = json.loads(
                response_content)['entry'][0]['content']
            cred = json.loads(response_dict.get('clear_password', '{}'))
            proxy_password = cred.get("proxy_password", None)
        except Exception as e:
            helper.log_error("Error While fetching proxy \n Error: {}".format(str(e)))
    proxy_settings = get_proxy_setting(proxy_type, proxy_username,
                                            proxy_password, proxy_url,
                                            proxy_port)
    return proxy_settings

def get_proxy_setting(proxy_type, proxy_username, proxy_password,
                        proxy_url, proxy_port):
    """Function To get Proxy Setting."""
    if proxy_username and proxy_password:
        proxy_username = requests.compat.quote_plus(proxy_username)
        proxy_password = requests.compat.quote_plus(proxy_password)
        proxy_uri = "%s://%s:%s@%s:%s" % (proxy_type, proxy_username,
                                            proxy_password, proxy_url,
                                            proxy_port)
    else:
        proxy_uri = "%s://%s:%s" % (proxy_type, proxy_url, proxy_port)
    proxy_settings = {"http": proxy_uri, "https": proxy_uri}

    return proxy_settings
