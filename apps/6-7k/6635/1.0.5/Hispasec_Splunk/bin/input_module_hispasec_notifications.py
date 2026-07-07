# encoding = utf-8

import app_common as utils

import requests
from urllib.parse import urlparse
from datetime import datetime
from dateutil.parser import parse as date_parse
import json
import sys
import os

APP_VERSION = utils.get_version()

def iso_format(helper,obj):
    try:
        if 'created_at' in obj:
            obj['created_at'] = date_parse(obj['created_at']).isoformat()
        if 'updated_at' in obj:
            obj['updated_at'] = date_parse(obj['updated_at']).isoformat()
    except Exception as err:
        helper.log_error('[Hispasec API] field format error: %s'%(str(err)))

def validate_input(helper, definition):
    interval = definition.parameters.get('interval', None)
    if interval is not None and int(interval) < 10:
        raise ValueError('The minimum public API access interval cannot be less than 10 seconds')


def collect_events(helper, ew):
    hispa_id = []
    STANZA = helper.get_input_stanza_names()
    helper.log_info('[Hispasec API] get stanza names: %s'%(str(STANZA)))
    token = helper.get_global_setting('token')
    endpoint = helper.get_global_setting('endpoint')
    
    if (not token) or (not endpoint):
        helper.log_info('[Hispasec API] no valid config, will pass')
        return 0
        
    parse_url = urlparse(endpoint)
    endpoint = "{}://{}{}".format(parse_url.scheme, parse_url.netloc, parse_url.path)
    helper.log_info('[Hispasec API] get endpoint: %s'%(str(endpoint)))
    https_proxy = helper.get_global_setting('https_proxy')
    helper.log_info('[Hispasec API] get https_proxy: %s'%(https_proxy))
    backoff_time = float(helper.get_global_setting('backoff_time') or 10)
    helper.log_info('[Hispasec API] get backoff_time: %d'%(backoff_time))
    
    proxies = {}
    
    if not https_proxy is None:
        proxies['https'] = https_proxy
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Token '+token
        }
        
        hispa_id_input = 0
        hispa_id.append(hispa_id_input)
        file_context = utils.fetch_context(STANZA,{'hispasec_id': hispa_id_input})
        hispa_id_input = file_context.get('hispasec_id', hispa_id_input)
        request_help = utils.request_help(2,backoff_time)
        
        try:
            res = request_help(url=endpoint, method='GET', headers=headers, proxies=proxies)
            res.raise_for_status()
            json_obj=res.json()
            if 'error' in json_obj:
                helper.log_error('[Hispasec API] error in Hispasec API: %s'%(str(err)))
            info = json_obj['results']
            info = sorted(info, key=lambda k: k['id'], reverse=False)
            
            for alert in info:
                id = alert['id']
                hispa_id.append(id)
                if id > hispa_id_input:
                    iso_format(helper,alert)
                    event_data = json.dumps(alert)
                    event = helper.new_event(data=event_data, host=endpoint, index=helper.get_output_index(), source=helper.get_input_type(), sourcetype=helper.get_sourcetype(), done=True, unbroken=True)
                    ew.write_event(event)
        except requests.exceptions.HTTPError as err:
            helper.log_error('[Hispasec API] API request error: %s'%(str(err)))
            return 1
        except requests.exceptions.Timeout as err:
            helper.log_error('[Hispasec API] API request timeout error: %s'%(str(err)))
            return 1
        except Exception as err:
            helper.log_error('[Hispasec API] API exception: %s'%(str(err)))
            
        utils.update_context(STANZA,'hispasec_id',max(hispa_id))
        
    except RuntimeError as err:
        helper.log_error('[Hispasec API] unknown exception: %s'%(str(err)))
        
        
