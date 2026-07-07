# encoding = utf-8

import os
import sys
import datetime
import time
import json

from azure.eventhub import EventHubClient, Receiver, Offset

def validate_input(helper, definition):
    amqp_uri = definition.parameters.get('amqp_uri', None)
    policy = definition.parameters.get('policy', None)
    key = definition.parameters.get('key', None)
    consumer_group = definition.parameters.get('consumer_group', None)
    partition = definition.parameters.get('partition', None)
    
    if consumer_group == "":
        consumer_group = "$Default"
    
    if partition == "":
        partition = 0

def collect_events(helper, ew):
    opt_amqp_uri = helper.get_arg('amqp_uri')
    opt_policy = helper.get_arg('policy')
    opt_key = helper.get_arg('key')
    opt_consumer_group = helper.get_arg('consumer_group')
    opt_partition = helper.get_arg('partition')
    
    """
    stanza = helper.get_input_stanza()
    print stanza
    if 'interval' in stanza.values()[0]:
        interval = stanza.values()[0]['interval']
    """
    
    opt_offset = Offset(datetime.datetime.utcnow()-datetime.timedelta(seconds=300))

    client = EventHubClient(opt_amqp_uri, debug=False, username=opt_policy, password=opt_key)
    
    try:
        receiver = client.add_receiver(opt_consumer_group, opt_partition, prefetch=5000, offset=opt_offset)
        client.run()

        for event_data in receiver.receive(timeout=1000):
            json_parsed = event_data.body_as_json()
            records = json_parsed['records']
            
            for rec in records:
                data = json.dumps(rec)
                event = helper.new_event(data, host=None, source=None, sourcetype='eventhubs', done=True, unbroken=True)
                try:
                    ew.write_event(event)
                except Exception as e:
                    raise e
    
        client.stop()

    except KeyboardInterrupt:
        pass
    finally:
        client.stop()