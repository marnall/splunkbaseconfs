import os
import sys
import time
import datetime
import json

eventTypeMap = {
    'CLIENT_ASSOCIATION': 'Association',
    'CLIENT_ASSOCIATION_FAILURE': 'Association Failure',
    'CLIENT_DEASSOCIATION': 'Disassociation',
    'CLIENT_REASSOCIATION': 'Reassociation',
    'CLIENT_IP_ASSIGNED': 'IP Assigned',
    'CLIENT_AUTHENTICATED': 'Authorization',
    'CLIENT_AUTHENTICATED_OKC': 'Fast Roaming OKC',
    'CLIENT_AUTHENTICATED_11R': 'Fast Roaming 802.11R',
    'CLIENT_DEAUTHENTICATION': 'Deauthentication',
    'CLIENT_DEAUTHENTICATED': 'Client Deauthenticated',
    'CLIENT_DNS_OK': 'DNS OK',
    'MARVIS_EVENT_CLIENT_AUTH_FAILURE': 'Authorization Failure',
    'MARVIS_EVENT_CLIENT_AUTH_FAILURE_11R': 'Fast Roaming Failure 802.11R',
    'MARVIS_EVENT_CLIENT_AUTH_FAILURE_OKC': 'Fast Roaming Failure OKC',
    'MARVIS_EVENT_CLIENT_DHCP_FAILURE': 'DHCP INIT Failure - Server Unresponsive',
    'MARVIS_EVENT_CLIENT_FAILED_DHCP_INFORM': 'Server Unresponsive - DHCP INFORM request',
    'MARVIS_EVENT_CLIENT_DHCP_NAK': 'DHCP NAK',
    'MARVIS_EVENT_CLIENT_DNS_FAILURE': 'DNS Failure',
    'MARVIS_EVENT_CLIENT_DNS_RECOVERY': 'DNS Recovery',
    'MARVIS_EVENT_INVALID_CLIENT_IP': 'Invalid IP',
    'MARVIS_HEALTH_EVENT_BAD_IP_ASSIGNMENT_PATTERN': 'Bad IP Assigned',
    'MARVIS_EVENT_CLIENT_DHCP_STUCK': 'DHCP Stuck - Bind Failure',
    'MARVIS_EVENT_CLIENT_FBT_SUCCESS': 'Fast BSS Assoc Success',
    'MARVIS_EVENT_CLIENT_FBT_FAILURE': 'Fast BSS Assoc Failure',
    'MARVIS_EVENT_CLIENT_MAC_AUTH_SUCCESS': 'MAC Authentication Success',
    'MARVIS_EVENT_CLIENT_MAC_AUTH_FAILURE': 'MAC Authentication Failure',
    'MARVIS_EVENT_CAPTIVE_PORTAL_FAILURE': 'Captive Portal Access Failure',
    'MARVIS_EVENT_CAPTIVE_PORTAL_AUTHORIZED': 'Captive Portal Authorization',
    'MARVIS_EVENT_CAPTIVE_PORTAL_REDIRECT': 'Captive Portal Redirection',
    'MARVIS_EVENT_WXLAN_CAPTIVE_PORT_FLOW_REDIRECT': 'Captive Portal Flow Redirection',
    'CLIENT_GW_ARP_OK': 'Default Gateway ARP Success',
    'CLIENT_GW_ARP_FAILURE': 'Default Gateway ARP Failure',
    'CLIENT_ARP_FAILURE': 'Impacted Traffic Flow',
    'MARVIS_EVENT_CLIENT_AUTH_DENIED': 'Authencation Denied',
    'MARVIS_EVENT_CLIENT_WXLAN_POLICY_LOOKUP_FAILURE': 'Wxlan Policy Lookup Failure',
    'MARVIS_EVENT_CLIENT_STATIC_IP_BLOCKED': 'Assigned Static IP blocked'
}

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    org_id = helper.get_global_setting('organization_id')
    api_token = helper.get_global_setting('api_token')
    opt_limit = helper.get_arg('limit')
    opt_duration = helper.get_arg('duration')
    opt_metrics = 'clients'
    filter_events = helper.get_arg('filter_by_events')

    helper.set_log_level("info")
    helper.log_info("input type :- " + helper.get_input_type())
    stanza_name = helper.get_input_stanza_names()
    helper.log_info("stanza name:- " + stanza_name)
    source_type = helper.get_sourcetype()
    helper.log_info("source type:- " + source_type)
    
    mist_url = 'https://api.mist.com/api/v1'
    # retrieve all sites related to this organization.

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
            param = {'metrics': opt_metrics, 'limit': opt_limit, 'duration': opt_duration}
            next1 = getEvents(helper, ew, site, param, api_token, mist_url, opt_duration, filter_events)
            while (not (next1 is None)):
                next1 = getnextEvents(helper, ew, site, next1, filter_events, api_token)

    except Exception as err:
        helper.log_error(str(err))
        
def getEvents(helper, ew, site, param, apitoken, mist_url, opt_duration, filter_events):
    site_name = site['name']
    site_id = site['id']

    mistsys_url = mist_url + '/sites/' + site_id +  '/stats/clients'
    helper.log_info("url created :- " + mistsys_url)
    response = helper.send_http_request(mistsys_url, "GET", parameters=None,
                                        payload=None,
                                        headers={
                                            'Content-Type': 'application/json',
                                            'Authorization': 'Token %s' % apitoken
                                        },
                                        cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=False)
    r_text = response.text
    clients = json.loads(r_text)
    opt_limit_1 = 1000

    for  client in clients:
        username = client.get('username')
        hostname = client.get('hostname')
        mac_id = client.get('mac')
        mac_id = '-'.join(s.encode('hex') for s in mac_id.decode('hex'))
        mistsys_url1 = mist_url + '/sites/' + site_id + '/clients/' + mac_id + '/events'
        param1 = {'limit': opt_limit_1, 'duration': opt_duration}
        response1 = helper.send_http_request(mistsys_url1, "GET", parameters=param1,
                payload=None,
                headers={                                         'Content-Type': 'application/json',
                       'Authorization': 'Token %s' % apitoken
                        },
                cookies=None, verify=True, cert=None,
                timeout=None, use_proxy=False)
        r_text1 = response1.text

        jsonObject = json.loads(r_text1)

        if len(str(r_text1)) == 2:
                return
        results = jsonObject.get('results',[])
        for result in results:
            writeEvents(helper, ew, result, site_name, site_id, mac_id, filter_events, username, hostname)
            
def writeEvents(helper, ew, result, site_name, site_id, client_mac_id,filter_events,username,hostname):
    reason = result.get('type')
    flag = False
    if 'All' in filter_events :
        flag = True
    else :
        if reason in filter_events :
            flag = True
    if (flag) :
        result['client_mac_id'] = client_mac_id
        result['site_name'] = site_name
        result['site_id'] = site_id
        result['username'] = username
        result['hostname'] = hostname
        result['type'] = eventTypeMap.get(reason)
        jsonObject = json.dumps(result)
        ap = result.get('ap')
        timestamp = result.get('timestamp')
        type_code =  result.get('type_code')
        seconds = int(timestamp)
        key = str(client_mac_id) + str(ap) + str(type_code) + str(timestamp)
        if helper.get_check_point(key) is None:
            event = helper.new_event(jsonObject, time=seconds, index=helper.get_output_index(),
                                 sourcetype=helper.get_sourcetype(), done=True,
                                 unbroken=True)
            ew.write_event(event)
            helper.save_check_point(key,0)