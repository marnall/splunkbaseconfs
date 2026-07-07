# encoding = utf-8

from opswat_auth import get_auth_token
from helpers import remove_https_from_host
import checkpoint_utils
import json
from time import sleep
from enum import Enum

class ProductType(Enum):
    PMP = 1
    MDD = 2
    CORE = 3

def validate_input(helper, definition):
    pass


def get_retrieve_report_detail(helper):
    try:
        return int(helper.get_arg('retrieve_report_details'))
    except:
        return 0


def define_product_type(api):
    if 'o/pmp/' in api:
        return ProductType.PMP
    elif 'o/mdd/' in api:
        return ProductType.MDD
    elif 'o/core/' in api:
        return ProductType.CORE
    else:
        raise ValueError('Invalid API endpoint: {}'.format(api))


def get_source_type(product_type):
    if product_type == ProductType.PMP:
        return "CM:PMP:"
    elif product_type == ProductType.MDD:
        return "CM:MDD:"
    elif product_type == ProductType.CORE:
        return "CM:MDCORE:"
    return None


def update_timestamp_for_data(data):
    if 'sync_time' in data:
        data['timestamp'] = data['sync_time']
        del data['sync_time']


def get_oauth_token_2(helper, global_account, from_checkpoint):
    account_name = global_account['name']
    client_key = global_account['client_key']
    client_secret = global_account['client_secret']
    host = remove_https_from_host(global_account['host'].strip('/'))
    auth_endpoint = "o/oauth2/token"
    use_proxy = True if helper.get_proxy() else False
    if from_checkpoint:
        return checkpoint_utils.get_token(
            account_name,
            helper,
            client_key,
            client_secret,
            host,
            auth_endpoint,
            use_proxy
        )
    else:
        token = get_auth_token(helper, client_key, client_secret, host, auth_endpoint, use_proxy)
        helper.save_check_point('{}_opswat_auth_token'.format(account_name), token)
        return token


def collect_events(helper, ew):
    global_account = helper.get_arg('global_account')
    account_name = global_account['name']
    input_name = '{0}_{1}'.format(account_name, list(helper.get_input_stanza().keys())[0])
    host = remove_https_from_host(global_account['host'].strip('/'))
    use_proxy = True if helper.get_proxy() else False
    request_filter = helper.get_arg('filter')
    start_date = helper.get_arg('start_date')
    path = helper.get_arg('api_endpoint').strip('/')
    product_type = define_product_type(path)
    time_checkpoints = checkpoint_utils.get_time(helper, input_name, start_date)
    retrieve_report_detail = get_retrieve_report_detail(helper)

    token = get_oauth_token_2(helper, global_account, from_checkpoint=True)
    endpoint = 'https://{}/{}'.format(host, path)
    sourcetype = "{}{}".format(get_source_type(product_type), "Reports")

    helper.log_info('{0} input starting, collecting events from {1} to {2}.'
                    .format(input_name, time_checkpoints['start_time'], time_checkpoints['end_time']))

    done = False
    nextPageToken = ''
    limit = 100

    while not done:
        helper.log_info('Invoking \'{0}\' request to {1} for token {2}'.format(input_name, endpoint, nextPageToken))

        valid_token = False
        auth_failures = 0

        while not valid_token:
            r = helper.send_http_request(
                endpoint,
                'POST',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': token
                },
                payload={
                    'token': nextPageToken,
                    'limit': limit,
                    'start_time': time_checkpoints['start_time'],
                    'end_time': time_checkpoints['end_time'],
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

                token = get_oauth_token_2(helper, global_account, from_checkpoint=False)
                helper.log_info('Expired auth token, requesting a new one')

        # If response status code == 200
        if r.ok:
            r_json = r.json()
            logs = r_json['data']
            helper.log_info('Successful \'{0}\' request for token {1}. Received {2} logs.'.format(input_name, nextPageToken, len(logs)))

            # If JSON payload contains logs
            if logs:
                helper.log_info('Creating and writing {} events.'.format(len(logs)))

                reports = []

                for log in logs:
                    update_timestamp_for_data(log)
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
                    reports.append({
                        "session_id": log['session_id'] if 'session_id' in log else None,
                        "total_threat": log['total_threat'] if 'total_threat' in log else None,
                        "scanned_by": log['scanned_by'] if 'scanned_by' in log else None,
                    })

                if len(reports) > 0 and retrieve_report_detail and product_type != ProductType.CORE:
                    for report in reports:
                        try:
                            get_report_detail(helper, ew, global_account, input_name, use_proxy, host, token, report, product_type)
                        except:
                            helper.log_error('Failed to retrieve report detail for session_id {}.'.format(report['session_id']))
                            continue

                nextPageToken = r_json['token']

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


def get_payload_by_product_type(product_type, request_filter, report):
    filter_data = json.loads(request_filter) if request_filter else None

    if product_type == ProductType.PMP:
        return {
            'filter': filter_data,
            "session_id": report['session_id']
        }
    elif product_type == ProductType.MDD:
        return {
            'filter': filter_data,
            "device_id": report['scanned_by'],
            "report_id": report['session_id']
        }


def get_report_detail(helper, ew, global_account, input_name, use_proxy, host, token, report, product_type):
    if report['session_id'] is None or report['session_id'] == '' or report['total_threat'] == 0:
        return None

    path = helper.get_arg('api_endpoint').strip('/')
    sourcetype = "{}{}".format(get_source_type(product_type), "ReportDetails")
    endpoint = 'https://{}/{}/details'.format(host, path)
    request_filter = helper.get_arg('filter')
    done = False

    while not done:
        valid_token = False
        auth_failures = 0

        while not valid_token:
            r = helper.send_http_request( endpoint, 'POST',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': token,
                },
                payload=get_payload_by_product_type(product_type, request_filter, report),
                cookies=None,
                timeout=None,
                use_proxy=use_proxy, stream=True
            )

            if r.status_code != 401:
                valid_token = True
            else:
                auth_failures+=1

                if auth_failures == 3:
                    helper.log_error('Cannot retrieve a valid auth token, exiting input now.')
                    return None

                token = get_oauth_token_2(helper, global_account, from_checkpoint=False)
                helper.log_info('Expired auth token, requesting a new one')

        # If response status code == 200
        if r.ok:
            helper.log_info('Successful \'{0}\' request.'.format(input_name))

            for line in r.iter_lines(decode_unicode=True):
                if line:
                    try:
                        report = json.loads(line)
                        update_timestamp_for_data(report)
                        event = helper.new_event(
                            json.dumps(report),
                            time=report['timestamp'] / 1000,
                            host=host,
                            index=None,
                            source=None,
                            sourcetype=sourcetype,
                            done=True,
                            unbroken=True
                        )
                        ew.write_event(event)
                    except json.JSONDecodeError:
                        print(f"Invalid JSON: {line}")
                        continue

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
    return None
