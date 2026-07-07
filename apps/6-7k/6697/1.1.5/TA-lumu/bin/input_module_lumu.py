# encoding = utf-8

import os
import sys
import json

# Complementary imports
from os import path
from datetime import datetime
from datetime import timezone

# Lumu streamer
from streamer import Streamer
from streamer import NON_TIMESTAMP_EVENTS
DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ"
]

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    # Set logging
    log_level = helper.get_log_level()
    helper.set_log_level(log_level)
    
    # Stanza information
    stanza_name = helper.get_input_stanza_names()
    
    # Index information
    index_info = helper.get_output_index()
    
    # Input type
    input_type = helper.get_input_type()
    
    # Source type
    source_type = helper.get_sourcetype()
    
    # Get version
    basepath = path.dirname(__file__)
    filepath = path.abspath(path.join(basepath, "..", "app.manifest"))
    
    with open(filepath, "r") as manifest:
        manifest_file = json.load(manifest)
        version = manifest_file["info"]["id"]["version"]
    
    # Get configuration data
    key = helper.get_arg("key")
    events_of_interest = helper.get_arg("events_of_interest")
    include_muted_updates = helper.get_arg("include_muted_updates")
    
    proxy = helper.get_proxy()
    
    if proxy:
        # Setting the required parameters for proxy support
        helper.log_debug("Setting proxy configuration.")
        proxy_auth = ""
        if proxy["proxy_username"]:
            # Authenticated proxy
            proxy_auth = f"{ proxy['proxy_username'] }:{ proxy['proxy_password'] }@"
        
        proxy_str = f"{ proxy['proxy_type'] }://{ proxy_auth }{ proxy['proxy_url'] }:{ proxy['proxy_port'] }"
        
        proxy_settings = {
            "http": proxy_str,
            "https": proxy_str
        }
    else:
        proxy_settings = None
    
    # Logging configuration detais
    helper.log_info(f"Lumu event streaming | Log level: { log_level }")
    helper.log_info(f"Lumu event streaming | Version: { version }")
    helper.log_info(f"Lumu event streaming | Proxy configuration: { proxy_settings }")
    helper.log_info(f"Lumu event streaming | Input: { stanza_name }")
    helper.log_info(f"Lumu event streaming | Index: { index_info }")
    
    check_point_offset = f"{ stanza_name }_offset"
    check_point_labels = f"{ stanza_name }_labels"
    
    offset = helper.get_check_point(check_point_offset)
    labels = helper.get_check_point(check_point_labels)
    
    if offset is None:
        offset = 0
    
    # Testing parameters
    helper.log_info(f"Lumu event streaming | Events of interest: { events_of_interest }")
    helper.log_info(f"Lumu event streaming | Include muted updates: { include_muted_updates }")
    helper.log_info(f"Lumu event streaming | Offset: { offset }")
    
    # Lumu streamer
    streamer = Streamer(company_key=key, 
                proxies=proxy_settings, 
                events_of_interest=events_of_interest,
                labels=labels,
                include_muted_updates=include_muted_updates)
    
    offset, messages = streamer.consult_updates(offset=offset)
    
    for message in messages:
        # Get timestamp from message
        message_type = message["eventType"]
        try:
            # First, check messages with no default timestamp
            if message_type in NON_TIMESTAMP_EVENTS:
                message_timestamp = message["data"]["statusTimestamp"]
            # Then, created or updated incident messages
            elif message_type in ["NewIncidentCreated", "IncidentUpdated"]:
                message_timestamp = message["data"]["incident"]["lastContact"]
            # Finally, other messages
            else:
                message_timestamp = message["data"]["incident"]["statusTimestamp"]
        except KeyError:
            helper.log_error(f"Cannot process message. Skipping")
            continue

        # Transform it to epoch format. First replace timezone to UTC
        for DATE_FORMAT in DATE_FORMATS:
            try:
                message_timestamp = datetime.strptime(message_timestamp, DATE_FORMAT).replace(tzinfo=timezone.utc).timestamp()
            except Exception as e:
                continue
        
        # Check error in parsing timestamp
        if not message_timestamp:
            helper.log_error(f"Cannot process timestamp for event. Skipping.")
            continue
        
        # Send each update as a message
        event = helper.new_event(source=stanza_name, index=index_info, sourcetype=source_type, data=json.dumps(message), time=message_timestamp)
        ew.write_event(event)
    
    # After the collectiong of events, query labels and update the labels check point
    labels = streamer.get_labels()
    helper.save_check_point(check_point_labels, labels)
    helper.save_check_point(check_point_offset, offset)
    helper.log_info(f"Lumu event streaming | Streaming finished. New offset: { offset }")
    
    