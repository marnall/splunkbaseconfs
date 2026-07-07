# encoding = utf-8

from opswat_auth import get_auth_token
from helpers import (
    remove_https_from_host,
    load_request_body,
    is_historical_data_time_range
)
import checkpoint_utils
import json
from time import sleep


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    global_account = helper.get_arg('global_account')
    account_name = global_account['name']
    input_name = '{0}_{1}'.format(account_name, list(helper.get_input_stanza().keys())[0])
    client_key = global_account['client_key']
    client_secret = global_account['client_secret']
    host = remove_https_from_host(global_account['host'].strip('/'))
    auth_endpoint = global_account['auth_endpoint'].strip('/')
    path = helper.get_arg('api_endpoint').strip('/')
    start_date = helper.get_arg('start_date')
    request_filter = helper.get_arg('filter')
    event_triggers = helper.get_arg('event_trigger')
    device_details_path = helper.get_arg('device_details_endpoint').strip('/')
    device_details_body = load_request_body(helper, helper.get_arg('device_details_body'))
    vulnerabilities_path = helper.get_arg('vulnerabilities_endpoint').strip('/')
    vulnerabilities_body = load_request_body(helper, helper.get_arg('vulnerabilities_body'))
    retrieve_device_details = int(helper.get_arg('retrieve_device_details'))
    retrieve_vulnerabilities = int(helper.get_arg('retrieve_vulnerabilities'))
    use_proxy = True if helper.get_proxy() else False
    token = checkpoint_utils.get_token(
        account_name,
        helper,
        client_key,
        client_secret,
        host,
        auth_endpoint,
        use_proxy
    )
    time_checkpoints = checkpoint_utils.get_time(helper, input_name, start_date)
    logs_endpoint = 'https://{0}/{1}'.format(host, path)
    details_endpoint = 'https://{0}/{1}'.format(host, device_details_path)
    vulnerabilities_endpoint = 'https://{0}/{1}'.format(host, vulnerabilities_path)
    helper.log_info('{0} input starting, collecting events from {1} to {2}.'.format(input_name, time_checkpoints['start_time'], time_checkpoints['end_time']))


    """ Collects the necessary data from device logs for 
    the additional requests """
    logs_data = get_logs(
        account_name,
        helper, 
        input_name, 
        logs_endpoint, 
        time_checkpoints, 
        request_filter, 
        use_proxy,
        client_key,
        client_secret,
        host,
        auth_endpoint,
        token,
        ew
    )

    """ Creates unique list of event log data, only 1 event log per device, most recent event """
    logs_data = sort_logs_data(logs_data, helper)


    if not logs_data:
        helper.log_info('No logs retrieved, {} input finished for this round.'.format(input_name))

    else:
        """ Checks if the input is collecting historical data.
        If time collection time range > 1 day, then Device
        Details & Device CVEs requests are not triggered """
        if not is_historical_data_time_range(time_checkpoints, helper):
            for log_data in logs_data:

                # If the log's event is a selected trigger
                if log_data['event'] in event_triggers:

                    # If Retrieve Device Details is checked
                    if retrieve_device_details:
                        helper.log_debug('Retrieving device details for device {0} with event {1}.'.format(log_data['device_id'], log_data['event']))

                        get_device_details(
                            account_name,
                            helper,
                            input_name,
                            details_endpoint,
                            device_details_body,
                            use_proxy,
                            client_key,
                            client_secret,
                            host,
                            auth_endpoint,
                            token,
                            ew,
                            log_data
                        )

                    # If Retrieve Device CVEs is checked
                    if retrieve_vulnerabilities:
                        helper.log_debug('Retrieving vulnerabilities for device {0} with event {1}.'.format(log_data['device_id'], log_data['event']))

                        get_device_vulnerabilities(
                            account_name,
                            helper,
                            input_name,
                            vulnerabilities_endpoint,
                            vulnerabilities_body,
                            use_proxy,
                            client_key,
                            client_secret,
                            host,
                            auth_endpoint,
                            token,
                            ew,
                            log_data
                        )

                # If the log's event is NOT a selected trigger
                else:
                    helper.log_debug('{0} not a selected trigger, skipping additional requests.'.format(log_data['event']))


def sort_logs_data(logs_data, helper):
    helper.log_info('Creating unique list of event log data for device details & vulnerabilities requests.')
    unique_logs_data = []
    devices = {}

    for data in logs_data:
        if not devices.get(data['device_id']):
            devices[data['device_id']] = []
        
        devices[data['device_id']].append(data)

    for _, data_list in devices.items():
        data_list.sort(key = lambda x:x['timestamp'])
        unique_logs_data.append(data_list[-1])

    return unique_logs_data


def get_logs(
    account_name,
    helper, 
    input_name, 
    endpoint, 
    time_checkpoints, 
    request_filter, 
    use_proxy,
    client_key,
    client_secret,
    host,
    auth_endpoint,
    token,
    ew
):
    done = False
    nextPageToken = ''
    limit = 100
    method = 'POST'
    logs_data = []
    sourcetype = 'MetaAccess:Device:Logs'

    while not done:
        helper.log_info('Invoking \'{0}\' {1} request to {2} for token {3}'.format(input_name, method, endpoint, nextPageToken))

        valid_token = False
        auth_failures = 0

        while not valid_token:
            r = helper.send_http_request(
                endpoint,
                method,
                parameters={
                    'verify': True
                },
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': token
                },
                payload={
                    'token': nextPageToken,
                    'limit': limit,
                    'start_time': time_checkpoints['start_time'],
                    'end_time': time_checkpoints['end_time'],
                    'event_category': 'device',
                    'filter': json.loads(request_filter) if request_filter else None
                },
                cookies=None,
                timeout=None,
                use_proxy=use_proxy
            )

            if r.status_code != 401:
                valid_token = True

            else:
                auth_failures+=1

                if auth_failures == 3:
                    helper.log_error('Cannot retrieve a valid auth token, exiting input now.')
                    return None

                helper.log_info('Expired auth token, requesting a new one.')
                token = get_auth_token(helper, client_key, client_secret, host, auth_endpoint, use_proxy)
                helper.save_check_point('{}_opswat_auth_token'.format(account_name), token)

        
        # If response status code == 200
        if r.ok:
            r_json = r.json()
            logs = r_json['data']
            helper.log_info('Successful \'{0}\' request for token {1}. Received {2} logs.'.format(input_name, nextPageToken, len(logs)))

            # If JSON payload contains logs
            if logs:
                helper.log_info('Creating and writing {} events.'.format(len(logs)))

                for log in logs:
                    event = helper.new_event(
                        json.dumps(log), 
                        time=None, 
                        host=host, 
                        index=None, 
                        source=None, 
                        sourcetype=sourcetype,
                        done=True, 
                        unbroken=True
                    )
                    ew.write_event(event)

                    # Adds necessary log data to list for subsequent requests to device details & CVEs
                    logs_data.append({
                        'device_id': log.get('device_id'),
                        'event': log.get('event'),
                        'timestamp': log.get('timestamp')
                    })

                nextPageToken = r_json['token']


            # Else if JSON payload is empty
            else:
                done = True


        # Else if response status code == 413 (No Items for Current Page)
        elif r.status_code == 413:
            helper.log_info('No logs returned for token {}.'.format(nextPageToken))
            helper.log_info('\'{}\' event collection finished for this round.'.format(input_name))
            done = True


        # Else if response status code == 429 (Rate Limit Reached)
        elif r.status_code == 429:
            helper.log_info('{}: API rate limit reached for this minute, waiting for 30 seconds...'.format(input_name))
            sleep(30)
            helper.log_info('{}: 30 second wait for rate limit complete, continuing event collection.'.format(input_name))


        # Else any other non-desirable response status code (400, 404, 405, etc.)
        else:
            r.raise_for_status()
            done = True
    
    return logs_data


def get_device_details(
    account_name,
    helper,
    input_name,
    endpoint,
    request_body,
    use_proxy,
    client_key,
    client_secret,
    host,
    auth_endpoint,
    token,
    ew,
    log_data
):
    done = False
    method = 'POST'
    sourcetype = 'MetaAccess:Device:Details'
    request_body['ids'] = [log_data['device_id']]
    
    while not done:
        helper.log_info('Invoking \'{0}\' {1} request to {2}'.format(input_name, method, endpoint))

        valid_token = False
        auth_failures = 0

        helper.log_info('Request body: {}'.format(request_body))

        while not valid_token:
            r = helper.send_http_request(
                endpoint,
                method,
                parameters={
                    'verify': True
                },
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': token
                },
                payload=request_body,
                cookies=None,
                timeout=None,
                use_proxy=use_proxy
            )

            if r.status_code != 401:
                valid_token = True

            else:
                auth_failures+=1

                if auth_failures == 3:
                    helper.log_error('Cannot retrieve a valid auth token, exiting input now.')
                    return None

                token = get_auth_token(helper, client_key, client_secret, host, auth_endpoint, use_proxy)
                helper.save_check_point('{}_opswat_auth_token'.format(account_name), token)


        # If response status code == 200
        if r.ok:
            r_json = r.json()
            helper.log_info('Successful \'{0}\' request.'.format(input_name))


            # If JSON payload contains data
            if r_json:
                r_json = r_json[0]

                # Adds event log data to the event as per the input requirement
                r_json['event_timestamp'] = log_data['timestamp']
                r_json['event'] = log_data['event']

                event = helper.new_event(
                    json.dumps(r_json), 
                    time=None, 
                    host=host, 
                    index=None, 
                    source=None, 
                    sourcetype=sourcetype,
                    done=True, 
                    unbroken=True
                )
                ew.write_event(event)

                done = True


            # Else if JSON payload is empty
            else:
                done = True


        # Else if response status code == 413 (No Items for Current Page)
        elif r.status_code == 413:
            helper.log_info('No data returned.')
            helper.log_info('\'{}\' event collection finished for this round.'.format(input_name))
            done = True


        # Else if response status code == 429 (Rate Limit Reached)
        elif r.status_code == 429:
            helper.log_info('{}: API rate limit reached for this minute, waiting for 30 seconds...'.format(input_name))
            sleep(30)
            helper.log_info('{}: 30 second wait for rate limit complete, continuing event collection.'.format(input_name))


        # Else any other non-desirable response status code (400, 404, 405, etc.)
        else:
            r.raise_for_status()
            done = True


def get_device_vulnerabilities(
    account_name,
    helper,
    input_name,
    endpoint,
    request_body,
    use_proxy,
    client_key,
    client_secret,
    host,
    auth_endpoint,
    token,
    ew,
    log_data
):
    done = False
    page = 1
    limit = 50
    method = 'POST'
    sourcetype = 'MetaAccess:Device:Vulnerabilities'
    all_cves = []
    
    while not done:
        helper.log_info('Invoking \'{0}\' {1} request to {2} for page {3}'.format(input_name, method, endpoint, page))
        valid_token = False
        auth_failures = 0
        request_body['page'] = page
        request_body['limit'] = limit
        request_body['id'] = log_data['device_id']

        helper.log_info('Request body: {}'.format(request_body))

        while not valid_token:
            r = helper.send_http_request(
                endpoint,
                method,
                parameters={
                    'verify': True
                },
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': token
                },
                payload=request_body,
                cookies=None,
                timeout=None,
                use_proxy=use_proxy
            )

            if r.status_code != 401:
                valid_token = True

            else:
                auth_failures+=1

                if auth_failures == 3:
                    helper.log_error('Cannot retrieve a valid auth token, exiting input now.')
                    return None

                token = get_auth_token(helper, client_key, client_secret, host, auth_endpoint, use_proxy)
                helper.save_check_point('{}_opswat_auth_token'.format(account_name), token)


        # If response status code == 200
        if r.ok:
            r_json = r.json()
            helper.log_info('Successful \'{0}\' request for page {1}.'.format(input_name, page))


            # If JSON payload contains data
            if r_json:

                # Appends all device CVEs to the 'all_cves' list for the final event
                for i in r_json:
                    all_cves.append(i)

                page+=1


            # Else if JSON payload is empty
            else:
                done = True


        # Else if response status code == 413 (No Items for Current Page)
        elif r.status_code == 413:
            helper.log_info('No data returned for page {}.'.format(page))
            helper.log_info('\'{}\' event collection finished for this round.'.format(input_name))
            done = True


        # Else if response status code == 429 (Rate Limit Reached)
        elif r.status_code == 429:
            helper.log_info('{}: API rate limit reached for this minute, waiting for 30 seconds...'.format(input_name))
            sleep(30)
            helper.log_info('{}: 30 second wait for rate limit complete, continuing event collection.'.format(input_name))


        # MetaAccess API returns HTTP 404 if device is not found on this endpoint (has been deleted)
        elif r.status_code == 404:
            helper.log_info('Device not found on CVEs endpoint for device ID: {}'.format(log_data['device_id']))
            done = True
            return


        # Else any other non-desirable response status code (400, 404, 405, etc.)
        else:
            r.raise_for_status()
            done = True

    helper.log_info('Device with ID {0} has a total of {1} associated CVEs.'.format(log_data['device_id'], len(all_cves)))

    # Creates the final event with all device CVEs & event log data as per the input requirements
    event_data = {
        'device_id': log_data['device_id'],
        'event_timestamp': log_data['timestamp'],
        'event': log_data['event'],
        'cves': all_cves
    }

    event = helper.new_event(
        json.dumps(event_data), 
        time=None, 
        host=host, 
        index=None, 
        source=None, 
        sourcetype=sourcetype,
        done=True, 
        unbroken=True
    )
    ew.write_event(event)
