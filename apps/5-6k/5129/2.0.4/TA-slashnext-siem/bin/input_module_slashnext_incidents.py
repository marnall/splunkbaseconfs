
# encoding = utf-8

import os
import sys
import time
from datetime import datetime, timedelta
import json

def create_event(helper, ew, json_data):
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(json_data), time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    ew.write_event(event)

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # slashnext_api_key = definition.parameters.get('slashnext_api_key', None)
    # historical_run = definition.parameters.get('historical_run', None)
    pass

def collect_events(helper, ew):
    try:
        
        # SlashNext Api Key
        API_KEY =  helper.get_arg('slashnext_api_key')
        # Historical Run
        HISTORICAL_RUN =  helper.get_arg('historical_run')
        checkpoint = helper.get_input_stanza_names()+':last_run' if helper.get_input_stanza_names() else 'last_run'
        start_time = helper.get_check_point(checkpoint)
        end_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        test_time = 'Ingesting Data'
        # Save checkpoint for next run
        helper.save_check_point(checkpoint,end_time)
        if start_time is None:
            if HISTORICAL_RUN:
                start_time = '2000-01-01 00:00:00'
                helper.log_info('Slashnext Siem historical run started')
            else:
                # If historical_run is False.
                # Save Checkpoint data & exit
                exit(0)
        
        # Fetch incidents and ingest in splunk.
        helper.log_info('Slashnext Processing Starting')
        # prepare the request payload
        payload = {
            "page": 1,
            "rpp": 2,
            "filters": [
                {"time": "{0}#{1}".format(start_time, end_time)}
            ]
        }
        headers = {
        "Content-type": "application/json",
        "apikey": API_KEY,
        }
        counter = 0
        total_event = 0
        process_data = True
        url = 'https://siemapis.slashnext.cloud/api/integration/v4/incidents/list'
        method = 'POST'
        retry = True
        
        url_details = 'https://siemapis.slashnext.cloud/api/integration/v4/incidents/detail'
        
        
        while process_data or counter < total_event:
            process_data = False
            response = helper.send_http_request(url, method, parameters=None, payload=payload,
                                            headers=headers, cookies=None, verify=True, cert=None,
                                            timeout=None, use_proxy=True)
            if response.status_code == 200:
                helper.log_info('Slashnext Listing API Working fine!')
                r_json = response.json()
                total_event = r_json['data']['totalitems']
                for item in r_json['data']['items']:
                    # Extract Incident ID for Details API Payload
                    incidentId = item["id"]
                    infvector = item["infectionvector"]
                    # Create Payload 
                    payload_details = {
                        "incidentId" : incidentId,
                        "infvector" : infvector
                    }
                    # Call details API
                    helper.log_info('Calling SlashNext Details API')
                    response_details = helper.send_http_request(url_details, method, parameters=None, payload=payload_details,
                                            headers=headers, cookies=None, verify=True, cert=None,
                                            timeout=None, use_proxy=True)
                    # If the API is successfully called, convert to json and ingest the data
                    if response_details.status_code == 200:
                        helper.log_info('Slashnext Details API Working fine!')
                        rd_json = response_details.json()
                        details_event = rd_json['data']
                        
                        
                        if infvector == 'email':
                            event_type = details_event['threat']['eventType']
                            if event_type == 'Email Text':
                                bec_event = {
                                    'Targeted User' : item['fullname'],
                                    'Targeted User Email' : item['email'],
                                    'Title' : details_event['user']['title'],
                                    'User Group' : item['groupname'],
                                    'Department' : item['department'],
                                    'Infection Vector' : item['infectionvector'],
                                    'Sender Email' : item['sender_email'],
                                    'Email Subject' : item['email_subject'],
                                    'Email Time' : item['email_time'],
                                    'Incident Time' : details_event['incident']['incidentTime'],
                                    'Email From - Display Name' : item['emailfrom_name'],
                                    'Email From - Email' : item['emailfrom_email'],
                                    'Threat Type' : item['threattypeText'],
                                    'Threat Name' : item['threatname'],
                                    'Detected Via' : item['eptypeText'],
                                    'Remediation Action' : item['remediation_action'],
                                    'Impersonation' : item['isimpersonated'],
                                    'VIP' : item['isvip'],
                                    'Has Attachment' : details_event['threat']['has_attachment'],
                                    'Has URL' : item['hasurl'],
                                    'Total User Incident' : item['totalincidents'],
                                    'User Risk Score' : details_event['user']['userRiskScore']
                                }
                                helper.log_info('Ingesting BEC Event')
                                create_event(helper, ew, bec_event)
                            else:
                                email_event = {
                                    'Targeted User' : item['fullname'],
                                    'Targeted User Email' : item['email'],
                                    'Title' : details_event['user']['title'],
                                    'User Group' : item['groupname'],
                                    'Department' : item['department'],
                                    'Infection Vector' : item['infectionvector'],
                                    'Sender Email' : item['sender_email'],
                                    'Email Subject' : item['email_subject'],
                                    'Email Time' : item['email_time'],
                                    'Incident Time' : details_event['incident']['incidentTime'],
                                    'Email From - Email' : item['emailfrom_email'],
                                    'Threat Type' : item['threattypeText'],
                                    'Malicious URL/Attachment' : item['phishingUrl'],
                                    'Threat Name' : item['threatname'],
                                    'Detected Via' : item['eptypeText'],
                                    'Remediation Action' : item['remediation_action'],
                                    'Impersonation' : item['isimpersonated'],
                                    'VIP' : item['isvip'],
                                    'Has Attachment' : details_event['threat']['has_attachment'],
                                    'Has URL' : item['hasurl'],
                                    'Total User Incident' : item['totalincidents'],
                                    'User Risk Score' : details_event['user']['userRiskScore']
                                }
                                helper.log_info('Ingesting Email Event')
                                create_event(helper, ew, email_event)
                        else:
                            event = {
                                'Targeted User' : item['fullname'],
                                'Targeted User Email' : item['email'],
                                'Title' : details_event['user']['title'],
                                'User Group' : item['groupname'],
                                'Department' : item['department'],
                                'Infection Vector' : item['infectionvector'],
                                'Device Name' : details_event['incident']['device'],
                                'SMS Sender' : details_event['threat']['smsSender'],
                                'SMS Content' : details_event['threat']['smsContent'],
                                'Incident Time' : details_event['incident']['incidentTime'],
                                'Threat Name' : item['threatname'],
                                'Malicious URL' : item['phishingUrl'],
                                'User Click' : details_event['threat']['userClicks'],
                                'URL Click Blocked' : details_event['incident']['threatBlocked'],
                                'Warning Served' : details_event['incident']['warningServed'],
                                'Detected Via' : item['eptypeText'],
                                'Remediation Action' : item['remediation_action'],
                                'Impersonation' : item['isimpersonated'],
                                'VIP' : item['isvip'],
                                'Has Attachment' : details_event['threat']['has_attachment'],
                                'Total User Incident' : item['totalincidents'],
                                'User Risk Score' : details_event['user']['userRiskScore']
                            }
                            helper.log_info('Ingesting Mobile Event')
                            create_event(helper, ew, event)
                        counter += 1
                    else:
                        helper.log_error('Slashnext Details API Failed!')
                payload['page'] += 1
            else :
                helper.log_error('Slashnext Listing API Failed!')
                if retry:
                    retry = False
                else:
                    helper.save_check_point(checkpoint,start_time)
                    exit(1)
    except Exception as e:
        helper.save_check_point(checkpoint,start_time)
        helper.log_error("error: {0}".format(e))
