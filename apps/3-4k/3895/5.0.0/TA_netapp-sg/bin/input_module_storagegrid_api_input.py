# Copyright (c) 2022 NetApp, Inc., All Rights Reserved

from __future__ import division
from __future__ import absolute_import


import os
import sys
import time
import datetime
import numbers
import json
import traceback
from threading import Thread
import six
import traceback
import uuid
from six.moves import queue
from six.moves import range
from six.moves.urllib import parse
import splunk.clilib.cli_common as scc
import splunk.rest as rest
from splunk_aoblib.setup_util import Setup_Util
from solnlib import conf_manager
from solnlib.utils import is_true
from netapp_sso_token import AzureSSOToken
from netapp_utils import get_proxy_setting
from requests.exceptions import HTTPError

APP_NAME = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONF_FILE_NAME = "ta_netapp_sg_settings"
STANZA = "ta_netapp_sg_account"
GLOBAL_CERT_VERIFY = True
KV_COLLECTION_NAME = "storagegrid_product_version"

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

def old_div(a, b):
    """
    Equivalent to ``a / b`` on Python 2 without ``from __future__ import
    division``.

    TODO: generalize this to other objects (like arrays etc.)
    """
    if isinstance(a, numbers.Integral) and isinstance(b, numbers.Integral):
        return a // b
    else:
        return a / b

def raise_for_status(response):
    """
    If the response status is not between [200, 300), raise the exception
    :param response: response of a request
    """
    if not(200 <= response.status_code < 300):
        message = response.json().get('message', dict()).get('text') or response.text
        raise HTTPError(message)

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # netapp_storagegrid_account = definition.parameters.get('netapp_storagegrid_account', None)
    pass

def read_conf_file(session_key, conf_file, stanza=None):
    """
    Get conf file content with conf_manager
    :param session_key: Splunk session key
    :param conf_file: conf file name
    :param stanza: If stanza name is present then return only that stanza, otherwise return all stanza
    """
    conf_file = conf_manager.ConfManager(session_key, APP_NAME, realm='__REST_CREDENTIAL__#{}#configs/conf-{}'.format(APP_NAME, conf_file)).get_conf(conf_file)
    if stanza:
        return conf_file.get(stanza)
    return conf_file.get_all()


def update_cert_verify(helper):
    """
    Read the values for SSL check from conf files and change the global variable "GLOBAL_CERT_VERIFY".
    :param helper: Instance of Splunk Base Modular input class which contains all metadata of splunk instance.
    """
    global GLOBAL_CERT_VERIFY
    session_key_of_splunk = helper.context_meta['session_key']
    content_from_conf = read_conf_file(session_key_of_splunk,'ta_netapp_sg_settings','additional_parameters')
    GLOBAL_CERT_VERIFY = True if is_true(str(content_from_conf['cert_verify']) ) else False

def find_product_version(helper, base_url, headers):
    """
    Get the NetApp StorageGRID product version and write it to KV Store
    :param helper: Instance of Splunk Base Modular input class which contains all metadata of splunk instance.
    :param base_url: base URL
    :param headers: request header
    """
    # Get product version by rest call
    helper.log_debug("Getting StorageGRID product version.")
    response = helper.send_http_request(str.format("%s/grid/config/product-version"%(str(base_url))), "GET", headers=headers, verify=GLOBAL_CERT_VERIFY)

    # Sample productVersion of StorageGRID from response: 11.4.0.3-20210122.0127.a27f960
    product_version = response.json().get('data').get('productVersion')
    product_version = product_version.split('.')[:2]
    product_version = float('.'.join(product_version))
    helper.log_debug("Product version found: {}".format(product_version))

    # write product version to kv store
    helper.log_debug("Writing product version to KV Store with collection: {}".format(KV_COLLECTION_NAME))
    splunkd_uri = helper.context_meta['server_uri']
    session_key_of_splunk = helper.context_meta['session_key']
    kv_log_info = [{'product_version': product_version, '_key': APP_NAME}]

    kv_update_url = "{}/servicesNS/nobody/{}/storage/collections/data/{}/batch_save".format(
        splunkd_uri,
        APP_NAME,
        KV_COLLECTION_NAME,
    )
    response, _ = rest.simpleRequest(
        kv_update_url,
        sessionKey=session_key_of_splunk,
        jsonargs=json.dumps(kv_log_info),
        method="POST",
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )

    if response.status in {200, 201}:
        helper.log_info("KV Store updated successfully.")
    else:
        helper.log_error("Error occurred while updating KV Store.")

    return product_version

def collect_events(helper, ew):
    try:
        update_cert_verify(helper)
        StorageGRID_system = helper.get_arg("StorageGRID_system")
        if not StorageGRID_system:
            helper.log_error("Invalid StorageGRID_system for input '{}'.".format(helper.get_arg("name")))
            return

        parameters,base_url,prometheus_url = getstoragegrid_parameter(helper, StorageGRID_system)
        headers={}
        headers['Content-Type'] = "application/json"
        headers['Accept'] = "application/json"
        authtoken = ""
        proxy_settings = get_proxy_setting(helper.get_proxy())
        
        if proxy_settings['http']:
            helper.log_info("Proxy is enabled.")
        
        helper.log_debug("ssl certificate verify={}".format(str(GLOBAL_CERT_VERIFY)))
        
        if StorageGRID_system.get('auth_type') == "azure":
            azure_sso = AzureSSOToken(
                StorageGRID_system.get('account_ip'),
                StorageGRID_system.get('username'),
                StorageGRID_system.get('password'),
                helper,
                proxy_settings,
                GLOBAL_CERT_VERIFY,
            )
            token = azure_sso.get_sso_auth_token()
            authtoken = token["auth_token"]
        else:
            response = helper.send_http_request(str.format("%s/authorize"%(str(base_url))), "POST", parameters=None, payload=parameters,headers=headers, cookies=None, verify=GLOBAL_CERT_VERIFY,timeout=None)
            raise_for_status(response)
            authtoken = response.json()['data']

        helper.log_debug("Authenticated to the REST API")
        headers["Authorization"] = str.format("Bearer %s"%(str(authtoken)))
        source_name=str(helper.get_arg('source_name'))
        helper.log_debug("Source Name: "+str(helper.get_arg('source_name')))

        if source_name == str(None):
            source_name='storagegrid_api_input'
        product_version = find_product_version(helper, base_url, headers)
        api_calls_threaded(helper,ew,base_url,prometheus_url,headers,source_name, product_version)
    except Exception as e : 
        helper.log_error("Error in calling authentication api. Message=%s\n%s" % (str(e), traceback.format_exc()))


def find_api_version(helper, webscale_url):
    """
    This method will return the major version of API in given webscale.
    :param helper: Instance of Splunk Base Modular input class which contains all metadata of splunk instance.
    :param webscale_url: url of webscale
    """
    try:
        version_url = str.format("https://%s/api/versions"%(str(webscale_url)))
        response = helper.send_http_request(version_url, "GET", verify=GLOBAL_CERT_VERIFY)
        return int(float(response.json()['apiVersion']))
    except Exception as e:
        helper.log_error("Error in calling version check api. Message = %s"%(str(e)))


def fetch_interval_of_data_input(helper):
    """
    This method will return string of interval for active data input configured by user.
    :param helper: Instance of Splunk Base Modular input class which contains all metadata of splunk instance.
    """
    try:
        active_input = helper.get_input_stanza()
        key = list(active_input.keys())
        details_of_active_input = helper.get_input_stanza(str(key[0]))
        interval = details_of_active_input['interval']
        interval = min(int(interval),86400)
        interval_in_string = str.format("%ss"%(str(interval)))
        return interval_in_string
    except Exception as e:
        helper.log_error("Error while fetching interval of active input. Message=%s\n%s" % (str(e), traceback.format_exc()))


def replace_delta_time(endpoint, interval):
    """
    This method will replace "DELTA_TIME" string with given interval in parameter.
    :param endpoint: Endpoint in which string will be replaced.
    :param intervaal: Interval which is placed instead of "DELTA_TIME".
    """
    return endpoint.replace("DELTA_TIME",interval)


def getstoragegrid_parameter(helper, StorageGRID_system):
    """
    This function fetches username and password from the global settings that are configured.
    Also this function sets base url and the prometheus url format.
    :param helper: Instance of Splunk Base Modular input class which contains all metadata of splunk instance.
    """
    parameters={}
    url = StorageGRID_system.get('account_ip')
    parameters['username'] =StorageGRID_system.get('username')
    parameters['password'] = StorageGRID_system.get('password')
    parameters['cookie'] = True
    parameters['csrfToken'] = True
    version_check = find_api_version(helper, url)
    api_version = str.format("v%s"%(str(version_check)))
    helper.log_debug("Rest API version={}".format(api_version))
    base_url = str.format("https://%s/api/%s"%(str(url), api_version))
    prometheus_url =str.format("https://%s/api/%s/query?query="%(str(url), api_version))
    return parameters,base_url,prometheus_url


def url_calls(helper,ew,queue,headers,source_name):
    """
    Function to make HTTP GET calls to the URLs fetched from filename management api and private api.
    Threading concurrency:
        For concurrency among the threads that would call this function, we use a queue.
        URL names are kept in a queue. Each of the concurrent thread try to fetch one URL at a time (for each loop) from the queue and make the URL call.
        Once the Queue is empty, all the thread begin to quit.
        The fetched GET request is then written as a new event.
    :param helper: Helper function provided by Splunk
    :param ew: Event Writer, writes event into the indexer.
    :param queue: The shared queue among all the threads
    :param url: URL to be fetched from queue
    :param response: HTTP response from the API
    """
    while True:
        try:
            if(queue.empty()):
                helper.log_debug('Queue is empty, thread breaks here')
                break
            endpoint_dict = queue.get()
            url = endpoint_dict['url']
            endpoint = endpoint_dict['endpoint']
            data_results = []
            if endpoint == "Accounts":
                data_results = handle_accounts(helper, url, headers)
            else:
                data_results = handle_other_endpoints(helper, url, endpoint, headers)
            ingest_count = 0
            if type(data_results) == list:
                ingest_count = process_list(helper, url, ew, endpoint, headers, source_name, data_results, ingest_count)
            else:
                ingest_count = process_result_list(helper, ew, endpoint, source_name, data_results, ingest_count)

            sys.stdout.flush()
            helper.log_info("Count={} Events ingested for endpoint={}".format(ingest_count, endpoint))
            queue.task_done()
        except Exception as e :
            helper.log_error("Error in calling api. Message=%s\n%s" % (str(e), traceback.format_exc()))  
            queue.task_done()

def handle_accounts(helper, url, headers):
    params = {
                "limit": 100,
                "includeMarker": "true",
                "order": "asc" 
            }
    data_results = []
    while True:
        helper.log_debug("Calling Account endpoint through markers")
        response = helper.send_http_request(url, "GET", parameters=params, payload=None,headers=headers, cookies=None, verify=GLOBAL_CERT_VERIFY,timeout=None)
        if old_div(int(response.status_code),100) == 4 or old_div(int(response.status_code),100) == 5:
            queue.task_done()
            raise_for_status(response)
            break                    
        account_results = response.json()['data']
        result_length = len(account_results)
        helper.log_debug("Account endpoint: Got {} accounts.".format(result_length))
        if result_length <= 1:
            break
        account_id = str(account_results[result_length-1]['id'])
        params["marker"] = account_id
        data_results += account_results
    return data_results

def handle_other_endpoints(helper, url, endpoint, headers):
    helper.log_debug("Requesting endpoint={}".format(endpoint))
    data_results = []
    response = helper.send_http_request(url, "GET", parameters=None, payload=None,headers=headers, cookies=None, verify=GLOBAL_CERT_VERIFY,timeout=None)
    if old_div(int(response.status_code),100) == 4 or old_div(int(response.status_code),100) == 5:
        queue.task_done()
    raise_for_status(response)
    data_results = response.json()['data']
    return data_results

def process_list(helper, url, ew, endpoint, headers, source_name, data_results, ingest_count):
    if endpoint=='Accounts':
        mark_true = {}
        for account in data_results:
            account_id = account['id']
            account_name = account['name']
            if mark_true.get(account_id):
                continue
            else:
                mark_true[account_id] = True
            response_account = helper.send_http_request(url+'/'+account_id+'/usage', "GET", parameters=None, payload=None,headers=headers, cookies=None, verify=GLOBAL_CERT_VERIFY,timeout=None)
            if old_div(int(response_account.status_code),100) == 4 or old_div(int(response_account.status_code),100) == 5:
                queue.task_done()
            raise_for_status(response_account)
            account_data = response_account.json()['data']
            endpoint= 'Account_Usage'
            account_data.update({'endpoint':endpoint})
            account_data.update({'id':account_id})
            account_data.update({'name':account_name})
            write_event_data(account_data,ew,helper,source_name)
            ingest_count += 1
        helper.log_debug("Total Accounts: " + str(len(mark_true)))
    else:
        for result in data_results:
            result.update({'endpoint': endpoint})
            write_event_data(result,ew,helper,source_name)
            ingest_count += 1
    return ingest_count

def process_result_list(helper, ew, endpoint, source_name, data_results, ingest_count):
    if 'result' in data_results:
        results = data_results['result']
        for singleresult in results:
            new_result = json.loads('{}')
            new_result.update({'endpoint':endpoint})
            new_result.update({'result': singleresult})
            new_result.update({'resultType':  data_results['resultType']})
            write_event_data(new_result,ew,helper,source_name)
            ingest_count += 1
    else:
        if endpoint in ["Health_topology_depth_node", "Health_topology_depth_component"]:
            execution_id = str(uuid.uuid4())
            for each_result in get_topology_events(data_results, dict()):
                each_result["executionID"] = execution_id
                each_result.update({'endpoint': endpoint})
                write_event_data(each_result,ew,helper,source_name)
                ingest_count += 1
        else:
            data_results.update({'endpoint': endpoint})
            write_event_data(data_results,ew,helper,source_name)
            ingest_count += 1
    return ingest_count

def get_topology_events(result, output):
    """
    Convert nested list of dictionaries to list of dictionaries.
    The method flattens the array of dictionaries 
    Example: 
    FROM {
        param_1: value_1,
        childeren: [
            {param_2: child_1},
            {param_2: child_2}
        ]
    } TO [{
        param_1: value_1,
        child: {
            param_2: child_1
        }
    }, {
        param_1: value_1,
        child: {
            param_2: child_2
        }
    }]
    """
    for each_param in result:
        if each_param != "children":
            output[each_param] = result[each_param]
    if "children" in result:
        for each_child in result[each_param]:
            for each_output in get_topology_events(each_child, {}):
                child_output = output.copy()
                child_output["child"] = each_output
                yield child_output
    else:
        yield output

def write_event_data(data,ew,helper,source_name):
    """
    Data which is passed to the function will be written as events in the system
    :param data: content for events
    :param ew: event writer
    :param helper: Instance of Splunk Base Modular input class which contains all metadata of splunk instance.
    """

    helper.log_debug("Add Account Name '{}' in the event. ".format(helper.get_arg("StorageGRID_system")["name"]))
    data['StorageGRID_system'] = helper.get_arg("StorageGRID_system")["name"]
    modified_data=json.dumps(data, ensure_ascii=False)

    event = helper.new_event(source=source_name, index=helper.get_output_index(), sourcetype='grid:rest:api', data=modified_data)
    ew.write_event(event)


def api_calls_threaded(helper,ew,base_url,prometheus_url,headers,source_name, product_version):
    """
    In order to fetch data from multiple URLs, we use a multi-threaded approach. 
    So here we make five concurrent daemon threads and each thread fetches URL from the queue and 
    then makes a HTTP GET call. Queue contains the URL list.
    In this function a queue is initialized, 5 concurrent threads are initialized. 
    Once the queue gets finished all the threads finish the work and return back to the main thread.
    :param helper: Instance of Splunk Base Modular input class which contains all metadata of splunk instance.
    :param ew: event writer
    :param base_url: base url
    :param prometheus_url: prometheus url
    :param headers: headers to be appended in URL call
    """
    try:
        qu=queue.Queue()
        num_of_concurrent_threads = 5
        dir_path = os.path.dirname(os.path.realpath(__file__))
        data = json.load(open(dir_path+'/api.json'))
        interval = fetch_interval_of_data_input(helper)

        # Adding all endpoints of different StorageGrid versions in queue to collect the data
        for endpoint in data['mgmt_api']['common']['endpoints'] :
            url = str.format("%s%s"%(base_url, str(endpoint['url'])))
            endpoint['url'] = url
            qu.put(endpoint)

        for endpoint in data['private_api']['common']['endpoints'] :
            url = replace_delta_time(str(endpoint['url']), interval)
            url = str.format("%s%s"%(prometheus_url, parse.quote_plus(str(url))))
            endpoint['url'] = url
            qu.put(endpoint)

        if product_version <= 11.3:
            version_key = "<=11.3"
        else:
            version_key = ">=11.4"
                
        # Few endpoint fields are changed in StorageGrid v11.4 and above.
        # Adding endpoints in the Queue based on StorageGrid versions to collect the data
        for endpoint in data['mgmt_api'][version_key]['endpoints'] :
            url = str.format("%s%s"%(base_url, str(endpoint['url'])))
            endpoint['url'] = url
            qu.put(endpoint)

        for endpoint in data['private_api'][version_key]['endpoints'] :
            url = replace_delta_time(str(endpoint['url']), interval)
            url = str.format("%s%s"%(prometheus_url, parse.quote_plus(str(url))))
            endpoint['url'] = url
            qu.put(endpoint)

        for _ in range(num_of_concurrent_threads):
            fetch_thread = Thread(target=url_calls,args=(helper,ew,qu,headers,source_name))
            fetch_thread.daemon = True
            fetch_thread.start()
    
        qu.join()
    except Exception as e:
        helper.log_error("Error in threading. Message=%s \n%s" % (str(e), traceback.format_exc()))
        
        