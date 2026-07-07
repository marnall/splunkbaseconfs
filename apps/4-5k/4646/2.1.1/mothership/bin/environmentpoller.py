from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from datetime import datetime
import logging
import os
import socket
import sys
import json
import uuid
import re
import time
import splunklib.client as client
import splunklib.binding as binding
import splunk.rest as rest
from six.moves.urllib.parse import urlparse
import log_helper
from environments_schema import is_url_valid
from splunk.clilib.bundle_paths import make_splunkhome_path
from io import open
import requests

# Global variables
pid = os.getpid()
tstart = datetime.now()
guid = str(uuid.uuid4().hex)

# Setup the handler
debug_logger = log_helper.setup(logging.INFO, 'EnvironmentPollerDebug', 'environment_poller_debug.log')
metrics_logger = log_helper.setup(logging.INFO, 'EnvironmentPollerMetrics', 'environment_poller_metrics.log')

def metric_log_message(environment_searches_link_alternate='', environment_link_alternate='', results_count='', sid='', job_run_duration='', script_run_duration='', report_search='', type='', message='', is_search_head_cluster_mode=False, is_search_head_cluster_captain=False, pid='', guid=''):
    """
    Returns a metric log in a consistent format.
    """
    is_search_head_cluster_mode = '1' if is_search_head_cluster_mode is True else '0'
    is_search_head_cluster_captain = '1' if is_search_head_cluster_captain is True else '0'
    return 'environment_searches_link_alternate="%s" environment_link_alternate="%s" results_count="%s" sid="%s" job_run_duration="%s" script_run_duration="%s" report_search="%s" type="%s" message="%s" is_search_head_cluster_mode="%s" is_search_head_cluster_captain="%s" pid="%s" guid="%s"' % (environment_searches_link_alternate, environment_link_alternate, results_count, sid, job_run_duration, script_run_duration, report_search, type, message, is_search_head_cluster_mode, is_search_head_cluster_captain, pid, guid)


def simple_request_messages_to_str(messages):
    """
    Returns a readable string from a simple request response message

    Arguments
    messages -- The simple request response message to parse
    """
    entries = []
    for message in messages:
        entries.append(message.get('text'))
    return ','.join(entries)


def simple_request_eai(url, action, method, session_key, params=None):
    """
    Returns the payload response from a simpleRequest call

    Arguments
    url -- The REST handler endpoint to use in the simpleRequest
    action -- The readable requested action used in logs
    method -- The REST method to make the request with
    session_key -- The valid session key which will be used in the request
    params -- The parameters sent in the POST body of the simpleRequest
    """
    if not params:
        params = {}
    debug_logger.info('action=http_internal_request state=start method=%s url=%s pid=%s guid=%s' % (method, url, pid, guid))
    try:
        response, content = rest.simpleRequest(
            url,
            getargs=dict(output_mode='json'),
            postargs=params,
            method=method,
            sessionKey=session_key
        )
    except Exception as e:
        debug_logger.error('action=http_internal_request state=error error="%s" pid=%s guid=%s' % (e, pid, guid))
        raise Exception('Unable to %s %s entry. %s' % (action, url, e))
    debug_logger.info('action=http_internal_request state=end pid=%s guid=%s' % (pid, guid))

    try:
        payload = json.loads(content)
    except Exception as e:
        debug_logger.error('action=http_internal_request state=error error="%s"' % e)
        raise Exception('Unable to parse %s response payload.' % url)

    if response.status not in [200, 201]:
        message = simple_request_messages_to_str(response.messages)
        debug_logger.error('action=http_internal_request state=error error="%s"' % message)
        raise Exception(
            'Unable to %s %s entry. %s' % (action, url, message))
    return payload


def get_credential(password_link_alternate, session_key):
    """
    Returns the password for the environment and username pair

    Arguments
    password_link_alternate -- The link alternate of the environment password.conf entry
    session_key -- The valid session key which will be used in the request
    """

    # Load password to check hash and length
    passwords_conf_payload = simple_request_eai(password_link_alternate, 'list', 'GET', session_key)
    return passwords_conf_payload['entry'][0]['content']['clear_password']


def set_default_internal_fields(environment_search_entry):
    """
    Generates and returns default internal field names based off of environment search metadata.
    Uses the search name guid.
    """

    environment_search_guid = environment_search_entry['name']

    defaults = {
        'default_host': 'host_%s' % environment_search_guid,
        'default_source': 'source_%s' % environment_search_guid,
        'default_sourcetype': 'sourcetype_%s' % environment_search_guid
    }

    return defaults


def elapsed_time(start_time):
    """
    Returns the time elapsed from the provided timestamp to the current time (microseconds)

    Arguments
    start_time -- a valid datetime
    """
    end_time = datetime.now()
    return int((end_time - start_time).total_seconds() * 1000)


def parse_environment(mgmt_scheme_host_port):
    """
    Returns the host and port from a mgmt_scheme_host_port string

    Arguments
    mgmt_scheme_host_port -- The mgmt_scheme_host_port to parse
    """
    parsed_url = urlparse(mgmt_scheme_host_port)
    environment_host = parsed_url.netloc.split(':')[0]
    environment_port = parsed_url.port

    return environment_host, environment_port


def parse_search_string(search_string):
    """
    Returns a string that starts with either 'search ' or '|'

    Arguments
    search_string -- An SPL search string
    """
    stripped_search_string = search_string.lstrip()

    if not stripped_search_string.startswith('search ') and not stripped_search_string.startswith('|'):
        return 'search %s' % search_string
    return search_string


def send_to_hec(job, environment_search_entry, stats, session_key):
    """
    Sends the results of a Splunk search job to localhost using HEC

    Arguments
    job -- A completed Splunk job created with the client.connect(...).service.jobs.create(...) command
    environment_entry -- The EAI entry for the environment
    environment_search_entry -- The EAI entry for the environment search
    """

    hec_global_rest_path = '/servicesNS/nobody/-/data/inputs/http/http'
    hec_eai_response_payload = simple_request_eai(hec_global_rest_path, 'update', 'GET', session_key)
    hec_entry = hec_eai_response_payload['entry'][0]
    use_https = hec_entry['content']['enableSSL'] == '1' or hec_entry['content']['enableSSL'] == 'True' or hec_entry['content']['enableSSL'] == 'true'

    hec_scheme = 'https' if use_https else 'http'
    hec_host = 'localhost'
    hec_port = hec_entry['content']['port']


    if (environment_search_entry['content']['hec_url'] == ''):
        hec_uri = '%s://%s:%s' % (hec_scheme, hec_host, hec_port)
    else:
        hec_uri = '%s://%s' % (hec_scheme, environment_search_entry['content']['hec_url'])
        hec_token = environment_search_entry['content']['hec_token']
    hec_collector_rest_path = '%s%s' % (hec_uri, '/services/collector')

    raw_event_internal_patterns = ['host', 'source', 'sourcetype', 'index', '\_.*']

    offset = 0
    count = 1000
    result_count = stats.get('resultCount', 0)

    while offset < result_count:
        job_results = job.results(count=count, offset=offset, output_mode='json', time_format='%s')
        results = json.loads(job_results.read())

        json_string = ''

        for event in results['results']:
            sourcetype =  event['sourcetype']

            if 'sourcetype' in environment_search_entry['content']:
                sourcetype = environment_search_entry['content']['sourcetype']

            payload = {}
            payload.update({
                'sourcetype': sourcetype,
                'source': event['source'],
                'host': event['host'],
                'index': environment_search_entry['content']['index']
            })

            if '_time' in event:
                payload.update({
                    'time': event['_time']
                })

            payload.update({
                'event': event['_raw']
            })

            fields = {}

            for field in event:
                for pattern in raw_event_internal_patterns:
                    if not re.match(pattern, field):
                        fields[field] = event[field]

            payload.update({
                'fields': fields
            })

            json_string = ''.join([json_string, json.dumps(payload)])

        if (environment_search_entry['content']['hec_token'] == ''):
            response, content = rest.simpleRequest(
                hec_collector_rest_path,
                jsonargs=json_string,
                method='POST',
                sessionKey=environment_search_entry['content']['hec_token_value'],
                token=False
            )
        else:
            response, content = rest.simpleRequest(
                hec_collector_rest_path,
                jsonargs=json_string,
                method='POST',
                sessionKey=environment_search_entry['content']['hec_token'],
                token=False
            )

        offset += count

def send_to_remote_hec(job, environment_search_entry, stats, session_key):
    """
    Sends the results of a Splunk search job to localhost using HEC

    Arguments
    job -- A completed Splunk job created with the client.connect(...).service.jobs.create(...) command
    environment_entry -- The EAI entry for the environment
    environment_search_entry -- The EAI entry for the environment search
    """

    offset = 0
    count = 1000
    result_count = stats.get('resultCount', 0)

    while offset < result_count:
        job_results = job.results(count=count, offset=offset, output_mode='json', time_format='%s')
        results = json.loads(job_results.read())

        json_string = ''

        for event in results['results']:

            payload = {}
            payload.update({
                'source': 'mothership_remote_instance',
            })

            payload.update({
                'event': event
            })

            json_string = ''.join([json_string, json.dumps(payload)])

        # url = environment_search_entry['content']['hec_endpoint']
        # authHeader = {'Authorization': 'Splunk ' + environment_search_entry['content']['hec_token']}
        # jsonDict = {"event": "through python -- again - does this thing work"}
        #
        # r = requests.post(url, headers=authHeader, json=jsonDict, verify=False)


        response, content = rest.simpleRequest(
            environment_search_entry['content']['hec_endpoint'],
            jsonargs=json_string,
            method='POST',
            sessionKey=environment_search_entry['content']['hec_token']
        )

        offset += count

def send_to_lookup(job, environment_search_entry, stats, session_key):
    """
    Writes the results of a Splunk search job to a lookup on the mothership host

    Arguments
    job -- A completed Splunk job created with the client.connect(...).service.jobs.create(...) command
    environment_entry -- The EAI entry for the environment
    environment_search_entry -- The EAI entry for the environment search
    """
    lookup_link_alternate = environment_search_entry['content']['lookup_link_alternate']
    hex_uuid = str(uuid.uuid4().hex)
    lookup_tmp_file = '%s.csv' % hex_uuid
    lookup_tmp_path = make_splunkhome_path(['var', 'run', 'splunk', 'lookup_tmp', lookup_tmp_file])

    with open(lookup_tmp_path, "w") as fp:

        offset = 0
        count = 1000
        result_count = stats.get('resultCount', 0)

        while offset < result_count:
            result = job.results(count=count, offset=offset, output_mode='csv', time_format='%s')

            if offset == 0:
                fp.write(result.read().decode("utf-8"))
            else:
                # Remove csv field header
                split_results = result.read().decode("utf-8").split('\n', 1)
                fp.write(split_results[1])
            offset += count

    lookup_rest_path = lookup_link_alternate
    lookup_postargs = {
        'eai:data': lookup_tmp_path
    }

    lookup_post_response_payload = simple_request_eai(lookup_rest_path, 'update', 'POST', session_key, lookup_postargs)


def grab_and_go(environment_search_link_alternate, session_key, app):
    """
    GETs the environment search associated with this poller and the environment associated with the environment search
    entry

    Returns the eai entry for the environment search, the eai entry for the environment, and the environment password
    """
    # Fetch the EAI entry for the environment search this poller will run
    debug_logger.info('action=environment_search_fetch state=start pid=%s guid=%s' % (pid, guid))
    try:
        environment_searches_eai_response_payload = simple_request_eai(
            environment_search_link_alternate,
            'list',
            'GET',
            session_key
        )
        environment_search_entry = environment_searches_eai_response_payload['entry'][0]
    except Exception as e:
        debug_logger.error('action=environment_search_fetch state=error error="%s" pid=%s guid=%s' % (e, pid, guid))
        raise e
    debug_logger.info('action=environment_search_fetch state=end pid=%s guid=%s' % (pid, guid))

    # Fetch the EAI entry for the remote environment this poller will send the search request to
    debug_logger.info('action=environment_fetch state=start pid=%s guid=%s' % (pid, guid))
    try:
        environments_eai_response_payload = simple_request_eai(
            environment_search_entry['content']['environment_link_alternate'],
            'list',
            'GET',
            session_key
        )
        environment_entry = environments_eai_response_payload['entry'][0]
    except Exception as e:
        debug_logger.error('action=environment_fetch state=error error="%s" pid=%s guid=%s' % (e, pid, guid))
        raise e
    debug_logger.info('action=environment_fetch state=end pid=%s guid=%s' % (pid, guid))

    # Fetch the password for the remote environment this poller will send the search request to
    debug_logger.info('action=environment_password_fetch state=start pid=%s guid=%s' % (pid, guid))
    try:
        environment_password = get_credential(
            environment_entry['content']['password_link_alternate'],
            session_key
        )
    except Exception as e:
        debug_logger.error('action=environment_password_fetch state=error error="%s" pid=%s guid=%s' % (e, pid, guid))
        raise e
    debug_logger.info('action=environment_password_fetch state=end pid=%s guid=%s' % (pid, guid))

    # Fetch search head cluster state
    debug_logger.info('action=server_roles_fetch state=start pid=%s guid=%s' % (pid, guid))
    try:
        server_roles_eai_response_payload = simple_request_eai(
            '/services/admin/server-roles',
            'list',
            'GET',
            session_key
        )
        server_roles_entry = server_roles_eai_response_payload['entry'][0]
    except Exception as e:
        debug_logger.error('action=server_roles_fetch state=error error="%s" pid=%s guid=%s' % (e, pid, guid))
    debug_logger.info('action=server_roles_fetch state=end pid=%s guid=%s' % (pid, guid))

    debug_logger.info('action=mothership_fetch state=start pid=%s guid=%s' % (pid, guid))
    try:
        mothership_settings_endpoint = '/servicesNS/nobody/%s/configs/conf-mothership/settings' % app
        mothership_eai_response_payload = simple_request_eai(
            mothership_settings_endpoint,
            'list',
            'GET',
            session_key
        )
        mothership_entry = mothership_eai_response_payload['entry'][0]
    except Exception as e:
        debug_logger.error('action=mothership_fetch state=error error="%s" pid=%s guid=%s' % (e, pid, guid))
        raise e
    debug_logger.info('action=mothership_fetch state=end pid=%s guid=%s' % (pid, guid))

    return environment_search_entry, environment_entry, environment_password, server_roles_entry, mothership_entry


@Configuration(type='reporting')
class EnvironmentPollerSearchCommand(GeneratingCommand):

    environment_search_link_alternate = Option(require=True)

    def generate(self):
        session_key = self._metadata.searchinfo.session_key
        app = self._metadata.searchinfo.app
        environment_search_link_alternate = str(self.environment_search_link_alternate)

        mgmt_scheme_host_port = self._metadata.searchinfo.splunkd_uri

        if not is_url_valid(mgmt_scheme_host_port, ssl_only=True):
            raise Exception('Invalid internal url %s.' % mgmt_scheme_host_port)

        url = mgmt_scheme_host_port + environment_search_link_alternate

        environment_search_entry, environment_entry, environment_password, server_roles_entry, mothership_entry = grab_and_go(url, session_key, app)
        mgmt_scheme_host_port = environment_entry['content']['mgmt_scheme_host_port']

        if not is_url_valid(mgmt_scheme_host_port, ssl_only=True):
            raise Exception('Invalid internal url %s.' % mgmt_scheme_host_port)

        environment_host, environment_port = parse_environment(mgmt_scheme_host_port)
        parsed_search_string = parse_search_string(environment_search_entry['content']['search_string'])
        role_list = server_roles_entry['content']['role_list']
        is_search_head_cluster_captain = 'shc_captain' in role_list
        is_search_head_cluster_mode = is_search_head_cluster_captain or 'shc_member' in role_list

        debug_logger.info(
            'action=poller state=start environment_link_alternate=%s environment_search_link_alternate=%s pid=%s guid=%s' % (environment_entry['links']['alternate'], environment_search_entry['links']['alternate'], pid, guid))
        # Run Splunk search on a remote instance
        debug_logger.info(
            'action=sdk_connect state=start instance_host=%s instance_port=%s pid=%s guid=%s' % (environment_host, environment_port, pid, guid))

        try:
            service = client.connect(
                host=environment_host,
                port=environment_port,
                username=environment_entry['content']['username'],
                password=environment_password,
                scheme='https',
            )
        except socket.error as e:
            debug_logger.info('action=sdk_connect state=error type=socket error="%s" pid=%s guid=%s' % (e, pid, guid))
            metrics_logger.info(
                metric_log_message(
                    environment_searches_link_alternate=environment_search_link_alternate,
                    environment_link_alternate=environment_entry['links']['alternate'],
                    script_run_duration=str(elapsed_time(tstart)),
                    type='socket_error',
                    message=str(e),
                    is_search_head_cluster_captain=is_search_head_cluster_captain,
                    is_search_head_cluster_mode=is_search_head_cluster_mode,
                    pid=str(pid),
                    guid=guid
                )
            )
            raise e
        except binding.AuthenticationError as e:
            debug_logger.info(
                'action=sdk_connect state=error type=authentication error="%s" pid=%s guid=%s' % (e, pid, guid))
            metrics_logger.info(
                metric_log_message(
                    environment_searches_link_alternate=environment_search_link_alternate,
                    environment_link_alternate=environment_entry['links']['alternate'],
                    script_run_duration=str(elapsed_time(tstart)),
                    type='auth_error',
                    message=str(e),
                    is_search_head_cluster_captain=is_search_head_cluster_captain,
                    is_search_head_cluster_mode=is_search_head_cluster_mode,
                    pid=str(pid),
                    guid=guid
                )
            )
            raise e
        except Exception as e:
            debug_logger.info(
                'action=sdk_connect state=error type=exception error="%s" pid=%s guid=%s' % (e, pid, guid))
            metrics_logger.info(
                metric_log_message(
                    environment_searches_link_alternate=environment_search_link_alternate,
                    environment_link_alternate=environment_entry['links']['alternate'],
                    script_run_duration=str(elapsed_time(tstart)),
                    type='connect_error',
                    message=str(e),
                    is_search_head_cluster_captain=is_search_head_cluster_captain,
                    is_search_head_cluster_mode=is_search_head_cluster_mode,
                    pid=str(pid),
                    guid=guid
                )
            )
            raise e

        debug_logger.info('action=sdk_connect state=end pid=%s guid=%s' % (pid, guid))

        earliest_interval = environment_search_entry['content'].get('interval')
        if not earliest_interval: # We're executing on a cron schedule and can't infer the time range, defaulting to 1h
            earliest_interval = 3600
        earliest_time = f'-{earliest_interval}s'

        kwargs_normalsearch = {
            'exec_mode': 'normal',
            'count': 0,
            'earliest_time': earliest_time,
            'latest_time': 'now'
        }
        debug_logger.info('action=sdk_job_create state=start pid=%s guid=%s' % (pid, guid))

        try:
            job = service.jobs.create(parsed_search_string, **kwargs_normalsearch)
        except Exception as e:
            debug_logger.error('action=sdk_job_create state=error error="%s" pid=%s guid=%s' % (e, pid, guid))
            metrics_logger.info(
                metric_log_message(
                    environment_searches_link_alternate=environment_search_link_alternate,
                    environment_link_alternate=environment_entry['links']['alternate'],
                    script_run_duration=str(elapsed_time(tstart)),
                    type='search_dispatch_error',
                    message=str(e),
                    is_search_head_cluster_captain=is_search_head_cluster_captain,
                    is_search_head_cluster_mode=is_search_head_cluster_mode,
                    pid=str(pid),
                    guid=guid
                )
            )
            raise e
        debug_logger.info('action=sdk_job_create state=end pid=%s guid=%s' % (pid, guid))

        # A normal search returns the job's SID right away, so we need to poll for completion
        debug_logger.info('action=sdk_job_is_ready state=start pid=%s guid=%s' % (pid, guid))

        is_done = False
        stats = {}
        sleepy_time = int(mothership_entry['content']['job_status_interval'])/1000
        remote_search_start_time = time.time()
        max_remote_search_time = int(mothership_entry['content']['job_done_timeout'])

        while not is_done:
            remote_search_elapsed_time = time.time() - remote_search_start_time
            if remote_search_elapsed_time > max_remote_search_time:
                debug_logger.info(
                    'action=sdk_job_is_ready state=error type=timeout error="Remote search duration exceeded timeout specified in mothership.conf" pid=%s guid=%s' % (pid, guid))
                metrics_logger.info(
                    metric_log_message(
                        environment_searches_link_alternate=environment_search_link_alternate,
                        environment_link_alternate=environment_entry['links']['alternate'],
                        script_run_duration=str(elapsed_time(tstart)),
                        type='timeout_error',
                        message='Remote search duration exceeded timeout specified in mothership.conf',
                        is_search_head_cluster_captain=is_search_head_cluster_captain,
                        is_search_head_cluster_mode=is_search_head_cluster_mode,
                        pid=str(pid),
                        guid=guid
                    )
                )
                e = Exception("Classic HOLLYWOOD timeout.")
                raise e
            if job.is_ready():
                if job['isDone'] == '1':
                    is_done = True
                    stats = {
                        'isDone': job['isDone'],
                        'doneProgress': float(job['doneProgress']) * 100,
                        'scanCount': int(job['scanCount']),
                        'eventCount': int(job['eventCount']),
                        'runDuration': int(float(job['runDuration']) * 1000),
                        'resultCount': int(job['resultCount']),
                        'reportSearch': job['reportSearch']
                    }
                else:
                    time.sleep(sleepy_time)
            else:
                time.sleep(sleepy_time)

        debug_logger.info('action=sdk_job_is_ready state=end pid=%s guid=%s' % (pid, guid))

        report_search = 1 if stats['reportSearch'] else 0

        if 'hec_endpoint' in environment_search_entry['content'] and 'hec_token' in environment_search_entry['content']:
            debug_logger.info('action=send_to_remote_hec state=start pid=%s guid=%s' % (pid, guid))
            try:
                send_to_remote_hec(job, environment_search_entry, stats, session_key)
            except Exception as e:
                debug_logger.info('action=send_to_remote_hec state=error error="%s" pid=%s guid=%s' % (e, pid, guid))
                metrics_logger.info(
                    metric_log_message(
                        environment_searches_link_alternate=environment_search_link_alternate,
                        environment_link_alternate=environment_entry['links']['alternate'],
                        results_count=stats.get('resultCount', ''),
                        sid=job.sid,
                        job_run_duration=stats.get('runDuration', ''),
                        script_run_duration=str(elapsed_time(tstart)),
                        report_search=str(report_search),
                        type='send_to_hec_error',
                        message=str(e),
                        is_search_head_cluster_captain=is_search_head_cluster_captain,
                        is_search_head_cluster_mode=is_search_head_cluster_mode,
                        pid=str(pid),
                        guid=guid
                    )
                )
                raise e
            debug_logger.info('action=send_to_hec state=end pid=%s guid=%s' % (pid, guid))
        else:
            if report_search == 1:
                debug_logger.info('action=send_to_lookup state=start pid=%s guid=%s' % (pid, guid))
                try:
                    send_to_lookup(job, environment_search_entry, stats, session_key)
                except Exception as e:
                    debug_logger.info('action=send_to_lookup state=error error="%s" pid=%s guid=%s' % (e, pid, guid))
                    metrics_logger.info(
                        metric_log_message(
                            environment_searches_link_alternate=environment_search_link_alternate,
                            environment_link_alternate=environment_entry['links']['alternate'],
                            results_count=stats.get('resultCount', ''),
                            sid=job.sid,
                            job_run_duration=stats.get('runDuration', ''),
                            script_run_duration=str(elapsed_time(tstart)),
                            report_search=str(report_search),
                            type='send_to_lookup_error',
                            message=str(e),
                            is_search_head_cluster_captain=is_search_head_cluster_captain,
                            is_search_head_cluster_mode=is_search_head_cluster_mode,
                            pid=str(pid),
                            guid=guid
                        )
                    )
                    raise e
                debug_logger.info('action=send_to_lookup state=end pid=%s guid=%s' % (pid, guid))
            else:
                debug_logger.info('action=send_to_hec state=start pid=%s guid=%s' % (pid, guid))
                try:
                    send_to_hec(job, environment_search_entry, stats, session_key)
                except Exception as e:
                    debug_logger.info('action=send_to_hec state=error error="%s" pid=%s guid=%s' % (e, pid, guid))
                    metrics_logger.info(
                        metric_log_message(
                            environment_searches_link_alternate=environment_search_link_alternate,
                            environment_link_alternate=environment_entry['links']['alternate'],
                            results_count=stats.get('resultCount', ''),
                            sid=job.sid,
                            job_run_duration=stats.get('runDuration', ''),
                            script_run_duration=str(elapsed_time(tstart)),
                            report_search=str(report_search),
                            type='send_to_hec_error',
                            message=str(e),
                            is_search_head_cluster_captain=is_search_head_cluster_captain,
                            is_search_head_cluster_mode=is_search_head_cluster_mode,
                            pid=str(pid),
                            guid=guid
                        )
                    )
                    raise e
                debug_logger.info('action=send_to_hec state=end pid=%s guid=%s' % (pid, guid))

        debug_logger.info('action=sdk_job_cancel state=start pid=%s guid=%s' % (pid, guid))
        try:
            job.cancel()
        except Exception as e:
            debug_logger.error('action=sdk_job_cancel state=error error="%s" pid=%s guid=%s' % (e, pid, guid))
            metrics_logger.info(
                metric_log_message(
                    environment_searches_link_alternate=environment_search_link_alternate,
                    environment_link_alternate=environment_entry['links']['alternate'],
                    results_count=stats.get('resultCount', ''),
                    sid=job.sid,
                    job_run_duration=stats.get('runDuration', ''),
                    script_run_duration=str(elapsed_time(tstart)),
                    report_search=str(report_search),
                    type='sdk_job_cancel_error',
                    message=str(e),
                    is_search_head_cluster_captain=is_search_head_cluster_captain,
                    is_search_head_cluster_mode=is_search_head_cluster_mode,
                    pid=str(pid),
                    guid=guid
                )
            )
            raise e
        debug_logger.info('action=sdk_job_cancel state=end pid=%s guid=%s' % (pid, guid))
        debug_logger.info('action=poller state=end pid=%s guid=%s' % (pid, guid))
        summary = dict(
            environment_searches_link_alternate=environment_search_link_alternate,
            environment_link_alternate=environment_entry['links']['alternate'],
            results_count=stats.get('resultCount', ''),
            sid=job.sid,
            job_run_duration=stats.get('runDuration', ''),
            script_run_duration=str(elapsed_time(tstart)),
            report_search=str(report_search),
            type='poller_success',
            is_search_head_cluster_captain=is_search_head_cluster_captain,
            is_search_head_cluster_mode=is_search_head_cluster_mode,
            pid=str(pid),
            guid=guid
        )

        metrics_logger.info(metric_log_message(**summary))
        yield summary

dispatch(EnvironmentPollerSearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
