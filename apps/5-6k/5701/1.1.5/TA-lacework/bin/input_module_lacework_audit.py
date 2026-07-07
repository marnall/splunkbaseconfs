# encoding = utf-8
import datetime
import requests
import json
import time


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    #################################################
    # Globals
    #################################################

    stanzas = helper.input_stanzas
    for stanza_name in stanzas:
        opt_stanza = stanza_name

    LOGSTR = "[EVO] Input: " + opt_stanza + " | "

    #################################################
    # End Globals
    #################################################

    ############################################
    # Utility Functions
    ############################################

    def log_debug(text):
        helper.log_debug(LOGSTR + text)

    def log_info(text):
        helper.log_info(LOGSTR + text)

    def log_warning(text):
        helper.log_warning(LOGSTR + text)

    def log_error(text):
        helper.log_error(LOGSTR + text)

    def get_cp(key):
        cp = helper.get_check_point(key)

        if not cp or cp is None:
            log_info("No existing checkpoint found. Assuming first run and pulling last 30 days.")
            # Start with 30 days ago
            cp = str((int(run_start_time) - 2592000))
        elif len(str(cp)) != 10:
            log_error("Checkpoint invalid. Creating new one.")
            cp = str((int(run_start_time) - 2592000))
        else:
            log_info("Retrieved checkpoint: " + str(cp))

        return int(cp)

    def save_cp(key, cp):
        helper.save_check_point(key, str(cp))
        log_info("Saved checkpoint: " + str(cp))

    def parse_timestamp_from_cp(x):

        epoch = None
        ms = None

        cp = str(x)

        if len(cp) == 13:
            epoch = str(cp)[:10]
            ms = str(cp)[-3:]
        elif len(cp) == 10:
            epoch = str(cp)
            # ms = "000"

        # ts = datetime.datetime.fromtimestamp(float(epoch)).strftime('%Y-%m-%dT%H:%M:%S') + "." + ms + "Z"

        ts = datetime.datetime.fromtimestamp(float(epoch)).strftime('%Y-%m-%dT%H:%M:%SZ')

        # raise Exception("\nx: " + str(x) + "\nepoch: " + str(epoch) + "\nts: " + ts)

        return str(ts)

    def parse_epoch_from_timestamp(timestamp):
        return datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ').timestamp()

    #################################################
    # End Utility Functions
    #################################################

    #################################################
    # Retrieve Config
    #################################################

    request_timeout = helper.get_global_setting("request_timeout")
    if not request_timeout:
        log_info("No Request Timeout Found. Defaulting to 5s.")
        request_timeout = 5

    opt_account = helper.get_arg('account_name')
    opt_interval = int(helper.get_arg('interval'))
    opt_key_id = helper.get_arg('global_account')["username"]
    opt_key_secret = helper.get_arg('global_account')["password"]
    idx = helper.get_output_index()
    st = "lacework:audit:" + opt_account

    api_base = "https://" + opt_account + ".lacework.net/api"
    audit_url = api_base + "/v2/AuditLogs"
    token_url = api_base + "/v2/access/tokens"

    run_start_time = time.time()
    next_run_start_time = time.time() + float(opt_interval)

    cp_key = "lacework:audit:" + opt_account

    #################################################
    # End Retrieve Config
    #################################################

    #################################################
    # Lacework API Calls
    #################################################
    def retrieve_token():

        headers = {
            'X-LW-UAKS': opt_key_secret,
            'Content-Type': 'application/json'
        }
        payload = {
            'keyId': opt_key_id,
            'expiryTime': 60
        }

        token = None

        try:
            response = helper.send_http_request(token_url, "POST", headers=headers, parameters=None,
                                                payload=payload, cookies=None, verify=None, cert=None,
                                                timeout=float(request_timeout), use_proxy=True)
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout,
                requests.exceptions.Timeout, requests.exceptions.ConnectionError) as ex:
            log_error("Current timeout is " + str(request_timeout)
                      + " (seconds). Try again after increasing the request timeout value.")
            raise ex

        if response.status_code == 201:
            token = response.json()["token"]

        else:
            log_error("Could not retrieve bearer token. Status: " + str(response.status_code))
            exit(1)

        return token

    def retrieve_data(token, parsed_start_time, parsed_end_time):

        retry_attempts = 5

        while True:

            # url = audit_url + "?startTime=" + str(parsed_start_time) + "&endTime=" + str(parsed_end_time)
            url = audit_url

            params = {
                'startTime': parsed_start_time,
                'endTime': parsed_end_time
            }
            headers = {
                'Authorization': token,
                'Content-Type': "application/json"
            }

            log_info("Querying: " + url)

            try:
                response = helper.send_http_request(url, "GET", headers=headers, parameters=params,
                                                    payload=None, cookies=None, verify=None, cert=None,
                                                    timeout=float(request_timeout), use_proxy=True)
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout,
                    requests.exceptions.Timeout, requests.exceptions.ConnectionError) as ex:
                log_error("Current timeout is " + str(request_timeout)
                          + " (seconds). Try again after increasing the request timeout.")
                raise ex

            r_status = response.status_code
            r_content = None
            log_debug("Response Code: " + str(r_status))

            # raise Exception(response.status_code)
            if r_status != 200 and r_status != 404 and r_status != 204:
                # raise Exception(audit_url)
                # raise Exception(response.json())
                # raise Exception(response.status_code)
                log_error("Received Error Code [" + str(r_status) + "] from api. Retrying ["
                          + str(retry_attempts) + "] more time(s).")
                retry_attempts = retry_attempts - 1
                if retry_attempts < 1:
                    log_error("Received Error Code [" + str(r_status)
                              + "] from api. No more retry attempts. Exiting.")
                    exit(0)
                    return False
                continue

            elif r_status == 404:
                log_info("Got 404 from API. If using the correct URL,this occurs when there was no data in the time range queried.")
                return r_status, None

            elif r_status == 204:
                log_info("Got 204-No Content from API. This occurs when there was no data in the time range queried.")
                return r_status, None

            else:
                try:
                    r_content = response.json()
                except ValueError:
                    log_error("Received successful (200) status code, but no content was returned. "
                              "Status Code: " + str(r_status))
                    return r_status, None

            # raise Exception(response.json())
            return r_status, r_content

    #################################################
    # End Lacework API Calls
    #################################################

    #################################################
    # Main Logic
    #################################################

    # Retrieve the checkpoint
    last_cp = get_cp(cp_key)

    # Start time is 1s after last cp.1
    start_time = parse_timestamp_from_cp(int(last_cp) + 1)

    # The new end time will be 10 seconds before this input's start time.
    end_time = parse_timestamp_from_cp(int(run_start_time) - 10)

    log_info("start_time = " + str(start_time) + " | end_time = " + str(end_time))

    token = retrieve_token()
    status, data = retrieve_data(token, start_time, end_time)

    if status == 404 or status == 204:
        log_info(
            "Audit Log Request returned 404/204. This generally means there were no audit entries in the timeframe queried. Updating checkpoint and Exiting.")
        save_cp(cp_key, str(int(parse_epoch_from_timestamp(end_time))))
        exit(0)

    # If there's no data, let's just stop right here
    if not data:
        log_error("Nothing returned. Did call error? Exiting.")
        exit(1)

    log_info("Successfully retrieved data from Lacework API.")

    # log_debug(data)

    # Ingest the events into splunk
    for event in data['data']:
        timestamp = event['createdTime']
        epoch = parse_epoch_from_timestamp(timestamp)
        event = helper.new_event(json.dumps(event), time=epoch)
        ew.write_event(event)

    save_cp(cp_key, str(int(parse_epoch_from_timestamp(end_time))))
    exit(0)