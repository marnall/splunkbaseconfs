# encoding = utf-8

import sys
import json
import logging
import requests
import traceback
from base64 import b64encode
from splunklib.modularinput import *
from urllib import parse


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    base_url = 'https://api.intel471.com'
    endpoint = '/v1/cve/reports'
    api_url = helper.get_arg('api_url')
    if not api_url:
        api_url = base_url + endpoint
    sort_param = 'earliest'
    count_param = 100
    params = '?sort=' + str(sort_param) + '&count=' + str(count_param)
    api_url = api_url + params

    api_user = helper.get_arg('global_account')['username']
    api_key = helper.get_arg('global_account')['password']
    enable_proxy = helper.get_arg('enable_proxy')

    session_key = helper.context_meta['session_key']
    server_uri = helper.context_meta['server_uri']

    request_count = 0
    offset_val = 0
    result = []
    proxy_dict = None
    response = None
    offset_check = False

    basic_auth_token = b64encode(
        bytes(str(api_user + ":" + api_key), "utf-8")
    ).decode("ascii")
    headers = {
        'Intel471-Authorization': 'Basic {}'.format(basic_auth_token)
    }
    try:
        logging.info('---Script run pull beginning---')
        if enable_proxy:
            proxy_settings = {
                'proxy_type': helper.get_arg('proxy_type'),
                'proxy_url': helper.get_arg('proxy_url'),
                'proxy_port': helper.get_arg('proxy_port'),
                'proxy_username': helper.get_arg('proxy_username'),
                'proxy_password': helper.get_arg('proxy_password')
            }
            proxy_dict = build_proxy_dict(proxy_settings)
            logging.info(
                "---Proxy: " + proxy_settings['proxy_url'] + ":" +
                proxy_settings['proxy_port'] + " is enabled.---"
            )
        else:
            logging.info("---Proxy is not enabled---")
        # ------ logic here ------ #
        logging.info('---Data pull beginning---')
        while True:
            last_updated_val = helper.get_check_point("checkpoint")
            log_checkpoint = 'Checkpoint:' + str(last_updated_val)
            if not last_updated_val:
                logging.info('---No saved previous checkpoint found. '
                             'First iteration probably---')
                first_iter = True
                #using SecureUserInputURLfunction to maintain a secure connection
                #implicilty using verify=false to support self-signed proxies
                response = requests.get(
                    SecureUserInputURL(api_url, server_uri, session_key),
                    headers=headers,
                    proxies=proxy_dict,
                    verify=False
                )
                request_count += 1
            else:
                first_iter = False
                if offset_check:
                    #using SecureUserInputURLfunction to maintain a secure connection
                    #implicilty using verify=false to support self-signed proxies
                    response = requests.get(
                        SecureUserInputURL(api_url + '&lastUpdatedFrom=' + str(last_updated_val) + "&offset=" + str(offset_val), server_uri, session_key),
                        headers=headers,
                        proxies=proxy_dict,
                        verify=False
                    )
                else:
                    #using SecureUserInputURLfunction to maintain a secure connection
                    #implicilty using verify=false to support self-signed proxies
                    response = requests.get(
                        SecureUserInputURL(api_url+'&lastUpdatedFrom='+str(last_updated_val), server_uri, session_key),
                        headers=headers,
                        proxies=proxy_dict,
                        verify=False
                    )
                request_count += 1
            if response.status_code in range(200, 300):
                helper.save_check_point("prev_checkpoint", last_updated_val)
                log_res_stats = 'STATUS:'+str(response.status_code)
                res_json = response.json()
                cve_count = res_json['cveReportsTotalCount']
                log_cve_count = 'CVE_COUNT:' + str(cve_count)
                if 'cveReports' not in res_json:
                    if offset_check:
                        last_updated_val += 1
                    logging.info('---0 reports returned in this iteration---')
                    logging.info('---Response---\n'+str(json.dumps(res_json)))
                    helper.save_check_point("checkpoint", last_updated_val)
                    break
                report_list = res_json['cveReports']
                report_count = len(report_list)
                log_report_count = 'REPORT_COUNT:'+str(report_count)
                first_report = report_list[0]
                last_report = report_list[-1]
                last_updated_val = last_report['last_updated']
                # logic to implement offset to API
                if first_report['last_updated'] == last_report['last_updated']:
                    offset_check = True
                    offset_val += 100
                    if offset_val == 1000:
                        last_updated_val = last_report['last_updated']+1
                        offset_check = False
                        offset_val = 0
                else:
                    offset_check = False
                    offset_val = 0
                # -- #
                if first_iter:
                    for entry in report_list:
                        result.append(entry)
                else:
                    for entry in report_list[1:]:
                        result.append(entry)
                # delete_check_point is for testing only, remove in production
                # helper.delete_check_point("checkpoint")
            else:
                logging.info('---Status code NOT in range:200,300---')
                helper.save_check_point("checkpoint", last_updated_val)
                raise_web_message(server_uri, session_key, response)
                break
            if cve_count == 1:
                logging.info('---All data pulled---')
                break
            if result:
                for res in result:
                    event = helper.new_event(
                        source=helper.get_input_type(),
                        index=helper.get_output_index(),
                        sourcetype=helper.get_sourcetype(),
                        data=json.dumps(res),
                    )
                    ew.write_event(event)
                log_eve_count = 'EVENTS_ADDED:' + str(len(result))
                result = []
                helper.save_check_point("checkpoint", last_updated_val)
                log_iter_count = 'ITER_COUNT:'+str(request_count)
                logging.info(
                    log_checkpoint + '|' + log_res_stats + '|'
                    + log_eve_count + '|' + log_iter_count + '|'
                    + log_cve_count + '|' + log_report_count + '|'
                )
                continue
            else:
                logging.info('---End of results---')
                helper.save_check_point("checkpoint", last_updated_val)
                break
        logging.info('---Data pull complete---')
    except requests.exceptions.InvalidURL:
        logging.info('---Provided URL is invalid')
        logging.info(traceback.format_exc())
        raise_web_message(server_uri, session_key, "InsecureURL")
    except:
        logging.info('---Something weird occurred---')
        logging.info(traceback.format_exc())
        if response:
            raise_web_message(server_uri, session_key, response)
        else:
            raise_web_message(server_uri, session_key)
    # ------ xx  xx  xx ------ #


def build_proxy_dict(proxy_settings):
    proxy_dict = None
    if proxy_settings:
        proxy_type = proxy_settings['proxy_type']
        if proxy_settings.get('proxy_username') and \
                proxy_settings.get('proxy_password'):
            proxy = '{proxy_type}://{user}:{password}@{host}:{port}'.format(
                proxy_type=proxy_type,
                user=proxy_settings['proxy_username'],
                password=proxy_settings['proxy_password'],
                host=proxy_settings['proxy_url'],
                port=proxy_settings['proxy_port'],
            )
        else:
            proxy = '{proxy_type}://{host}:{port}'.format(
                proxy_type=proxy_type,
                host=proxy_settings['proxy_url'],
                port=proxy_settings['proxy_port']
            )
        proxy_dict = {
            'http': proxy,
            'https': proxy
        }
    return proxy_dict


def raise_web_message(server_uri, session_key, response=None):
    if response == "InsecureURL":
        msg = 'Intel 471 Vulnerability Intelligence Add-on Data input failed to connect to API, ' \
          'This could be due to an Insecure/Malformed URL provided in Add-on input.' \
          'Please provide a secure URL or set URL as `https://api.intel471.com/v1/cve/reports` if unsure.'
    else:
        msg = 'Intel 471 Vulnerability Intelligence Add-on Data input failed to connect to API, ' \
          'This could be either due to use of invalid credentials in ' \
          'Add-on Configuration or connectivity issues or invalid Proxy Settings.'
    try:
        uri = server_uri + '/services/messages/new'
        headers = {'Authorization': 'Splunk ' + session_key}
        if response and response !="InsecureURL":
            msg += 'STATUS_CODE:' + str(response.status_code) + \
                   ', ERROR_MESSAGE: ' + str(response.text),
        data = {
            'name': 'Custom message from Intel 471 Vulnerability Intelligence Add-on',
            'value': msg,
            'severity': 'warn'
        }
        #Posting message to splunk Rest API on server URI by helper function, no need of SSL verification here.
        requests.post(uri, headers=headers, data=data, verify=False)
    except Exception as e:
        logging.info('---error in raise_web_message---')
        logging.info(e)
    sys.exit(msg)

def SecureUserInputURL(api_url, server_uri, session_key):
    try:
        parsed_url = parse.urlparse(api_url)
        if parsed_url.scheme != 'https':
            logging.info('api_url has http, replacing with https')
            url_components = (
                'https',
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                parsed_url.query,
                parsed_url.fragment
            )
            api_url = parse.urlunparse(url_components)
        else:
            logging.info('api_url has https and is already secure, no replace required')
        return api_url
    except Exception as e:
        logging.info('---URL maybe malformed, using default---')
        logging.info('Core desc : ' + str(e))
        logging.info('Full desc :\n' + str(traceback.format_exc()))
        raise_web_message(server_uri, session_key, response="InsecureURL")