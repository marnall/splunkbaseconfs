import os
import sys # noqa # pylint: disable=unused-import
import time
import datetime
import re
import logging # noqa # pylint: disable=unused-import
import json
import fileinput
import math
from six import string_types

from collections import OrderedDict

# Import the OAuth2 libraries
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
from vulndb_utility import get_conf_file, get_splunk_version

SLEEP_TIME = 15
MAX_RETRIES = 3
TOKEN_URL = "https://vulndb.flashpoint.io/oauth/token"
UNIX_EPOCH_START_DATE = "1970-01-01"
DEFAULT_START_DATE_HOURS = "T00:00:00"

"""
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""
"""
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
"""


def call_api(session, proxies, url, api_key, api_secret, helper, headers):
    """Method to call api."""
    max_retries = MAX_RETRIES
    try:
        while max_retries > 0:
            try:
                max_retries -= 1
                result = session.request("GET", url, proxies=proxies, headers=headers)
                if result.status_code == 200:
                    return result.content, None
                elif result.status_code == 404:
                    # It returns 404 when no new vulnerability found.
                    return "finished", None
                elif result.status_code == 401:
                    new_session = create_new_session(api_key)
                    new_session.fetch_token(token_url=TOKEN_URL, proxies=proxies, client_id=api_key,
                                            client_secret=api_secret)
                    result = new_session.request("GET", url, proxies=proxies, headers=headers)
                    if result.status_code == 200:
                        return result.content, new_session
            except Exception:
                time.sleep(SLEEP_TIME)
                continue
        raise ValueError('Timeout')
    except Exception:
        helper.log_error("Error getting response in API call")


def validate_input(helper, definition):
    """
    Validates the input parameters and provides error to user on UI if the validation fails.

    :param helper: object of BaseModInput class
    :param definition: object containing input parameters
    """
    api_server = definition.parameters.get('api_server', None)
    api_key = definition.parameters.get('api_key', None)
    api_secret = definition.parameters.get('api_secret', None)
    start_date = definition.parameters.get('start_date', None)
    interval = definition.parameters.get('interval', None)
    min_cvssv2_score = definition.parameters.get('min_cvssv2_score', None)
    try:
        page_size = definition.parameters.get('page_size', None)
        if page_size:
            page_size = int(page_size)

    except Exception:
        helper.log_error("Page Size value should be a number in range 1 to 100.")
        raise Exception("Page Size value should be a number in range 1 to 100.")

    try:
        if min_cvssv2_score:
            min_cvssv2_score = float(min_cvssv2_score)

    except Exception:
        helper.log_error("CVSSv2 score should be a number in range 0 to 10.")
        raise Exception("CVSSv2 score should be a number in range 0 to 10.")

    if api_server and not re.match(r"^https:\/\/[0-9a-zA-Z]([-\\w]*[.]?[0-9a-zA-Z])*$", api_server):
        helper.log_error("Only secure URLs are supported.")
        raise Exception("Only secure URLs are supported.")

    if api_key and (len(api_key) > 8192):
        helper.log_error("Max length of text input is 8192.")
        raise Exception("Max length of text input is 8192.")

    if api_secret and (len(api_secret) > 8192):
        helper.log_error("Max length of text input is 8192.")
        raise Exception("Max length of text input is 8192.")

    if start_date and not re.match(r"^\d\d\d\d-\d\d-\d\d$|^1$", start_date):
        helper.log_error("Start Date should be in proper format.")
        raise Exception("Start Date should be in proper format.")

    if interval and not re.match(r"^[1-9]\d*$", interval):
        helper.log_error("Interval must be the positive integer.")
        raise Exception("Interval must be the positive integer.")

    if page_size and (page_size < 1 or page_size > 100):
        helper.log_error("Page Size value should be a number in range 1 to 100.")
        raise Exception("Page Size value should be a number in range 1 to 100.")

    if min_cvssv2_score is not None and (min_cvssv2_score < 0 or min_cvssv2_score > 10):
        helper.log_error("CVSSv2 score should be a number in range 0 to 10.")
        raise Exception("CVSSv2 score should be a number in range 0 to 10.")

    try:
        if (start_date != "1"):
            date_format = '%Y-%m-%d'
            datetime.datetime.strptime(start_date, date_format)
    except Exception:
        helper.log_error("Invalid Start Date. Start Date should be in the YYYY-MM-DD format")
        raise Exception("Invalid Start Date. Start Date should be in the YYYY-MM-DD format")


def utctime(start_date):
    """Convert start date to utctime in hours."""
    try:
        # start_date will be in YYYY-mm-dd'T'HH:MM:SS format.
        year, month, day = start_date[:10].split("-")
        hour, minute, second = start_date[11:].split(":")
        utc_time = datetime.datetime.utcnow()
        secs = utc_time - datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
        secs = secs.total_seconds()
        hours = int(secs) // 3600
    except Exception:
        hours = -1
    return hours


def epochtime(timestr, fmt):
    """Convert timestring to seconds since epoch."""
    tmp = datetime.datetime.strptime(timestr, fmt)
    epoch = datetime.datetime.utcfromtimestamp(0)
    tmp = int((tmp - epoch).total_seconds())
    return tmp


# This function will set the reset_input = 0 in the inputs.conf file
def unset_reset_flag(helper):
    """Method to unset reset flag."""
    dirname = os.path.dirname
    app_name = helper.get_app_name()
    conf_file = os.path.join(dirname(dirname(dirname(__file__))),
                             app_name, 'local', 'inputs.conf')
    helper.log_debug("Config File: " + str(conf_file))
    input_stanza = helper.get_input_stanza()
    stanza_name = list(input_stanza.keys())[0]
    helper.log_debug("Flag: reset_input is True. Deleting marker location and setting to start_date.")
    helper.log_debug("Flag: reset_input reset to 0.")
    match = 0
    for line in fileinput.input(conf_file, inplace=True):
        if (re.match("^\[.*" + stanza_name + "\]", line)):  # noqa: W605
            match = 1
        elif (re.match("^\[", line)):  # noqa: W605
            match = 0
        if (match):
            line = re.sub(r'reset_input\s*=\s*(1|[Tt][Rr][Uu][Ee])', r'reset_input = 0', line.rstrip())  # noqa: W605
            print(line)
        else:
            print(line.rstrip())


def data_with_min_score(helper, min_score, data):
    """Method to calculate data with minimum score."""
    data = json.loads(json.dumps(data))
    score_list = data["cvss_metrics"]
    score_source_list = []
    for score_data in score_list:
        source = score_data["source"]
        if "RBS" in source:
            source = "rbs"
        if "nvd" in source:
            source = "nvd"
        generated_on = score_data["generated_on"]
        score = score_data["calculated_cvss_base_score"]
        score_source_list.append({"score": score, "generated_on": generated_on, "source": source})

    score_source_list = sorted(score_source_list, key=lambda k: (k['source'], k['generated_on']))
    try:
        latest_score = score_source_list[-1]["score"]
    except Exception:
        # When empty data comes from event it will raise list index out of bound.
        return False
    return True if latest_score >= min_score else False


def calculate_cvss_score(helper, data):
    """Method to calculate cvss score."""
    data = json.loads(json.dumps(data))
    score_list = data["cvss_metrics"]
    score_source_list = []
    for score_data in score_list:
        source = score_data["source"]
        if "RBS" in source:
            source = "rbs"
        if "nvd" in source:
            source = "nvd"
        generated_on = score_data["generated_on"]
        score = score_data["score"]
        score_source_list.append({"score": score, "generated_on": generated_on, "source": source})

    score_source_list = sorted(score_source_list, key=lambda k: (k['source'], k['generated_on']), reverse=True)

    try:
        latest_score = score_source_list[0]["score"]
        data["overall_cvss_score"] = latest_score
    except Exception:
        # When empty data comes from event it will raise list index out of bound.
        pass

    return data


def write_events(helper, ew, eventlist, marker, min_score):
    """Event writer helper."""
    latest = "1"
    cnt = 0
    ingest_count = 0
    for x in sorted(eventlist.keys()):
        if min_score != 0:
            if not data_with_min_score(helper, min_score, eventlist[x]["data"]):
                continue

        cnt += 1
        et = epochtime(eventlist[x]["moddate"], "%Y-%m-%dT%H:%M:%SZ")
        id = eventlist[x]["id"]
        if (int(et) > int(latest)):
            latest = et
        if (int(et) > int(marker)):
            try:
                event_data = calculate_cvss_score(helper, eventlist[x]["data"])
                event = helper.new_event(source=helper.get_input_type(),
                                         index=helper.get_output_index(),
                                         sourcetype=helper.get_sourcetype(),
                                         data=json.dumps(event_data))
                helper.log_debug("VulnDB ID [" + str(id) + "] : Mod date [" + str(eventlist[x]["moddate"]) + "]")
                ew.write_event(event)
                ingest_count += 1
            except Exception:
                helper.log_error("Error writing event to Splunk: " + str(sys.exc_info()[0]))
                continue
        else:
            helper.log_debug("Mod time is less than marker, skipping VulnDB ID [" + str(id) + "]")
    return cnt, ingest_count


def collect_events(helper, ew):
    # 'application' code
    """Implement your data collection logic here."""
    helper.log_info("=== Starting collect_events routine ===")

    # Setup variables for use in loops and tracking pages
    page = '1'
    finished = False
    total_entries = '0'
    event = None  # noqa: F841
    success = False
    nodata = True
    nosort = False
    processed = 0
    total_ingest_count = 0
    hours_difference = 0

    helper.log_debug("Loading inputs.conf settings for " + list(helper.get_input_stanza().keys())[0])
    opt_api_server = helper.get_arg('api_server')
    opt_api_key = helper.get_arg('api_key')
    opt_api_secret = helper.get_arg('api_secret')
    opt_start_date = helper.get_arg('start_date')
    opt_page_size = helper.get_arg('page_size')
    opt_nested = helper.get_arg('nested')
    opt_additional_info = helper.get_arg('additional_info')
    opt_show_cpe = helper.get_arg('show_cpe')
    opt_category = helper.get_arg('category')
    opt_full_reference_url = helper.get_arg('full_reference_url')
    opt_package_info = helper.get_arg('package_info')
    opt_show_cvss_v3 = helper.get_arg('show_cvss_v3')
    opt_changelog = helper.get_arg('changelog')
    opt_reset_input = helper.get_arg('reset_input')
    opt_min_cvssv2_score = helper.get_arg('min_cvssv2_score', None)

    # Create string variables for use in URL
    nested = 'true' if opt_nested else 'false'
    additional_info = 'true' if opt_additional_info else 'false'
    show_cpe = 'true' if opt_show_cpe else 'false'
    category = 'true' if opt_category else 'false'
    full_reference_url = 'true' if opt_full_reference_url else 'false'
    package_info = 'true' if opt_package_info else 'false'
    show_cvss_v3 = 'true' if opt_show_cvss_v3 else 'false'
    vtem = 'false'
    changelog = 'true' if opt_changelog else 'false'
    page_size = int(opt_page_size)
    start_date = str(opt_start_date)
    if opt_min_cvssv2_score is not None and opt_min_cvssv2_score != "":
        min_cvssv2_score = float(opt_min_cvssv2_score)
    else:
        min_cvssv2_score = 0

    session_key = helper.context_meta['session_key']
    splunk_version = get_splunk_version(helper, session_key)
    app_conf_file = get_conf_file(helper, session_key, "app", stanza="launcher")
    app_version = app_conf_file.get("version") if app_conf_file else None
    headers = {
        "User-Agent": "Splunk-{}-TA-vuln-db-{}".format(splunk_version, app_version),
        "Accept": "vnd.flashpoint.v2+json"
    }

    # Check the start date to see if we need to get everything
    if (start_date == "1"):
        helper.log_debug("start_date set to '1', retrieving ALL vulnerabilities.")
        search = '0/find_next_to_vulndb_id?'
        start_date = UNIX_EPOCH_START_DATE
        get_all = True
    else:
        search = 'find_by_time?hours_ago='
        get_all = False

    # Check to see if we have an existing starting point saved from the last run
    if (not opt_reset_input):
        try:
            marker = helper.get_check_point("marker")
            start_date = datetime.datetime.utcfromtimestamp(int(marker))
            start_date = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            helper.log_debug("Marker found: " + str(marker))
            helper.log_debug("Start date set to marker date: " + start_date)
            search = 'find_by_time?hours_ago='
        except Exception:
            start_date = start_date + DEFAULT_START_DATE_HOURS
            marker = epochtime(start_date, "%Y-%m-%dT%H:%M:%S")
            helper.log_info("Marker not found: Setting marker to start_date [" + start_date + "]")
    else:
        helper.log_debug("Reset input is True.  Removing marker and setting to start_date [" + start_date + "]")
        helper.delete_check_point("marker")
        start_date = start_date + DEFAULT_START_DATE_HOURS
        marker = epochtime(start_date, "%Y-%m-%dT%H:%M:%S")
        unset_reset_flag(helper)

    hours = utctime(start_date)
    if hours > 0:
        hours_difference = int(math.ceil(hours))
    elif hours == 0:
        hours_difference = 1
    else:
        helper.log_error("Error processing start date. Please check for valid date.")

    if (not get_all or (get_all and marker)):
        search = search + str(hours_difference)

    helper.log_info(">>> Starting REST API call loop <<<")
    eventlist = {}

    session = create_new_session(opt_api_key)
    uri = helper._get_proxy_uri()
    proxy_settings = {
        "http": uri,
        "https": uri
    }

    try:
        result = session.fetch_token(token_url=TOKEN_URL, proxies=proxy_settings, client_id=opt_api_key,  # noqa: F841
                                     client_secret=opt_api_secret)
    except Exception:
        helper.log_error("Some error occurred while collecting data. Please check that entered server URL, Consumer "
                         "Key and Consumer Secret are valid OR check your proxy settings.")

    start_time = datetime.datetime.utcnow()

    while (not finished):
        url = opt_api_server + '/vulnerabilities/' + search + \
            '&page=' + str(page) + \
            '&size=' + opt_page_size + \
            '&nested=' + nested + \
            '&additional_info=' + additional_info + \
            '&show_cpe=' + show_cpe + \
            '&social_risk_score=true' + \
            '&category=' + category + \
            '&full_reference_url=' + full_reference_url + \
            '&package_info=' + package_info + \
            '&show_cvss_v3=' + show_cvss_v3 + \
            '&vtem=' + vtem + \
            '&changelog=' + changelog
        helper.log_info("Final search string: " + search)

        try:
            data, new_session = call_api(session, proxy_settings, url, opt_api_key, opt_api_secret, helper, headers)
            if data == "finished":
                helper.log_info("No vulnerability found.")
                finished = True
                break
            if new_session:
                session = new_session
        except Exception:
            helper.log_error("Error fetching Page - " + str(page))
            break

        if data:
            success = True
        helper.log_debug("While loop - Page " + str(page))

        # decode the data to utf-8 for python 2/3 compatibility
        data = data.decode('utf-8')
        if (isinstance(data, string_types)):
            apidata = json.loads(data, object_pairs_hook=OrderedDict)
            try:
                helper.log_error("API Error: " + str(apidata["error"]))
                success = False
                finished = True
                break
            except Exception:
                helper.log_info("No errors detected, continuing...")
            try:
                total_entries = apidata["total_entries"]
                current_page = apidata["current_page"]  # noqa: F841
                results = apidata["results"]
                helper.log_debug("Total entries found: " + str(total_entries))
            except Exception:
                helper.log_error("Error retrieving API results: " + str(sys.exc_info()[0]))
                helper.log_debug("API JSON Dump:\n" + json.dumps(apidata))
                success = False
                finished = True
                break
            # Try to calculate the number of pages
            try:
                page = apidata["current_page"]
                total_entries = apidata["total_entries"]
                pages = (total_entries // page_size)
                # Add one more page if it's not evenly divided
                if (total_entries % page_size > 0):
                    pages = pages + 1
                success = True
                # If there are more than 10000 results, don't sort and write events a page at a time
                if (int(total_entries) > 10000):
                    nosort = True
            except Exception:
                helper.log_error("Error calculating page delineation: " + str(sys.exc_info()[0]))
                page = None
                total_entries = None
                pages = None
                results = {}
                success = False
            vulns = results
            cnt = 0
            for vuln in vulns:
                cnt += 1
                id = vuln["vulndb_id"]
                eventlist[id] = {}
                eventlist[id]["id"] = vuln["vulndb_id"]
                eventlist[id]["moddate"] = vuln["vulndb_last_modified"]
                eventlist[id]["data"] = vuln
            helper.log_debug("Processed " + str(cnt) + " events from page " + str(page))
            nodata = False
        else:
            helper.log_info("No new vulnerability information found.")
            success = False
            nodata = True
            finished = True
            break
        helper.log_info("Page " + str(page) + " of " + str(pages))

        # If we have a lot of pages, write events now and don't sort
        if (nosort):
            helper.log_debug("Writing events to Splunk...")
            tmpcnt, tmp_ingest_count = write_events(helper, ew, eventlist, 0, min_cvssv2_score)
            processed += tmpcnt
            total_ingest_count += tmp_ingest_count
            eventlist = {}

        # Check to see if we are on the last page
        if (page >= pages):
            finished = True
        else:
            finished = False
        page += 1
    if (success and not nodata):
        helper.log_info(">>> Finished REST API call loop <<<")
        if (not nosort):
            cnt, ingested_event_count = write_events(helper, ew, eventlist, marker, min_cvssv2_score)
        else:
            cnt = processed
            ingested_event_count = total_ingest_count
        helper.log_info("Processed " + str(cnt) + " total records.")
        helper.log_info("Ingested " + str(ingested_event_count) + " records to Splunk.")
        helper.log_debug("Current marker: " + str(marker))

        try:
            marker = int((start_time - datetime.datetime.utcfromtimestamp(0)).total_seconds())
            helper.log_info("Saving marker: " + str(marker))
            helper.save_check_point("marker", marker)
        except Exception:
            helper.log_error("Error saving marker: " + str(marker) + "\n" + str(sys.exc_info()[0]))
    elif (not success and nodata):
        pass
    else:
        helper.log_info("The API data collection was unsuccessful.")
    helper.log_info("=== Finished collect_events routine ===")


def create_new_session(api_key):
    """Method to create a new session using OAuth."""
    client = BackendApplicationClient(client_id=api_key)
    return OAuth2Session(client=client)


"""
        # Verify that the modification dates are newer than the saved date
#         latest = "1"
#         cnt = 0
#         for x in sorted(eventlist.keys()):
#             cnt += 1
#             et = epochtime(eventlist[x]["moddate"], "%Y-%m-%dT%H:%M:%SZ")
#             id = eventlist[x]["id"]
#             if(int(et) > int(marker)):
#                 try:
#                     event = helper.new_event(source=helper.get_input_type(),
#                     index=helper.get_output_index(),
#                     sourcetype=helper.get_sourcetype(),
#                     data=json.dumps(eventlist[x]["data"]))
#                     helper.log_debug("VulnDB ID [" + str(id) + "] : Mod date [" + str(eventlist[x]["moddate"]) + "]")
#                     ew.write_event(event)
#                 except Exception
#                     helper.log_error("Error writing event to Splunk: " + str(sys.exc_info()[0]))
#                     continue
#             else:
#                 helper.log_debug("Mod time is less than marker, skipping VulnDB ID [" + str(id) + "]")
#             if(int(et) > int(latest)):
#                 latest = et
"""
