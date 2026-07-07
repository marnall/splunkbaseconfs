# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
import asyncio
import json
import sys
import time

try:
    import http.client as httplib
except ImportError:
    import httplib

import splunk.rest as rest
from splunk import RESTException
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path  # noqa
import itsi_py3

# Process .pth files
import site

from ITOA.controller_utils import ITOAError, itoa_response_headers
from ITOA.event_management.event_onboarding_utils import EventOnboardingUtils
from ITOA.itoa_exceptions import ItoaError
from ITOA.itoa_exceptions import ItoaValidationError
from ITOA.rest_interface_provider_base import SplunkdRestInterfaceBase
from ITOA.setup_logging import getLogger
from ITOA.storage.statestore import StateStoreError
from SA_ITOA_app_common.solnlib.conf_manager import ConfManager
from itsi.itoa_rest_interface_provider.itoa_rest_interface_provider import ItoaInterfaceProvider
from itsi.itsi_utils import ITOAInterfaceUtils

from user_access_errors import UserAccessError

try:
    from SA_ITOA_app_common.splunklib import client
    from SA_ITOA_app_common.splunklib import results
    from SA_ITOA_app_common.solnlib.splunk_rest_client import _request_handler
except ImportError as err:
    print('*** ERROR ***')
    print(err)
    sys.exit(1)


logger = getLogger()


class EventManagementTelemetryInterfaceProviderSplunkd(ItoaInterfaceProvider):
    def __init__(self, session_key, current_user, rest_method):
        """
        The decorator invoked wrapper for the decorated function (REST handler)
        This wrapper does the access check on the REST request and throws an exception if access is denied

        @type: string
        @param session_key: the splunkd session key for the request

        @type: string
        @param current_user: current user invoking the request

        @type: string
        @param: type of REST method of this request, GET/PUT/POST/DELETE
        """
        self._setup(session_key, current_user, rest_method)
        self.service = client.connect(token=self._session_key, handler=_request_handler({}))

    def event_onboarding_telemetry(self):
        """
        Gets the usage summary of data integrations in a user's environment
        """

        event_onboarding_utils = EventOnboardingUtils(self._session_key, self._current_user)
        connections = event_onboarding_utils.integration_interface.get_bulk(self._current_user)

        summary = {}
        connection_types = ['generic', 'nagios', 'solarwinds', 'o11y', 'scom', 'appdynamics', 'thousandeyes', 'cloudtrail']

        for connection_type in connection_types:
            summary[connection_type] = {
                'active': 0,
                'inactive': 0,
                'titles': []
            }
        for connection in connections:
            data_source = connection['data_source']
            title = connection['title']
            status = connection['status']

            if status == 'active':
                summary[data_source]['active'] += 1
            else:
                summary[data_source]['inactive'] += 1
            summary[data_source]['titles'].append(title)

        return json.dumps({'data': summary})

    @staticmethod
    async def wait_for_job(search_job, maxtime=10):
        """
        Wait up to maxtime seconds for search_job to finish.  If maxtime is
        negative, waits forever.  Returns true, if job finished.
        """
        pause = 0.2
        lapsed = 0.0
        while not search_job.is_done():
            time.sleep(pause)
            lapsed += pause
            if maxtime >= 0 and lapsed > maxtime:
                break
        return search_job.is_done()

    @staticmethod
    async def get_search_output(job, job_results):
        """
        Waits for the search job to complete and returns its contents
        @param job: splunk search job
        @param job_results: list of job results
        @return:
        """
        await EventManagementTelemetryInterfaceProviderSplunkd.wait_for_job(job)
        rr = results.JSONResultsReader(job.results(output_mode='json'))
        for result in rr:
            if isinstance(result, dict):
                # Normal events are returned as dicts
                job_results.append(result)
        job_results.append({})

    async def nats_telemetry(self):
        """
        Get NATS usage statistics
        @return:
        """

        cfm = ConfManager(self._session_key, 'SA-ITOA')
        conf = cfm.get_conf('itsi_event_management')
        telemetry = conf.get('telemetry')
        latency_query = telemetry['latency_query']
        queue_enabled_query = telemetry['queue_enabled_query']
        cpu_mem_query = telemetry['cpu_mem_query']
        backfill_rate_query = telemetry['backfill_rate_query']
        events_processed_rate_query = telemetry['events_processed_rate_query']
        messages_pushed_to_nats_rate_query = telemetry['messages_pushed_to_nats_rate_query']
        rules_engine_start_stop_query = telemetry['rules_engine_start_stop_query']

        query_list = [latency_query,
                      queue_enabled_query,
                      cpu_mem_query,
                      backfill_rate_query,
                      events_processed_rate_query,
                      messages_pushed_to_nats_rate_query,
                      rules_engine_start_stop_query]
        job_list = [ITOAInterfaceUtils.run_search(self._session_key, logger, query) for query in query_list]

        jobs = []
        job_results = []
        for job in job_list:
            jobs.append(asyncio.create_task(self.get_search_output(job, job_results)))
        await asyncio.gather(*jobs)

        result_json = {
            "eventProcessingLatency": "0",
            "queueEnabled": "0",
            "cpuAverage": "0",
            "memAverage": "0",
            "eventsBackfilledPerMinute": "0",
            "eventsProcessedPerMinute": "0",
            "eventsIngestedPerMinute": "0",
            "rulesEngineStarted": "0",
            "rulesEngineStopped": "0"
        }
        for r in job_results:
            result_json.update(r)

        return json.dumps({'data' : result_json})

    def neap_enhancement_telemetry(self):
        """
        Gets the usage summary of NEAP enhancements in a user's environment
        """
        telemetry = {
            'total_neaps': 0,
            'total_neaps_enabled': 0,
            'enhanced_neaps_enabled': 0,
            'cpma_neaps_enabled': 0
        }
        response, content = rest.simpleRequest(
            path="/servicesNS/nobody/SA-ITOA/event_management_interface/notable_event_aggregation_policy",
            method='GET',
            sessionKey=self.service.token
        )
        if response.status != 200:
            logger.error('Failed to fetch NEAP enhancements telemetry: %s', content)
            raise Exception('Failed to fetch NEAP enhancements telemetry')
        neaps = json.loads(content)
        telemetry['total_neaps'] = len(neaps)
        for neap in neaps:
            if neap['disabled'] == 0:
                if self._is_using_neap_enhancements(neap):
                    telemetry['enhanced_neaps_enabled'] += 1
                elif 'da-itsi-cp-monitoring-alerting' in neap['_key']:
                    telemetry['cpma_neaps_enabled'] += 1
                telemetry['total_neaps_enabled'] += 1
        return json.dumps({'data': telemetry})

    def _is_using_neap_enhancements(self, neap):
        """
        Checks if the user is using NEAP enhancements
        """
        # Check to see if highest event type severity is used
        if 'group_severity' in neap and neap['group_severity'] == '%highest_event_type_severity%':
            return True

        # Check the rules to see if new enhanced action rules are used
        rules = neap['rules']
        for rule in rules:
            for item in rule['activation_criteria']['items']:
                notable_event_type = item['type'] == 'notable_event_type'
                severity_status_duration = (item['type'] == 'episode_event_status' or item['type'] == 'episode_event_severity') and 'limit' in item['config']
                if notable_event_type or severity_status_duration:
                    return True
        return False


class EventManagementTelemetryInterfaceSplunkd(PersistentServerConnectionApplication, SplunkdRestInterfaceBase):
    """
    This wrapper class for the REST provider in EventManagementRestProvider which
    handles all access check decorators and passes on to provider to serve
    rest of the request
    """

    def __init__(self, command_line, command_arg):
        '''
        Basic constructor

        @type: string
        @param command_line: command line invoked for handler

        @type: string
        @param command_arg: args for invoked command line for handler
        '''
        super(EventManagementTelemetryInterfaceSplunkd, self).__init__()

    def migration_check(self, session_key):
        '''
        Override migration_check in SplunkdRestInterfaceBase
        MigrationInterfaceSplunkd should be accessible during migration and serve request regardless of migration
        running
        Thus override migration_check of SplunkdRestInterfaceBase
        '''
        pass

    def handle(self, args):
        """
        Blanket handler for all REST calls on the interface routing the GET/POST/PUT/DELETE requests.
        Derived implementation from PersistentServerConnectionApplication.

        @type args: json
        @param args: a JSON string representing a dictionary of arguments to the REST call.

        @rtype: json
        @return: a valid REST response
        """
        return self._default_handle(args)

    def _default_handle(self, args):
        """
        Blanket handler for all REST calls on the interface routing the GET/POST/PUT/DELETE requests.
        Derived implementation from PersistentServerConnectionApplication.
        This is a generic implementation that specific derived implementation could use optionally

        @type args: json
        @param args: a JSON string representing a dictionary of arguments to the REST call.

        @rtype: json
        @return: a valid REST response
        """
        logger.cleanUpContext()
        logger.info('Splunkd REST handler for EA Telemetry received request with args: %s', args)

        response_status = 500
        response_payload = []

        try:
            args = json.loads(args)
            self.migration_check(args['session']['authtoken'])

            result = self._dispatch_to_provider(args)

            if result is None or isinstance(result, itsi_py3.string_type):
                rest_method = args['method']
                response_status = 200
                if rest_method == 'DELETE':
                    response_status = 204
                response_payload = result
            else:
                response_status = 500
                response_payload = {'message': 'Received unexpected results from dispatcher: {}'.format(result)}
        except (ITOAError, UserAccessError) as e:
            logger.exception(e)
            response_status = e.status
            response_payload = self.handle_payload_error(e, e._message)
        except RESTException as e:
            logger.exception(e)
            response_status = e.statusCode
            response_payload = self.handle_payload_error(e, str(e))
        except StateStoreError as e:
            response_status = e.status_code or 500
            response_payload = self.handle_payload_error(e, str(e))
        except ItoaError as e:
            response_status = e.status_code or 500
            response_payload = self.handle_payload_error(e, str(e))
        except Exception as e:
            logger.exception(e)
            response_status = 500
            response_payload = self.handle_payload_error(e, str(e))
        try:
            response_status = int(response_status)
        except (ValueError, TypeError):
            response_status = 500

        headers = [['Content-Type', 'text/plain']]
        response = {
            'status': response_status,
            'payload': response_payload,
            'headers': headers,
        }

        return response

    def _dispatch_to_provider(self, args):
        if not isinstance(args, dict):
            message = f'Invalid REST args received by Data Integrations Template Interface - {args}'
            raise ItoaValidationError(message=message, logger=logger)

        session_key = args['session']['authtoken']
        current_user = args['session']['user']
        rest_method = args['method']

        rest_path = args['rest_path']

        path_parts = rest_path.strip().strip('/').split('/')

        interface_provider = EventManagementTelemetryInterfaceProviderSplunkd(session_key, current_user,
                                                                              rest_method)

        if len(path_parts) == 3 and path_parts[2] == 'event_onboarding':
            return interface_provider.event_onboarding_telemetry()
        if len(path_parts) == 3 and path_parts[2] == 'nats':
            return asyncio.run(interface_provider.nats_telemetry())
        if len(path_parts) == 3 and path_parts[2] == 'neap_enhancement':
            return interface_provider.neap_enhancement_telemetry()
        raise ITOAError(status=404, message=f'Specified REST url/path is invalid - {rest_path}.')
