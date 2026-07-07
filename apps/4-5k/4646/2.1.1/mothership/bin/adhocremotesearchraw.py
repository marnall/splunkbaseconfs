from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
import logging
import os
import sys
import json
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
import time
import splunklib.client as client
import splunk.rest as rest
from six.moves.urllib.parse import urlparse
import log_helper
from environments_schema import is_url_valid

pid = os.getpid()

debug_logger = log_helper.setup(logging.INFO, 'AdHocRemoteSearchDebug', 'ad_hoc_remote_search_debug.log')

@Configuration()
class AdHocRemoteSearchCommand(GeneratingCommand):

    def simple_request_messages_to_str(self, messages):
        """
        Returns a readable string from a simple request response message

        Arguments
        messages -- The simple request response message to parse
        """
        entries = []
        for message in messages:
            entries.append(message.get('text'))
        return ','.join(entries)


    def double_rainbow(self, uri):
        return six.moves.urllib.parse.quote_plus(six.moves.urllib.parse.quote_plus(uri))


    def triple_rainbow(self, uri):
        return six.moves.urllib.parse.quote_plus(
            six.moves.urllib.parse.quote_plus(six.moves.urllib.parse.quote_plus(uri)))


    def simple_request_eai(self, url, action, method, session_key, params=None):
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
        debug_logger.info('action=http_internal_request state=start method=%s url=%s pid=%s' % (method, url, pid))
        try:
            response, content = rest.simpleRequest(url, getargs=dict(output_mode='json'), postargs=params, method=method,                                           sessionKey=session_key)
        except Exception as e:
            debug_logger.error('action=http_internal_request state=error error=%s pid=%s' % (e, pid))
            raise Exception('Unable to %s %s entry. %s' % (action, url, e))
        debug_logger.info('action=http_internal_request state=end pid=%s' % (pid))

        try:
            payload = json.loads(content)
        except Exception as e:
            debug_logger.error('action=http_internal_request state=error error=%s' % (e))
            raise Exception('Unable to parse %s response payload.' % url)

        if response.status not in [200, 201]:
            message = self.simple_request_messages_to_str(response.messages)
            debug_logger.error('action=http_internal_request state=error error=%s' % (message))
            raise Exception(
                'Unable to %s %s entry. %s' % (action, url, message))
        return payload


    def get_credential(self, password_link_alternate, session_key):
        # Load password to check hash and length
        passwords_conf_payload = self.simple_request_eai(password_link_alternate, 'list', 'GET', session_key)
        return passwords_conf_payload['entry'][0]['content']['clear_password']


    def parse_search_string(self, search_string):
        """
        Returns a string that starts with either 'search ' or '|'

        Arguments
        search_string -- An SPL search string
        """
        stripped_search_string = search_string.lstrip()

        if (not stripped_search_string.startswith('search ') and not stripped_search_string.startswith('|')):
            return 'search %s' % search_string
        return search_string


    def grab_and_go(self, environment_link_alternate, session_key, search_string, app):
        environments_eai_response_payload = self.simple_request_eai(environment_link_alternate, 'list', 'GET', session_key)

        entry_attrs = environments_eai_response_payload['entry'][0]['content']

        parsed_url = urlparse(entry_attrs['mgmt_scheme_host_port'])

        mothership_settings_endpoint = '/servicesNS/nobody/%s/configs/conf-mothership/settings' % app
        mothership_eai_response_payload = self.simple_request_eai(
            mothership_settings_endpoint,
            'list',
            'GET',
            session_key
        )
        mothership_entry = mothership_eai_response_payload['entry'][0]

        # Get parameters for the ES instance being monitored
        request_args = {
            'instance_host': parsed_url.hostname,
            'instance_port': parsed_url.port,
            'instance_user': entry_attrs['username'],
            'instance_password': self.get_credential(entry_attrs['password_link_alternate'], session_key),
            'search_string': self.parse_search_string(search_string),
            'job_status_interval': int(mothership_entry['content']['job_status_interval']),
            'job_done_timeout': int(mothership_entry['content']['job_done_timeout'])
        }

        return request_args


    environment_link_alternates = Option(require=True)
    search_string = Option(require=True)

    def generate(self):
        jobs_list = []

        environment_link_alternates_list = self.environment_link_alternates.split('&')

        mgmt_scheme_host_port = self._metadata.searchinfo.splunkd_uri

        app = self._metadata.searchinfo.app

        if not is_url_valid(mgmt_scheme_host_port, ssl_only=True):
            raise Exception('Invalid internal url %s.' % mgmt_scheme_host_port)

        for environment_link_alternate in environment_link_alternates_list:
            url = mgmt_scheme_host_port + environment_link_alternate
            request_args = self.grab_and_go(url, self._metadata.searchinfo.session_key, self.search_string, app)

            # Run Splunk search on a remote instance
            debug_logger.info('action=sdk_connect state=start instance_host=%s instance_port=%s pid=%s' % (
            request_args["instance_host"], request_args["instance_port"], pid))
            service = client.connect(
                host=request_args["instance_host"],
                port=request_args["instance_port"],
                username=request_args["instance_user"],
                password=request_args["instance_password"],
                scheme='https',
            )
            debug_logger.info('action=sdk_connect state=end pid=%s' % (pid))

            kwargs_normalsearch = {
                'exec_mode': 'normal',
                'count': 0,
                'earliest_time': '-1m',
                'latest_time': 'now'
            }
            debug_logger.info('action=sdk_job_create state=start pid=%s' % (pid))
            try:
                job = service.jobs.create(request_args["search_string"], **kwargs_normalsearch)
                service_bound_job = client.Job(service, job['sid'])
                jobs_list.append(service_bound_job)
            except Exception as e:
                debug_logger.error('action=sdk_job_create state=error error=%s pid=%s' % (e, pid))
                raise e

            debug_logger.info('action=sdk_job_create state=end pid=%s' % (pid))

            # A normal search returns the job's SID right away, so we need to poll for completion
            debug_logger.info('action=sdk_job_is_ready state=start pid=%s' % (pid))

        completed_jobs = 0
        number_of_jobs = len(jobs_list)
        completed_jobs_list = [False]*number_of_jobs
        job_stats = [0]*number_of_jobs

        is_done = False
        sleepy_time = request_args['job_status_interval']/1000
        remote_search_start_time = time.time()
        max_remote_search_time = request_args['job_done_timeout']

        while completed_jobs != number_of_jobs:
            remote_search_elapsed_time = time.time() - remote_search_start_time
            if remote_search_elapsed_time > max_remote_search_time:
                e = Exception("Remote search duration exceeded timeout specified in mothership.conf")
                raise e
            for i, job in enumerate(jobs_list):
                if job.is_ready():
                    if job['isDone'] == '1' and not completed_jobs_list[i]:
                        completed_jobs_list[i] = True
                        completed_jobs+=1
                        job_stats[i] = {
                            'isDone': job['isDone'],
                            'resultCount': job['resultCount']
                        }
                time.sleep(sleepy_time)

        debug_logger.info('action=sdk_job_is_ready state=end pid=%s' % (pid))

        for i, job in enumerate(jobs_list):
            # Get the results and display them
            debug_logger.info('action=sdk_result_reader state=start pid=%s' % (pid))
            try:
                resultCount = job["resultCount"]
                offset = 0
                count = 1000

                if int(resultCount) > 0:
                    while offset < int(resultCount):
                        kwargs_paginate = {"count": count, "offset": offset, 'output_mode': 'json'}
                        page = job.results(**kwargs_paginate)

                        obj = json.loads(page.read())

                        for result in obj['results']:
                            if result:
                                result['mothership_environment'] = environment_link_alternates_list[i]

                                yield result

                        offset += count

            except Exception as e:
                debug_logger.error('action=sdk_result_reader state=error error=%s pid=%s' % (e, pid))
                raise e

            debug_logger.info('action=sdk_result_reader state=end pid=%s' % (pid))

            debug_logger.info('action=sdk_job_cancel state=start pid=%s' % (pid))

            try:
                job.cancel()
            except Exception as e:
                debug_logger.error('action=sdk_job_cancel state=error error=%s pid=%s' % (e, pid))
                raise e

            debug_logger.info('action=sdk_job_cancel state=end pid=%s' % (pid))

dispatch(AdHocRemoteSearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
