# Version 1.0.15

import os
import sys
import time
import datetime
import json


def use_single_instance_mode():
    return True


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):

    #helper.log_error(helper.get_input_stanza_names())

    for stanza in helper.get_input_stanza_names():
        helper.log_info("POLLING instance: " + stanza)
        helper.log_info("=================");

        # Ensure HTTPS only
        forgerock_id_cloud_tenant_url = helper.get_arg("forgerock_id_cloud_tenant")[stanza]
        if forgerock_id_cloud_tenant_url.startswith('http://'):
            forgerock_id_cloud_tenant_url = forgerock_id_cloud_tenant_url.replace('http://', 'https://', 1)

        # Get config for this tenant
        api_key_id = helper.get_arg("api_key_id")[stanza]
        api_key_secret = helper.get_arg("api_key_secret")[stanza]
        log_sources = helper.get_arg("log_sources",stanza)
        log_filter = helper.get_arg("log_filter",stanza)
        if log_sources == None:
            log_sources = 'am-authentication,am-access,am-config,idm-activity'
        helper.log_info("Sources: " + log_sources)

        index = helper.get_output_index()[stanza]

        #parameters = { "source": "am-authentication,am-access,am-config,idm-activity" }
        headers = { "x-api-key": api_key_id, "x-api-secret": api_key_secret }

        # Determine time of last request to log endpoint
        previousBeginTime = helper.get_check_point("beginTime-" + stanza)
        # Catch broken datetime
        try:
            datetime.datetime.strptime(previousBeginTime,'%Y-%m-%dT%H:%M:%S%z')
        except:
            previousBeginTime = None

        if previousBeginTime == None:
            helper.log_info("No previous beginTime saved so backdating to 1 minute ago")
            beginTime = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
        elif ((datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.strptime(previousBeginTime,'%Y-%m-%dT%H:%M:%S%z')).seconds > 3600):
            helper.log_info("Previous saved beginTime "+ datetime.datetime.strptime(previousBeginTime,'%Y-%m-%dT%H:%M:%S%z').strftime("%Y-%m-%dT%H:%M:%SZ") +" too old (> 1 hour) so backdating to 1 minute ago")
            beginTime = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:        
            beginTime = previousBeginTime

        endTime = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
        helper.save_check_point("beginTime-" + stanza, endTime)

        helper.log_info("beginTime " + beginTime)
        helper.log_info("endTime   " + endTime)


        # Begin requesting log events in pages
        pages = 0
        pagedResultsCookie = None
        pagedResults = 0

        # Limit the number of pages requested to avoid throttling
        while pages < 100:

            helper.log_info("Requesting page: " + str(pages))
            pages = pages + 1

            parameters = { "_pageSize": 500, "source": log_sources, "beginTime": beginTime, "endTime": endTime }

            if pagedResultsCookie != None:
                parameters["_pagedResultsCookie"] = pagedResultsCookie

            if log_filter != None:
                parameters["_queryFilter"] = log_filter
                
            # Call logging endpoint
            response = helper.send_http_request(forgerock_id_cloud_tenant_url + "/monitoring/logs", 'GET', parameters=parameters, payload=None, headers=headers, cookies=None, verify=True, cert=None, timeout=60, use_proxy=False)

            r_status = response.status_code
            if r_status != 200:
                helper.log_info("Unexpected response from ForgeRock: " + str(r_status))
                response.raise_for_status()
                break
            
            else:
                r_json = response.json()

                if r_json["resultCount"] > 0:
                    final_result = []
                    for entry in r_json["result"]:
                        final_result.append(entry['payload'])

                    event = helper.new_event(json.dumps(final_result), time=None, host=None, index=index, source=stanza, sourcetype='_json', done=True, unbroken=True)
                    ew.write_event(event)
                    helper.log_info("Log count: " + str(len(final_result)))
                    pagedResults = pagedResults + len(final_result)
                
                if r_json["pagedResultsCookie"] != None:
                    pagedResultsCookie = r_json["pagedResultsCookie"]
                    helper.log_info("Found pagedResultsCookie so more events to retrieve")                    
                else:
                    helper.log_info("No pagedResultsCookie so all events logged")
                    break

        helper.log_info("TOTAL RESULTS: " + str(pagedResults))
