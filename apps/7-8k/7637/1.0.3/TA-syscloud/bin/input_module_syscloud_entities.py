from datetime import datetime, timezone
import requests
import json
from utils import get_host_url, get_authtoken

def validate_input(helper, definition):
    """
    Validate the inputs
    """

    interval_value = float(definition.parameters.get('interval', None))
    if interval_value < 86400:
        helper.log_error("Interval must be greater than or equal 86400 seconds.")
        raise Exception('Interval must be greater than or equal to 86400 seconds (1 day).')

    index_value = definition.parameters.get('index', None)
    if index_value != 'main':
        helper.log_error('Invalid index name entered, please enter the correct index name as: main')
        raise Exception('Invalid index name entered, please enter the correct index name as: main')

def collect_events(helper, ew):
    """
    Collect and save the entities events
    """

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    headers['authorization'] = get_authtoken(helper, headers)
    headers['x-source'] = 'splunk'

    cloud_value = helper.get_arg('select_clouds')

    for cloud in cloud_value:
        helper.log_info(cloud)
        checkpoint_key = 'entity_domain_' + cloud

        # helper.delete_check_point(checkpointKey)
        checkPoint =  helper.get_check_point(checkpoint_key)
        diff = None

        host = get_host_url() + 'entities/' + cloud + '/domains'

        if checkPoint is not None: 
            current_date = datetime.now(timezone.utc)
            checkpoint_date = datetime.strptime(checkPoint, '%Y-%m-%dT%H:%M:%S.%fZ')
            diff = (current_date - checkpoint_date).days
            if diff <= 0:
                helper.log_info(f'Skipped for cloud :{cloud}')
                continue

        try:
            response = requests.request("GET", host , headers=headers)
            response.raise_for_status()
            if response.status_code == 200:
                # Extract JSON content from the response
                json_response = response.json()

                # Extract the 'value' list from the JSON response
                values = json_response.get('value', [])
                checkpoint_date_value = None

                # Looping through each event
                for event_data in values:
                    helper.log_info(event_data)
                    now = datetime.now(timezone.utc)
                    checkpoint_date_value = now.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                    event_date = {'event_date': checkpoint_date_value}
                    event_data = {**event_date, **event_data}
                    event_data_json = json.dumps(event_data)
                    event = helper.new_event(source=helper.get_input_type(), index='main', sourcetype=helper.get_sourcetype(), data=event_data_json, done=True, unbroken=True)
                    ew.write_event(event)

                # Save Checkpoint
                if checkpoint_date_value is not None:
                    helper.save_check_point(checkpoint_key, checkpoint_date_value)
        except requests.exceptions.RequestException as e:
            helper.log_error("An unexpected error occurred")
            return

    now = datetime.now(timezone.utc)
    event_data = {
        "event_date": now.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        "event_message": "Data Input Populated", 
        "event_input": "syscloud_entities"
    }
    population_event_json = json.dumps(event_data)
    event = helper.new_event(source=helper.get_input_type(), index='main', sourcetype=helper.get_sourcetype(), data=population_event_json, done=True, unbroken=True)
    ew.write_event(event)
    helper.log_info('Success')