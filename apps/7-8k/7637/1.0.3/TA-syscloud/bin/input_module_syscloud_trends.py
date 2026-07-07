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

def get_checkpoint_datekey(trend_type):
    """
    Get the checkpoint date key
    """

    if trend_type == 'backup':
        return 'date'
    else:
        return 'startdate'

def collect_trendentites_events(helper, ew, headers, host):
    """
    Collect and save the trends entities data events
    """

    host = host + '/domain'
    response = requests.request("GET", host , headers=headers)
    response.raise_for_status()
    if response.status_code == 200:
        json_response = response.json()

        # Extract the 'value' list from the JSON response
        values = json_response.get('value', [])

        # Looping through each event
        for event_data in values:
            helper.log_info(event_data)
            event_data.pop("trends", None)
            now = datetime.now(timezone.utc)
            event_date = {'event_date': now.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}
            event_data = {**event_date, **event_data}
            event_data_json = json.dumps(event_data)
            event = helper.new_event(source=helper.get_input_type(), index='main', sourcetype=helper.get_sourcetype(), data=event_data_json, done=True, unbroken=True)
            ew.write_event(event)

def delete_checkpoint(helper, cloud_value):
    """
    Delete the checkpoint data
    """

    trend_services = ['backup', 'restore', 'export']

    for cloud in cloud_value:
        for trend in trend_services:
            checkpoint_key = f'trend_{trend}_{cloud}'
            helper.delete_check_point(checkpoint_key)

    helper.log_info('deleted')

def get_trend_host(trend, cloud):
    """
    Get the Trends Host URL
    """
    return get_host_url() + 'trends/' + trend + '/storage/' + cloud

def collect_events(helper, ew):
    """
    Collect and save the trends data events
    """

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    headers['authorization'] = get_authtoken(helper, headers)
    headers['x-source'] = 'splunk'

    cloud_value = helper.get_arg('select_clouds')
    helper.log_info(cloud_value)
    # delete_checkpoint(helper, cloud_value)

    for cloud in cloud_value:
        trend_services = ['backup', 'restore', 'export']
    
        for trend in trend_services:
            checkpoint_key = f'trend_{trend}_{cloud}'
            helper.log_info('processing trend : ' + trend)
            trend_checkpoint =  helper.get_check_point(checkpoint_key)
            diff = None

            host = get_trend_host(trend, cloud)
            if trend_checkpoint is not None: 
                current_date = datetime.now(timezone.utc)
                checkpoint_date = datetime.strptime(trend_checkpoint, '%Y-%m-%dT%H:%M:%S.%fZ')
                diff = (current_date - checkpoint_date).days
                if diff <= 0:
                    helper.log_info(f'Skipped for trend :{trend}')
                    continue
                host += '?period=' + str(diff) + 'D'

            try:
                trends_response = requests.request("GET", host , headers=headers)
                trends_response.raise_for_status()
                if trends_response.status_code == 200:
                    # Extract JSON content from the response
                    json_response = trends_response.json()
                    # now = datetime.now(timezone.utc)

                    # Extract the 'value' list from the JSON response
                    values = json_response.get('value', [])
                    checkpoint_date_value = None
    
                    # Looping through each event
                    for event_data in values:
                        helper.log_info(event_data)
                        if checkpoint_date_value is None:
                            datekey = get_checkpoint_datekey(trend)
                            if datekey == 'startdate' and trend_checkpoint == str(event_data[datekey]):
                                break
                            checkpoint_date_value = str(event_data[datekey])
                        event_data_json = json.dumps(event_data)
                        event = helper.new_event(source=helper.get_input_type(), index='main', sourcetype=helper.get_sourcetype(), data=event_data_json, done=True, unbroken=True)
                        ew.write_event(event)

                    # if trend == 'backup':
                    #     collect_trendentites_events(helper, ew, headers, get_trend_host(trend, cloud))

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
        "event_input": "syscloud_trends"
    }
    population_event_json = json.dumps(event_data)
    event = helper.new_event(source=helper.get_input_type(), index='main', sourcetype=helper.get_sourcetype(), data=population_event_json, done=True, unbroken=True)
    ew.write_event(event)
    helper.log_info('Success')