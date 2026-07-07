
# encoding = utf-8

from datetime import datetime, timedelta
import time
import rs_client as rsclient
import common_utils as utils
import session_parser as sessionparser
import xml.etree.ElementTree as ET
import re

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
    # rs_hostname = definition.parameters.get('rs_hostname', None)
    # rs_client_id = definition.parameters.get('rs_client_id', None)
    # rs_client_secret = definition.parameters.get('rs_client_secret', None)
    pass

def collect_events(helper, ew):
    rs_hostname = helper.get_arg('rs_hostname')
    rs_client_id = helper.get_arg('rs_client_id')
    rs_client_secret = helper.get_arg('rs_client_secret')
    interval = int(helper.get_arg('interval'))

    auth_token = rsclient.get_auth_token(helper, rs_hostname, rs_client_id, rs_client_secret)
    # If no auth token, exit
    if auth_token == None:
        helper.log_warning('No auth token returned; exiting')
        return
    
    source = helper.get_input_type() or 'beyondtrust_rs_reporting_api_session_events'
    source_type = helper.get_sourcetype() or 'beyondtrust:rs:session:cef'
    index = helper.get_output_index() or 'beyondtrust_rs'
    
    default_end_date = int(time.time()) - interval
    last_ingested_event_date = utils.get_end_date(helper, default_end_date) + 1

    helper.log_debug(f"Last ingested date: {datetime.fromtimestamp(last_ingested_event_date).strftime('%Y-%m-%dT%H:%M:%S.%fZ')}")
    helper.log_debug(f'source={source}, index={index}, sourcetype={source_type}')

    session_report = rsclient.get_session_report(helper, auth_token, rs_hostname, last_ingested_event_date)

    session_tree = ET.fromstring(session_report)
    xmlns = __get_xml_namespace(session_tree)

    total_ingested_events_count = 0
    total_failed_events_count = 0

    for session in session_tree:
        # need to get events per session and write them out before moving onto the next session due to splunk ingestion rate limits.
        # unclear if this is an actual rate limit or just splunk services not processing as fast as we can write them out if they are
        # written all at once. if we grab all events first then write them all out, splunk ends up dropping events
        session_events = sessionparser.get_events(helper, session, rs_hostname, xmlns)
        for event_data in session_events['events']:
            try:
                event_to_write = helper.new_event(source=source, index=index, sourcetype=source_type, host=rs_hostname, data=event_data)
                ew.write_event(event_to_write)
                last_ingested_event_date = session_events['end_time']
                total_ingested_events_count += 1
            except Exception as e:
                total_failed_events_count += 1
                helper.log_error(f'Failed to ingest event: {event_data} - {str(e)}')
        
    # Save the ingested date of the last event that was processed so the next run can pick up where this one left off.
    utils.save_end_date(helper, last_ingested_event_date)

    helper.log_info(f'Ingested {total_ingested_events_count} total')
    helper.log_warning(f'Failed {total_failed_events_count} total')

########## -----------------------------------------------

def __get_xml_namespace(session_tree: ET.Element):
    # need to manually regex out the namespace so we can pass it along for xml searching to work
    m = re.match(r'\{(.*)\}', session_tree.tag)
    return { 'xmlns': m.group(1) }
