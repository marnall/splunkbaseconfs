# TODO: This API stinks. It doesnt appear to always return all data points.

encoding = "utf-8"

import os, sys, time, json, datetime, requests

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    helper.set_log_level(helper.get_log_level())
    debugging = ""

    api_key = helper.get_arg("api_key")
    monitors = helper.get_arg('monitors')
    seconds_of_data_to_fetch = helper.get_arg('seconds_of_data_to_fetch')
    
    if api_key == None:
        api_key = ""
    if monitors == None:
        monitors = ""
    if seconds_of_data_to_fetch == None:
        seconds_of_data_to_fetch = "60"        

    api_key = api_key.strip()
    monitors = monitors.strip()
    seconds_of_data_to_fetch = seconds_of_data_to_fetch.strip()
    
    url = "https://api.uptimerobot.com/v2/getMonitors"
    
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "cache-control": "no-cache"
    }
    
    epoch_time = int(time.time())
    
    pagination_complete = False
    pagination_offset = 0
    pagination_limit = 50
    
    while not pagination_complete:
       
        payload = "format=json&logs=1&response_times=1&api_key=" + api_key + "&logs_start_date=" + str(epoch_time - int(seconds_of_data_to_fetch))  + "&logs_end_date=" + str(epoch_time + 300) + "&response_times_start_date=" + str(epoch_time - int(seconds_of_data_to_fetch))  + "&response_times_end_date=" + str(epoch_time + 300) + "&offset=" + str(pagination_offset) + "&limit=" + str(pagination_limit)
        
        if monitors != "":
            payload += "&monitors=" + monitors
        
        proxy_settings = helper.get_proxy()
    
        debugging += "Requesting URL: " + url + "\n" + str(payload) + "\n"
    
        # The following examples send rest requests to some endpoint.
        response = helper.send_http_request(url, "POST", parameters=None, payload=payload,
                       headers=headers, cookies=None, verify=False, cert=None, timeout=30, use_proxy=True)
      
        sourcetype = helper.get_sourcetype()
        index = helper.get_output_index()
        source = helper.get_input_stanza_names()
    
        # If the body text is not a json string, raise a ValueError
        try:
            r_json = response.json()
            #debugging += json.dumps(r_json) + "\n"

            for monitorObj in r_json["monitors"]:
                #debugging += json.dumps(monitorObj) + "\n"
                monitor_id = str(monitorObj["id"])
                source_with_id = "monitor_" + monitor_id
                m = {}
                m["datetime"] = epoch_time
                m["status"] = monitorObj["status"]
                m["friendly_name"] = monitorObj["friendly_name"]
                ew.write_event(helper.new_event(source=source_with_id, index=index, sourcetype=sourcetype, data=json.dumps(m)))
                
                if "response_times" in monitorObj:
                    events_written = 0
                    events_skipped = 0
                    start_event = helper.get_check_point("monitor_rt_" + monitor_id)
                    debugging += "loading checkpoint=" + "monitor_rt_" + monitor_id + " ==> " + str(start_event) + "\n"
                    if start_event == None:
                        start_event = 0
                    else:
                        start_event = int(start_event)
                    last_datetime = 0
                    for item in monitorObj["response_times"]:
                        item["friendly_name"] = monitorObj["friendly_name"]
                        item["response_time"] = item.pop('value', None)
                        datetime = int(item["datetime"])
                        if datetime > start_event:
                            eventdata = json.dumps(item)
                            events_written += 1
                            ew.write_event(helper.new_event(source=source_with_id, index=index, sourcetype=sourcetype, data=eventdata))
                            if datetime > last_datetime:
                                last_datetime = datetime
                        else:
                            #debugging += "Skipping monitor=\"" + monitorObj["friendly_name"] + "\" datetime=" + str(datetime) + "\n"
                            events_skipped += 1
                    
                    debugging += "Processed monitor=\"" + monitorObj["friendly_name"] + "\" written=" + str(events_written) + " skipped=" + str(events_skipped) + "\n"
                    if last_datetime != 0:
                        debugging += "saving checkpoint=" + "monitor_rt_" + monitor_id + " to " + str(last_datetime) + "\n"
                        helper.save_check_point("monitor_rt_" + monitor_id, str(last_datetime))
        
                    
                if "logs" in monitorObj:
                    events_written = 0
                    events_skipped = 0
                    start_event = helper.get_check_point("monitor_log_" + monitor_id)
                    debugging += "loading checkpoint=" + "monitor_log_" + monitor_id + " ==> " + str(start_event) + "\n"
                    if start_event == None:
                        start_event = 0
                    else:
                        start_event = int(start_event)
                    last_datetime = 0
                    for item in monitorObj["logs"]:
                        item["friendly_name"] = monitorObj["friendly_name"]
                        datetime = int(item["datetime"])
                        if datetime > start_event:
                            eventdata = json.dumps(item)
                            events_written += 1
                            ew.write_event(helper.new_event(source=source_with_id, index=index, sourcetype=sourcetype, data=eventdata))
                            if datetime > last_datetime:
                                last_datetime = datetime
                        else:
                            #debugging += "Skipping monitor=\"" + monitorObj["friendly_name"] + "\" datetime=" + str(datetime) + "\n"
                            events_skipped += 1
                    
                    debugging += "Processed monitor=\"" + monitorObj["friendly_name"] + "\" written=" + str(events_written) + " skipped=" + str(events_skipped) + "\n"
                    if last_datetime != 0:
                        debugging += "saving checkpoint=" + "monitor_log_" + monitor_id + " to " + str(last_datetime) + "\n"
                        helper.save_check_point("monitor_log_" + monitor_id, str(last_datetime))
            if int(r_json["pagination"]["total"]) > pagination_offset + pagination_limit:
                pagination_offset = pagination_offset + pagination_limit
                time.sleep(5)
            else:
                pagination_complete = True
                
        except:
            ew.write_event(helper.new_event(source=source, index=index, sourcetype=sourcetype, data=str(response.text)))
            pagination_complete = True
            
    # Uncomment this line for debugging events
    #ew.write_event(helper.new_event(source=source, index=index, sourcetype=sourcetype, data=debugging))

  
