
# encoding = utf-8

import os
import sys
import time
from datetime import datetime
from builtins import str
import json
from six.moves.urllib.parse import urlparse, parse_qs
import agari_utils
from ta_agari_helpers import (
    encapsulate_event,
    get,
    auth,
    get_index,
    TIMESTAMP_FORMAT_THREAT_FEED_SUBMISSIONS,
    splunk_data_ingestion
)
API_VERSION = "v1/cp"
# ToDo: the following should be turned into config file params
FAILURE_DATA_MODE = "alerts"  # one of: all, alerts or None
LIMIT = 200
FAILURE_STATES_LIMIT = 1000
FAILURE_SAMPLES_LIMIT = 100

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    interval = float(definition.parameters.get('interval', None))
    if interval < 120:
        helper.log_error("Interval must be greater than or equal to 120 seconds.")
        raise Exception('Interval must be greater than  or equal to 120 seconds')

def dedup(array):
    i = 0
    ii = i + 1
    # in-place delete duplicate array entries
    while True:
        if ii < len(array):
            if array[i] == array[ii]:
                del array[ii]
            else:
                ii += 1
        else:
            i += 1
            ii = i + 1
            if ii > -len(array):
                break
    return array

def api_url(api_host, path, idx=None, actions=[]):
    path_segments = [api_host, API_VERSION, path]
    if idx:
        path_segments.extend([str(idx)])
    if actions:
        path_segments.extend(actions)
    return "/".join(path_segments)

def get_checkpoint(helper, stanza_name):
    return helper.get_check_point(stanza_name)

def set_checkpoint(helper, stanza_name, state):
    return helper.save_check_point(stanza_name, state)

def status(helper, host, access_token):
    # get API status
    rslt = get(helper, access_token, api_url(host, "status"), "status")
    return [encapsulate_event("status", rslt)]

def extract_links(data, links=None):
    # extract links from data payload
    # list() to avoid modifying dict while iterating over it.
    for k, v in list(data.items()):
        if v is None or v == [] or v == "":
            continue
        if k == "links":
            # list() to avoid modifying dict while iterating over it.
            for _k, _v in list(v.items()):
                if links is not None:
                    if _k not in links:
                        links[_k] = []
                    links[_k].append(_v)
            del data[k]
        elif k == "failure_samples_link":
            if links is not None:
                if k not in links:
                    links[k] = []
                links[k].append(v)
            del data[k]
        elif isinstance(v, list):
            for _v in v:
                if isinstance(_v, dict):
                    extract_links(_v, links)
    return links

def alerts(
    helper, access_token, api_host, start_date, end_date, alert_types=None, detail_only=False
):
    # get API alert events
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "sort": "created_at ASC",
        "limit": LIMIT,
    }
    if alert_types:
        params["alert_types"] = ",".join(alert_types)

    alert_output = []
    # alert event summary
    helper.log_debug("Collecting alert_events Start Time: {} End Time: {}".format(start_date, end_date))
    for aes in next(get_index(helper, access_token, api_url(api_host, "alert_events"), "alert_events", params=params, chunk=False)):
        if not detail_only:
            alert_output.append(encapsulate_event("alert_summary", aes, "created_at"))
            continue
        # alert event details
        aed = get(helper, access_token, api_url(api_host, "alert_events", aes["id"]), "alert_event")
        alert_type = aed["alert_type"]
        if alert_type == "spf_record_changed":
            for k in ["old_spf_tree", "new_spf_tree"]:
                if k in aed:
                    # normalize the old_spf_tree and new_spf_tree fields
                    if isinstance(aed[k], dict):
                        aed[k] = json.dumps(aed[k])
                    else:
                        aed[k] = json.dumps(json.loads(aed[k] or "{}"))
        alert_output.append(encapsulate_event("alert_detail", aed, "created_at"))
    return alert_output


def failure_stats_for_alert(helper, access_token, link, stats_type, alert_id):
    # obtains failure stats from a full/preconstructed URL
    # e.g. from preconstructed URL links in alert responses
    url = urlparse(link).scheme + "://" + urlparse(link).netloc + urlparse(link).path
    params = parse_qs(urlparse(link).query)
    params["limit"] = FAILURE_STATES_LIMIT
    helper.log_debug("Collecting failue_stats with url: {} and params: {}".format(url, params))
    stats = next(get_index(helper, access_token, url, "failure_stats", params=params, chunk=False))
    return encapsulate_event(stats_type, stats, "first_occurrence", alert_id)


def failure_samples_for_alert(helper, access_token, link, samples_type, alert_id):
    # obtains failure samples from a full/preconstructed URL
    # e.g. from preconstructed URL links in alert responses
    url = urlparse(link).scheme + "://" + urlparse(link).netloc + urlparse(link).path
    params = parse_qs(urlparse(link).query)
    params["limit"] = FAILURE_SAMPLES_LIMIT
    helper.log_debug("Collecting failue_stats with url: {} and params: {}".format(url, params))
    samples = next(get_index(helper, access_token, url, "failure_samples", params=params, chunk=False))
    return encapsulate_event(samples_type, samples, "time", alert_id)

def failure_samples(helper, access_token, api_host, start_date, end_date):
    params = {"start_date": start_date, "end_date": end_date, "limit": FAILURE_SAMPLES_LIMIT}
    helper.log_debug("Collecting failure_samples Start Time: {} and End Time: {}".format(start_date, end_date))
    samples = next(get_index(helper, access_token, api_url(api_host, "failure_samples"), "failure_samples", params=params, chunk=False))
    return [encapsulate_event("failure_samples", samples, "time")]

def failure_stats(helper, access_token, api_host, start_date, end_date, group_by="subject"):
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "limit": FAILURE_STATES_LIMIT,
        "group": group_by,
    }
    helper.log_debug("Collecting failure_stats Start Time: {} and End Time: {}".format(start_date, end_date))
    stats = next(get_index(helper, access_token, api_url(api_host, "failure_stats"), "failure_stats", params=params, chunk=False))
    return [
        encapsulate_event("failure_stats_by_%s" % group_by, stats, "first_occurrence")
    ]

def get_threat_feed_ids(helper, access_token, api_host):
    threat_feeds = get(helper, access_token,
        api_url(api_host, "threat_feeds"), "threat_feeds", {"add_fields": "enabled"}
    )
    return [
        tf["id"] for tf in threat_feeds if tf["enabled"]
    ]

def threat_feed_submissions(helper, access_token, api_host, id, params):
    threat_feed_submissions_output = []
    for tfs in next(get_index(helper, access_token,
        api_url(api_host, "threat_feeds", id, ["submissions"]),
        "threat_feed_submissions",
        params=params,
        chunk=False
    )):
        threat_feed_submissions_output.append(
            encapsulate_event(
                "threat_feed_submission",
                tfs,
                "timestamp",
                None,
                {"timestamp_format": TIMESTAMP_FORMAT_THREAT_FEED_SUBMISSIONS},
            )
        )
    return threat_feed_submissions_output

def get_threat_feed_submissions(helper, access_token, api_host, start_date, end_date):
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "sort": "created_at ASC",
        "limit": LIMIT,
    }
    helper.log_debug("Collecting threat_feed_submissions Start Time: {} and End Time: {}".format(start_date, end_date))
    threat_feed_ids = get_threat_feed_ids(helper, access_token, api_host)
    all_threat_feed_submissions_output = []
    for threat_feed_id in threat_feed_ids:
        all_threat_feed_submissions_output.extend(
            threat_feed_submissions(helper, access_token, api_host, threat_feed_id, params)
        )
    return all_threat_feed_submissions_output

def collect_events(helper, ew):
    config_start_date = helper.get_arg('start_date')
    time = datetime.now()
    end_date = time.isoformat()
    input_name = helper.get_input_stanza_names()
    input_stanza = helper.get_input_stanza()

    alert_types = helper.get_arg("alert_types")
    failure_data_mode = helper.get_arg("failure_data_mode")
    threat_feeds_mode = helper.get_arg("threat_feeds_mode")
    alert_mode = helper.get_arg("alert_mode")
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

    helper.log_info("Starting data collection with failure_data_mode: {} and alert_mode: {}".format(failure_data_mode,alert_mode)) 
    helper.log_info("Collecting data for alert_types: {} and Start Time: {} End Time: {}".format(alert_types, start_date, end_date))
    api_data = {}
    access_token = auth(helper, api_host, client_id, client_secret)
    api_data["status"] = status(helper, api_host, access_token)
    
    if api_data:
       indexing_done = splunk_data_ingestion(helper, ew, api_data, index, source, "agari:bp:status")
       api_data = {}

    detail_only = False
    if alert_mode == "alert_details":
        detail_only = True

    api_data["alerts"] = alerts(
        helper, access_token, api_host, start_date, end_date, alert_types=alert_types, detail_only=detail_only
    )
    
    if api_data["alerts"]:
        indexing_done = splunk_data_ingestion(helper, ew, api_data, index, source, "agari:bp:alerts")
        if failure_data_mode == "all":
           api_data = {}

    if threat_feeds_mode == "on":
        api_threat_data = {}
        api_threat_data["threat_feed_submissions"] = get_threat_feed_submissions(helper, access_token, api_host,
            start_date, end_date
        )
        if api_threat_data:
            indexing_done = splunk_data_ingestion(helper, ew, api_threat_data, index, source, "agari:bp:threatfeeds")
    
    if failure_data_mode == "all":
        # get failure data for the specified start/end_date range
        api_failure_all = {}
        api_failure_all["failure_stats_by_subject"] = failure_stats(
            helper, access_token, api_host, start_date, end_date, group_by="subject"
        )
        api_failure_all["failure_stats_by_ip"] = failure_stats(
            helper, access_token, api_host, start_date, end_date, group_by="ip"
        )
        api_failure_all["failure_samples"] = failure_samples(helper, access_token, api_host, start_date, end_date)
        if api_failure_all:
            indexing_done = splunk_data_ingestion(helper, ew, api_failure_all, index, source, "agari:bp:failures")

    elif failure_data_mode == "alerts":
        # Get failure data from links included in alert responses
        api_failure_data = {}
        api_failure_data["failure_samples"] = []
        api_failure_data["failure_stats"] = []
        for alert in api_data["alerts"]:
            links = {}
            extract_links(alert["event_data"], links)
            alert_id = alert["event_data"]["id"]

            fstats = []
            fsamps = []
            for k, v in list(links.items()):
                for link in list(set(v)):
                    if "/failure_stats?" in link:
                        fstat = failure_stats_for_alert(helper, access_token, link, "failure_stats", alert_id)
                        if fstat:
                            extract_links(fstat)
                            fstats.append(fstat)
                    elif "/failure_samples?" in link:
                        fsamp = failure_samples_for_alert(
                            helper, access_token, link, "failure_samples", alert_id
                        )
                        if fsamp:
                            fsamps.append(fsamp)

            # dedup the collected failure_stats/samples data and add to the api_data for the alert_event
            for fstat in dedup(fstats):
                api_failure_data["failure_stats"].append(fstat)
            for fsamp in dedup(fsamps):
                api_failure_data["failure_samples"].append(fsamp)
        if api_failure_data:
            indexing_done = splunk_data_ingestion(helper, ew, api_failure_data, index, source, "agari:bp:failures")
    api_data = {}
    
    state["config_start_date"] = config_start_date
    state["last_end_date"] = end_date
    set_checkpoint(helper, stanza_name, state)

    helper.log_info(
        "processing time (seconds): %f" % (datetime.now() - start_ti).total_seconds()
    )