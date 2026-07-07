# encoding = utf-8

import os
import sys
import time
import datetime
import json

from azure.eventhub import EventHubClient, Receiver, Offset

def validate_input(helper, definition):
    event_hub_namespace = definition.parameters.get('event_hub_namespace', None)
    event_hub_name = definition.parameters.get('event_hub_name', None)
    policy = definition.parameters.get('policy', None)
    key = definition.parameters.get('key', None)
    consumer_group = definition.parameters.get('consumer_group', None)
    partition = definition.parameters.get('partition', None)

    if consumer_group == "":
        consumer_group = "$Default"

    if partition == "":
        partition = 0

def collect_events(helper, ew):
    opt_event_hub_namespace = helper.get_arg('event_hub_namespace')
    opt_event_hub_name = helper.get_arg('event_hub_name')
    opt_policy = helper.get_arg('policy')
    opt_key = helper.get_arg('key')
    opt_consumer_group = helper.get_arg('consumer_group')
    opt_partition = helper.get_arg('partition')

    #Checkpoint file creation
    cfname = time.strftime("%Y%m%d") + "_" + opt_event_hub_namespace + "_"  + opt_event_hub_name  + ".ckp"
    fname = os.path.join(os.path.dirname(__file__), cfname)
    exists = os.path.isfile(fname)

    if not exists:
        f = open(fname,"w+")
        f.close()
    
    #List creation for "IDs" storage
    lstRecs = []
    append = "N"
    
    #opt_offset = Offset("-1")
    #opt_offset = Offset(datetime.datetime.utcnow()-datetime.timedelta(seconds=300))
    opt_offset = Offset(datetime.datetime.utcnow())
    
    amqp_uri = "amqps://" + opt_event_hub_namespace + ".servicebus.windows.net/" + opt_event_hub_name

    client = EventHubClient(amqp_uri, debug=False, username=opt_policy, password=opt_key)

    try:
        receiver = client.add_receiver(opt_consumer_group, opt_partition, prefetch=5000, offset=opt_offset)
        client.run()

        for event_data in receiver.receive(timeout=1000):
            json_parsed = event_data.body_as_json()
            records = json_parsed['records']

            #Values to make the ID 
            recTime = json_parsed.get('records')[0].get('time')
            recCorrId = json_parsed.get('records')[0].get('correlationId')
            recResType = json_parsed.get('records')[0].get('resultType')
            
            #ID
            ckpRecs = recTime + '|' + recCorrId + '|' + recResType
            
            #Append ID to the List
            lstRecs.append(ckpRecs)
            
            for rec in records:
                data = json.dumps(rec)

                #Read Checkpoint file
                f = open(fname, "r")
                fContent = f.read()
                
                #If its empty write events into Splunk
                if ckpRecs not in fContent:
                    event = helper.new_event(data, host=None, source=None, sourcetype='eventhubs', done=True, unbroken=True)
                    append = "Y"
                    try:
                        ew.write_event(event)
                    except Exception as e:
                        raise e

        #Close Checkpoint file (for reading)        
        f.close()

        client.stop()

        #Save Checkpoint file with Listed data
        if append == "Y":
            f = open(fname, "a+")
            f.write(str(lstRecs))
            f.close()

    except Exception as e:
        pass
    finally:
        client.stop()