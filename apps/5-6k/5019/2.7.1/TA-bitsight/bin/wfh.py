import import_declare_test  # noqa
import traceback
import sys

import splunklib.client as client
import splunk.Intersplunk
import json
import requests as req
import splunk.entity as entity
import bitsight_utils as utils
from setup_logger import setup_logging
import constants as const
from bitsight_exceptions import BitsightException
import splunk.version as v

logger = setup_logging("ta_bitsight_wfh")


def check_for_https(url):
    """Method to validate URL."""
    url_prefix = url.split(":")
    if url_prefix[0] == "http":
        url = url.replace("http", "https")
        return url
    elif url_prefix[0] == "https":
        return url
    else:
        return ""


def bitsight_api_call(request_url, api_credentials, headers, settings, req_params=None):
    """This function make API calls to the `BITSIGHT ENDPOINTS` and returns the response in json format."""
    request_url = check_for_https(request_url)
    session_key = str(settings.get('sessionKey'))
    proxies = utils.get_proxy_uri(session_key)
    api_key = api_credentials.get("api_key")
    if (request_url):
        response = req.get(url=request_url, auth=(api_key, ''),
                           params=req_params, headers=headers, proxies=proxies, verify=const.VERIFY_SSL)
        return response.json()


def get_ip_info(src_ip, api_credentials, settings):
    """This funtion creates url, headers and ip_info required for the API Call."""
    base_url = api_credentials.get('api_url')
    request_url = base_url + 'ratings/v1/findings/wfh/'
    headers = {
        'Accept': 'application/json',
        'X-BITSIGHT-CONNECTOR-NAME-VERSION': 'BitSight Security Performance Management for Splunk Add-On {}'.format(
            utils.get_app_version(settings.get('sessionKey'))),
        'X-BITSIGHT-CALLING-PLATFORM-VERSION': 'Splunk-Enterprise {}'.format(v.__version__)}
    PARAMS = {'ips': src_ip}
    res_list = bitsight_api_call(
        request_url, api_credentials, headers, settings, req_params=PARAMS)
    next_link = (res_list.get('links').get('next'))
    c_data = {}
    PARAMS['limit'] = 100
    PARAMS['offset'] = 100
    while next_link:
        c_data['next1'] = bitsight_api_call(next_link, api_credentials, headers, settings)
        next_link = (c_data['next1'].get('links').get('next'))
        res_list.get('results').extend(c_data['next1'].get('results'))
        PARAMS['offset'] = PARAMS['offset'] + 100
    return res_list


def get_data(wfh_li, api_credentials, settings):
    """Method to get data using BitSight API Token."""
    wfh_len = len(wfh_li)
    s = ','
    data = {'result': []}
    for i in range(0, wfh_len, 50):
        j = i + 50
        if (j > wfh_len):
            j = wfh_len
        s1 = s.join(wfh_li[i:j])
        wfh_data = get_ip_info(s1, api_credentials, settings)
        data.get('result').extend(wfh_data.get('results'))
    return data


def get_index(settings):
    """Method to get Index."""
    session_key = str(settings.get('sessionKey'))
    app_name = str(settings.get('namespace'))
    configs = entity.getEntities('/admin/conf-ta_bitsight_settings', namespace=app_name,
                                 sessionKey=session_key, owner='nobody')
    custom_command_index = str(configs.get('wfh', {}).get('custom_command_index'))
    return custom_command_index


def index_data(ls_ip, index, settings):
    """Method to index data."""
    session_key = str(settings.get('sessionKey'))
    app_name = str(settings.get('namespace'))
    server_settings = entity.getEntities(
        '/server/settings', sessionKey=session_key)
    mgmtport = server_settings['settings']['mgmtHostPort']
    splunk_service = client.connect(token=session_key, app=app_name, port=mgmtport)
    myindex = splunk_service.indexes[index]
    if (len(ls_ip) != 0):
        for i in ls_ip:
            i = json.dumps(i, sort_keys=True)
            myindex.submit(i, sourcetype="bitsight-wfh-ip",
                           host="bitsight_wfh")


def process_events(results, api_credentials):
    """Method to process events."""
    api_key = api_credentials.get("api_key")
    api_url = api_credentials.get("api_url")
    ls_ip = []
    if api_key is None:
        error_msg = "BitSight API Token not configured, go to Configuration > Authentication > Add BitSight API Token."
        results = [{"wfh_data": error_msg}]
        splunk.Intersplunk.outputResults(results)
        logger.error(error_msg)
        sys.exit(0)
    elif api_url is None:
        error_msg = "BitSight API URL not configured, go to Configuration > Authentication > Add BitSight API URL."
        results = [{"wfh_data": error_msg}]
        splunk.Intersplunk.outputResults(results)
        logger.error(error_msg)
        sys.exit(0)
    for result in results:
        if "src_ip" in result.keys():
            srcip = result["src_ip"]
            ls_ip.append(srcip)
    return ls_ip


if __name__ == "__main__":

    results, d_results, settings = splunk.Intersplunk.getOrganizedResults()
    session_key = str(settings.get('sessionKey'))
    api_credentials = utils.get_credentials(session_key)
    in_data = process_events(results, api_credentials)
    if (len(in_data) != 0):
        out_data = get_data(in_data, api_credentials, settings)
        is_data_found = out_data.get('result')
        if (len(is_data_found)) != 0:
            try:
                index = get_index(settings)
                if not index:
                    raise BitsightException("No configuration found for Custom Command Index. "
                                            "Please configure Custom Command Index "
                                            "by navigating to Configuration > Work From Home.")
                index_data(out_data['result'], index, settings)
                logger.info("Ingested data into index {}".format(index))
                out_result = [{'wfh_data': f} for f in (out_data['result'])]
                results = out_result
                logger.info("Indexed {} WFH events successfully.".format(len(is_data_found)))
                splunk.Intersplunk.outputResults(results)
            except KeyError:
                error_msg = "Configured Custom Command Index '{}' not found. " \
                            "Please make sure the index you have entered exists.".format(index)
                results = [{"wfh_data": error_msg}]
                splunk.Intersplunk.outputResults(results)
                logger.error(error_msg)
            except Exception as e:
                results = [{"wfh_data": "Error occured while collecting data {}".format(str(e))}]
                splunk.Intersplunk.outputResults(results)
                logger.error(traceback.format_exc())
        else:
            error_msg = "No Data Found for given IP Address(es)."
            results = [{"wfh_data": error_msg}]
            splunk.Intersplunk.outputResults(results)
            logger.error(error_msg)
    else:
        error_msg = "The search result does not contain src_ip field. Make sure you are running valid search."
        results = [{"wfh_data": error_msg}]
        splunk.Intersplunk.outputResults(results)
        logger.error(error_msg)
