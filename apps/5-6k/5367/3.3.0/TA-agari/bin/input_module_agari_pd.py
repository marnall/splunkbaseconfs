
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
API_VERSION = "v1/ep"

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
        return "/".join([host, API_VERSION, path, str(idx)])
    else:
        return "/".join([host, API_VERSION, path])


def status(helper, access_token, host):
    rslt = get(helper, access_token, api_url(host, "status"), "status")
    return [encapsulate_event("status", rslt)]


def policy_events(helper, access_token, host, start_date, end_date, policy_action, policy_details, state=None, config_start_date=None, stanza_name=None):
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "sort": "created_at ASC",
        "limit": 200
    }

    if policy_action:
        params["policy_action"] = str(policy_action)
    url = api_url(host, "policy_events")
    helper.log_debug("Collecting policy_events Start Time: {} and End Time: {}".format(start_date, end_date))
    for policy_events in get_index(helper, access_token, url, "alert_events", params=params, chunk=True):
        created_at = None
        for policy_event in policy_events:
            policy_output = []
            created_at = policy_event.get("created_at", None)
            helper.log_debug("Response received for Id: {} and Policy Created At: {}".format(policy_event.get("id", None), created_at))
            policy_event = get(helper, access_token, api_url(host, "policy_events", policy_event["id"]), "alert_event")
            if policy_event:
                policy_output.append(encapsulate_event("policy_detail", policy_event, "created_at"))
            yield policy_output
        if created_at:
            state["config_start_date"] = config_start_date
            state["last_end_date"] = created_at
            set_checkpoint(helper, stanza_name, state)
        

def collect_events(helper, ew):
    config_start_date = helper.get_arg('start_date')
    time = datetime.now()
    end_date = time.isoformat()
    input_name = helper.get_input_stanza_names()
    input_stanza = helper.get_input_stanza()
    policy_actions = helper.get_arg("policy_action")
    messages_flag = helper.get_arg("messages")
    global_account = helper.get_arg('global_account')
    api_host = agari_utils.AGARI_HOSTNAME
    client_id = input_stanza[input_name]['global_account']['client_id']
    client_secret = input_stanza[input_name]['global_account']['client_secret']
    stanza_name = list(input_stanza.keys())[0]
    api_host = "https://{}".format(api_host)
    index=helper.get_arg("index")
    source = "agari"
    start_ti = datetime.now()

    state = get_checkpoint(helper, stanza_name) or dict()
    if not state:
        start_date = config_start_date
    else:
        if config_start_date != state.get("config_start_date"):
           start_date = config_start_date
        else:
           start_date = state.get("last_end_date")
    
    helper.log_info("Collecting data for Agari Phishing Defense. Start Time: {} End Time: {}".format(start_date, end_date))
    access_token = auth(helper, api_host, client_id, client_secret, api_version=API_VERSION)

    api_data = {"status": status(helper, access_token, api_host)}
    if api_data:
       indexing_done = splunk_data_ingestion(helper, ew, api_data, index, source, "agari:pd:status")
       api_data = {}
    
    if len(policy_actions) == 6:
        helper.log_info("Collecting data for Policy Action: {}".format(policy_actions))
        for policy in policy_events(helper, access_token, api_host, start_date, end_date, None, policy_details=True, state=state, config_start_date=config_start_date, stanza_name=stanza_name):
            api_data["policy_details"] = policy
            if api_data:
                indexing_done = splunk_data_ingestion(helper, ew, api_data, index, source, "agari:pd:policy_events")
            if messages_flag:
                for policy in api_data.get("policy_details"):
                    helper.log_debug("Collecting Message for policy: {}".format(policy.get("event_data", {}).get("id", None)))
                    message_link = policy.get("event_data", {}).get("links", {}).get("messages")
                    message_link = "{}?add_fields=uris".format(message_link)
                    message = get(helper, access_token, message_link, "message")
                    if message:
                        helper.log_debug("Collecting message from URL: {}".format(message_link))
                        message_data_ingestion(helper, ew, encapsulate_event("messages", message, "date", options={"timestamp_format":"%Y-%m-%dT%H:%M:%S%z"}), index, source, "agari:pd:messages")
                    else:
                        helper.log_error("Message is not available hence skipping message call for URL: {}".format(message_link))
                        continue
                    api_data = {}
    else:
        for policy_action in policy_actions:
            helper.log_info("Collecting data for Policy Action: {}".format(policy_action))
            for policy in policy_events(helper, access_token, api_host, start_date, end_date, policy_action, policy_details=True, state=state, config_start_date=config_start_date, stanza_name=stanza_name):
                api_data["policy_details"] = policy
                if api_data:
                    indexing_done = splunk_data_ingestion(helper, ew, api_data, index, source, "agari:pd:policy_events")
                if messages_flag:
                    for policy in api_data.get("policy_details"):
                        helper.log_info("Collecting Message for policy: {}".format(policy.get("event_data", {}).get("id", None)))
                        message_link = policy["event_data"]["links"]["messages"]
                        message = get(helper, access_token, message_link, "message")
                        if message:
                            helper.log_debug("Collecting message from URL: {}".format(message_link))
                            message_data_ingestion(helper, ew, encapsulate_event("messages", message, "date", options={"timestamp_format":"%Y-%m-%dT%H:%M:%S%z"}), index, source, "agari:pd:messages")
                        else:
                            helper.log_error("Message is not available hence skipping message call for URL: {}".format(message_link))
                            continue
                        api_data = {}
    
    helper.log_info(
        "processing time (seconds): %f" % (datetime.now() - start_ti).total_seconds()
    )
    