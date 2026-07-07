# encoding = utf-8
from fetch_data import AWSDataFetcher
from state_manager import StateManager
import json
import os

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    helper.log_debug("stream events started")
    splunk_home = os.environ['SPLUNK_HOME']

    input_type = helper.get_input_type()
    input_stanza = helper.get_input_stanza_names()
    index = helper.get_output_index(input_stanza)
    
    bucket_name = helper.get_arg("s3_bucket_name")
    region = helper.get_arg("s3_bucket_region")
    client_prefix = helper.get_arg("s3_client_prefix")
    key_id = helper.get_global_setting("access_key_id")
    secret_key = helper.get_global_setting("secret_access_key")

    aws_data_fetcher = AWSDataFetcher(
        bucket_name, region, client_prefix, key_id, secret_key, input_stanza)
    state_manager = StateManager(f"{splunk_home}/etc/apps/TA-pdns-block-data-connector/{input_stanza}-last-time.txt")

    keys_and_dates = aws_data_fetcher.get_recent_file_keys_and_dates()
    for key, _ in keys_and_dates:
        stix_events = aws_data_fetcher.get_stix_events_from_file_key(key)
        for stix_event in stix_events:
            stix_type = stix_event["type"]
            sourcetype = f"STIX:{stix_type.replace('-','_')}"
            event = helper.new_event(
                source=input_type, 
                index=index,
                sourcetype=sourcetype, 
                data=json.dumps(stix_event)
            )
            ew.write_event(event)
    if keys_and_dates:
        checkpoint = {
            "Key": keys_and_dates[-1][0],
            "Date": keys_and_dates[-1][1].isoformat()
        }
        state_manager.post(json.dumps(checkpoint))
        
        