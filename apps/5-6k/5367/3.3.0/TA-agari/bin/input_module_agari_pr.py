
# encoding = utf-8

import os
import sys
import time
from datetime import datetime
import datetime as dt
import agari_utils
from ta_agari_helpers import (
    encapsulate_event,
    get,
    auth,
    get_index,
    splunk_data_ingestion,
    message_data_ingestion
)

API_VERSION = "v1/apr"

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    interval = float(definition.parameters.get('interval', None))
    if interval < 120:
        helper.log_error("Interval must be greater than or equal to 120 seconds.")
        raise Exception('Interval must be greater than  or equal to 120 seconds')

def get_checkpoint(helper, stanza_name):
    return helper.get_check_point(stanza_name)

def set_checkpoint(helper, stanza_name, state):
    return helper.save_check_point(stanza_name, state)

def api_url(host, path, idx=None):
    if idx:
        return "/".join([host, API_VERSION, path,  str(idx)])
    else:
        return "/".join([host, API_VERSION, path])


def status(helper, access_token, host):
    rslt = get(helper, access_token, api_url(host, "status"), "status")
    return [encapsulate_event("status", rslt)]


def investigation_events(helper, access_token, host, start_date, end_date, investigation_details, state=None, config_start_date=None, stanza_name=None):
    params = {
        "start_date": start_date,
        "end_date": end_date
    }

    url = api_url(host, "investigations")
    helper.log_debug("Collecting investigation_events Start Time: {} and End Time: {}".format(start_date, end_date))
    checkpoint_flag=True
    for investigation_events in get_index(helper, access_token, url, "investigations", params=params, chunk=True):
        created_at = None
        for investigation_event in investigation_events:
            investigation_output = []
            if checkpoint_flag:
                created_at = investigation_event.get("created_at", None)
                checkpoint_flag = False
            helper.log_debug("Response received for Id: {} and investigation Created At: {}".format(investigation_event.get("id", None), created_at))
            investigation_event = get(helper, access_token, "{}?add_fields=similar_messages_link".format(api_url(host, "investigations", investigation_event["id"])), "investigation")
            if investigation_event:
                investigation_output.append(encapsulate_event("investigation_detail", investigation_event, "created_at"))
            yield investigation_output
        if created_at:
            # add one second to avoid duplication of last event
            date_time_obj = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
            added_seconds = dt.timedelta(0, 1)
            added_time= date_time_obj+added_seconds
            added_time = added_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            state["config_start_date"] = config_start_date
            state["last_end_date"] = added_time
            set_checkpoint(helper, stanza_name, state)

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # multiple_dropdown = definition.parameters.get('multiple_dropdown', None)
    pass

def collect_events(helper, ew):
    config_start_date = helper.get_arg('start_date')
    time = datetime.now()
    end_date = time.isoformat()
    input_name = helper.get_input_stanza_names()
    input_stanza = helper.get_input_stanza()
    data_types = helper.get_arg("data_types")
    global_account = helper.get_arg('global_account')
    api_host = agari_utils.AGARI_HOSTNAME
    client_id = input_stanza[input_name]['global_account']['client_id']
    client_secret = input_stanza[input_name]['global_account']['client_secret']
    stanza_name = list(input_stanza.keys())[0]
    api_host = "https://{}".format(api_host)
    index=helper.get_arg("index")
    source = "agari"
    start_ti = datetime.now()
    messages_flag = True
    if not data_types:
        data_types = ["ips", "domains", "attachments", "uris", "tags"]
    state = get_checkpoint(helper, stanza_name) or dict()
    if not state:
        start_date = config_start_date
    else:
        if config_start_date != state.get("config_start_date"):
           start_date = config_start_date
        else:
           start_date = state.get("last_end_date")
    
    helper.log_info("Collecting data for Agari Phishing Response. Start Time: {} End Time: {}".format(start_date, end_date))
    access_token = auth(helper, api_host, client_id, client_secret, api_version=API_VERSION)

    api_data = {"status": status(helper, access_token, api_host)}
    if api_data:
       indexing_done = splunk_data_ingestion(helper, ew, api_data, index, source, "agari:pr:status")
       api_data = {}
    
    for investigation in investigation_events(helper, access_token, api_host, start_date, end_date, investigation_details=True, state=state, config_start_date=config_start_date, stanza_name=stanza_name):
        api_data["investigation_details"] = investigation
        if api_data:
            indexing_done = splunk_data_ingestion(helper, ew, api_data, index, source, "agari:pr:investigation_details")
        
        for investigation in api_data.get("investigation_details"):
            investigation_id = investigation.get("event_data", {}).get("id", None)
            created_at = investigation.get("event_data", {}).get("created_at", None)
            helper.log_info("Collecting Message for investigation: {}".format(investigation_id))
            if messages_flag:
                message_link = investigation["event_data"]["similar_messages_link"]
                message = get(helper, access_token, message_link, "messages")
                if message:
                    helper.log_debug("Collecting message from URL: {}".format(message_link))
                    params = {"sort": "date asc", "limit": "200"}
                    for messages in get_index(helper, access_token, message_link, "messages", params=params, chunk=True):
                        for message in messages:
                            message["investigation_id"] = str(investigation_id)
                            message_data_ingestion(helper, ew, encapsulate_event("messages", message, "date", options={"timestamp_format":"%Y-%m-%dT%H:%M:%S%z"}), index, source, "agari:pr:messages")
                else:
                    helper.log_error("Message is not available hence skipping message call for URL: {}".format(message_link))
            
            if "attachments" in data_types:
                helper.log_info("Collecting Attachments for investigation: {}".format(investigation_id))
                attachments = get(helper, access_token,  "{}/attachments".format(api_url(api_host, "investigations", investigation_id)), "attachments")
                for a1 in attachments:
                    a1["investigation_id"] = str(investigation_id)
                    message_data_ingestion(helper, ew, encapsulate_event("attachements", a1, direct_ts_value=created_at), index, source, "agari:pr:attachments")
            
            if "domains" in data_types:
                helper.log_info("Collecting Domains for investigation: {}".format(investigation_id))
                attachments = get(helper, access_token,  "{}/domains".format(api_url(api_host, "investigations", investigation_id)), "domains")
                for a1 in attachments:
                    a1["investigation_id"] = str(investigation_id)
                    message_data_ingestion(helper, ew, encapsulate_event("domains", a1, direct_ts_value=created_at), index, source, "agari:pr:domains")
            
            if "ips" in data_types:
                helper.log_info("Collecting IPs for investigation: {}".format(investigation_id))
                attachments = get(helper, access_token,  "{}/ips".format(api_url(api_host, "investigations", investigation_id)), "ips")
                for a1 in attachments:
                    a1["investigation_id"] = str(investigation_id)
                    message_data_ingestion(helper, ew, encapsulate_event("ips", a1, direct_ts_value=created_at), index, source, "agari:pr:ips")
            
            if "uris" in data_types:
                helper.log_info("Collecting URIs for investigation: {}".format(investigation_id))
                attachments = get(helper, access_token,  "{}/uris".format(api_url(api_host, "investigations", investigation_id)), "uris")
                for a1 in attachments:
                    a1["investigation_id"] = str(investigation_id)
                    message_data_ingestion(helper, ew, encapsulate_event("uris", a1, direct_ts_value=created_at), index, source, "agari:pr:uris")
            
            if "tags" in data_types:
                helper.log_info("Collecting Tags for investigation: {}".format(investigation_id))
                tag_ids = investigation.get("event_data", {}).get("tag_ids", None)
                for tag_id in tag_ids:
                    attachments = get(helper, access_token,  "{}/{}/tags/{}".format(api_host, API_VERSION, tag_id), "tag")
                    if attachments:
                        attachments["investigation_id"] = str(investigation_id)
                        message_data_ingestion(helper, ew, encapsulate_event("tag", attachments, direct_ts_value=created_at), index, source, "agari:pr:tags")

            api_data = {}
    
    helper.log_info(
        "processing time (seconds): %f" % (datetime.now() - start_ti).total_seconds()
    )