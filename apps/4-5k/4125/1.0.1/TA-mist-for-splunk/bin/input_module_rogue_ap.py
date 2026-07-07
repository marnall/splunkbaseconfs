import os
import sys
import time
import datetime
import json

def validate_input(helper, definition):
   pass


def collect_events(helper, ew):

    org_id = helper.get_global_setting('organization_id')
    api_token = helper.get_global_setting('api_token')
    opt_limit = helper.get_arg('limit')
    opt_duration = helper.get_arg('duration')
    opt_type = helper.get_arg('type')
    helper.set_log_level("info")
    helper.log_info("input type :- " + helper.get_input_type())
    stanza_name = helper.get_input_stanza_names()
    helper.log_info("stanza name:- " + stanza_name)
    source_type = helper.get_sourcetype()
    helper.log_info("source type:- " + source_type)
    mist_url = 'https://api.mist.com/api/v1'
  

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
            param = {'limit': opt_limit, 'duration': opt_duration, 'type': opt_type}
            next1 = getEvents(helper, ew, site, param, api_token, mist_url)
            while (not (next1 is None)):
                next1 = getnextEvents(helper, ew, site, next1, api_token)

    except Exception, err :
        event = helper.new_event(str(err), time=None, index=helper.get_output_index(),
                                 sourcetype=helper.get_sourcetype(), done=True,
                                 unbroken=True)
        ew.write_event(event)
        helper.log_error(str(err))


def getEvents(helper, ew, site, param, apitoken, mist_url):
    site_name = site['name']
    site_id = site['id']
    mistsys_url = mist_url + '/sites/' + site_id +  '/insights/rogues'
    helper.log_info("url created :- " + mistsys_url)

    response = helper.send_http_request(mistsys_url, "GET", parameters=param,                                    payload=None,
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
        site_name = site['name']
        site_id = site['id']
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

        return  jsonObject.get('next', None)
    except Exception , err :
        helper.log_error(err)


def writeEvents(helper, ew, result, site_name, site_id):
    result['site_id'] = site_id
    result['site_name'] = site_name
    event = helper.new_event(json.dumps(result), time=None, index=helper.get_output_index(),
                                 sourcetype=helper.get_sourcetype(), done=True,
                                 unbroken=True)
    ew.write_event(event)