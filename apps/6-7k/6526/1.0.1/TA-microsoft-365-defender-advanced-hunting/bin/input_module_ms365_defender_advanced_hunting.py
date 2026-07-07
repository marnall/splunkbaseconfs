
# encoding = utf-8

import os
import sys
import time
from datetime import datetime, timezone, timedelta
from dateutil import parser
import json
import urllib.request
import urllib.parse
import requests

'''
boilerplate code is from https://docs.microsoft.com/en-us/microsoft-365/security/defender-endpoint/run-advanced-query-sample-python?view=o365-worldwide
'''


def validate_input(helper, definition):
    pass
    
def collect_events(helper, ew):
  
    # Get bearer token
    account = helper.get_arg('account')
    tenantId = helper.get_arg('tenant_id')
    clientId = account['username']
    appSecret = account['password']
    proxy_settings = helper.get_proxy()
    if proxy_settings:
        use_proxy = True
    else:
        use_proxy = False

    url = "https://login.windows.net/%s/oauth2/token" % (tenantId)
    method = "POST"
    body = {
        'grant_type' : 'client_credentials',
        'resource' : 'https://api.security.microsoft.com',
        'client_id' : clientId,
        'client_secret' : appSecret
        
    }
    # data = urllib.parse.urlencode(body).encode("utf-8")
    
    try:
        helper.log_info("Getting AAD token")
        response = requests.request(method, url, data=body)
        jsonResponse = response.json()
        aadToken = jsonResponse["access_token"]
        
    except Exception as e:
        helper.log_error("Failed getting AAD token.")
        helper.log_error("Error was: %s" % e)
        exit()
    
    

    # Handle query and checkpoint
    query = helper.get_arg('custom_query')
    # query = "EmailEvents | where EmailDirection != "Intra-org" | where Timestamp > ago(7m) and Timestamp < ago(5m) | sort by Timestamp asc | take 10000"
    
    # Check query has a checkpoint
    if "@@@" in query:
        has_checkpoint = True
    else:
        has_checkpoint = False
    
    # if it has checkpoint.
    #   get latest checkpoint or create a new
    if has_checkpoint:
        checkpoint_name = helper.get_app_name() + ":"+ helper.get_input_type() + ":" + helper.get_input_stanza_names()
        checkpoint_column = helper.get_arg('checkpoint_column')

        # get the current value of the checkpoint
        query_from = helper.get_check_point(checkpoint_name)

        # If no current checkpoint, check for initial from config
        if isinstance(query_from,str) == False:
            query_from = (datetime.utcnow() - timedelta(days=1)).isoformat()
            
            # at the end, save the checkpoint with updated value
            helper.save_check_point(checkpoint_name, query_from)
            query_from = helper.get_check_point(checkpoint_name)
        
        tmp_ts = parser.isoparse(query_from)
        
        # Update query
        query = query.replace("@@@", query_from)
        helper.log_debug("Query has been updated with checkpoint. Query: %s" % query)

        
    # Run query
    try:   
        helper.log_debug("Will attempt to run query: %s" % query)
        
        url = "https://api.security.microsoft.com/api/advancedhunting/run"
        method = "POST"
        headers = { 
            'Content' : 'application/json',
            'Authorization' : "Bearer " + aadToken
        }
        data = {
            'Query' : query
        }
        # helper.log_debug("Payload being sent: %s" % json.dumps(data))
        response = requests.request(method, url, headers=headers, json=data)
    except Exception as e:
        helper.log_error("Exception: " + str(e))
        
    # Handle response
    if response.status_code == 200:
        try:
            jsonResponse = response.json()
            stats = jsonResponse["Stats"]
            schema = jsonResponse["Schema"]
            results = jsonResponse["Results"]
            helper.log_info("Query: \"%s\" took %s to complete." % (query, str(stats["ExecutionTime"])))
            helper.log_info("Resource Usage: %s" % (str(stats["resource_usage"])))
        except JSONDecodeError:
            helper.log_error("Couldn't decode response as JSON. Response was: " + response.text)
        except Exception as e:
            helper.log_error("Exception occured when parsing response: %s" % response.text)
    else:
        helper.log_error("Response: %s" % response.text)
        exit()

    # Send to splunk
    try:
        st = helper.get_arg("my_sourcetype")
        
        if len(results) > 0:
            for result in results:
                # helper.log_debug("Result: " + str(result))

                event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=st, data=json.dumps(result))
                ew.write_event(event)
                
                # Update checkpoint
                if has_checkpoint:
                    try:
                        helper.log_debug("result timestamp: %s" % str(parser.isoparse(result[checkpoint_column])))
                        helper.log_debug("tmp_ts timestamp: %s" % str(tmp_ts))
                        if parser.isoparse(result[checkpoint_column]).replace(tzinfo=timezone.utc) > tmp_ts.replace(tzinfo=timezone.utc):
                            tmp_ts = parser.isoparse(result[checkpoint_column])
                            new_checkpoint = tmp_ts.isoformat()
                            
                    except Exception as e:
                        helper.log_debug("something failed when checking the timestamps: %s" % str(e))
            
            # save checkpoint
            if has_checkpoint:
                helper.log_debug("Updating checkpoint to %s." % str(new_checkpoint))
                helper.save_check_point(checkpoint_name, new_checkpoint)
                
        else:
            helper.log_info("No results returned for the query: \"%s\"" % query) 
      
    except Exception as e:
        helper.log_error("There was an error iterating the results. Enable debug to see the results.")
        helper.log_debug("Failed to iterate the returned results:\n%s" % str(results))
        
    
    
