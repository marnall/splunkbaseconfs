
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import urllib.request
import urllib.parse

'''
boilerplate code is from https://docs.microsoft.com/en-us/microsoft-365/security/defender-endpoint/run-advanced-query-sample-python?view=o365-worldwide
'''


def validate_input(helper, definition):
    pass
    
def collect_events(helper, ew):
    """
    # The following examples send rest requests to some endpoint.
    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
    # get the response headers
    r_headers = response.headers
    # get the response body as text
    r_text = response.text
    # get response body as json. If the body text is not a json string, raise a ValueError
    r_json = response.json()
    # get response cookies
    r_cookies = response.cookies
    # get redirect history
    historical_responses = response.history
    # get response status code
    r_status = response.status_code
    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()

    # The following examples show usage of check pointing related helper functions.
    # save checkpoint
    helper.save_check_point(key, state)
    # delete checkpoint
    helper.delete_check_point(key)
    # get checkpoint
    state = helper.get_check_point(key)

    # To create a splunk event
    helper.new_event(data, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
    """

    '''
    # The following example writes a random number as an event. (Multi Instance Mode)
    # Use this code template by default.
    import random
    data = str(random.randint(0,100))
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)
    '''

    '''
    # The following example writes a random number as an event for each input config. (Single Instance Mode)
    # For advanced users, if you want to create single instance mod input, please use this code template.
    # Also, you need to uncomment use_single_instance_mode() above.
    import random
    input_type = helper.get_input_type()
    for stanza_name in helper.get_input_stanza_names():
        data = str(random.randint(0,100))
        event = helper.new_event(source=input_type, index=helper.get_output_index(stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=data)
        ew.write_event(event)
    '''
    
    
    # Get bearer token
    account = helper.get_arg('account')
    tenantId = helper.get_arg('tenant_id')
    clientId = account['username']
    appSecret = account['password']
    proxy_settings = helper.get_proxy()

    url = "https://login.windows.net/%s/oauth2/token" % (tenantId)
    
    resourceAppIdUri = 'https://api.security.microsoft.com'
    
    body = {
        'resource' : resourceAppIdUri,
        'client_id' : clientId,
        'client_secret' : appSecret,
        'grant_type' : 'client_credentials'
    }
    data = urllib.parse.urlencode(body).encode("utf-8")
    
    try:
        helper.log_info("Getting AAD token")
        req = urllib.request.Request(url, data)
        response = urllib.request.urlopen(req)
        jsonResponse = json.loads(response.read())
        aadToken = jsonResponse["access_token"]
        helper.log_error("Access token: %s" % aadToken)
        
    except Exception as e:
        helper.log_error("Failed getting AAD token.")
        helper.log_error("Error was: %s" % e)
        exit()
    
    
    # Run query
    try:
        query = helper.get_arg('custom_query')
        # manage checkpoint 
        
        
        
        helper.log_debug("Will attempt to run query: %s" % query)
        
        url = "https://api.security.microsoft.com/api/advancedhunting/run"
        headers = { 
            'Content' : 'application/json',
            'Authorization' : "Bearer " + aadToken
        }
        
        data = json.dumps({ 'Query' : query }).encode("utf-8")
        req = urllib.request.Request(url, data, headers)
        response = urllib.request.urlopen(req)

            # Handle response
        if response.status == 403:
            helper.log_error("403 Unauthorized. " + response.read())
        if response.status == 429:
            helper.log_error("API quota reached for tenancy: %s." % tenantId)
        if response.status == 200:
            try:
                jsonResponse = json.loads(response.read())
                stats = jsonResponse["Stats"]
                schema = jsonResponse["Schema"]
                results = jsonResponse["Results"]
                helper.log_info("Query: \"" + query + "\" took " + str(stats["ExecutionTime"]) + " to complete.")
            except json.JSONDecodeError:
                helper.log_error("Couldn't decode response as JSON. Response was: " + str(response.read()))
    
    except Exception as e:
        helper.log_error("Exception: " + str(e))

    
    # send to splunk
    try:
        for result in results:
            result = str(result)
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=result)
            ew.write_event(event)
      
    except Exception as e:
        helper.log_error("There was an error iterating the results. Enable debug to see the output.")
        helper.log_debug("Failed to iterate the returned results:\n%s" % str(results))
        
    
    
