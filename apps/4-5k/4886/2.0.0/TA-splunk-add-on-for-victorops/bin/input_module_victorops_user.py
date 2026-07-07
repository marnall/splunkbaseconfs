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


def get_users(helper, headers):

    # Get web proxy configuration.
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
    endpoint = 'https://api.victorops.com/api-public/v1/user'
    req = Request(endpoint, None, headers);

    try:
        res = urlopen(req);
        if res.status == 200:
            body = res.read()
            return json.loads(body)
   
    except HTTPError as e:
        helper.log_info(e)
        helper.log_info("Waiting {} seconds".format(t + 60 - time.perf_counter()))
        time.sleep(t + 60 - time.perf_counter())
        return get_users(helper, headers)

    #get_users_url = 'https://api.victorops.com/api-public/v1/user'
    #t = time.perf_counter()
    #helper.log_info("Time : {}".format(t))
    #req = requests.get(get_users_url, headers=headers)
    ## RATE LIMITS
    #while req.status_code == 403:
    #    helper.log_info("Waiting {} seconds".format(t + 60 - time.perf_counter()))
    #    time.sleep(t + 60 - time.perf_counter())
    #    # reset timer to current time
    #    t = time.perf_counter()
    #    # retry
    #    req = requests.get(get_users_url, headers=headers)
    #
    #if req.status_code == 200:
    #    return json.loads(req.text)
    #else:
    #    helper.log_info("Failed to get usernames . . .")


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
    # helper.log_info("Headers : {}".format(headers))
    users = get_users(helper, headers)
    # helper.log_info("Users : {}".format(users))
    for user in users['users'][0]:
        temp_user = {
            'type': 'user',
            'info': user,
            'org': organization_id,
            'contactMethods': get_user_contact_methods(user['username'], helper, headers),
            'pagingPolicy': get_user_paging_policy(user['username'], helper, headers)
        }
        temp_user['info'].pop('_selfUrl')
        helper.log_info("temp_user : ")
        helper.log_info("{}".format(temp_user))
        check_point_key = "{}_{}_user".format(
            helper.get_input_stanza_names(), user['username'])
        md5 = get_check_point(helper, check_point_key)
        user_json = json.dumps(temp_user, sort_keys=True)
        temp_user_md5 = voUtils.md5_compat(user_json)
        if temp_user_md5 == md5:
            helper.log_info(
                "Data about {} was ingested. So Skipping . . . ".format(user['username']))
            continue
        else:
            if temp_user_md5 == None:
                helper.log_info(
                    "Fresh data index about {}".format(user['username']))
            else:
                helper.log_info(
                    "Something about {} has changed. Indexing the new event . . .".format(user['username']))
            # Ensure sourcetype matches the shipped props.conf stanza so parsing is consistent
            # across AOB/UCC builds and Splunk versions.
            st = helper.get_sourcetype()
            if not st or st == helper.get_input_type() or st == "victorops_user":
                st = "splunk:victorops:users:json"
            event = helper.new_event(
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=st,
                data=json.dumps(temp_user),
            )
            ew.write_event(event)
            helper.save_check_point(check_point_key, temp_user_md5)


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


def get_user_contact_methods(username, helper, headers):

    try:
        t = time.perf_counter()
        endpoint = 'https://api.victorops.com/api-public/v1/user/' + username + '/contact-methods'
        req = Request(endpoint, None, headers);
        res = urlopen(req);

        if res.status == 200:
            helper.log_info("Retrieved User Contact Methods")
            body = res.read()
            response = json.loads(body)
            phones = response['phones']['contactMethods']
            emails = response['emails']['contactMethods']
            push = response['devices']['contactMethods']
            contactMethods = []
            # iterate through contactMethod types list
            for x in [phones, emails, push]:
                # for each method of contact type x
                # print x
                for y in x:
                    # is it a mobile device, if yes, special
                    if "deviceType" in y:
                        contactMethods.append({
                            "label": y['label'],
                            "type": y['deviceType']
                        }
                        )
                    # otherwise it is a phone/email which have the same response
                    else:
                        contactMethods.append({
                            "label": y['label'],
                            "type": y['contactType'],
                            "value": y['value']
                        }
                        )
                    # print the most recent contact method
                    # print contactMethods[-1]

            # print username + ':' + phone + email + push
            # print "\n\n CONTACT METHODS\n=========================\n" + str(contactMethods) + "\n\n"
            # [response['phones'].pop(, response['emails'], response['devices']]
            return contactMethods

        else:
            helper.log_info(
                "Cannot get contact-methods for {}. Exiting . . . ".format(username))
            sys.exit()

    except HTTPError as e:
        #helper.log_error('Exception retrieving user contact methods: ' + str(e.code));

        # Not Found Case - User has no contact methods
        helper.log_error(e.code)
        if e.code == 404:
            helper.log_error('user has no contact methods: ' + str(e.code));
            return {}
      
        helper.log_error(e);

        ## RATE LIMITS
        helper.log_info("Waiting {} seconds".format(t + 60 - time.perf_counter()))
        time.sleep(60)
        return get_user_contact_methods(username, helper, headers)

def get_user_paging_policy(username, helper, headers):
    try:
        t = time.perf_counter()
        endpoint = 'https://api.victorops.com/api-public/v1/profile/' + username + '/policies'
        req = Request(endpoint, None, headers);
        res = urlopen(req);

        if res.status == 200:
            helper.log_info("Retrieved User Paging Policy")
            body = res.read()
            return json.loads(body)['steps']

        # NON-RATE LIMIT FAILURE
        else:
            helper.log_info("Cannot get paging-policy for {}. Skipping . . .".format(username))

    except HTTPError as e:
        #helper.log_error('Exception retrieving user paging policies: ' + str(e.code));

        helper.log_error(e.code)
        if e.code == 404:
            helper.log_error('user has no paging policies: ' + str(e.code));
            return {}

        ## RATE LIMITS
        helper.log_info("Waiting {} seconds".format(t + 60 - time.perf_counter()))
        time.sleep(60)
        return get_user_paging_policy(username, helper, headers)
