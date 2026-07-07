# encoding = utf-8

import timestamp_utils
from opswat_auth import get_auth_token
from helpers import (
    remove_https_from_host,
    get_start_time_epoch_ms
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
    event_category = helper.get_arg('event_category')
    start_date = helper.get_arg('start_date')
    method = 'POST'
    request_filter = helper.get_arg('filter')
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
    endpoint = 'https://{}/{}'.format(host, path)

    helper.log_info('{0} input starting, collecting events from {1} to {2}.'.format(input_name, time_checkpoints['start_time'], time_checkpoints['end_time']))

    done = False
    nextPageToken = ''
    limit = 100

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
                    'event_category': event_category,
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
                        sourcetype=None,
                        done=True, 
                        unbroken=True
                    )
                    ew.write_event(event)

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
