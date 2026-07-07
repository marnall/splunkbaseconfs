import base64
import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from aiohttp import ClientError

import vt_constants
import vt_mappings
from vt_service import get_api_key, get_proxy, get_fields_custom_prefix
from vt_exceptions import VTConfigException, VTAPIException, VTException
from vt_utils import build_report



async def make_request(splunk_service, session, endpoint, method, params):

    try:
        api_key = get_api_key(splunk_service)
    except Exception:
        raise VTConfigException("VirusTotal API key not configured or the list_all_passwords permission \
                        it's missing. Go to App to setup.")
    
    try:
        proxy = get_proxy(splunk_service)
    except Exception:
        raise VTConfigException("An error occurred loading proxy configuration")
    
    headers = {
        "Accept": "application/json", 
        "x-apikey": api_key
    }

    if endpoint == vt_constants.VT_API_V3_FILE_REPORT_ENDPOINT:
        url = f'{vt_constants.VT_API_V3}/{endpoint}/{params[vt_constants.COMMAND_OPTION_IOC_TYPE_HASH]}'
    elif endpoint == vt_constants.VT_API_V3_URL_REPORT_ENDPOINT:
        url_id = base64.urlsafe_b64encode(params[vt_constants.COMMAND_OPTION_IOC_TYPE_URL].encode()).decode().strip("=")
        url = f"{vt_constants.VT_API_V3}/{endpoint}/{url_id}"
    elif endpoint == vt_constants.VT_API_V3_DOMAIN_REPORT_ENDPOINT:
        url = f'{vt_constants.VT_API_V3}/{endpoint}/{params[vt_constants.COMMAND_OPTION_IOC_TYPE_DOMAIN]}'
    elif endpoint == vt_constants.VT_API_V3_IP_REPORT_ENDPOINT:
        url = f'{vt_constants.VT_API_V3}/{endpoint}/{params[vt_constants.COMMAND_OPTION_IOC_TYPE_IP]}'

    try:
        response = await session.request(
            method, url, headers=headers, proxy=proxy, ssl=True
        )
        return response
    except ClientError as e:
        raise VTException(f"An error occurred fetching data from VirusTotal: {e}")


async def handle_request_response(splunk_service, event, response, endpoint):
    status_code = response.status
    response_json = await response.json()
    

    if status_code == 200:
        data = response_json["data"]
        
        try:
            fields_custom_prefix = get_fields_custom_prefix(splunk_service)
        except Exception:
            raise VTConfigException("An error occurred loading the custom prefix configuration")

        if endpoint == vt_constants.VT_API_V3_FILE_REPORT_ENDPOINT:
            result = build_report(fields_custom_prefix, vt_mappings.FILE_REPORT_MAPPING, data)
        elif endpoint == vt_constants.VT_API_V3_URL_REPORT_ENDPOINT:
            result = build_report(fields_custom_prefix, vt_mappings.URL_REPORT_MAPPING, data)
        elif endpoint == vt_constants.VT_API_V3_DOMAIN_REPORT_ENDPOINT:
            result = build_report(fields_custom_prefix, vt_mappings.DOMAIN_REPORT_MAPPING, data)
        elif endpoint == vt_constants.VT_API_V3_IP_REPORT_ENDPOINT:
            result = build_report(fields_custom_prefix, vt_mappings.IP_REPORT_MAPPING, data)

        event.update(result)

    elif status_code >= 400 and status_code <= 499 and "error" in response_json:
        raise VTAPIException(response_json["error"]["message"], response_json["error"]["code"])
    else:
        response_text = await response.text()
        raise VTAPIException(f"HTTP {str(status_code)}" , response_text) 

    return event


async def make_file_report_request(splunk_service, event, session, params):
    endpoint = vt_constants.VT_API_V3_FILE_REPORT_ENDPOINT
    response = await make_request(splunk_service, session, endpoint, "GET", params)
    return await handle_request_response(splunk_service, event, response, endpoint)


async def make_url_report_request(splunk_service, event, session, params):
    endpoint = vt_constants.VT_API_V3_URL_REPORT_ENDPOINT
    response = await make_request(splunk_service, session, endpoint, "GET", params)
    return await handle_request_response(splunk_service, event, response, endpoint)


async def make_domain_report_request(splunk_service, event, session, params):
    endpoint = vt_constants.VT_API_V3_DOMAIN_REPORT_ENDPOINT
    response = await make_request(splunk_service, session, endpoint, "GET", params)
    return await handle_request_response(splunk_service, event, response, endpoint)


async def make_ip_report_request(splunk_service, event, session, params):
    endpoint = vt_constants.VT_API_V3_IP_REPORT_ENDPOINT
    response = await make_request(splunk_service, session, endpoint, "GET", params)
    return await handle_request_response(splunk_service, event, response, endpoint)
