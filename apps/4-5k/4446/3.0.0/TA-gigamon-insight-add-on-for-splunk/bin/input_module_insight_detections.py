# encoding = utf-8
import json
from datetime import datetime
from client_api import *
import global_variables
from datetime import timedelta, datetime
from typing import List, Dict, Any

TRAINING_ACC = 'f6f6f836-8bcd-4f5d-bd61-68d303c4f634'
DEFAULT_START_DATE = '2021-11-01T00:00:00.000000Z'
MAX_DETECTIONS = 1000

def validate_input(helper, definition):
    pass


def _get_arguments(helper):
    entity_arg = helper.get_arg('entities')
    # Stringify and remove spaces from entities enter entities into list
    entities = str(entity_arg).replace(" ", "").split(",")
    
    args = {
        'api_key': helper.get_global_setting("api_token"),
    
    
        'include_signature': helper.get_arg('include_signature'),
        'include_description': helper.get_arg('include_description'),
        'include_events': helper.get_arg('include_events'),
        'include_pdns': helper.get_arg('include_pdns'),
        'include_dhcp': helper.get_arg('include_dhcp'),
        
        'start_date': helper.get_arg('start_date'),
        'account_uuid': helper.get_arg('account_uuid'),
        
        'severity_levels': helper.get_arg('severity_levels'),
        'confidence_levels': helper.get_arg('confidence_levels'),
        
        'pull_only_active': helper.get_arg('status'),
        'pull_muted_rules': helper.get_arg('pull_muted_rules'),
        'pull_muted_devices': helper.get_arg('pull_muted_devices'),
        'pull_muted_detections': helper.get_arg('pull_muted_detections'),
        
        'filter_training_detections': helper.get_arg('filter_training_detections'),
    }
    
    helper.log_info('Arguments retrieved.')
    return args

   
def _get_start_date(helper, start_date_arg: str, checkpoint: str ) -> datetime:
    helper.log_debug('Getting the starting date to retrieve events.')
    
    # initialice the start_date as default start date
    start_date = DEFAULT_START_DATE
    
    # If a Start Date argument was provided use it converting it to UTC
    if start_date_arg:
        start_date = start_date_arg

    # If the checkpoint date has been set before, then use it...
    if checkpoint:
        # Convert string to datetime object for formatting (checkpoint are allways created in UTC)
        start_date = checkpoint

    helper.log_info(f'Events will be retrieved since {start_date} UTC.')
           
    return start_date
    

def _get_checkpoint_key(helper) -> str:
    helper.log_debug('Getting checkpoint key.')     
     
    # Get the checkpoint timestamp key for the received event_type and sensor
    stanza_names = helper.get_input_stanza_names()
    prefix = f'{stanza_names}'
    
    last_checkpoint_key = f'{prefix}_last_checkpoint'
    
    helper.log_debug(f'Checkpoint key retrieved ({last_checkpoint_key}).')
    return last_checkpoint_key


def _get_checkpoint(helper) -> str:
    helper.log_debug(f'Getting last checkpoint.')
    
    last_checkpoint_key = _get_checkpoint_key(helper)    
    last_checkpoint = helper.get_check_point(last_checkpoint_key)
        
    helper.log_info(f'Last checkpoint was {last_checkpoint}.')
    
    return last_checkpoint
    
    
def _set_checkpoint(helper, checkpoint_date: str):
    helper.log_debug(f'Setting checkpoint to: {checkpoint_date}.')
    
    last_checkpoint_key = _get_checkpoint_key(helper)
    
    # Convert checkpoint date to datetime so we can increment 1ms
    checkpoint_datetime = datetime.strptime(checkpoint_date, '%Y-%m-%dT%H:%M:%S.%fZ')
    # Increment datetime 1ms. This is to prevent event duplication
    checkpoint_datetime = checkpoint_datetime + timedelta(milliseconds=1)
    
    # Convert back to a string for saving
    checkpoint_date = datetime.strftime(checkpoint_datetime, '%Y-%m-%dT%H:%M:%S.%fZ')
    
    # Delete the old checkpoints
    helper.delete_check_point(last_checkpoint_key)
    
    # Save this timestamp as the last checkpoint for interval poll
    helper.save_check_point(last_checkpoint_key, checkpoint_date)
    
    helper.log_info(f'Checkpoint has been set to: {checkpoint_date}.')


def _process_response(response: Dict[str, Any]):
    # Crete detections list
    detections = []
    rules = {}
    total_count = response['total_count'] if 'total_count' in response else -1
            
    # Put pulled detections and rules into lists
    for detection in response['detections']:
        detections.append(detection)
        
    for rule in response['rules']:
        if not rule['uuid'] in rules:
            rules[rule['uuid']] = rule
    
    return {
        'detections': detections,
        'rules': rules,
        'total_count': total_count
    }
    
    
def _get_detections_inc(helper, args: Dict[str, str], api_object: InsightAPI, checkpoint_date: str, offset: int = 0) -> Dict[str, Any]:
    helper.log_info(f'Retrieving Detections with offset = {offset}.')
           
    response = api_object.get_detections(helper=helper,
                                        sort_by='last_seen',
                                        sort_order='asc',
                                        include='rules',
                                        limit=MAX_DETECTIONS,
                                        account_uuid=args['account_uuid'],
                                        status=args['pull_only_active'],
                                        muted_rule=args['pull_muted_rules'],
                                        muted_device=args['pull_muted_devices'],
                                        muted=args['pull_muted_detections'],
                                        created_or_shared_start_date=checkpoint_date,
                                        offset=offset)
    
    # Check the response status, if the status is not successful, raise requests.HTTPError
    response.raise_for_status()
    helper.log_info(response)
    
    # Get response body as json. If the body text is not a json string, raise a ValueError
    r_json = response.json()
    helper.log_debug("Raw response: {}".format(r_json))
        
    # Crete detections list
    return _process_response(response = r_json)
    
    
def _get_detections(helper, args: Dict[str, str], api_object: InsightAPI, start_date: str) -> Dict[str, Any]:
    helper.log_info(f'Retrieving Detections from {start_date}.')
    
    result = {
        'total_count': -1,
        'detections': [],
        'rules': {}
    }
    
    offset = 0
    total_count = 0
    
    while result['total_count'] < 0 or offset < result['total_count']:
        next_piece = _get_detections_inc(helper = helper, args = args, api_object = api_object, checkpoint_date = start_date, offset = offset)
        
        if result['total_count'] < 0:
            result['total_count'] = next_piece['total_count']
            
        result['detections'].extend(next_piece['detections'])
        result['rules'] = dict(next_piece['rules'], **result['rules'])
        offset += MAX_DETECTIONS
        
        total_count += len(next_piece['detections'])
    
    helper.log_info(f'{total_count} Detections successfully retrieved.')    
    return result
   
        
def _add_detection_rule(helper, args: Dict[str, str], detection: Dict[str, Any], rules: Dict[str, Any]):
    """ Create a new detection rule.
    """
    # Find the detection's rule in the dictionary and update the detection
    rule = rules[detection['rule_uuid']]

    detection.update({'rule_name': rule['name']})
    detection.update({'rule_description': rule['description']})
    detection.update({'rule_severity': rule['severity']})
    detection.update({'rule_confidence': rule['confidence']})
    detection.update({'rule_category': rule['category']})
    if args['include_description']:
        detection.update({'rule_description': rule['description']})
    if args['include_signature']:
        detection.update({'rule_signature': rule['query_signature']})
   
       
def _get_detection_rule_event(helper, api_object: InsightAPI, detection: Dict[str, Any]):
    # Get rule events if requested
    detection_events = []
    
    helper.log_debug("include events enabled")
    this_response = api_object.get_detection_rule_events(helper=helper,
                                                            uuid=detection['rule_uuid'],
                                                            account_uuid=detection['account_uuid'])
    this_response.raise_for_status()
    this_r_json = this_response.json()
    
    # Move events into its own list
    for event in this_r_json['events']:
        # Filter training events
        if event['customer_id'] != 'chg':
            event.update({'detection_uuid': detection['uuid']})
            detection_events.append(event)
            
    return detection_events
        
                    
def _enrich_entity(helper, args: Dict[str, str], api_object: InsightAPI, entity_arg: str, entity: str):
    helper.log_debug(f'Enriching entity {entity_arg}.')
        
    # If entity enrichment is checked, then extract all the src and dst ips so they can be sent for bulk lookup
    fetch_pdns = args['include_pdns']
    fetch_dhcp = args['include_dhcp']
    filter_training_detections = args['filter_training_detections']
    
    # Get PDNS/VT/DHCP info if requested
    if fetch_pdns:
        pdns_data = api_object.get_entity_pdns(helper, [entity_arg], filter_training_detections)
        entity.update({"pdns": pdns_data})
        
        helper.log_info(f'PDNS data has been added to entity {entity_arg}.')

    if fetch_dhcp:
        dhcp_data = api_object.get_entity_dhcp(helper, [entity_arg],
                                               filter_training_detections)
        entity.update({"dhcp": dhcp_data})
        
        helper.log_info(f'DHCP data has been added to entity {entity_arg}.')
    
 
def _create_splunk_event(helper, ew, args: Dict[str, str], detection: Dict[str, Any], detection_events: List[dict]):
    helper.log_debug(f'Creating Splunk events.')

    
    time_stamp = datetime.strptime(detection['last_seen'], "%Y-%m-%dT%H:%M:%S.%fZ")
    last_seen_timestamp = "{:.3f}".format(time_stamp.timestamp())
    
    # Build the splunk event for this detection
    if detection['rule_severity'] in args['severity_levels'] and detection['rule_confidence'] in args['confidence_levels']:
        helper.log_debug("severity and confidence levels matched")
        this_detection = helper.new_event(time=last_seen_timestamp,
                                            source=helper.get_input_type(),
                                            index=helper.get_output_index(),
                                            sourcetype=helper.get_sourcetype(),
                                            data=json.dumps(detection))

        # Filter training environment detections if necessary
        if not args['filter_training_detections'] or detection['account_uuid'] != TRAINING_ACC:
            ew.write_event(this_detection) 
            helper.log_info(f"Splunk 'Detection' events were successfully created.")

    # Write associated events if requested
        if args['include_events']:
            for event in detection_events:
                time_stamp_event = datetime.strptime(event['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ")
                time_stamp = "{:.3f}".format(time_stamp_event.timestamp())
                this_event = helper.new_event(time=time_stamp,
                                                source=helper.get_input_type(),
                                                index=helper.get_output_index(),
                                                sourcetype=helper.get_sourcetype(),
                                                data=json.dumps(event))
                ew.write_event(this_event)
                
    helper.log_info(f"{len(detection_events)} Splunk 'Detection Rule Event' events were successfully created.")


def collect_events(helper, ew):
    helper.log_info('Collecting events.')
    # Get args
    args = _get_arguments(helper)

    # Get the utc datetime for now
    now = datetime.utcnow()
    
    # Get checkpoint variable, convert to string
    last_checkpoint = _get_checkpoint(helper)
    start_date = _get_start_date(helper = helper, start_date_arg = args['start_date'], checkpoint = last_checkpoint)
    
    # get user agent from global variables
    user_agent = global_variables.user_agent
    # Make API call for detections
    api_object = InsightAPI(args['api_key'], user_agent)
        
    # Get all the detections
    result = _get_detections(helper = helper, args = args, api_object = api_object, start_date = start_date)    

    # Set the checkpoint as the current time date in UTC
    _set_checkpoint(helper = helper, checkpoint_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'))    
        
    # Iterate detections list so we can add some additional information to the results
    for detection in result['detections']:
        # Add the detections' rule
        _add_detection_rule(helper = helper, args = args, detection = detection, rules = result['rules'])
        
        # Add the PDNS and DHCP information if requested
        _enrich_entity(helper = helper, args = args, api_object = api_object, entity_arg = detection['device_ip'], entity = detection)

        # Get rule events if requested
        detection_events = _get_detection_rule_event(helper = helper, api_object = api_object, detection = detection) if args['include_events'] else []

        _create_splunk_event(helper = helper, ew = ew, args = args, detection = detection, detection_events = detection_events)