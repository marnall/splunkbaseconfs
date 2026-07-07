import os
import sys
import time
import json

change_type_cat = {
    'admin_action/config_update' : 'Configuration Change',
    'admin_action/manual_reboot' : 'Manual Access Point Reboot',
    'admin_action/fw_upgrade' : 'Firmware Upgrade',
    'rrm_update/periodic-update' : 'Periodic Optimization',
    'rrm_update/interference_management' : 'Interference-based Adjustment',
    'rrm_update/automatic-channel-selection(device-reboot)' :  'Automatic Channel Selection'
}

mist_url = 'https://api.mist.com/api/v1'

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    org_id = helper.get_global_setting('organization_id')
    api_token = helper.get_global_setting('api_token')
    opt_limit = helper.get_arg('limit')
    opt_duration = helper.get_arg('duration')
    helper.set_log_level("info")
    helper.log_info("input type :- " + helper.get_input_type())
    filter_events = helper.get_arg('filter_events')
    stanza_name = helper.get_input_stanza_names()
    helper.log_info("stanza name:- " + stanza_name)
    source_type = helper.get_sourcetype()
    helper.log_info("source type:- " + source_type)

   # retrieve all sites related to this organization. User can add dynamic sites , so caching is not a good solution.
    try:
        mist_url_sites = mist_url + '/orgs/' + org_id + '/sites'

        response = helper.send_http_request(mist_url_sites, "GET", parameters={},
                                            payload=None,
                                            headers={
                                                'Content-Type': 'application/json',
                                                'Authorization': 'Token %s' % api_token
                                            },
                                            cookies=None, verify=True, cert=None,
                                            timeout=None, use_proxy=False)
        r_text = response.text
        site_details = json.loads(r_text)
        length = len(site_details)
        for site in site_details:
            param = {'limit': opt_limit, 'duration': opt_duration}
            next1 = getEvents(helper, ew, site, param, api_token, mist_url, filter_events)
            while (not (next1 is None)):
                next1 = getnextEvents(helper, ew, site, next1, filter_events, api_token)


    except Exception, err:
        helper.log_error(err)
    
def getEvents(helper, ew, site, param, api_token, mist_url, filter_events):
    site_name = site.get('name', None)
    site_id = site.get('id', None)
    mistsys_url = mist_url + '/sites/' + site_id + '/events/system'
    helper.log_info("url created :- " + mistsys_url)

    response = helper.send_http_request(mistsys_url, "GET", parameters=param,
                                        payload=None,
                                        headers={
                                            'Content-Type': 'application/json',
                                            'Authorization': 'Token %s' % api_token
                                        },
                                        cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
    r_text = response.text
    jsonObject = json.loads(r_text)
    results = jsonObject.get('results', None)

    for result in results:
        writeEvents(helper, ew, result, site_name, site_id, filter_events)

    return jsonObject.get('next', None)

def getnextEvents(helper, ew, site, next1, filter_events, api_token):
    try :
        site_name = site.get('name', None)
        site_id = site.get('id', None)
        response = helper.send_http_request('https://api.mist.com/'+ next1, "GET", 
                                            headers={
                                                'Content-Type': 'application/json',
                                                'Authorization': 'Token %s' % api_token
                                            },
                                            cookies=None, verify=True, cert=None,
                                            timeout=None, use_proxy=False )
        r_text = response.text
        jsonObject = json.loads(r_text)
        results = jsonObject.get('results', None)
        for result in results:
            writeEvents(helper, ew, result, site_name, site_id, filter_events)

        return jsonObject.get('next', None)
    except Exception , err :
        helper.log_error(str(err))


def writeEvents(helper, ew, result, site_name, site_id, filter_events):
    try :

        change = result.get('change_cat', None)
        if change == 'ap_health':
            return
        type_1 = result.get('type', None)
        timestamp = result.get('timestamp', None)

        metadata = json.loads(result.get('metadata'), None)

        key = str(site_id) + '_' + str(result.get('type', None)) + '-' + str(timestamp)
        result['metadata'] = metadata
        result['site_name'] = site_name
        result['site_id'] = site_id
        map_key = change + '/' + type_1
        result['description'] = change_type_cat.get(map_key, 'Not defined')
        jsonObject = json.dumps(result)

        flag = False
        if 'all' in filter_events :
            flag = True
        else :
            if result.get('description', None) in filter_events :
                flag = True
            else :
                if change in filter_events :
                    flag = True
        if (flag) :
           if helper.get_check_point(key) is None:
                event = helper.new_event(jsonObject, time=timestamp, index=helper.get_output_index(),
                                 sourcetype=helper.get_sourcetype(), done=True,
                                 unbroken=True)
                ew.write_event(event)
                helper.save_check_point(key, jsonObject)
    except Exception , err:
        helper.log_error(str(err))
