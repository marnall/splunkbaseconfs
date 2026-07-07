
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
def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # pmc_hostname = definition.parameters.get('pmc_hostname', None)
    # pmc_client_id = definition.parameters.get('pmc_client_id', None)
    # pmc_client_secret = definition.parameters.get('pmc_client_secret', None)
    # pmc_batch_size = definition.parameters.get('pmc_batch_size', None)
    # pmc_log_level = definition.parameters.get('pmc_log_level', None)
    pass
########## -----------------------------------------------


########## Base function for event collection
def collect_events(helper, ew):    
    # Before we proceed, make sure we aren't sleeping due to a previous API rate limit violation
    sleep_until_date = utils.get_sleep_until(helper)
    if sleep_until_date != None:
        if sleep_until_date > datetime.now():
            # If we haven't hit the sleep-until date yet, log something and exit
            helper.log_info('Still sleeping due to API rate limit violation; will not attempt to pull events this interval period')
            return
        else:
            # If we've hit or passed the sleep-until date, then clear it and start pulling data again
            utils.clear_sleep_until(helper)

    hostname = helper.get_arg('pmc_hostname')
    client_id = helper.get_arg('pmc_client_id')
    client_secret = helper.get_arg('pmc_client_secret')
    batch_size = int(helper.get_arg('pmc_batch_size'))
    connection_timeout = helper.get_arg('connection_time_out')
    read_timeout = helper.get_arg('read_time_out')
    interval = int(helper.get_arg('interval'))

    source = helper.get_input_type() or 'beyondtrust_pm_cloud_rest_api_events' or 'beyondtrust_pm_cloud_rest_api_client_events'
    source_type = helper.get_sourcetype() or 'beyondtrust:pmcloud:ecs'
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
    total_ingested_events_count = 0
    total_failed_events_count = 0
    default_start_date = datetime.utcnow() - timedelta(seconds=interval)  # by default go back 1 interval length 
    last_ingested_event_date = utils.get_start_date(helper, default_start_date) + timedelta(milliseconds=1)  # add 1 ms so we don't get the last event over and over
    original_start_date = last_ingested_event_date
    
    helper.log_debug(f'Last Ingested Client Audits Datetime: {last_ingested_event_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}')
    helper.log_debug(f'source={source}, index={index}, sourcetype={source_type}')

    while True:
        events_batch = pmcloud.get_client_events_batch(helper, auth_token, hostname, last_ingested_event_date, batch_size, connection_timeout, read_timeout)    
        # If no event data, exit
        if events_batch == None:
            helper.log_info('No event data returned; exiting')
            return

        for event_data in events_batch['events']:
            try:
                # There's no way to exactly match the incoming format so the value will need to be sanitized before attempting to parse as datetime
                if event_data['event']['ingested'].endswith('+00:00'):
                    tz_offset_index = event_data['event']['ingested'].index('+00:00')
                    # Because the fractional seconds cannot go beyond the microsecond position for conversion via datetime.strptime(), ensure the index is not > 26
                    if tz_offset_index > 26:
                        tz_offset_index = 26
                    trimmed_date = event_data['event']['ingested'][0:tz_offset_index]
                    try:
                        last_ingested_event_date = datetime.strptime(trimmed_date, '%Y-%m-%dT%H:%M:%S.%f')
                    except ValueError:
                        # In some instances the parsing WITH microseconds may fail, but we can still try and parse with that bit
                        microseconds_index = len(trimmed_date)
                        if '.' in trimmed_date:
                            microseconds_index = trimmed_date.index('.')
                        trimmed_date = trimmed_date[0:microseconds_index]                        
                        last_ingested_event_date = datetime.strptime(trimmed_date, '%Y-%m-%dT%H:%M:%S')
                    helper.log_debug(f'Original ingested date [{event_data["event"]["ingested"]}] sanitized to [{trimmed_date}]')
                else:
                    helper.log_warning(f'Event ingested datetime ({event_data["event"]["ingested"]}) is not in the expected format! Add-on will attempt to write event anyway, but the value could not be captured for the next request')
                event_to_write = helper.new_event(source=source, index=index, sourcetype=source_type, host=event_data['host']['hostname'], data=json.dumps(event_data))
                ew.write_event(event_to_write)
                total_ingested_events_count += 1
            except Exception as e:                
                total_failed_events_count += 1
                helper.log_error(f'Failed to ingest event - {str(e)}: {event_data["event"]["action"]} (ID: {event_data["event"]["id"]}) at {event_data["event"]["ingested"]}')

        # Save the ingested date of the last event that was processed so the next run can pick up where this one left off
        utils.save_start_date(helper, last_ingested_event_date)

        # If the number of events returned in this batch is smaller than the batch size, it must be the last batch
        if events_batch['totalRecordsReturned'] < batch_size:
            break
    
    helper.log_info(f'Ingested {str(total_ingested_events_count)} events from {hostname} starting at {original_start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}')
    if total_failed_events_count > 0:
        helper.log_error('Failed to ingest a total of ' + str(total_failed_events_count) + ' events from ' + hostname + ' starting at ' + original_start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
########## -----------------------------------------------