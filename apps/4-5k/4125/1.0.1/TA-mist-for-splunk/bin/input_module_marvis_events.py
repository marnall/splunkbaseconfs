import os
import sys
import time
import datetime
import json

type_1 = { 'ap-down': 'AP is Down',
    'excessive-auth-failures': 'Client Auth Failures',
    'dns-down': 'DNS is Down',
    'dhcp-down': 'DHCP is Unresponsive',
    'interference': 'Interference',
    'l2tp-tunnel-down': 'L2TP tunnel is Down'
    }

r_code = {
    'CLOUD-CONNECTION-LOSS': 'Cloud Inaccessible',
    'AP-REBOOT': 'Reboot'
}

severity_1 = { 100 : 'critical'}

mist_url = 'https://api.mist.com/api/v1'

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    org_id = helper.get_global_setting('organization_id')
    api_token = helper.get_global_setting('api_token')
    opt_acked = helper.get_arg('acked')
    opt_resolved = helper.get_arg('resolved')
    opt_limit = helper.get_arg('limit')
    opt_duration = helper.get_arg('duration')

    helper.set_log_level("info")
    helper.log_info("input type :- " + helper.get_input_type())
    stanza_name = helper.get_input_stanza_names()
    helper.log_info("stanza name:- " + stanza_name)
    source_type = helper.get_sourcetype()
    helper.log_info("source type:- " + source_type)

    # retrieve all sites related to this organization.
    try :
        mist_url_sites = mist_url + '/orgs/'  + org_id + '/sites'
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
            param = {'limit': opt_limit, 'duration': opt_duration, 'acked': opt_acked, 'resolved': opt_resolved}
            next1 = getEvents(helper, ew, site, param, api_token, mist_url)
            while (not (next1 is None)):
                next1 = getnextEvents(helper, ew, site, next1, api_token)

    except Exception , err :
        helper.log_error(str(err))
        
def getEvents(helper, ew, site, param, apitoken, mist_url):
    site_name = site.get('name', None)
    site_id = site.get('id',None)
    mistsys_url = mist_url + '/sites/' + site_id + '/insights/marvis'
    helper.log_info("url created :- " + mistsys_url)

    response = helper.send_http_request(mistsys_url, "GET", parameters=param,
                                        payload=None,
                                        headers={
                                            'Content-Type': 'application/json',
                                            'Authorization': 'Token %s' % apitoken
                                        },
                                        cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=False)
    r_text = response.text
    jsonObject = json.loads(r_text)
    results = jsonObject.get('results',[])

    for result in results:
        writeEvents(helper, ew, result, site_name, site_id)
    return jsonObject.get('next', None)


def getnextEvents(helper, ew, site, next1, api_token):
    try :
        site_name = site.get('name', None)
        site_id = site.get('id', None)
        response = helper.send_http_request('https://api.mist.com/'+ next1, "GET",  headers={
                                            'Content-Type': 'application/json',
                                            'Authorization': 'Token %s' % api_token
                                        },
                                        cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=False )
        r_text = response.text
        jsonObject = json.loads(r_text)
        results = jsonObject.get('results',[])
        for result in results:
            writeEvents(helper, ew, result, site_name, site_id)

        return jsonObject.get('next', None)
    except Exception , err :
        helper.log_error(err)

def writeEvents(helper, ew, result, site_name, site_id):
    try :
        result['site_name'] = site_name
        result['site_id'] = site_id
        reason_code = result.get('reason_code',None)
        result['reason_code'] = r_code.get(reason_code, reason_code )
        type1 = result.get('type')
        result['type'] = type_1.get(type1, type1 )
        severity = result.get('severity', None)
        result['severity'] = severity_1.get(severity, severity)
        jsonObject = json.dumps(result)
        result_id = result.get('id',None)
        created_time = result.get('created_time',None)
        resolved = result.get('resolved_time', None)
        key = str(site_id) + '_' + str(result_id) + '_' + str(created_time) + str(resolved)
        if helper.get_check_point(key) is None:
            event = helper.new_event(jsonObject, time=created_time, index=helper.get_output_index(),
                               sourcetype=helper.get_sourcetype(), done=True,
                                 unbroken=True)
            ew.write_event(event)
            helper.save_check_point(key, 0)
    except Exception , err :
        helper.log_error(err)