
# encoding = utf-8

import json
from datetime import datetime, timedelta
import pmcloud_client as pmcloud
import common_utils as utils

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
########## Base function for input validation
def validate_input(helper, ew):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # pmc_hostname = definition.parameters.get('pmc_hostname', None)
    # pmc_client_id = definition.parameters.get('pmc_client_id', None)
    # pmc_client_secret = definition.parameters.get('pmc_client_secret', None)
    # pmc_page_size = definition.parameters.get('pmc_audit_page_size', None)
    pass
########## -----------------------------------------------

########## Base function for audit data collection
def collect_events(helper, ew):
    # Before we proceed, make sure we aren't sleeping due to a previous API rate limit violation
    sleep_until_date = utils.get_sleep_until(helper)
    if sleep_until_date != None:
        if sleep_until_date > datetime.now():
            # If we haven't hit the sleep-until date yet, log something and exit
            helper.log_info('Still sleeping due to API rate limit violation; will not attempt to pull audit data this interval period')
            return
        else:
            # If we've hit or passed the sleep-until date, then clear it and start pulling data again
            utils.clear_sleep_until(helper)

    hostname = helper.get_arg('pmc_hostname')
    client_id = helper.get_arg('pmc_client_id')
    client_secret = helper.get_arg('pmc_client_secret')
    page_size = int(helper.get_arg('pmc_page_size'))
    connection_timeout = helper.get_arg('connection_time_out')
    read_timeout = helper.get_arg('read_time_out')
    interval = int(helper.get_arg('interval'))

    source = helper.get_input_type() or 'beyondtrust_pm_cloud_rest_api_audit_data'
    source_type = helper.get_sourcetype() or 'beyondtrust:pmcloud:audit'
    index = helper.get_output_index() or 'idx_beyondtrust_pmc'
    
    # Process timeout values
    if connection_timeout != '' and connection_timeout != None:
        connection_timeout = float(connection_timeout)
    else:
        connection_timeout = None
    
    if read_timeout != '' and read_timeout != None:
        read_timeout = float(read_timeout)
    else:
        read_timeout = None
    
    auth_token = pmcloud.get_auth_token(helper, hostname, client_id, client_secret)
    # If no auth token, exit
    if auth_token == None:
        helper.log_warning('No auth token returned; exiting')
        return
    page_number = 1
    total_ingested_activities_count = 0
    total_failed_activities_count = 0
    default_start_date = datetime.utcnow() - timedelta(seconds=interval)  # by default go back 1 interval length 
    last_ingested_activity_date = utils.get_start_date(helper, default_start_date) + timedelta(milliseconds=1)  # add 1 ms so we don't get the last event over and over
    original_start_date = last_ingested_activity_date
    
    helper.log_debug(f'Last Ingested Activity Audits Datetime: {last_ingested_activity_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}')
    helper.log_debug(f'source={source}, index={index}, sourcetype={source_type}')

    while True:
        batch_response = pmcloud.get_activity_audits_batch(helper, auth_token, hostname, original_start_date, datetime.utcnow(), page_size, page_number, connection_timeout, read_timeout) 
        # If no activity audits data, exit
        if batch_response == None:
            helper.log_info('No Activity Audits data returned; exiting')
            return

        helper.log_debug(f'Raw Response: {batch_response}')
        
        total_record_count = batch_response['totalRecordCount']
        activities_data = []     
        activities_data = batch_response['data']
        if not activities_data or len(activities_data) < 1:
            helper.log_info(f'Activity Audits data does not exist for the specified date: {original_start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")} for the API call')
            return
        else:
            helper.log_info(f'Successfully retrieved {len(activities_data)} out of {total_record_count} total Activity Audits records in this batch')

        for activity in activities_data:
            try:
                # If there was no timezone offset supplied, assume UTC and append it to the string so Splunk won't assume local time
                if '+' not in activity["created"]:
                    activity["created"] = activity["created"] + '+00:00'
                created_date = activity["created"]
                end_index = created_date.index('+')
                
                # Because the fractional seconds cannot go beyond the microsecond position for conversion via datetime.strptime(), ensure the index is not > 26
                if end_index > 26:
                    end_index = 26
                trimmed_date = created_date[0:end_index]
                try:
                    last_ingested_activity_date = datetime.strptime(trimmed_date, '%Y-%m-%dT%H:%M:%S.%f')
                except ValueError:
                    # In some instances the parsing WITH microseconds may fail, but we can still try and parse with that bit
                    microseconds_index = len(trimmed_date)
                    if '.' in trimmed_date:
                        microseconds_index = trimmed_date.index('.')
                    trimmed_date = trimmed_date[0:microseconds_index]
                    last_ingested_activity_date = datetime.strptime(trimmed_date, '%Y-%m-%dT%H:%M:%S')
                    
                helper.log_debug(f'Original ingested datetime [{created_date}] sanitized to [{trimmed_date}] for activity audit data ID: {activity["id"]}')
                event_to_write = helper.new_event(source=source, index=index, sourcetype=source_type, host=hostname, data=json.dumps(activity))
                ew.write_event(event_to_write)
                total_ingested_activities_count += 1  
            except Exception as e:                
                total_failed_activities_count += 1
                helper.log_error(f'Failed to write the activity audit data - {str(e)}: {activity}')
        
        # Save the ingested date of the last event that was processed so the next run can pick up where this one left off
        utils.save_start_date(helper, last_ingested_activity_date)

        # If the pageCount in the response is smaller than or equal to the current page number, it must be the last call
        if batch_response['pageCount'] <= page_number:
           break
        # Increment for the next page
        page_number += 1
        
    helper.log_info(f'Ingested {str(total_ingested_activities_count)} events from {hostname} starting at {original_start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}')
    if total_failed_activities_count > 0:
        helper.log_error(f'Failed to ingest a total of {str(total_failed_activities_count)} events from {hostname} starting at {original_start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}')
########## -----------------------------------------------