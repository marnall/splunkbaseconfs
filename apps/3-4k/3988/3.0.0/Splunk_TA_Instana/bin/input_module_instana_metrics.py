import time
import json


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # if type(helper.get_arg('interval')) == dict:
    #    interval = helper.get_arg('interval')[stanza_name]
    # else:
    #    interval = helper.get_arg('interval')

    # helper.log_info(interval)
    # if int(interval) < 300:
    #    raise Exception('Time interval must be more than 300')
    # else:
    #    pass


def collect_events(helper, ew):
    stanzas = helper.input_stanzas

    for stanza_name in stanzas:
        settings = Settings(helper, stanza_name)

        if int(settings.opt_interval) >= 300:
            while settings.nextPageExists:
                response = send_api_request(settings, helper)
                process_api_response(response, helper, ew, settings)
                change_settings_for_pagination(settings, response)
        else:
            helper.log_info('Interval set to ' + str(
                settings.opt_interval) + ' which is less than 300 seconds! Please reconfigure the input.')


def change_settings_for_pagination(settings, response):
    settings.page = response.json()['page']
    settings.pageSize = response.json()['pageSize']
    settings.totalHits = response.json()['totalHits']
    settings.nextPageExists = settings.page * settings.pageSize < settings.totalHits


def send_api_request(settings, helper):
    headers = {'authorization': 'apiToken ' + settings.api_token, 'Content-Type': 'application/json'}
    url_metrics = settings.base_url + '/api/application-monitoring/metrics/' + settings.input_entity_type + 's'
    body = build_request_body(settings)
    return helper.send_http_request(url_metrics, 'POST', headers=headers,
                                    parameters=None, payload=body, cookies=None,
                                    verify=None, cert=None, timeout=None, use_proxy=True)


def build_request_body(settings):
    window_size = int(settings.opt_interval) * 1000
    time_frame = {'windowSize': window_size, 'to': settings.time_now}
    name_filter = ''
    pagination = {'page': settings.page + 1, 'pageSize': 20}

    if settings.input_select_all == 'False':
        name_filter = settings.input_entity_name

    return {'pagination': pagination, 'metrics': get_desired_metrics(settings.opt_interval), 'nameFilter': name_filter,
            'timeFrame': time_frame}


def get_desired_metrics(granularity):
    return [{'metric': 'latency', 'aggregation': 'MEAN'},
            {'metric': 'calls', 'aggregation': 'SUM'},
            {'metric': 'errors', 'aggregation': 'MEAN'}]


def process_api_response(response, helper, ew, settings):
    if response.status_code == 200:
        entity_list = get_entities_from_api_response(response, helper)

        if settings.input_select_all == 'False':
            entity = find_entity_with_input_name(entity_list, settings.input_entity_name, settings.input_entity_type)

            if entity is not None:
                process_single_entity(entity, helper, ew, settings)
            else:
                helper.log_error('Did not find any entity that matches given input name ' + settings.input_entity_name)
        else:
            process_all_entities(entity_list, helper, ew, settings)
    else:
        helper.log_error(
            'Could not retrieve metrics from API. Server Returned: ' + str(response.status_code) + str(
                response.content))


def get_entities_from_api_response(response, helper):
    try:
        return response.json()['items']
    except Exception as e:
        helper.log_error('Could not find any application/service.', e)
        raise e


def process_all_entities(entity_list, helper, ew, settings):
    for entity in entity_list:
        process_single_entity(entity, helper, ew, settings)


def process_single_entity(entity, helper, ew, settings):
    data = refactor_metrics(entity['metrics'], settings.opt_interval)
    if contains_metrics(data):
        data = divide_sum_of_calls_with_interval_value(data)
        event = create_splunk_event(entity[settings.input_entity_type], settings, data, helper)
        write_result_to_splunk(helper, ew, event)


def contains_metrics(data):
    return data['calls_per_second'] > 0


def find_entity_with_input_name(entity_list, input_entity_name, input_entity_type):
    for entity in entity_list:
        # find entity that has the exact name as specified
        if entity[input_entity_type]['label'] == input_entity_name:
            return entity
    return None


def refactor_metrics(metrics, granularity):
    new_metrics = {}

    calls_per_second = metrics.pop('calls.sum')
    calls_per_second = extract_metric_value(calls_per_second)
    avg_response_time = metrics.pop('latency.mean')
    avg_response_time = extract_metric_value(avg_response_time)
    error_rate = metrics.pop('errors.mean')
    error_rate = extract_metric_value(error_rate)

    new_metrics['calls_per_second'] = calls_per_second
    new_metrics['avg_response_time_ms'] = avg_response_time
    new_metrics['avg_error_rate'] = error_rate
    return new_metrics


def extract_metric_value(metric_list):
    return metric_list[0][1]


def divide_sum_of_calls_with_interval_value(data):
    data['calls_per_second'] = data['calls_per_second'] / 300
    return data


def get_timestamp_from_event_data(data):
    return data['avg_error_rate'][0]['timestamp']


def create_splunk_event(entity, settings, data, helper):
    src = 'instana:' + str(settings.stanza_name)
    splunk_event = {'type': entity['entityType'],
                    'name': entity['label'],
                    'timestamp': settings.time_now,
                    'time_interval_ms': settings.opt_interval, 'data': data}

    return helper.new_event(source=src, index=settings.idx, sourcetype=settings.st,
                            data=json.dumps(splunk_event, sort_keys=False))


def write_result_to_splunk(helper, ew, event):
    try:
        ew.write_event(event)
    except Exception as e:
        helper.log_error(e)
        raise e


class Settings:
    time_now = None
    base_url = None
    api_token = None
    opt_interval = None
    input_entity_name = None
    input_entity_type = None
    idx = None
    st = None
    stanza_name = None
    nextPageExists = True
    page = 0
    pageSize = 20
    totalHits = None

    def __init__(self, helper, stanza_name):
        self.time_now = int(time.time() * 1000)
        self.stanza_name = stanza_name
        self.nextPageExists = True
        self.api_token = str(helper.get_global_setting("instana_api_token"))
        self.base_url = str(helper.get_global_setting("instana_base_url"))
        if self.multiple_inputs_configured(helper.get_arg('interval')):
            self.opt_interval = helper.get_arg('interval')[stanza_name]
            self.input_entity_type = str(helper.get_arg('entity_type')[stanza_name])
            self.input_entity_name = str(helper.get_arg('entity_name')[stanza_name])
            self.input_select_all = str(helper.get_arg('select_all')[stanza_name])
            self.idx = helper.get_output_index()[stanza_name]
            self.st = helper.get_sourcetype()[stanza_name]
        else:
            self.opt_interval = helper.get_arg('interval')
            self.input_entity_type = str(helper.get_arg('entity_type'))
            self.input_entity_name = str(helper.get_arg('entity_name'))
            self.input_select_all = str(helper.get_arg('select_all'))
            self.idx = helper.get_output_index()
            self.st = helper.get_sourcetype()

    @staticmethod
    def multiple_inputs_configured(opt_interval):
        return isinstance(opt_interval, dict)
