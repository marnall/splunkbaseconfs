# encoding = utf-8
from html import entities
import re
import json
from client_api import *
import global_variables
from typing import List, Dict


def validate_input(helper, definition):
    pass


def _get_arguments(helper):
    entity_arg = helper.get_arg('entities')
    # Stringify and remove spaces from entities enter entities into list
    entities = str(entity_arg).replace(" ", "").split(",")
    
    args = {
        'api_key': helper.get_global_setting("api_token"),
    
        'entities': entities,       
        'fetch_pdns': helper.get_arg('fetch_pdns'),
        'fetch_dhcp': helper.get_arg('fetch_dhcp'),
        'filter_training_events': helper.get_arg('filter_training_events')
    }
    
    helper.log_info('Arguments retrieved.')
    return args


def _get_entity_type(entity: str) -> str:
    reg = re.compile("^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")
    
    if reg.match(entity):
        entity_type = "ip address"
    else:
        entity_type = "domain/hostname"
            
    return entity_type


def _get_entities(helper, args) -> List[dict]:    
    # Get global variable configuration, api_token
    api_key = args['api_key']
    
    # get user agent from global variables
    user_agent = global_variables.user_agent
    api_object = InsightAPI(api_key, user_agent)
    
    entities_arg = args['entities']
    helper.log_info(f'Searching for {len(entities_arg)} entitities.')
    
    entities = []
    for entity_arg in entities_arg:
        entity = _get_entity(helper = helper, args = args, api_object = api_object, entity_arg = entity_arg)
        entities.append(entity)
        
    return entities
        
        
def _get_entity(helper, args: Dict[str, str], api_object: InsightAPI, entity_arg: str):
    helper.log_info(f'Searching for entity {entity_arg}.')
    
    entity_summary = api_object.get_entity_summary(helper, entity_arg)
    
    # Check the response status, if the status is not successful, raise requests.HTTPError
    entity_summary.raise_for_status()
    
    helper.log_info(f'Entity {entity_arg} successfully found.')
    helper.log_info(entity_summary)
    
    # Get response body as json. If the body text is not a json string, raise a ValueError
    entity_summary_response = entity_summary.json()        
    helper.log_debug("Raw response: {}".format(entity_summary_response))
    
    # Insert entity type to summary
    entity_summary_response['summary'].update({'type': _get_entity_type(entity = entity_arg)})
    
    # Create this entity
    entity = {'summary': entity_summary_response['summary']}
    _enrich_entity(helper = helper, args = args, api_object = api_object, entity_arg = entity_arg, entity = entity)
    
    return entity
        

def _enrich_entity(helper, args: Dict[str, str], api_object: InsightAPI, entity_arg: str, entity: str):
    helper.log_debug(f'Enriching entity {entity_arg}.')
        
    # If entity enrichment is checked, then extract all the src and dst ips so they can be sent for bulk lookup
    fetch_pdns = args['fetch_pdns']
    fetch_dhcp = args['fetch_dhcp']
    filter_training_events = args['filter_training_events']
    
    # Get PDNS/VT/DHCP info if requested
    if fetch_pdns:
        pdns_data = api_object.get_entity_pdns(helper, [entity_arg], filter_training_events)
        entity.update({"pdns": pdns_data})
        
        helper.log_info(f'PDNS data has been added to entity {entity_arg}.')

    if fetch_dhcp:
        dhcp_data = api_object.get_entity_dhcp(helper, [entity_arg],
                                               filter_training_events)
        entity.update({"dhcp": dhcp_data})
        
        helper.log_info(f'DHCP data has been added to entity {entity_arg}.')

        
def _create_splunk_events(helper, ew, entity_list: List[dict]):
    helper.log_debug(f'Creating Splunk events.')

    # Iterate events json and write each event to splunk
    for entity in entity_list:
        # Build the splunk event
        splunk_event = helper.new_event(source=helper.get_input_type(),
                                        index=helper.get_output_index(),
                                        sourcetype=helper.get_sourcetype(),
                                        data=json.dumps(entity))

        # Write the splunk event
        ew.write_event(splunk_event)

    helper.log_info(f'{len(entity_list)} Splunk events were successfully created.')


def collect_events(helper, ew):    
    helper.log_info('Collecting events.')
    # Get args
    args = _get_arguments(helper)

    entities = _get_entities(helper = helper, args = args)
    _create_splunk_events(helper = helper, ew = ew, entity_list = entities)