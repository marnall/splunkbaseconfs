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


def get_teams(helper, headers):

    # Get web proxy configuration.
    proxyConfig = {}
    try:
        proxy = voUtils.getWebProxyConfig(helper.context_meta['session_key']);

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
    endpoint = 'https://api.victorops.com/api-public/v1/team'
    req = Request(endpoint, None, headers);

    try:
        res = urlopen(req);
        if res.status == 200:
            body = res.read()
            return json.loads(body)

    except HTTPError as e:
        helper.log_info("Waiting {} seconds".format(t + 60 - time.perf_counter()))
        time.sleep(t + 60 - time.perf_counter())
        return get_teams(helper, headers)

    #t = time.perf_counter()
    #req = requests.get(
    #    'https://api.victorops.com/api-public/v1/team', headers=headers)
    ## RATE LIMITS
    #while req.status_code == 403:
    #    # wait until minute has passed
    #    helper.log_info("waiting {} seconds".format(t + 60 - time.perf_counter()))
    #    time.sleep(t + 60 - time.perf_counter())
    #    # reset timer to current time
    #    t = time.perf_counter()
    #    # retry
    #    req = requests.get(
    #        'https://api.victorops.com/api-public/v1/team', headers=headers)
    #if req.status_code == 200:
    #    return json.loads(req.text)
    ## NON-RATE LIMIT FAILURE
    #else:
    #    helper.log_info("Failed to get usernames . . .")


def get_team_policies(teamSlug, helper, headers):
    try:
        t = time.perf_counter()
        endpoint = "https://api.victorops.com/api-public/v1/team/" + teamSlug + "/policies"
        req = Request(endpoint, None, headers);
        res = urlopen(req);

        if res.status == 200:
            helper.log_info("Retrieved Team Policies")
            body = res.read()
            return json.loads(body)['policies']
        # NON-RATE LIMIT FAILURE
        else:
            helper.log_info("Cannot get team escalation policies for {}. Skipping . . . ".format(teamSlug))

    except HTTPError as e:
        #helper.log_error('Exception retrieving team policies: ' + str(e.code));

        # RATE LIMITS
        helper.log_info("Waiting {} seconds".format(t + 60 - time.perf_counter()))
        time.sleep(t + 60 - time.perf_counter())
        return get_team_policies(teamSlug, helper, headers)

    #t = time.perf_counter()
    #url = "https://api.victorops.com/api-public/v1/team/" + teamSlug + "/policies"
    #req = requests.get(url, headers=headers)
    ## RATE LIMITS
    #while req.status_code == 403:
    #    # wait until minute has passed
    #    helper.log_info("waiting {} seconds".format(t + 60 - time.perf_counter()))
    #    time.sleep(t + 60 - time.perf_counter())
    #    # reset timer to current time
    #    t = time.perf_counter()
    #    # retry
    #    req = requests.get(url, headers=headers)
    #if req.status_code == 200:
    #    return json.loads(req.text)['policies']
    ## NON-RATE LIMIT FAILURE
    #else:
    #    helper.log_info(
    #        "Cannot get team escalation policies for {}. Skipping . . . ".format(teamSlug))


def get_routing_keys(helper, headers):
    try:
        t = time.perf_counter()
        endpoint = 'https://api.victorops.com/api-public/v1/org/routing-keys'
        req = Request(endpoint, None, headers);
        res = urlopen(req);

        if res.status == 200:
            helper.log_info("Retrieved Routing Keys")
            body = res.read()
            return json.loads(body)['routingKeys']
        # NON-RATE LIMIT FAILURE
        else:
            helper.log_info("Failed to get routing keys . . .")

    except HTTPError as e:
        #helper.log_error('Exception retrieving routing keys: ' + str(e.code));

        # RATE LIMITS
        helper.log_info("Waiting {} seconds".format(t + 60 - time.perf_counter()))
        time.sleep(t + 60 - time.perf_counter())
        return get_routing_keys(helper, headers)

    #t = time.perf_counter()
    #req = requests.get(
    #    'https://api.victorops.com/api-public/v1/org/routing-keys', headers=headers)
    ## RATE LIMITS
    #while req.status_code == 403:
    #    # wait until minute has passed
    #    helper.log_info("waiting {} seconds".format(t + 60 - time.perf_counter()))
    #    time.sleep(t + 60 - time.perf_counter())
    #    # reset timer to current time
    #    t = time.perf_counter()
    #    # retry
    #    req = requests.get(
    #        'https://api.victorops.com/api-public/v1/org/routing-keys', headers=headers)
    #if req.status_code == 200:
    #    return json.loads(req.text)['routingKeys']
    ## NON-RATE LIMIT FAILURE
    #else:
    #    helper.log_info("Failed to get routing keys . . .")


def get_team_members(team, helper, headers):
    try:
        t = time.perf_counter()
        endpoint = 'https://api.victorops.com/api-public/v1/team/' + team + '/members'
        req = Request(endpoint, None, headers);
        res = urlopen(req);

        if res.status == 200:
            helper.log_info("Retrieved Team Members")
            body = res.read()
            return json.loads(body)['members']
        # NON-RATE LIMIT FAILURE
        else:
            helper.log_info("Failed to get team members. . .")

    except HTTPError as e:
        #helper.log_error('Exception retrieving team members: ' + str(e.code));

        # RATE LIMITS
        helper.log_info("Waiting {} seconds".format(t + 60 - time.perf_counter()))
        time.sleep(t + 60 - time.perf_counter())
        return get_team_members(team, helper, headers)

    #t = time.perf_counter()
    #url = 'https://api.victorops.com/api-public/v1/team/' + team + '/members'
    #req = requests.get(url, headers=headers)
    ## RATE LIMITS
    #while req.status_code == 403:
    #    # wait until minute has passed
    #    helper.log_info("waiting {} seconds".format(t + 60 - time.perf_counter()))
    #    time.sleep(t + 60 - time.perf_counter())
    #    # reset timer to current time
    #    t = time.perf_counter()
    #    # retry
    #    req = requests.get(url, headers=headers)
    ## return the members
    #if req.status_code == 200:
    #    members = json.loads(req.text)['members']
    #    return members
    ## NON-RATE LIMIT FAILURE
    #else:
    #    helper.log_info("Failed to get team members . . .")


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


def collect_events(helper, ew):
    org = {
        "Teams": [],
        "routingKeys": []
    }
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
    # get teams
    teams = get_teams(helper, headers)
    for t in teams:
        teamSlugTmp = t['slug']
        teamTmp = {
            'type': 'team',
            'org': organization_id,
            'info': t,
            'policies': get_team_policies(teamSlugTmp, helper, headers),
            'members': get_team_members(teamSlugTmp, helper, headers),
        }
        # cleanup
        teamTmp['info'].pop('_selfUrl')
        teamTmp['info'].pop('_membersUrl')
        teamTmp['info'].pop('_adminsUrl')
        teamTmp['info'].pop('_policiesUrl')
        teamTmp['info'].pop('isDefaultTeam')
        teamTmp['info'].pop('version')
        # count verified users
        verifiedMembers = 0
        for u in teamTmp['members']:
            if u['verified'] == True:
                verifiedMembers = verifiedMembers + 1
        teamTmp['info']['verifiedMembers'] = verifiedMembers
        org['Teams'].append(teamTmp)

    # get routing key info
    org["routingKeys"] = get_routing_keys(helper, headers)
    for r in org['routingKeys']:
        r['type'] = 'routingKey'
        r['org'] = organization_id
        for t in r['targets']:
            t['teamSlug'] = t['_teamUrl'].replace('/api-public/v1/team/', '')
            t.pop('_teamUrl')
            for team in org['Teams']:
                if team['info']['slug'] == t['teamSlug']:
                    t['teamName'] = team['info']['name']
                    break

    # TODO -- parse out team slug from teams_url, get team name and add to routing key
    for t in org['Teams']:
        check_point_key = "{}_{}_teams".format(
            helper.get_input_stanza_names(), t['info']['slug'])
        md5 = get_check_point(helper, check_point_key)
        team_json = json.dumps(t, sort_keys=True)
        temp_team_md5 = voUtils.md5_compat(team_json)
        if temp_team_md5 == md5:
            helper.log_info(
                "Data about {} was ingested. So Skipping . . . ".format(t['info']['slug']))
            continue
        else:
            if temp_team_md5 == None:
                helper.log_info(
                    "Fresh data index about {}".format(t['info']['slug']))
            else:
                helper.log_info(
                    "Something about {} has changed. Indexing the new event . . .".format(t['info']['slug']))
            # Ensure sourcetype matches the shipped props.conf stanza so parsing is consistent
            # across AOB/UCC builds and Splunk versions.
            st = helper.get_sourcetype()
            if not st or st == helper.get_input_type() or st == "victorops_teams":
                st = "splunk:victorops:teams:json"
            event = helper.new_event(
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=st,
                data=json.dumps(t),
            )
            ew.write_event(event)
            helper.save_check_point(check_point_key, temp_team_md5)

    for r in org['routingKeys']:
        check_point_key = "{}_{}_routingKeys".format(
            helper.get_input_stanza_names(), r['routingKey'])
        md5 = get_check_point(helper, check_point_key)
        temp_routingKeys_md5 = voUtils.md5_compat(json.dumps(r))
        if temp_routingKeys_md5 == md5:
            helper.log_info("Data about {} was ingested. So Skipping . . . ".format(
                r['routingKey']))
            continue
        else:
            if temp_routingKeys_md5 == None:
                helper.log_info(
                    "Fresh data index about {}".format(r['routingKey']))
            else:
                helper.log_info(
                    "Something about {} has changed. Indexing the new event . . .".format(r['routingKey']))
            # Use the same sourcetype as teams so props.conf applies consistently.
            st = helper.get_sourcetype()
            if not st or st == helper.get_input_type() or st == "victorops_teams":
                st = "splunk:victorops:teams:json"
            event = helper.new_event(
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=st,
                data=json.dumps(r),
            )
            ew.write_event(event)
            helper.save_check_point(check_point_key, temp_routingKeys_md5)
