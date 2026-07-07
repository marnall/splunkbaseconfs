# encoding = utf-8
import os
import sys
import time
import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from falconpy import FileVantage
import json


date_format_str = '%Y-%m-%dT%H:%M:%S.%fZ'
def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    
    #Uncomment and put your proxy URLs if you are using proxy
    #proxy = {"https": "https://someproxy.local:8000", "http": "http://someproxy.local:8000"}
  
    falcon = FileVantage(client_id=helper.get_arg('client_id'), client_secret=helper.get_arg('secret'))

    # Checkpoint  
    checkpoint_name = "cs_filevantage_checkpoint"
    helper.log_debug('checkpoint name: ' + checkpoint_name)
    helper.delete_check_point(checkpoint_name)

    # Yest date time in UTC
    date_yest = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    date_yest = date_yest.strftime(date_format_str)

    checkpoint = helper.get_check_point(checkpoint_name)
    
    if checkpoint is None:
        helper.log_debug('set first checkpoint: ' +date_yest)
        helper.save_check_point(checkpoint_name, date_yest)
        checkpoint = date_yest

    helper.log_info('current checkpoint: ' + str(checkpoint))

    # parameters to send request for changeIds to FileVantage       
    parameters = {'offset':0,'limit':100,'sort':"action_timestamp|desc",'filter':f"action_timestamp:>'{checkpoint}'"}
    
    #proxy =  helper.get_proxy()
    
    
    offset=0
    total=0
    iteration_count=0
    
    try:
        
        while (offset<=total):
            
            iteration_count +=1
            # List of change Ids
            helper.log_info('sending request to filevantage to get change Ids')
            id_list_response = falcon.query_changes(parameters=parameters)
            
            if id_list_response['status_code']!=200:
                helper.log_info('breaking out - status code other than 200: '+str(id_list_response))
                break

            total = id_list_response['body']['meta']['pagination']['total']

            if total == 0:
                helper.log_info('breaking out - total count of records is 0')
                break

            # Get first change id in the resource array. Since it is ordered in desc order of action timestamp
            # Get the timestamp of the first id of the first iteration and save that for the checkpoint
            if iteration_count==1:
                checkpoint_change_id=id_list_response['body']['resources'][0]

            helper.log_info('sending request to filevantage to get change details')
            
            # Details of each change per changeId
            change_details = falcon.getChanges(ids=id_list_response['body']['resources'])

            helper.log_info('writing change events to splunk')

            # for each change retrieved, start writing to splunk index
            for change_detail in change_details['body']['resources']:
                evt = helper.new_event(json.dumps(change_detail), time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
                ew.write_event(evt)
                
                # Get the action timestamp from checkpoint change id and store it as checkpoint
                if change_detail['id'] == checkpoint_change_id and iteration_count==1 :
                    helper.log_info('setting checkpoint to latest action_timestamp '+change_detail['action_timestamp'])
                    helper.save_check_point(checkpoint_name, change_detail['action_timestamp'])

            offset = id_list_response['body']['meta']['pagination']['offset']
            limit = id_list_response['body']['meta']['pagination']['limit']
            offset=offset+limit
            helper.log_info('offset::'+str(offset)+' total::'+str(total)+' limit::'+str(limit))
            parameters['offset'] = offset
          
    except Exception as e:
        helper.log_error("Problem while making a call to filevantage API: " + str(e))
        