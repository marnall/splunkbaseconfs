# encoding = utf-8
import json
from datetime import timedelta, datetime, timezone
from client_api import *
import global_variables
import metastream_client_declare
from metastream_client.metastream import fetch_events, fetch_events_by_day, fetch_event_types
from typing import List, Dict

MAXIMUM_RECOVERABLE_DAYS = 7
BUCKET = 'production'

def validate_input(helper, definition):
    pass


def _get_arguments(helper):
    event_types = helper.get_arg('event_types')
    args = {
        'api_key': helper.get_global_setting("api_token"),
        'aws_access_key': helper.get_arg('aws_access_key'),
        'aws_secret_key': helper.get_arg('aws_secret_key'),
        'account_code': helper.get_arg('account_code'),
    
        'event_types': fetch_event_types() if 'all' in event_types else event_types,
        'days_to_collect': helper.get_arg('days_to_collect'),
       
        'fetch_pdns': helper.get_arg('fetch_pdns'),
        'fetch_dhcp': helper.get_arg('fetch_dhcp')
    }
    helper.log_info('Arguments retrieved.')
    return args
    
 
    
def _get_start_date(helper, days_to_collect: str, checkpoint: str ) -> datetime:
    helper.log_debug('Getting the starting date to retrieve events.')
    
    # Get the date now for last usage
    now = datetime.now(timezone.utc)
    default_start_date = now - timedelta(days=MAXIMUM_RECOVERABLE_DAYS)

    # initialice the start_date as default start date (7 days ago)
    start_date = default_start_date
    
    # If a Collect From Date argument was provided use it converting it to UTC
    if days_to_collect:
        try:
            delta_days = int(days_to_collect)
            start_date = now - timedelta(days=delta_days)
        except Exception as e:
            helper.log_warning(f"Days to collect argument ({days_to_collect}) cannot be parsed ({str(e)}). Retrieving events from {MAXIMUM_RECOVERABLE_DAYS} days ago.")
            start_date = default_start_date 


    # If the checkpoint date has been set before, then use it...
    if checkpoint:
        # Convert string to datetime object for formatting (checkpoint are allways created in UTC)
        start_date = datetime.strptime(checkpoint, '%Y-%m-%dT%H:%M:%S.%f').astimezone().replace(tzinfo=timezone.utc)

    if start_date < default_start_date:
        start_date = default_start_date
     
    start_date_str = datetime.strftime(start_date, '%Y-%m-%dT%H:%M:%S.%f')
    helper.log_info(f'Events will be retrieved since {start_date_str} UTC.')
           
    return start_date
    

def _get_checkpoint_key(helper, event_type: str = 'all', sensor: str = 'all') -> str:
    helper.log_debug(f'Getting checkpoint key for event type {event_type} and sensor {sensor}.')
     
    # Get the checkpoint timestamp key for the received event_type and sensor
    stanza_names = helper.get_input_stanza_names()
    prefix = f'{stanza_names}_{event_type}_{sensor}'
    
    last_checkpoint_key = f'{prefix}_last_checkpoint'
    
    helper.log_debug(f'Checkpoint key retrieved ({last_checkpoint_key}).')
    return last_checkpoint_key


def _get_checkpoint(helper, event_type: str = 'all', sensor: str = 'all') -> str:
    helper.log_debug(f'Getting checkpoint for event type {event_type} and sensor {sensor}.')
    
    last_checkpoint_key = _get_checkpoint_key(helper, event_type, sensor)    
    last_checkpoint = helper.get_check_point(last_checkpoint_key)
        
    helper.log_info(f'Last checkpoint for event type {event_type} and sensor {sensor} was {last_checkpoint}.')
    return last_checkpoint
    
    
def _set_checkpoint(helper, checkpoint_date: str, event_type: str = 'all', sensor: str = 'all'):
    helper.log_debug(f'Setting checkpoint for event type {event_type} and sensor {sensor} to: {checkpoint_date}.')
    
    last_checkpoint_key = _get_checkpoint_key(helper, event_type, sensor)
    
    # Drop the trailing "Z" from the checkpoint_date if it exists so we can save it
    checkpoint_date = checkpoint_date.replace("Z", "")
    # Convert checkpoint date to datetime so we can increment 1ms
    checkpoint_datetime = datetime.strptime(checkpoint_date, '%Y-%m-%dT%H:%M:%S.%f')
    # Increment datetime 1ms. This is to prevent event duplication
    checkpoint_datetime = checkpoint_datetime + timedelta(milliseconds=1)
    
    # Convert back to a string for saving
    checkpoint_date = datetime.strftime(checkpoint_datetime, '%Y-%m-%dT%H:%M:%S.%f')
    
    # Delete the old checkpoints
    helper.delete_check_point(last_checkpoint_key)
    
    # Save this timestamp as the last checkpoint for interval poll
    helper.save_check_point(last_checkpoint_key, checkpoint_date)
    
    helper.log_info(f'Checkpoint for event type {event_type} and sensor {sensor} has been set to: {checkpoint_date}.')

      
def _enrich_events(helper, args: Dict[str, str], events: List[dict]):
    # If entity enrichment is checked, then extract all the src and dst ips so they can be sent for bulk lookup
    fetch_pdns = args['fetch_pdns']
    fetch_dhcp = args['fetch_dhcp']
    
    # Get global variable configuration, api_token
    api_key = args['api_key']
    
    # get user agent from global variables
    user_agent = global_variables.user_agent
    api_object = InsightAPI(api_key, user_agent)
    
    entities = []
    if fetch_pdns or fetch_dhcp:
        
        helper.log_debug(f'Enriching {len(events)} events.')
        
        for event in events:
            # Extract the src and dst IPs from each returned event
            src_ip = event['src_ip'] if 'src_ip' in event else ""
            dst_ip = event['dst_ip'] if 'dst_ip' in event else ""
            # Add src and dst IPs to the entities list if they are unique
            if src_ip and src_ip not in entities:
                entities.append(src_ip)
            if dst_ip and dst_ip not in entities:
                entities.append(dst_ip)
                
    # Get PDNS/VT/DHCP info if requested
    if fetch_pdns:
        pdns_data = api_object.get_entity_pdns(helper, entities)
        # Add pdns data to events
        for event in events:
            for entry in pdns_data:
                if 'src_ip' in event and event['src_ip'] == entry:
                    event['src_ip_enrichments'].update({'pdns': pdns_data[entry]})
        
        helper.log_info(f'PDNS data has been added to {len(events)} events.')

    if fetch_dhcp:
        dhcp_data = api_object.get_entity_dhcp(helper, entities)
        # Add dhcp data to events
        for event in events:
            for entry in dhcp_data:
                if 'dst_ip' in event and event['dst_ip'] == entry:
                    event['dst_ip_enrichments'].update({'dhcp': dhcp_data[entry]})
        
        helper.log_info(f'DHCP data has been added to {len(events)} events.')


def _create_splunk_events(helper, ew, events: List[dict], start_date: datetime, event_type: str):
    helper.log_debug(f'Creating Splunk events.')
    
    # Iterate through events and write each as a Splunk event
    checkpoint_date = start_date.strftime('%Y-%m-%dT%H:%M:%S.%f')
    latest_date = start_date
    
    for event in events:
        # Check counter for last event. If it is, capture the timestamp and set as checkpoint date
        event_timestamp = event['timestamp'].replace("Z", "")
        time_stamp = datetime.strptime(event_timestamp, '%Y-%m-%dT%H:%M:%S.%f').astimezone().replace(tzinfo=timezone.utc)
        
        if  latest_date < time_stamp:
            latest_date = time_stamp
            checkpoint_date = event['timestamp']
        
        # Build the splunk event
        # Get the timestamp from the event
        event_timestamp = "{:.3f}".format(time_stamp.timestamp())
        splunk_event = helper.new_event(time=event_timestamp,
                                        source=helper.get_input_type(),
                                        index=helper.get_output_index(),
                                        sourcetype=helper.get_sourcetype(),
                                        data=json.dumps(event))
        # Write the splunk event
        ew.write_event(splunk_event)
        
    helper.log_info(f'{len(events)} Splunk events were successfully created.')
    _set_checkpoint(helper, checkpoint_date, event_type)
 
    
def _collect_events_by_day(helper, ew, args: Dict[str, str], start_date: datetime, event_type: str, env: str):
    start_day = start_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)   
    str_start_day = start_day.strftime('%Y-%m-%d')
    helper.log_info('Searching for events {} occurred on {}.'.format(event_type, str_start_day))
            
    count = 0
    total = 0
    for events in fetch_events_by_day(day = start_day, event_type = event_type, access_key = args['aws_access_key'], secret_key = args['aws_secret_key'], account_code = args['account_code'], api_token = args['api_key'], env = env):
        count += 1
        total += len(events)
        
        helper.log_info(f'{len(events)} were retrieved in block# {count}')
        
        _enrich_events(helper, args, events)
        _create_splunk_events(helper, ew, events, start_day, event_type)
        
    helper.log_info(f'{total} events were retrieved for event type {event_type} on day {str_start_day}')
    next_day = start_day + timedelta(days=1) 
    
    checkpoint_date = next_day.strftime('%Y-%m-%dT%H:%M:%S.%f')
    _set_checkpoint(helper, checkpoint_date, event_type)

    
def _collect_events_since(helper, ew, args: Dict[str, str], start_date: datetime, event_type: str, env: str):  
    str_start_date = start_date.strftime('%Y-%m-%dT%H:%M:%S.%f')
    helper.log_info('Searching for events {} from {}.'.format(event_type, str_start_date))
        
    count = 0
    total = 0
    for events in fetch_events(start_date = start_date, event_types = [event_type], access_key = args['aws_access_key'], secret_key = args['aws_secret_key'], account_code = args['account_code'], api_token = args['api_key'], env = env):
        count += 1
        total = len(events)
        
        helper.log_info(f'{len(events)} were retrieved in block# {count}')
        
        _enrich_events(helper, args, events)
        _create_splunk_events(helper, ew, events, start_date, event_type)
        
    helper.log_info(f'{total} events were retrieved for event type {event_type} since {str_start_date}')
    
        
def collect_events(helper, ew):
    helper.log_info('Collecting events.')
    # Get args
    args = _get_arguments(helper)
    
    event_types = args['event_types']
    for event_type in event_types:
        
        # Get checkpoint
        last_checkpoint = _get_checkpoint(helper, event_type)
    
        # Get start date
        start_date = _get_start_date(helper, args['days_to_collect'], last_checkpoint)
        
        now = datetime.now(timezone.utc)
        delta_days = (now - start_date).days
        if delta_days > 0: start_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        
        while delta_days > 0:
            _collect_events_by_day(helper, ew, args, start_date, event_type, BUCKET)
            
            start_date = start_date + timedelta(days=1)
            delta_days = delta_days - 1
    
        _collect_events_since(helper, ew, args, start_date, event_type, BUCKET)