from __future__ import division

# encoding = utf-8

from builtins import str
from past.utils import old_div
import datetime
import json
import math
import os
import ssl
import sys
import time


import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from requests import Request


class MyAdapter(HTTPAdapter):
    """"Transport adapter" that allows us to use TLSv1."""

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize,
            block=block, ssl_version=ssl.PROTOCOL_TLSv1_2)


# Defaults
DEFAULT_TIME_RANGE = '15m'
DEFAULT_DATA_TYPE = 'appsensor'

# Valid ranges (going outside these will output unrelated-looking errors)
TIME_RANGES = ['1m', '10m', '15m', '30m', '1h', '3h', '6h', '12h', '24h', '48h',
               '72h', '3d', '5d', '1w', '2w', '1mo', '3mo']

EVENTVIEWER_SOURCES = {'appfirewall': ['time', 'app_id', 'id', 'detectionPoint', 'strippedUri', 'fullUri', 'location',
                                       'city', 'country', 'route', 'routeId', 'method', 'path', 'parameter', 'payload',
                                       'userId', 'sessionId', 'transactionId', 'remoteHost', 'patternId'],
                       'login': ['time', 'linkIcon', 'app_id', 'company', 'headerKeys', 'tags', 'eventName', 'ip',
                                 'attackIds', 'referrer', 'attribs', 'userAgent', 'id', 'userValid', 'userId',
                                 'documentUri', 'confidence', 'session', 'browser', 'location', 'city', 'country',
                                 'reputation'],
                       'csp': ['time', 'id', 'linkIcon', 'app_id', 'company', 'blockedDomain', 'directive',
                               'documentUri', 'referrer', 'ip', 'reputationGroup', 'tags', 'features', 'browser',
                               'location', 'violationAttribute', 'city', 'country', 'reputation', 'routeId',
                               'sessionId', 'transactionId', 'confidence'],
                       'inline': ['time', 'id', 'linkIcon', 'app_id', 'company', 'directive', 'documentUri', 'referrer',
                                  'similarScripts', 'ip', 'tags', 'browser', 'location', 'city', 'country',
                                  'reputation', 'scriptId', 'relatedScriptId', 'staticHash', 'scriptPos'],
                       'cmdi': ['agent', 'app_id', 'blocked', 'city', 'client_ip', 'commands', 'country', 'fingerprint',
                                'full_commandline', 'hostname', 'id', 'ip', 'location', 'method', 'path', 'route',
                                'route_id', 'session_id', 'stripped_uri', 'time', 'user_id'],
                       'lfi': ['agent', 'app_id', 'blocked', 'city', 'client_ip', 'country', 'dir_type', 'file_exists',
                               'file_path', 'file_type', 'hostname', 'id', 'ip', 'location', 'method', 'mode', 'path',
                               'route', 'route_id', 'rule_id', 'session_id', 'stripped_uri', 'time', 'user_id']}
# Treat appsensor/appfirewall as interchangeable keys
EVENTVIEWER_SOURCES['appsensor'] = EVENTVIEWER_SOURCES['appfirewall']
RUN_MODES = ['oneshot', 'continuous']
SPLUNK_DB = os.environ.get('SPLUNK_DB')
if SPLUNK_DB:
    # Should always be present.
    BASE_COUNTER_PATH = os.path.join(
        SPLUNK_DB, 'modinputs', 'tcell_events', 'checkpoint')
else:
    BASE_COUNTER_PATH = '/tmp/tcell_splunk_counter'
DEFAULT_SLEEP = 10
BASE_DOMAIN = 'us.api.insight.rapid7.com'

tcell_api_key = ""

# Debug log settings
DEBUG_MODE = True


# Log a debug or error message
def error(msg):
    sys.stderr.write(msg + '\n')


def debug(msg):
    if DEBUG_MODE:
        sys.stderr.write(msg + '\n')


def make_request(full_url, params):
    headers = {'X-API-Key': tcell_api_key,
               'content-type': "application/json"}
    p = Request('GET', full_url, params=params).prepare()
    debug('About to make this request: {} ; params   {} ; headers   {}'.format(
        p.url, str(params), str(headers)))
    with requests.Session() as s:
        s.mount('https://', MyAdapter())
        return requests.get(full_url, params=params, headers=headers)


def get_event_time_ms(event):
    """"Return the event time in milliseconds from Unix epoch, if present"""
    # Apparently the API changed at some point
    avail_time_text = event.get('time') or event.get('timestamp')
    if avail_time_text:
        return int(avail_time_text)
    return None


def get_event_time_s(event):
    """"Return the event time in classic seconds from Unix epoch, if present"""
    event_time_ms = get_event_time_ms(event)
    if not event_time_ms:
        return None
    return old_div(event_time_ms, 1000)


def add_timestamp_to_event(event):
    event_time_s = get_event_time_s(event)
    if not event_time_s:
        # Time not found
        return event

    event_timestamp = datetime.datetime.utcfromtimestamp(
        event_time_s).isoformat()
    event['event_timestamp'] = event_timestamp
    return event


def get_latest_event_time(events):
    """Get the most recent event time in milliseconds for the whole set"""
    latest_time = None
    for event in events:
        event_time_ms = get_event_time_ms(event)
        if latest_time is None or event_time_ms > latest_time:
            latest_time = event_time_ms
    return latest_time


def make_counter_path(base_counter_path, app_id, source):
    counter_path = base_counter_path + '_' + app_id + '_' + source + '.txt'
    debug('counter_path created: ' + counter_path)
    return counter_path


def save_time(counter_path, timestamp):
    if timestamp is not None:
        with open(counter_path, 'w') as f:
            try:
                int(timestamp)
                f.write(str(timestamp))
                debug('Wrote {} to {}'.format(str(timestamp), counter_path))
            except ValueError:
                raise ValueError('timestamp is not an int')


def get_saved_time(counter_path):
    timestamp = None
    if os.path.isfile(counter_path):
        with open(counter_path, 'r') as f:
            try:
                timestamp = int(f.read())
            except ValueError:
                raise ValueError('timestamp is not an int')
    return timestamp


def print_usage():
    sys.stderr.write(
        'Usage: tcell_splunk.py <continuous|oneshot> <data_type> <company> <app_id> <api_key>')


def validate_time_range():
    # Validate time range, in case the range was manually changed
    if DEFAULT_TIME_RANGE not in TIME_RANGES:
        error('Invalid time range: ' + DEFAULT_TIME_RANGE)
        error('Time range options: ' + str(TIME_RANGES))
        error('Fix by modifying DEFAULT_TIME_RANGE in tcell_splunk.py')
        sys.exit(1)


def validate_data_type(data_type):
    if data_type not in handle_data_type:
        error('Invalid data type: ' + data_type)
        error('Data type options: ' + str(list(handle_data_type.keys())))
        print_usage()
        sys.exit(1)


def create_full_url_from_endpoint(endpoint):
    base_url = 'https://' + BASE_DOMAIN + '/'
    return base_url + 'tcell/api/v1' + endpoint


def get_packages(run_mode, data_type, company, app_id, api_key, helper, ew):
    helper.log_debug("Entered get_packages, for %s for app %s" %
                     (data_type, app_id))

    if run_mode == 'continuous':
        error('continuous mode not supported for packages')
        sys.exit(1)
    elif run_mode == 'oneshot':
        # Set counter path
        counter_path = make_counter_path(BASE_COUNTER_PATH, app_id, data_type)

        timestamp = None
        # Set timestamp
        try:
            timestamp = get_saved_time(counter_path)
        except ValueError:
            # If counter_path's contents cannot be parsed as an integer, don't set timestamp
            error('Error in getting counter value. timestamp: ' + str(timestamp))
            pass

        full_url = create_full_url_from_endpoint(
            '/apps/{}/packages').format(app_id)

        params = {}
        now = int(math.floor(time.time() * 1e3))
        if timestamp is not None:
            params['from'] = timestamp + 1
            params['to'] = now

        debug('params: ' + str(params))
        response = make_request(full_url, params)

        if response.ok:
            packages = json.loads(response.content.decode('utf8'))['packages']

            for package in packages:
                timestamped_event = add_timestamp_to_event(package)
                event_time = get_event_time_s(package)
                event_text = json.dumps(timestamped_event)
                splunk_ev = helper.new_event(event_text, time=event_time, host=None, index=None,
                                             source='tcell_pkg', sourcetype='tcell_events')

                ew.write_event(splunk_ev)

            save_time(counter_path, get_latest_event_time(packages))
        else:
            error('error: ok=' + str(response.ok) +
                  ', status code=' + str(response.status_code))
            sys.exit(1)


def get_package_vulnerability_events(run_mode, data_type, company, app_id, api_key, helper, ew):
    if run_mode == 'continuous':
        error('continuous mode not supported for vulnerabilities')
        sys.exit(1)
    elif run_mode == 'oneshot':
        # Set counter path
        counter_path = make_counter_path(BASE_COUNTER_PATH, app_id, data_type)

        timestamp = None
        # Set timestamp
        try:
            timestamp = get_saved_time(counter_path)
        except ValueError:
            # If counter_path's contents cannot be parsed as an integer, don't set timestamp
            error('Error in getting counter value. timestamp: ' + str(timestamp))
            pass

        full_url = create_full_url_from_endpoint(
            '/apps/{}/packages/vulnerability_events').format(app_id)

        params = {}
        now = int(math.floor(time.time() * 1e3))
        if timestamp is not None:
            params['from'] = timestamp + 1
            params['to'] = now

        debug('params: ' + str(params))
        response = make_request(full_url, params)

        if response.ok:
            package_events = json.loads(response.content.decode('utf8'))[
                'vulnerability_events']

            for package_event in package_events:
                timestamped_event = add_timestamp_to_event(package_event)
                event_time = get_event_time_s(package_event)
                event_text = json.dumps(timestamped_event)
                splunk_ev = helper.new_event(event_text, time=event_time, host=None, index=None,
                                             source='tcell_vuln', sourcetype='tcell_events')
                ew.write_event(splunk_ev)

            save_time(counter_path, get_latest_event_time(package_events))
        else:
            error('error: ok=' + str(response.ok) +
                  ', status code=' + str(response.status_code))
            sys.exit(1)


# Make an API request for all events since the timestamp, or all events in
# the last DEFAULT_TIME_RANGE if no timestamp
def create_eventviewer_request(timestamp, now, source, app_id, company, api_key):
    if source == 'appsensor':
        source = 'appfirewall'

    full_url = create_full_url_from_endpoint(
        '/apps/{}/sources/{}/table').format(app_id, source)
    params = {'orderBy': 'asc:time',
              'tableColumns': EVENTVIEWER_SOURCES[source]}

    # Fill in timerange with default value if unspecified
    if timestamp is None:
        params['timerange'] = DEFAULT_TIME_RANGE
    else:
        # make query non-inclusive on range by adding +1
        params['from'] = timestamp + 1
        params['to'] = now

    return full_url, params


def emit_eventviewer_events(response, data_type, helper, ew):
    timestamp = None

    source_name = "tcell_%s" % (data_type, )

    # splunk_ev = helper.new_event("hi mom, MONKEYS FOREVER", time=None, host=None, index=None,
    #                             source=source_name, sourcetype='tcell_events')
    # ew.write_event(splunk_ev)
    if response.ok:
        # Parse results
        results = json.loads(response.content.decode('utf-8'))
        debug(response.content.decode('utf-8') + '\n\n\n\n\n\n')
        events = results['table']

        # Emit each event
        for event in events:
            timestamped_event = add_timestamp_to_event(event)
            event_text = json.dumps(timestamped_event)
            event_time = get_event_time_s(event)
            splunk_ev = helper.new_event(event_text, time=event_time, host=None, index=None,
                                         source=source_name, sourcetype='tcell_events')
            ew.write_event(splunk_ev)

        # Set timestamp to latest timestamp in response
        latest_time = get_latest_event_time(events)
        if latest_time not in (0, None):
            timestamp = int(latest_time)
        debug('***** results timestamp is ' + str(timestamp))
    else:
        error('error: ok=' + str(response.ok) +
              ', status code=' + str(response.status_code))
        sys.exit(1)

    return timestamp


def eventviewer_loop(run_mode, data_type, company, app_id, api_key, helper, ew):
    helper.log_debug("Entered eventviewer_loop, for %s for app %s" %
                     (data_type, app_id))
    # Set counter path
    counter_path = make_counter_path(BASE_COUNTER_PATH, app_id, data_type)
    # splunk_ev = helper.new_event("eventviewer_loop: %s, MONKEYS FOREVER" % data_type, time=None, host=None,
    #                             index=None, source="tcell_debug", sourcetype='tcell_events')
    # ew.write_event(splunk_ev)

    # Set timestamp
    try:
        timestamp = get_saved_time(counter_path)
    except ValueError:
        # If counter_path's contents cannot be parsed as an integer, don't set timestamp
        error('Error in getting counter value. timestamp: ' + str(timestamp))
        pass
    if run_mode == 'continuous':
        while True:
            now = int(math.floor(time.time() * 1e3))
            full_url, params = create_eventviewer_request(
                timestamp, now, data_type, app_id, company, api_key)
            response = make_request(full_url, params)
            timestamp = emit_eventviewer_events(
                response, data_type, helper, ew)
            save_time(counter_path, timestamp)
            time.sleep(DEFAULT_SLEEP)
    elif run_mode == 'oneshot':
        now = int(math.floor(time.time() * 1e3))
        full_url, params = create_eventviewer_request(
            timestamp, now, data_type, app_id, company, api_key)
        response = make_request(full_url, params)
        emit_eventviewer_events(response, data_type, helper, ew)


def get_all_app_ids(tcell_company_name, tcell_api_key, helper):
    helper.log_debug("Entered get_all_app_ids, for %s" % tcell_company_name)

    full_url = create_full_url_from_endpoint('/apps')
    params = {}
    response = make_request(full_url, params)

    if response.ok:
        all_apps = json.loads(response.content.decode('utf8'))['apps']
        all_app_ids = [app["id"] for app in all_apps]
        return all_app_ids
    else:
        error('error: ok=' + str(response.ok) +
              ', status code=' + str(response.status_code))
        sys.exit(1)


# Returns a function that is called with (run_mode, data_type, company, app_id, api_key).
# Functions include continuous and oneshot functionality.
handle_data_type = {'appfirewall': eventviewer_loop,
                    'appsensor': eventviewer_loop,
                    'login': eventviewer_loop,
                    'csp': eventviewer_loop,
                    'inline': eventviewer_loop,
                    'vulnerabilities': get_package_vulnerability_events,
                    'cmdi': eventviewer_loop,
                    'lfi': eventviewer_loop,
                    'packages': get_packages}


# tcell_splunk.py will take in 5 parameters
#    run_mode - oneshot or continuous
#    data_type - login, csp, etc.
#    company - the name of the subdomain the company is using
#    app_id - the app_id in tCell
#    api_key - the user's api key
#    NOTE: originally had environment variable ways of passing things in, but not clear Splunk can manage those
#          so, just doing anything with parameters.
def old_main():
    if len(sys.argv) < 6:
        print_usage()

    # Set values
    run_mode = sys.argv[1]
    data_type = sys.argv[2]
    company = sys.argv[3]
    app_id = sys.argv[4]
    api_key = sys.argv[5]

    # Validate values
    validate_time_range()
    validate_data_type(data_type)

    # Handle input
    handle_data_type[data_type](run_mode, data_type, company, app_id, api_key)


'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # tcell_company_name = definition.parameters.get('tcell_company_name', None)
    # tcell_api_key = definition.parameters.get('tcell_api_key', None)
    # tcell_app = definition.parameters.get('tcell_app', None)
    # data_types = definition.parameters.get('data_types', None)
    pass


def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_tcell_company_name = helper.get_arg('tcell_company_name')
    opt_tcell_api_key = helper.get_arg('tcell_api_key')
    opt_tcell_app = helper.get_arg('tcell_app')
    opt_data_types = helper.get_arg('data_types')

    # In single instance mode, to get arguments of a particular input, use
    # opt_tcell_company_name = helper.get_arg('tcell_company_name', stanza_name)
    # opt_tcell_api_key = helper.get_arg('tcell_api_key', stanza_name)
    # opt_tcell_app = helper.get_arg('tcell_app', stanza_name)
    # opt_data_types = helper.get_arg('data_types', stanza_name)

    # get input type
    helper.get_input_type()

    # The following examples get input stanzas.
    # get all detailed input stanzas
    helper.get_input_stanza()
    # get specific input stanza with stanza name
    helper.get_input_stanza(stanza_name)
    # get all stanza names
    helper.get_input_stanza_names()

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    loglevel = helper.get_log_level()
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()
    # get account credentials as dictionary
    account = helper.get_user_credential_by_username("username")
    account = helper.get_user_credential_by_id("account id")
    # get global variable configuration
    global_userdefined_global_var = helper.get_global_setting(
        "userdefined_global_var")

    # The following examples show usage of logging related helper functions.
    # write to the log for this modular input using configured global log level or INFO as default
    helper.log("log message")
    # write to the log using specified log level
    helper.log_debug("log message")
    helper.log_info("log message")
    helper.log_warning("log message")
    helper.log_error("log message")
    helper.log_critical("log message")
    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    helper.set_log_level(log_level)

    # The following examples send rest requests to some endpoint.
    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
    # get the response headers
    r_headers = response.headers
    # get the response body as text
    r_text = response.text
    # get response body as json. If the body text is not a json string, raise a ValueError
    r_json = response.json()
    # get response cookies
    r_cookies = response.cookies
    # get redirect history
    historical_responses = response.history
    # get response status code
    r_status = response.status_code
    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()

    # The following examples show usage of check pointing related helper functions.
    # save checkpoint
    helper.save_check_point(key, state)
    # delete checkpoint
    helper.delete_check_point(key)
    # get checkpoint
    state = helper.get_check_point(key)

    # To create a splunk event
    helper.new_event(data, time=None, host=None, index=None,
                     source=None, sourcetype=None, done=True, unbroken=True)
    """

    '''
    # The following example writes a random number as an event. (Multi Instance Mode)
    # Use this code template by default.
    import random
    data = str(random.randint(0,100))
    event = helper.new_event(source=helper.get_input_type(
    ), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)
    '''

    '''
    # The following example writes a random number as an event for each input config. (Single Instance Mode)
    # For advanced users, if you want to create single instance mod input, please use this code template.
    # Also, you need to uncomment use_single_instance_mode() above.
    import random
    input_type = helper.get_input_type()
    for stanza_name in helper.get_input_stanza_names():
        data = str(random.randint(0,100))
        event = helper.new_event(source=input_type, index=helper.get_output_index(
            stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=data)
        ew.write_event(event)
    '''
    helper.set_log_level('debug')

    stanza_names = helper.get_input_stanza_names()
    helper.log_debug("stanza_names=%s" % stanza_names)
    if isinstance(stanza_names, str):
        single_instance = True
        stanza_names = [stanza_names]
    else:
        single_instance = False
        # TODO: implement multi-instance mode

    stanza = stanza_names[0]
    stuff = helper.get_input_stanza()
    helper.log_debug("input_stanza=%s" % stuff)

    tcell_company_name = helper.get_arg('tcell_company_name')
    if not tcell_company_name:
        helper.log_error("tcell_company_name missing from stanza=%s" % stanza)
        return

    global tcell_api_key
    tcell_api_key = helper.get_arg('tcell_api_key')
    if not tcell_api_key:
        helper.log_error("tcell_api_key missing from stanza=%s" % stanza)
        return

    tcell_app_id = helper.get_arg('tcell_app_id')
    tcell_apps = helper.get_arg('tcell_apps')
    if not (tcell_apps or tcell_app_id):
        helper.log_error(
            "tcell_apps or tcell_app_id required in stanza=%s" % stanza)
        return

    tcell_app_ids = get_all_app_ids(
        tcell_company_name, tcell_api_key, helper) if tcell_apps else [tcell_app_id]

    collect_login = helper.get_arg('login')
    collect_csp = helper.get_arg('csp')
    collect_inline = helper.get_arg('inline')
    collect_appsensor = helper.get_arg('appsensor')
    collect_vulnerabilties = helper.get_arg('vulnerabilities')
    collect_cmdi = helper.get_arg('cmdi')
    collect_lfi = helper.get_arg('lfi')
    collect_packages = helper.get_arg('packages')
    if not (collect_login or collect_csp or collect_inline or collect_appsensor or collect_vulnerabilities or collect_cmdi or collect_lfi or collect_packages):
        helper.log_error("No data collection enabled for stanza=%s" % stanza)
        return

    helper.log_debug("tcell_company_name=%s" % repr(tcell_company_name))
    debug("tcell_company_name=%s" % repr(tcell_company_name))
    debug("tcell_api_key=%s" % repr(tcell_company_name))
    debug("tcell_app_ids=%s" % repr(tcell_app_ids))
    helper.log_debug("collect_login=%s" % repr(collect_login))
    helper.log_debug("tcell_api_key=%s" % repr(tcell_api_key))

    for app_id in tcell_app_ids:
        if collect_login:
            eventviewer_loop('oneshot', 'login', tcell_company_name,
                             app_id, tcell_api_key, helper, ew)
        if collect_csp:
            eventviewer_loop('oneshot', 'csp', tcell_company_name,
                             app_id, tcell_api_key, helper, ew)
        if collect_inline:
            eventviewer_loop('oneshot', 'inline', tcell_company_name,
                             app_id, tcell_api_key, helper, ew)
        if collect_appsensor:
            eventviewer_loop('oneshot', 'appsensor', tcell_company_name,
                             app_id, tcell_api_key, helper, ew)
        if collect_vulnerabilties:
            get_package_vulnerability_events(
                'oneshot', 'vulnerabiltiies', tcell_company_name, app_id, tcell_api_key, helper, ew)
        if collect_cmdi:
            eventviewer_loop('oneshot', 'cmdi', tcell_company_name,
                             app_id, tcell_api_key, helper, ew)
        if collect_lfi:
            eventviewer_loop('oneshot', 'lfi', tcell_company_name,
                             app_id, tcell_api_key, helper, ew)
        if collect_packages:
            get_packages('oneshot', 'packages', tcell_company_name,
                         app_id, tcell_api_key, helper, ew)
