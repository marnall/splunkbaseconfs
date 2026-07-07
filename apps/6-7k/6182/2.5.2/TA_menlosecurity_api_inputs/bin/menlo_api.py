import datetime
import json
import time

log_prefix = "menlo_log_api"


def fetch_logs(helper, ew):
    global log_prefix
    log_prefix = f'[{helper.get_input_type()}://{helper.get_input_stanza_names()}]'

    try:
        config = get_config(helper)
    except Exception as paramsEx:
        helper.log_error(f'{log_prefix} Aborting interval - error initializing input: {paramsEx}')
        raise

    if config['end'] < config['start']:
        helper.log_info(f'{log_prefix} Aborting interval: log_type={config["log_type"]} - start time is greater than end time')
        return

    interval_start_seconds = time.time()
    total_event_count = 0

    interval_start_epoch = config['start']
    interval_end_epoch = config['end']
    api_timeout = config['api_timeout']
    api_batch_span = config['api_batch_span']
    helper.log_info(f'{log_prefix} Interval start: log_type={config["log_type"]} api_timeout={api_timeout} api_batch_span={api_batch_span} max_page_size={config["limit"]} start="{format_timestamp(interval_start_epoch)}" end="{format_timestamp(interval_end_epoch)}"')

    batch_number = 0
    start_epoch = interval_start_epoch
    while start_epoch < interval_end_epoch:
        end_epoch = min(start_epoch + api_batch_span, interval_end_epoch)
        batch_number += 1
        total_event_count += fetch_batch(helper, ew, config, batch_number, start_epoch, end_epoch)
        helper.save_check_point(config['input_stanza'], end_epoch)
        start_epoch = end_epoch

    interval_seconds = time.time() - interval_start_seconds
    helper.log_info(f'{log_prefix} Interval complete: log_type={config["log_type"]} interval_events_per_second={(total_event_count / interval_seconds):.1f} interval_seconds={interval_seconds:.3f} batches_processed={batch_number} total_events_indexed={total_event_count} next_checkpoint="{format_timestamp(interval_end_epoch)}"')


def fetch_batch(helper, ew, config, batch_number, batch_start_epoch, batch_end_epoch):
    batch_start_seconds = time.time()

    request_params = {
        'format': 'json',
        'limit': config['limit'],
        'start': batch_start_epoch,
        'end': batch_end_epoch
    }

    if config['api_query']:
        request_params['query'] = config['api_query']

    request_headers = {
        'Content-Type': 'application/json',
        'User-Agent': config['api_user_agent']
    }
    request_body = {
        'token': helper.get_arg('api_token'),
        'log_type': config['log_type']
    }

    url = f'https://{config["api_host"]}/api/rep/{config["api_version"]}/fetch/client_select'

    has_more = True
    page_count = 0
    batch_event_count = 0

    helper.log_debug(f'{log_prefix} Request: batch_number={batch_number} URL={url} headers={request_headers} params={request_params}')

    while has_more:
        start_api_call_epoch = time.time()
        try:
            response = helper.send_http_request(url, method='POST', parameters=request_params, headers=request_headers, payload=request_body, timeout=config['api_timeout'])
            response.raise_for_status()
        except Exception as ex:
            helper.log_error(f'{log_prefix} Error encountered calling api - aborting interval: batch_number={batch_number} page_number={page_count} URL={url} params={request_params} headers={request_headers} message="{ex}"')
            raise

        page_count += 1

        api_call_seconds = time.time() - start_api_call_epoch
        helper.log_debug(
            f'{log_prefix} Event fetch completed: log_type={config["log_type"]} batch_number={batch_number} page_number={page_count} page_fetch_seconds={api_call_seconds:.3f} response_headers: {response.headers}')

        if 'Content-Length' in response.headers and response.headers['Content-Length'] == '0':
            if page_count == 0:
                helper.log_warning(f'{log_prefix} Batch complete - API did not respond with any content: batch_number={batch_number} page_number={page_count}"')
                return
            helper.log_info(f'{log_prefix} Empty response returned for last page query: batch_number={batch_number} page_number={page_count}"')
            break

        response_json = response.json()[0]
        if 'result' not in response_json or 'events' not in response_json['result'] or len(
                response_json['result']['events']) == 0:
            if page_count == 0:
                helper.log_debug(
                    f'{log_prefix} Batch complete - no events found for time range: log_type={config["log_type"]} batch_number={batch_number} page_number={page_count}" start={format_timestamp(request_params["start"])} end={format_timestamp(request_params["end"])}')
                return
            helper.log_debug(f'{log_prefix} No events in last page: batch_number={batch_number} page_number={page_count}"')
            break

        result = response_json['result']

        page_event_count = len(result["events"])
        helper.log_debug(
            f'{log_prefix} Start processing page: batch_number={batch_number} page_number={page_count} page_event_count={page_event_count} page_timestamp={response_json["timestamp"]}')
        processing_start_epoch = time.time()
        data = ""
        for event in result['events']:
            event_json = event['event']
            if config['remove_na_fields']:
                for field in list(event_json.keys()):
                    if event_json[field] == 'NA':
                        # helper.log_debug(f'{log_prefix} Removing {field} field')
                        del event_json[field]
            event_str = json.dumps(event_json)

            data += event_str
            data += '\r\n'
            batch_event_count += 1

        try:
            e = helper.new_event(
                host=config['host'],
                index=helper.get_output_index(),
                source=config['source'],
                sourcetype=config['sourcetype'],
                data=data
            )
            ew.write_event(e)
        except Exception as ex:
            helper.log_error(f'{log_prefix} Error sending event to Splunk: batch_number={batch_number} page_number={page_count} message="{ex}" event="{event_json}"')
            raise

        processing_seconds = time.time() - processing_start_epoch
        helper.log_debug(
            f'{log_prefix} Completed processing page: batch_number={batch_number} page_number={page_count}  processed_events_per_second={(page_event_count / processing_seconds):.1f}  retrieved_and_processed_events_per_second={(page_event_count / (api_call_seconds + processing_seconds)):.1f} page_processing_seconds={processing_seconds:.3f} page_timestamp={response_json["timestamp"]} events_indexed={page_event_count}')

        if 'pagingIdentifiers' in result:
            if 'last_iteration' in result['pagingIdentifiers'] and result['pagingIdentifiers']['last_iteration']:
                has_more = False
            else:
                request_body['pagingIdentifiers'] = result['pagingIdentifiers']
        else:
            has_more = False

    batch_seconds = time.time() - batch_start_seconds
    helper.log_info(f'{log_prefix} Fetched Batch: batch_number={batch_number} start="{format_timestamp(batch_start_epoch)}" end="{format_timestamp(batch_end_epoch)}" batch_events_per_second={(batch_event_count / batch_seconds):.1f} batch_seconds={batch_seconds:.3f} pages_processed={page_count} batch_events_indexed={batch_event_count}')

    return batch_event_count


def get_config(helper):
    import requests
    answer = {
        'input_type'       : helper.get_input_type(),
        'input_stanza'     : helper.get_input_stanza_names(),
        'api_host'         : helper.get_global_setting('api_host'),
        'api_timeout'      : helper.get_global_setting('api_timeout'),
        'api_token'        : helper.get_arg('api_token'),
        'api_version'      : helper.get_arg('api_version'),
        'api_user_agent'   : f"{requests.utils.default_headers()['User-Agent']} (Splunk TA_menlosecurity_api_inputs)",
        'host'             : helper.get_arg('host'),
        'source'           : helper.get_arg('source'),
        'sourcetype'       : helper.get_sourcetype(),
        'log_type'         : helper.get_arg('log_type'),
        'remove_na_fields' : helper.get_arg('remove_na_fields'),
        'api_batch_span'   : helper.get_arg('api_batch_span'),
        'settling_time'    : helper.get_arg('settling_time'),
        'api_query'        : helper.get_arg('api_query'),
        'limit'            : helper.get_arg('max_page_size')
    }

    if not answer['api_batch_span']:
        answer['api_batch_span'] = 3600
    else:
        answer['api_batch_span'] = int(answer['api_batch_span'])
        min_api_batch_span = 60
        max_api_batch_span = 86400
        if answer['api_batch_span'] < min_api_batch_span:
            helper.log_warning(f'{log_prefix} api_batch_span is less than than minimum - resetting: orig_api_batch_span={answer["api_batch_span"]} new_api_batch_span={min_api_batch_span}')
            answer['api_batch_span'] = min_api_batch_span
        elif answer['api_batch_span'] > max_api_batch_span:
            helper.log_warning(f'{log_prefix} api_batch_span is greater than than maximum - resetting: orig_api_batch_span={answer["api_batch_span"]} new_api_batch_span={max_api_batch_span}')
            answer['api_batch_span'] = max_api_batch_span

    if not answer['settling_time']:
        answer['settling_time'] = 120
    else:
        answer['settling_time'] = int(answer['settling_time'])
        min_settling_time = 60
        max_settling_time = 600
        if answer['settling_time'] < min_settling_time:
            helper.log_warning(f'{log_prefix} settling_time is less than than minimum - resetting: orig_settling_time={answer["settling_time"]} new_settling_time={min_settling_time}')
            answer['settling_time'] = min_settling_time
        elif answer['settling_time'] > max_settling_time:
            helper.log_warning(f'{log_prefix} settling_time is greater than than maximum - resetting: orig_settling_time={answer["settling_time"]} new_settling_time={max_settling_time}')
            answer['settling_time'] = max_settling_time

    if not answer['api_host']:
        answer['api_host'] = 'logs.menlosecurity.com'

    if not answer['api_host']:
        answer['api_host'] = 'logs.menlosecurity.com'

    if not answer['api_timeout']:
        answer['api_timeout'] = 20
    else:
        answer['api_timeout'] = int(answer['api_timeout'])
        min_api_timeout = 5.0
        max_api_timeout = 20.0
        if answer['api_timeout'] < min_api_timeout:
            helper.log_warning(f'{log_prefix} api_timeout is less than than minimum - resetting: orig_api_timeout={answer["api_timeout"]} new_api_timeout={min_api_timeout}')
            answer['api_timeout'] = min_api_timeout
        elif answer['api_timeout'] > max_api_timeout:
            helper.log_warning(f'{log_prefix} api_timeout is greater than than maximum - resetting: orig_api_timeout={answer["api_timeout"]} new_api_timeout={max_api_timeout}')
            answer['api_timeout'] = max_api_timeout

    if not answer['api_version']:
        answer['api_version'] = 'v1'

    if hasattr(helper, 'service'):
        default_user_agent = requests.utils.default_headers()['User-Agent']
        app_id = helper.get_app_name()
        app_version = helper.service.apps[app_id].content['version']
        splunk_server_version = helper.service.confs['app']['launcher']['version']
        answer['api_user_agent'] = f"{default_user_agent} (Splunk/{splunk_server_version} {app_id}/{app_version})"

    helper.log_debug(f'{log_prefix} User-Agent="{answer["api_user_agent"]}"')

    if answer['host'] is None or answer['host'] == '$decideOnStartup':
        answer['host'] = answer['api_host']

    if answer['source'] is None:
        answer['source'] = f'{helper.get_input_type()}://{helper.get_input_stanza_names()}'

    if answer['sourcetype'] == 'menlo:log' or answer['sourcetype'] is None:
        answer['sourcetype'] = f'menlo:log:{answer["log_type"]}'

    if not answer['limit'] :
        answer['limit'] = 10000
    else:
        answer['limit'] = int(answer['limit'])
        min_limit = 1
        max_limit = 10000
        if answer['limit'] < min_limit:
            helper.log_warning(f'{log_prefix} max_page_size is less than than minimum - resetting: orig_max_page_size={answer["limit"]} new_max_page_size={min_limit}')
            answer['limit'] = min_limit
        elif answer['limit'] > max_limit:
            helper.log_warning(f'{log_prefix} max_page_size  is greater than than maximum - resetting: orig_max_page_size={answer["limit"]} new_max_page_size={max_limit}')
            answer['limit'] = max_limit

    tmp_checkpoint = helper.get_check_point(helper.get_input_stanza_names())
    if tmp_checkpoint is not None:
        answer['start'] = int(tmp_checkpoint)
        min_checkpoint_value = int(time.time() - (30 * 86400))
        if answer['start'] < min_checkpoint_value:
            helper.log_warning(f'{log_prefix} Checkpoint Found is older than 30-days - resetting: orig_checkpiont={format_timestamp(answer["start"])} new_checkpoint={format_timestamp(min_checkpoint_value)}')
            answer['start'] = min_checkpoint_value
        else:
            helper.log_info(f'{log_prefix} Found Checkpoint: start="{format_timestamp(answer["start"])}"')
    else:
        backfill_start_days = helper.get_arg('backfill_start_days')
        if not backfill_start_days:
            # Default is for last 5 minutes
            answer['start'] = int(time.time() - 300)
            helper.log_info(
                f'{log_prefix} No Checkpoint found and backfill not set - defaulting to last 5 minutes: start="{format_timestamp(answer["start"])}"')
        else:
            backfill_start_days = float(backfill_start_days)
            min_backfill_start_days = 0.001
            max_backfill_start_days = 30
            if backfill_start_days < min_backfill_start_days:
                helper.log_warning(
                    f'{log_prefix} backfill_start_days is less than than minimum - resetting: orig_backfill_start_days={backfill_start_days} new_backfill_start_days={min_backfill_start_days}')
                backfill_start_days = min_backfill_start_days
            elif backfill_start_days > max_backfill_start_days:
                helper.log_warning(
                    f'{log_prefix} backfill_start_days is greater than than maximum - resetting: orig_backfill_start_days={backfill_start_days} new_backfill_start_days={max_backfill_start_days}')
                backfill_start_days = max_backfill_start_days
            answer['start'] = int(time.time() - (backfill_start_days * 86400))
            helper.log_info(f'{log_prefix} No Checkpoint found - backfilling: backfill_days="{backfill_start_days}" start="{format_timestamp(answer["start"])}')

    # To avoid missing data, use the configured settling time
    answer['end'] = int(time.time() - answer['settling_time'])

    return answer


def format_timestamp(timestamp):
    return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)


def parse_bool(bool_str, default_value):
    if bool_str is not None:
        if bool_str in ['True', 'true', '1']:
            return True
        else:
            return False
    else:
        return default_value
