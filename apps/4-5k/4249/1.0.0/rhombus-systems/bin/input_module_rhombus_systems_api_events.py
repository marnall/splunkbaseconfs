# encoding = utf-8

import os
import sys
import time
import datetime 
from datetime import timedelta
import json


def validate_input(helper, definition):
    helper.log_debug("Validating input variables")
    api_call = definition.parameters.get('api_call', None)
    spec_api_call = definition.parameters.get('specific_rhombus_api_endpoint', '')
    rep_type = definition.parameters.get('reporting_type', '')
    rep_scope = definition.parameters.get('reporting_scope', '')

    if api_call == 'other' and spec_api_call == '':
        raise Exception(" You need to specify an endpoint if you select Other Endpoint!")
            
    elif api_call == 'report/getCountReports' and (rep_type == '' or rep_scope == ''):
        raise Exception(" You need to specify the reporting type and scope if you select Count Reports!")


def collect_events(helper, ew):
    api_url = 'https://api2.rhombussystems.com/api'
    empty_reqs = {'report/getDiagnosticFeed', 'device/getCameraList'}
               
    unsupported_api = False
    api_call = helper.get_arg('rhombus_api_events')
    if api_call == 'other':
        unsupported_api = True
        api_call = helper.get_arg('specific_rhombus_api_endpoint')

    if api_call in empty_reqs or unsupported_api:
        helper.log_debug("Handling empty payload api calls")
        _handle_empty_reqs(helper, ew, api_url, api_call)
    elif api_call == 'report/getCountReports':
        helper.log_debug("Handling count report api calls")
        _handle_count_reports_req(helper, ew, api_url, api_call)
        

def _handle_count_reports_req(helper, ew, api_url, api_call):
    headers = {"x-auth-scheme": "api",
               "x-auth-apikey": helper.get_global_setting('api_key')}
    cert = (helper.get_global_setting('certificate_path'), 
            helper.get_global_setting('private_key_path'))
    
    #Poll for results since the last time we polled
    now = datetime.datetime.utcnow().replace(microsecond=0, second=0)
    
    state = helper.get_check_point("{}-{}-checkpoint".format(helper.get_arg('reporting_type'),
                                                             helper.get_arg('reporting_scope')))
    if state is None:
        state = (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
    if helper.get_arg('reporting_type') == 'BANDWIDTH':
        interval = 'HOURLY'
    else:
        interval = 'QUARTERHOURLY'

    payload = {'startDate': state,
                            'endDate': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
                            'interval': interval,
                            'scope': helper.get_arg('reporting_scope'),
                            'type': helper.get_arg('reporting_type')
                            }
    helper.log_debug("Sending payload: {}".format(payload))
    response = helper.send_http_request("{}/{}".format(api_url, api_call), "POST",
                                        payload=payload, headers=headers,
                                        verify=True, cert=cert)

    r_status = response.status_code
    if r_status == 200:
        nonempty = False
        r_json = response.json()
        helper.log_debug("Got response: {}".format(r_json))
        for uuid, series in r_json.get("timeSeriesDataPointsMap", {}).iteritems():
            for count in series:
                if count.get('eventCountMap', {}):
                    nonempty = True
                    event_data = {'reportingType': helper.get_arg('reporting_type'),
                              'reportingScope': helper.get_arg('reporting_scope'),
                              'reportingInterval': interval,
                              'uuid': uuid,
                              'timestamp': count.get('dateLocal', 'None')}
                    event_map_count = count.get('eventCountMap', {})
                    event_map_count.pop('eventCount', -1)
                    event_data.update(event_map_count)
                    
                    helper.log_debug("Sending event: {}".format(event_data))
                    event = helper.new_event(data=json.dumps(event_data), 
                                             source=helper.get_input_type(), 
                                             index=helper.get_output_index(), 
                                             sourcetype=helper.get_sourcetype())
                    ew.write_event(event)
        if nonempty:
            helper.save_check_point("{}-{}-checkpoint".format(helper.get_arg('reporting_type'),
                                                              helper.get_arg('reporting_scope')),
                                    now.strftime('%Y-%m-%dT%H:%M:%SZ'))
    else:
        helper.log_debug("Something went wrong with the api call: [{}] {}".format(r_status, response.text))
        response.raise_for_status() 
    
    
def _handle_empty_reqs(helper, ew, api_url, api_call):
    headers = {"x-auth-scheme": "api",
               "x-auth-apikey": helper.get_global_setting('api_key')}
    payload = {}
    cert = (helper.get_global_setting('certificate_path'), 
            helper.get_global_setting('private_key_path'))
            
    helper.log_debug("Sending payload: {}".format(payload))
    response = helper.send_http_request("{}/{}".format(api_url, api_call), "POST",
                                        payload=payload, headers=headers,
                                        verify=True, cert=cert)

    r_status = response.status_code
    if r_status == 200:
        # Break up diagnostic feed into individual events
        if api_call == 'report/getDiagnosticFeed':
            state = helper.get_check_point("diagnosticFeed")
            r_json = response.json()
            helper.log_debug("Got response: {}".format(r_json))

            last_timestamp = 0
            for e in r_json.get("diagnosticEvents", []):
                # Only write events if we haven't seen them yet
                if state is None or e.get("timestamp", 0) > int(state):
                    helper.log_debug("Sending event: {}".format(json.dumps(e)))
                    event = helper.new_event(data=json.dumps(e), 
                                source=helper.get_input_type(), 
                                index=helper.get_output_index(), 
                                sourcetype=helper.get_sourcetype())
                    ew.write_event(event)
                if e.get("timestamp", 0) > last_timestamp:
                    last_timestamp = e.get("timestamp", 0)
        
            helper.save_check_point("diagnosticFeed", str(last_timestamp))
        # Handle everything else by just dumping the json into splunk
        else:
            helper.log_debug("Sending event: {}".format(event_data))
            event = helper.new_event(data=response.text, 
                            source=helper.get_input_type(), 
                            index=helper.get_output_index(), 
                            sourcetype=helper.get_sourcetype())
            ew.write_event(event)
    else:
        helper.log_debug("Something went wrong with the api call: [{}] {}".format(r_status, response.text))
        response.raise_for_status() 
