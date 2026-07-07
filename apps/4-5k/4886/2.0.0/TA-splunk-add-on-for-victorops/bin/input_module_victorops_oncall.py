import os
import sys
import json
import time
import voUtils

#from future.moves.urllib.request import urlopen, Request, ProxyHandler, HTTPBasicAuthHandler, build_opener, install_opener
#from future.moves.urllib.error import HTTPError

try:
    # For Python 3.0 and later
    from urllib.request import urlopen, ProxyHandler, HTTPBasicAuthHandler, build_opener, install_opener, Request
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen, ProxyHandler, HTTPBasicAuthHandler, build_opener, install_opener, Request
try:
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import HTTPError

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
    # organization_id = definition.parameters.get('organization_id', None)
    # api_id = definition.parameters.get('api_id', None)
    # api_key = definition.parameters.get('api_key', None)
    pass


def collect_events(helper, ew):
    organization_id = helper.get_arg('organization_id')
    api_id = helper.get_arg('api_id')
    api_key = helper.get_arg('api_key')

    appVersion = voUtils.getAppVersion();
    splunkVersion = voUtils.getSplunkVersion()
    pythonVersion =  sys.version_info
    userAgent = "VictorOpsTA/" + appVersion + " Splunk/" + splunkVersion + " Python/" + str(pythonVersion)

    headers = {
        'Content-Type': 'application/json',
        'X-VO-Api-Id': api_id,
        'X-VO-Api-Key': api_key,
        'Accept': 'application/json',
        'User-Agent': userAgent
    }
    oncall = get_on_call(helper, headers)
    for t in oncall['teamsOnCall']:
        oncallTeam = {
            'type': 'oncall',
            'org': organization_id,
            'teamName': t['team']['name'],
            'teamSlug': t['team']['slug'],
            'policies': []
        }
        for p in t['oncallNow']:
            policyTmp = {
                'policyName': p['escalationPolicy']['name'],
                'policySlug': p['escalationPolicy']['slug'],
                'oncallUsers': []
            }
            for u in p['users']:
                policyTmp['oncallUsers'].append(u['onCalluser']['username'])
            oncallTeam['policies'].append(policyTmp)

        # helper.log_info("{}".format(json.dumps(oncallTeam)))
        check_point_key = "{}_{}_oncall_team".format(
            helper.get_input_stanza_names(), oncallTeam['teamSlug'])
        md5 = get_check_point(helper, check_point_key)
        oncall_json = json.dumps(oncallTeam, sort_keys=True)
        temp_oncall_md5 = voUtils.md5_compat(oncall_json)
        if temp_oncall_md5 == md5:
            helper.log_info("Data about {} was ingested. So Skipping . . . ".format(
                oncallTeam['teamSlug']))
        else:
            if temp_oncall_md5 == None:
                helper.log_info(
                    "Fresh data index about {}".format(oncallTeam['teamSlug']))
            else:
                helper.log_info(
                    "Something about {} has changed. Indexing the new event . . .".format(oncallTeam['teamSlug']))
            # Ensure sourcetype matches the shipped props.conf stanza so parsing is consistent
            # across AOB/UCC builds and Splunk versions.
            st = helper.get_sourcetype()
            if not st or st == helper.get_input_type() or st == "victorops_oncall":
                st = "splunk:victorops:oncall:json"
            event = helper.new_event(
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=st,
                data=json.dumps(oncallTeam),
            )
            ew.write_event(event)
            helper.save_check_point(check_point_key, temp_oncall_md5)


def get_check_point(helper, check_point_key):
    md5 = helper.get_check_point(check_point_key)
    if (md5 not in [None, '']):
        helper.log_info(
            "Valid MD5 found for {}. Its value is {}".format(check_point_key, md5))
        return md5
    else:
        helper.log_info(
            "No MD5 found for {}. Data has to be ingested.".format(check_point_key))
        return None


def get_on_call(helper, headers):
    proxyConfig = {}
    try:
        proxy = voUtils.getWebProxyConfig(helper.context_meta['session_key']);
        #helper.log_info(proxy)

        if 'host' in proxy and proxy['host'] != '':
            helper.log_info('Using Web proxy for requests: ' + proxy['protocol'] + '://' + proxy['host'] + ':' + str(proxy['port']));
            proto = proxy['protocol'];
            proxyUrl = proto + '://' + proxy['host'] + ':' + proxy['port'] + '/';
            conf = {};

            # All calls to VictorOps API are https, setup proxy URL to reference
            # the proxy which could be http or https.
            conf['https'] = proxyUrl;
            conf['http'] = proxyUrl;
            helper.log_info('Proxy Configuration: ' + repr(conf));
            proxy_handler = ProxyHandler(conf);

            if 'user' in proxy and proxy['user'] != '' and 'pass' in proxy and proxy['pass'] != '':
                helper.log_info('Configuring proxy configuration to use authentication...');
                # Proxy https requests with auth.
                proxy_auth_handler = HTTPBasicAuthHandler();
                proxy_auth_handler.add_password(None, proxyUrl, proxy['user'], proxy['pass']);
                opener = build_opener(proxy_handler, proxy_auth_handler);
            else:
                # Auth not defined, proxy all https requests w/out auth.
                helper.log_info('Using http proxy w/out authentication...');
                opener = build_opener(proxy_handler);

            install_opener(opener);

        else:
            helper.log_info('Proxy IS NOT configured!');


    except Exception as e:
        helper.log_error('Exception retrieving webProxy config');
        helper.log_error(e);

    t = time.perf_counter()
    helper.log_info("Time : {}".format(t))
    endpoint = 'https://api.victorops.com/api-public/v1/oncall/current'
    req = Request(endpoint, None, headers);

    try:
        res = urlopen(req);
        if res.status == 200:
            body = res.read()
            return json.loads(body)

    except HTTPError as e:
        helper.log_info("Waiting {} seconds".format(t + 60 - time.perf_counter()))
        time.sleep(t + 60 - time.perf_counter())
        return get_on_call(helper, headers)

    #t = time.perf_counter()
    #get_on_call_url = 'https://api.victorops.com/api-public/v1/oncall/current'
    #req = requests.get(get_on_call_url, headers=headers)
    ## RATE LIMITS
    #while req.status_code == 403:
    #    # wait until minute has passed
    #    helper.log_info("Waiting {} seconds".format(t + 60 - time.perf_counter()))
    #    time.sleep(t + 60 - time.perf_counter())
    #    # reset timer to current time
    #    t = time.perf_counter()
    #    # retry
    #    req = requests.get(get_on_call_url, headers=headers)
    #if req.status_code == 200:
    #    return json.loads(req.text)
    ## NON-RATE LIMIT FAILURE
    #else:
    #    helper.log_info("Failed to get onCall . . .")
