# encoding = utf-8

import timestamp_utils
from opswat_auth import get_auth_token
from helpers import (
    remove_https_from_host,
    load_request_body
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
    method = helper.get_arg('http_request_method').upper()
    request_body = load_request_body(helper, helper.get_arg('body'))
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
    endpoint = 'https://{}/{}'.format(host, path)

    helper.log_info('{0} input starting at {1}'.format(input_name, timestamp_utils.get_epoch_s()))


    # If request method == 'POST'
    if method.lower() == 'post':
        v34_devices_api = (path == 'o/api/v3.4/devices')
        done = False
        page = 1
        page_token = ''
        limit = 50
        
        while not done:
            helper.log_info('Invoking \'{0}\' {1} request to {2} for page {3}'.format(input_name, method, endpoint, page))

            valid_token = False
            auth_failures = 0
            # For cursor based APIs use token instead of page
            if v34_devices_api:
                request_body['token'] = page_token
            else:
                request_body['page'] = page
            request_body['limit'] = limit

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
                    if v34_devices_api:
                        for i in r_json["devices"]:
                            event = helper.new_event(
                                json.dumps(i),
                                time=None,
                                host=host,
                                index=None,
                                source=None,
                                sourcetype=None,
                                done=True,
                                unbroken=True
                            )
                            ew.write_event(event)

                        if r_json["next_token"]:
                            page_token = r_json["next_token"]
                        else:
                            done = True


                    # If JSON data is type list
                    elif type(r_json) == list:
                        for i in r_json:
                            event = helper.new_event(
                                json.dumps(i), 
                                time=None, 
                                host=host, 
                                index=None, 
                                source=None, 
                                sourcetype=None,
                                done=True, 
                                unbroken=True
                            )
                            ew.write_event(event)


                    # Else if JSON data is a dictionary
                    elif type(r_json) == dict:
                        for key, value in r_json.items():
                            for v in value:
                                event = helper.new_event(
                                    json.dumps(v), 
                                    time=None, 
                                    host=host, 
                                    index=None, 
                                    source=None, 
                                    sourcetype=None,
                                    done=True, 
                                    unbroken=True
                                )
                                ew.write_event(event)

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


            # Else any other non-desirable response status code (400, 404, 405, etc.)
            else:
                r.raise_for_status()
                done = True


    # Else if request method == 'GET'
    else:
        helper.log_info('Invoking \'{0}\' {1} request to {2}.'.format(input_name, method, endpoint))

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
            helper.log_info('Successful \'{0}\' request.'.format(input_name))

            event = helper.new_event(
                json.dumps(r_json), 
                time=None, 
                host=host, 
                index=None, 
                source=None, 
                sourcetype=None,
                done=True, 
                unbroken=True
            )
            ew.write_event(event)
            
            helper.log_info('\'{}\' event collection finished for this round.'.format(input_name))


        # Else if response status code == 429 (Rate Limit Reached)
        elif r.status_code == 429:
            helper.log_info('{}: API rate limit reached for this minute, waiting for 30 seconds...'.format(input_name))
            sleep(30)
            helper.log_info('{}: 30 second wait for rate limit complete, continuing event collection.'.format(input_name))


        # Else any other non-desirable response status code (400, 404, 405, etc.)
        else:
            r.raise_for_status()
