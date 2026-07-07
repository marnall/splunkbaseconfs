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

def collect_trendentites_counts(helper, ew, headers, service, cloud):
    """
    Collect and save the entities counts events
    """

    trends_host = get_host_url() + 'trends/items/' + cloud + '/' + service
    response = requests.request("GET", trends_host , headers=headers)
    response.raise_for_status()
    try:
        if response.status_code == 200:
            event_data = response.json()

            now = datetime.now(timezone.utc)
            event_date = {'event_date': now.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}
            event_data = {**event_date, **event_data}
            event_data_json = json.dumps(event_data)
            event = helper.new_event(source=helper.get_input_type(), index='main', sourcetype=helper.get_sourcetype(), data=event_data_json, done=True, unbroken=True)
            ew.write_event(event)
    except requests.exceptions.RequestException as e:
        helper.log_error("An unexpected error occurred")    

def collect_trendentites_utilisedstorage(helper, ew, headers, cloud):
    """
    Collect and save the entities utilisedstorage events
    """

    trends_host = get_host_url() + 'trends/backup/utilisedstorage/' + cloud + '/user'
    response = requests.request("GET", trends_host , headers=headers)
    response.raise_for_status()
    try:
        if response.status_code == 200:
            json_response = response.json()

            for event_data in json_response:
                now = datetime.now(timezone.utc)
                event_date = {'event_date': now.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}
                event_data = {**event_date, **event_data}
                event_data_json = json.dumps(event_data)
                event = helper.new_event(source=helper.get_input_type(), index='main', sourcetype=helper.get_sourcetype(), data=event_data_json, done=True, unbroken=True)
                ew.write_event(event)
    except requests.exceptions.RequestException as e:
        helper.log_error("An unexpected error occurred")  

def collect_trendentites_errors(helper, ew, headers, cloud):
    """
    Collect and save the entities errors events
    """

    trends_host = get_host_url() + 'trends/backup/errors/' + cloud
    response = requests.request("GET", trends_host , headers=headers)
    response.raise_for_status()
    try:
        if response.status_code == 200:
            event_data = response.json()

            now = datetime.now(timezone.utc)
            event_date = {'event_date': now.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}
            event_data = {**event_date, **event_data}
            event_data_json = json.dumps(event_data)
            event = helper.new_event(source=helper.get_input_type(), index='main', sourcetype=helper.get_sourcetype(), data=event_data_json, done=True, unbroken=True)
            ew.write_event(event)
    except requests.exceptions.RequestException as e:
        helper.log_error("An unexpected error occurred") 

def delete_checkpoint(helper, cloud_value):

    for cloud in cloud_value:
        checkpointKey = 'trenddatautils_' + cloud
        helper.delete_check_point(checkpointKey)
        
    helper.log_info('deleted')

def collect_events(helper, ew):
    """
    Collect and save the entities events
    """

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    headers['authorization'] = get_authtoken(helper, headers)
    headers['x-source'] = 'splunk'

    cloud_value = helper.get_arg('select_clouds')
    helper.log_info(cloud_value)
    # delete_checkpoint(helper, cloud_value)

    for cloud in cloud_value:
        services = ['restore', 'export']
        trendUtilCheckPoint = None
        diff = None
        checkpointKey = 'trenddatautils_' + cloud
        trendUtilCheckPoint = helper.get_check_point(checkpointKey)
        currentDate = datetime.now(timezone.utc)
        currentDateStr = currentDate.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        if trendUtilCheckPoint is not None: 
            checkpointDate = datetime.strptime(trendUtilCheckPoint, '%Y-%m-%dT%H:%M:%S.%fZ')
            diff = (currentDate - checkpointDate).days

        if diff is None or diff > 0:
            for service in services:
                collect_trendentites_counts(helper, ew, headers, service, cloud)

            collect_trendentites_utilisedstorage(helper, ew, headers, cloud)
            collect_trendentites_errors(helper, ew, headers, cloud)

            helper.save_check_point(checkpointKey, currentDateStr)

            # Log the checkpoint date as string
            # helper.log_info('checkpoint : ' + currentDateStr)
    now = datetime.now(timezone.utc)
    event_data = {
        "event_date": now.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        "event_message": "Data Input Populated", 
        "event_input": "syscloud_trendutils"
    }
    population_event_json = json.dumps(event_data)
    event = helper.new_event(source=helper.get_input_type(), index='main', sourcetype=helper.get_sourcetype(), data=population_event_json, done=True, unbroken=True)
    ew.write_event(event)
    helper.log_info('Success')