#!/usr/bin/env python
# coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License'): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
# from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
import time
import json
import logging
import uuid
import threading

current_path = os.path.dirname(__file__)
sys.path.append(os.path.join(current_path, '..', 'libs', 'external'))

from splunklib.searchcommands import (  # noqa: E402
    dispatch, GeneratingCommand, Configuration, Option, validators
)
import sim_common  # noqa: E402
from signalfx.signalflow import SignalFlowClient, messages, sse  # noqa: E402


@Configuration()
class SIMCommand(GeneratingCommand):

    # sim command parameters
    query = Option(
        doc='''**Syntax: query=<string>
        **Description:** the SignalFlow program used to fetch the data from Infrastructure
        Monitoring.''',
        require=True)
    resolution = Option(
        doc='''**Syntax: resolution=<integer>
        **Description:** the metric resolution of search results. Defaults to 300000 (5 mins).''',
        default=300000, validate=validators.Integer())
    with_derived_metadata = Option(
        doc='''**Syntax: with_derived_metadata=<bool>
        **Description:** When `true`, the search results contains full metadata.
        Defaults to `false`.''',
        default=False, validate=validators.Boolean())
    format = Option(
        doc='''**Syntax:** format=[table|raw]
        **Description:** the format of search results.''',
        default='table', validate=validators.Set('table', 'raw'))
    org_id = Option(
        doc='''**Syntax: org_id=<<Infrastructure Monitoring Organization ID>>
        **Description:** When provided, the command fetch the results from the provided sim
        organization account. When not provided, the command fetch the results from the default
        sim organization account.''',
        default=None)

    # sim command parameters specifically for events sub-command
    # limit on number of events when calling events rest endpoint
    limit = Option(
        doc='''**Syntax:** limit=<integer>
        **Description:** the limit on number of events to return in the response''',
        default=10000, require=False)

    # offset on events when calling events rest endpoint
    offset = Option(
        doc='''**Syntax:** offset=<integer>
        **Description:** the offset on the order of the events returned in the response''',
        require=False)

    # flag to search on event timestamp or event occurred time
    search_on_event_timestamp = Option(
        doc='''**Syntax:** search_on_event_timestamp=<bool>
        **Description:** When `true`, the command will search events on timestamp/occurred time
        instead of event created time. Defaults to `false`.''',
        default=False, require=False)

    # Constants

    SPLUNK_SIM_CONF_NAME = 'sim'
    SPLUNK_SIM_CONF_API_STANZA_NAME = 'sim_api'

    SIM_META_DATA_FIELDS_TO_IGNORE_IN_FLOW_RESULTS_DEFAULT = (
        'sf_originatingMetric,sf_createdOnMs,sf_isPreQuantized,sf_key,'
        'sf_metric,sf_type,sf_singletonFixedDimensions'
    )
    SIM_META_DATA_FIELDS_TO_IGNORE_IN_EVENT_RESULTS_DEFAULT = 'sf_recipients'
    SIM_API_TIMEOUT_DEFAULT = 5
    SIM_FLOW_LIMIT_MSG_CODE = 'FIND_LIMITED_RESULT_SET'
    EMPTY_SEARCH_RESULTS = []
    SIM_API_EVENT_SEARCH_URL = '/v2/event/find'
    SIM_API_SIGNAL_FLOW_USE_SSE = 0
    SIM_SERACH_TIMEOUT = 600
    ENABLE_WATCHDOG = True

    # internal class variables
    old_data_delay = 0
    new_data_delay = 999999
    sim_command_flow_metadata_fields_to_ignore = []
    sim_command_event_metadata_fields_to_ignore = []
    msg_last_seen = time.time()
    break_watchdog = False

    class SubCommands:
        FLOW = 'flow'
        EVENT = 'event'

    class ResultsFormats:
        TABLE = 'table'
        RAW = 'raw'

    class LoggerContextFilter(logging.Filter):
        """
        This is a filter which injects command invocation instance UUID in the logs.
        """
        request_id = uuid.uuid4().hex

        def filter(self, record):
            record.request_id = self.request_id
            return True

    def generate(self):

        self.logger.addFilter(self.LoggerContextFilter())

        # get subcommand. ex: 'flow'
        if not self.fieldnames:
            self.logger.error(
                'status=error, action=execute_sim_command, error_code=no_sub_command'
            )
            self.write_command_error('Invalid arguments. No subcommand specified.')
            return self.EMPTY_SEARCH_RESULTS
        self.sim_sub_command = self.fieldnames[0]

        try:
            self.logger.info(
                'status=start, action=get_sim_connection, sub_command={0}, org_id={1}'.format(
                    self.sim_sub_command, self.org_id
                )
            )
            self.sim_connection = sim_common.SIMConnection(self.service, self.org_id)
            self.org_id = self.sim_connection.org_id
            self.logger.info(
                'status=complete, action=get_sim_connection, sub_command={0}, org_id={1}, '
                'is_default={2}, org_name={3}, realm={4}, access_token=*************{5}'.format(
                    self.sim_sub_command, self.sim_connection.org_id,
                    self.sim_connection.is_default, self.sim_connection.org_name,
                    self.sim_connection.realm, self.sim_connection.access_token[-4:]
                )
            )
        except Exception as e:
            self.logger.error(
                'status=error, action=get_sim_connection, sub_command={0}, error_msg={1}'.format(
                    self.sim_sub_command, str(e)
                ),
                exc_info=True
            )
            self.write_command_error(
                'Splunk Infrastructure Monitoring API Connection not configured.'
            )
            return self.EMPTY_SEARCH_RESULTS

        # Search Command parameters initialization
        self.logger.info(
            'status=start, action=execute_sim_command, sub_command={0}, org_id={1}'.format(
                self.sim_sub_command, self.sim_connection.org_id
            )
        )
        self.sim_api_conf_stanza = sim_common.get_conf_stanza(
            self.service, self.SPLUNK_SIM_CONF_NAME, self.SPLUNK_SIM_CONF_API_STANZA_NAME
        )
        self.timeout = int(
            self.sim_api_conf_stanza.get('sim_api_timeout', self.SIM_API_TIMEOUT_DEFAULT)
        )
        self.sim_api_signal_flow_use_sse = int(
            self.sim_api_conf_stanza.get(
                'sim_api_signal_flow_use_sse', self.SIM_API_SIGNAL_FLOW_USE_SSE
            )
        )
        self.sim_api_proxy_url = self.sim_api_conf_stanza.get('sim_api_proxy_url', None)
        flow_fields_default = self.SIM_META_DATA_FIELDS_TO_IGNORE_IN_FLOW_RESULTS_DEFAULT
        self.sim_command_flow_metadata_fields_to_ignore = [
            x.strip() for x in self.sim_api_conf_stanza.get(
                'sim_command_flow_metadata_fields_to_ignore', flow_fields_default
            ).split(',')
        ]
        event_fields_default = self.SIM_META_DATA_FIELDS_TO_IGNORE_IN_EVENT_RESULTS_DEFAULT
        self.sim_command_event_metadata_fields_to_ignore = [
            x.strip() for x in self.sim_api_conf_stanza.get(
                'sim_command_event_metadata_fields_to_ignore', event_fields_default
            ).split(',')
        ]
        self.sim_search_timeout_seconds = int(
            self.sim_api_conf_stanza.get('sim_search_timeout_seconds', self.SIM_SERACH_TIMEOUT)
        )
        self.sim_flow_enable_watchdog = int(
            self.sim_api_conf_stanza.get('sim_flow_enable_watchdog', self.ENABLE_WATCHDOG)
        )

        # get search search_earliest_time and search_latest_time
        has_latest_time = (
            self.metadata and self.metadata.searchinfo and self.metadata.searchinfo.latest_time
        )
        if has_latest_time:
            self.search_latest_time = int(self.metadata.searchinfo.latest_time * 1000)
        else:
            # set 10 min from current time as search_latest_time
            self.search_latest_time = int(time.time() * 1000) - 600000
            self.logger.info(
                'action=set_default_latest_time, sub_command={0}, org_id={1}, value={2}'.format(
                    self.sim_sub_command, self.sim_connection.org_id,
                    str(self.search_latest_time)
                )
            )

        has_earliest_time = (
            self.metadata and self.metadata.searchinfo and self.metadata.searchinfo.earliest_time
        )
        if has_earliest_time:
            self.search_earliest_time = int(self.metadata.searchinfo.earliest_time * 1000)
        else:
            # set 10 min from search_latest_time as search_earliest_time
            self.search_earliest_time = self.search_latest_time - 600000
            self.logger.info(
                'action=set_default_earliest_time, sub_command={0}, org_id={1}, value={2}'.format(
                    self.sim_sub_command, self.sim_connection.org_id,
                    str(self.search_earliest_time)
                )
            )

        # Search Command Execution
        if self.sim_sub_command == self.SubCommands.FLOW:
            return self.execute_flow_sub_command()
        elif self.sim_sub_command == self.SubCommands.EVENT:
            return self.execute_event_sub_command()
        else:
            self.logger.error(
                'status=error, action=execute_sim_command, error_code=invalid_sub_command, '
                'sub_command={0}, org_id={1}'.format(
                    self.sim_sub_command, self.sim_connection.org_id
                )
            )
            self.write_command_error(
                'Invalid arguments. Subcommand {0} not found.'.format(self.sim_sub_command)
            )
            return self.EMPTY_SEARCH_RESULTS

    #########################################################################
    # EVENT SUB COMMAND #####################################################
    #########################################################################

    def execute_event_sub_command(self):
        self.logger.info(
            'status=start, action=execute_sim_sub_command_event, sub_command={0}, '
            'search_earliest_time={1}, search_latest_time={2}, query={3}, limit={4}, '
            'format={5}, search_on_event_timestamp={6}, org_id={7}'.format(
                self.sim_sub_command, self.search_earliest_time, self.search_latest_time,
                self.query, self.limit, self.format, str(self.search_on_event_timestamp),
                self.sim_connection.org_id
            )
        )
        events_count, events_size = 0, 0
        try:
            session = self.sim_connection.get_sim_request_session()
            url = self.sim_connection.sim_api_url + self.SIM_API_EVENT_SEARCH_URL
            event_create_time_filter = ' AND sf_eventCreatedOnMs:[{0} TO {1}]'.format(
                str(self.search_earliest_time), str(self.search_latest_time)
            )
            if self.search_on_event_timestamp:
                data = {
                    'query': self.query,
                    'startTime': self.search_earliest_time,
                    'endTime': self.search_latest_time,
                    'offset': self.offset,
                    'limit': self.limit
                }
            else:
                data = {
                    'query': self.query + event_create_time_filter,
                    'offset': self.offset,
                    'limit': self.limit
                }

            events_json = self.get_sim_events(session, url, data, self.timeout)
            for event_json in events_json:
                try:
                    event_timestamp = sim_common.normalize_time(
                        event_json.get('timestamp', time.time())
                    )
                    event_create_time = sim_common.normalize_time(
                        event_json.get('properties', {}).get('sf_eventCreatedOnMs', time.time())
                    )
                    self.old_data_delay = max(self.old_data_delay, time.time() - event_timestamp)
                    self.new_data_delay = min(self.new_data_delay, time.time() - event_timestamp)
                    # if the format is 'table' then we return the events flattened
                    if self.format == self.ResultsFormats.TABLE:
                        flat_json = self.flatten_event(event_json)
                        flat_json['sf_organizationID'] = self.org_id
                        if self.search_on_event_timestamp:
                            flat_json['_time'] = event_timestamp
                        else:
                            flat_json['_time'] = event_create_time
                        flat_json['_raw'] = json.dumps(flat_json)
                        yield flat_json
                        # TABLE: return streamed output as soon as it processed
                    # if the format is 'raw'. Keep the default path.
                    else:
                        if self.search_on_event_timestamp:
                            event_time = event_timestamp
                        else:
                            event_time = event_create_time
                        yield {
                            'id': event_json.get('id', ''),
                            '_time': event_time,
                            'sf_eventType': event_json.get('sf_eventType', ''),
                            'sf_eventCategory': event_json.get('sf_eventCategory', ''),
                            'tsId': event_json.get('tsId', ''),
                            'sf_organizationID': self.org_id,
                            '_raw': json.dumps(event_json)
                        }
                    events_size += sys.getsizeof(str(event_json))
                except Exception as e:
                    self.logger.error(
                        'status=error, action=execute_sim_sub_command_event, sub_command={0}, '
                        'org_id={1}, error_msg={2}'.format(
                            self.sim_sub_command, self.sim_connection.org_id, str(e)
                        ),
                        exc_info=True
                    )
            events_count = len(list(events_json))

            # check if SIM REST API limit on number of events per search returned has been reached
            sim_event_limit_reached = False
            if events_count == 10000:
                sim_event_limit_reached = True
                self.logger.error(
                    'status=error, error_code=limit_reached, error_msg=sim event search reached '
                    'event limit of {0}., action=execute_sim_sub_command_event, sub_command={1}, '
                    'sim_event_limit_reached={2}, sim_event_limit={0}, org_id={3}'.format(
                        str(events_count), self.sim_sub_command, str(sim_event_limit_reached),
                        self.sim_connection.org_id
                    ),
                    exc_info=True
                )
                self.write_warning(
                    '"sim" event search reached limit of {0} events.'.format(str(events_count))
                )
        except Exception as e:
            self.logger.error(
                'status=error, action=execute_sim_sub_command_event, sub_command={0}, '
                'org_id={1}, error_msg={2}'.format(
                    self.sim_sub_command, self.sim_connection.org_id, str(e)
                ),
                exc_info=True
            )
            self.write_command_error(
                'Error calling REST Events endpoint. error_msg={0}'.format(str(e))
            )
            return
        finally:
            session.close()
            self.logger.info(
                'status=process, action=close_rest_client_connection, sub_command={0}, '
                'org_id={1}'.format(self.sim_sub_command, self.sim_connection.org_id)
            )
            self.logger.info(
                'status=complete, action=execute_sim_sub_command_event, sub_command={0}, '
                'events_count={1}, events_size={2}, old_data_delay={3}, new_data_delay={4}, '
                'org_id={5}'.format(
                    self.sim_sub_command, str(events_count), str(events_size),
                    str(self.old_data_delay), str(self.new_data_delay), self.sim_connection.org_id
                )
            )
            self.logger.info(
                'status=complete, action=execute_sim_command, sub_command={0}, org_id={1}'.format(
                    self.sim_sub_command, self.sim_connection.org_id
                )
            )

    def get_sim_events(self, session, url, data, timeout):
        response = session.post(url, data=json.dumps(data), timeout=timeout)
        response.raise_for_status()
        return response.json()

    # TODO: this flat meta data extraction works good for non group alerts.
    # for group alerts the meta data not present in the event payload.
    def flatten_event(self, event_json):
        # get root level field values which are not a dict
        flat_json = {k: v for k, v in event_json.items() if not type(v) is dict}

        # get meta data from event json
        metadata_json = event_json.get('metadata', {})
        flat_json.update({'metadata_' + k: v for k, v in metadata_json.items()})

        # process properties
        properties_json = event_json.get('properties', {})
        for k, v in properties_json.items():
            if k == 'inputs' and type(v) is dict:
                inputs_json = v
                inputs_meta_data = {}
                inputs_meta_data_key = None
                for key, val in inputs_json.items():
                    if type(val) is dict:
                        if 'key' in val:
                            temp_inputs_meta_data = val.get('key', {})
                            # TODO: Assumption1: resource value input object in generally
                            # contains 'key' object with highest length.
                            if len(temp_inputs_meta_data) > len(inputs_meta_data):
                                if inputs_meta_data_key is not None:
                                    signal_value = flat_json.get('signal_resource_value', None)
                                    threshold_key = 'signal_threshold_' + str(inputs_meta_data_key)
                                    flat_json[threshold_key + '_value'] = signal_value
                                    flat_json.update({
                                        threshold_key + '_' + k: v
                                        for k, v in inputs_meta_data.items()
                                    })
                                inputs_meta_data_key = key
                                inputs_meta_data = temp_inputs_meta_data.copy()
                                flat_json['signal_resource_value'] = val.get('value', None)
                            else:
                                threshold_key = 'signal_threshold_' + str(key)
                                signal_value = flat_json.get('signal_resource_value', None)
                                flat_json[threshold_key + '_value'] = signal_value
                                flat_json.update({
                                    threshold_key + '_' + k: v
                                    for k, v in temp_inputs_meta_data.items()
                                })
                        else:
                            # TODO: Assumption1: if 'key' is not present then item may not be
                            # a resource value in case of non group stats
                            threshold_key = 'signal_threshold_' + str(key)
                            flat_json[threshold_key + '_value'] = val.get('value', None)
                # add the sf key meta data like- ip, host to root
                flat_json.update({
                    'signal_resource_' + k: v for k, v in inputs_meta_data.items()
                })

            elif not type(v) is dict:
                # Rename the "incidentId" field to "sf_incidentId".
                # so it won't conflict with "incidentId" in other Splunk events.
                if k == 'incidentId':
                    flat_json['sf_' + k] = v
                else:
                    flat_json[k] = v
        # Remove unused metadata fields
        for key_ig in self.sim_command_event_metadata_fields_to_ignore:
            flat_json.pop(key_ig, None)
        return flat_json

    #########################################################################
    # FLOW SUB COMMAND ######################################################
    #########################################################################

    def execute_flow_sub_command(self):
        self.logger.info(
            'status=start, action=execute_sim_sub_command_flow, sub_command={0}, '
            'search_earliest_time={1}, search_latest_time={2}, format={3}, query={4}, '
            'with_derived_metadata={5}, resolution={6}, org_id={7}'.format(
                self.sim_sub_command, self.search_earliest_time, self.search_latest_time,
                self.format, self.query, str(self.with_derived_metadata),
                str(self.resolution), self.sim_connection.org_id
            )
        )

        # Initialize Signal Flow Client
        flow_client = None
        try:
            stream_url = self.sim_connection.sim_stream_url
            self.logger.info(
                'status=process, action=initialize_sim_client, sub_command={0}, org_id={1}, '
                'url={2}, use_sse={3}, proxy_url={4}'.format(
                    self.sim_sub_command, self.sim_connection.org_id, stream_url,
                    str(self.sim_api_signal_flow_use_sse), str(self.sim_api_proxy_url)
                )
            )
            if self.sim_api_signal_flow_use_sse:
                flow_client = SignalFlowClient(
                    token=self.sim_connection.access_token,
                    endpoint=stream_url,
                    transport=sse.SSETransport,
                    proxy_url=self.sim_api_proxy_url
                )
            else:
                flow_client = SignalFlowClient(
                    token=self.sim_connection.access_token,
                    endpoint=stream_url,
                    proxy_url=self.sim_api_proxy_url
                )
        except Exception as e:
            self.logger.error(
                'status=error, action=initialize_sim_client, sub_command={0}, org_id={1}, '
                'error_msg={2}'.format(
                    self.sim_sub_command, self.sim_connection.org_id, str(e)
                ),
                exc_info=True
            )
            self.write_command_error(
                'Error initializing Splunk Infrastructure Monitoring client. '
                'url={0}, error_msg={1}'.format(stream_url, str(e))
            )
            return self.EMPTY_SEARCH_RESULTS

        try:
            return self.run_signalflow_program(
                flow_client=flow_client,
                program=self.query,
                start=self.search_earliest_time,
                stop=self.search_latest_time,
                format=self.format,
                with_derived_metadata=self.with_derived_metadata,
                resolution=self.resolution
            )
        except Exception as e:
            self.logger.error(
                'status=error, action=execute_sim_sub_command_flow, sub_command={0}, '
                'org_id={1}, error_msg={2}'.format(
                    self.sim_sub_command, self.sim_connection.org_id, str(e)
                ),
                exc_info=True
            )
            self.write_command_error(
                'Error calling SignalFlow program. error_msg={0}'.format(str(e))
            )
            return self.EMPTY_SEARCH_RESULTS
            # run SIM Flow connection and internal websocket
        finally:
            self.logger.info(
                'status=complete, action=execute_sim_sub_command_flow, sub_command={0}, '
                'org_id={1}'.format(self.sim_sub_command, self.sim_connection.org_id)
            )

    def run_signalflow_program(self, flow_client, program, start, stop, format,
                               with_derived_metadata, resolution):

        # If the search took longer than the defined time interval then watchdog_bark will
        # stop the search execution
        def watchdog_bark():
            self.logger.info(
                "Watchdog for the search started, will shutdown the search in {} seconds "
                "if not completed".format(self.sim_search_timeout_seconds)
            )
            while True:
                if self.break_watchdog:
                    break
                current_time = time.time()
                if current_time - self.msg_last_seen > self.sim_search_timeout_seconds:
                    flow_client.close()
                    self.logger.error(
                        'Sim search timed out after {} seconds'.format(
                            self.sim_search_timeout_seconds
                        )
                    )
                    os._exit(1)
                time.sleep(5)

        if self.sim_flow_enable_watchdog:
            watchdog = threading.Thread(target=watchdog_bark)
            watchdog.start()
        meta_data, computation = {}, None

        try:
            # Execute the computation and iterate over the message stream
            self.logger.info(
                'status=start, action=execute_signalflow_program, sub_command={0}, '
                'org_id={1}'.format(self.sim_sub_command, self.sim_connection.org_id)
            )

            # set immediate=true, overrides the value of stop and stops the computation
            # immediately when data stops arriving
            # refer https://developers.signalfx.com/signalflow_analytics/websocket_request_messages
            computation = flow_client.execute(
                program, start=start, stop=stop, resolution=resolution, immediate=True,
                withDerivedMetadata=with_derived_metadata, resolutionAdjustable=True
            )

            self.logger.info(
                'status=complete, action=execute_signalflow_program, sub_command={0}, '
                'org_id={1}'.format(self.sim_sub_command, self.sim_connection.org_id)
            )
        except Exception as e:
            self.logger.error(
                'status=error, action=execute_signalflow_program, sub_command={0}, org_id={1}, '
                'error_msg={2}'.format(
                    self.sim_sub_command, self.sim_connection.org_id, str(e)
                ),
                exc_info=True
            )
            self.write_command_error(
                'Error executing SignalFlow program. error_msg={0}'.format(str(e))
            )
            flow_client.close()
            return

        data_msg_count, data_msg_size = 0, 0
        metadata_msg_count, metadata_msg_size = 0, 0
        mts_count, other_msg_count = 0, 0
        computation_id = ''
        sim_flow_limit_reached = False
        self.logger.info(
            'status=start, action=process_signalflow_program_results, sub_command={0}, '
            'org_id={1}, format={2}'.format(
                self.sim_sub_command, self.sim_connection.org_id, format
            )
        )
        try:
            for msg in computation.stream():
                self.msg_last_seen = time.time()
                try:
                    if isinstance(msg, messages.JobStartMessage):
                        computation_id = msg.handle
                    # Check for SIM Limit reached message
                    if not sim_flow_limit_reached and isinstance(msg, messages.InfoMessage):
                        msg_code = msg.message.get('messageCode', None) if msg.message else None
                        if msg_code == self.SIM_FLOW_LIMIT_MSG_CODE:
                            sim_flow_limit_reached = True

                    if format == self.ResultsFormats.TABLE:
                        if isinstance(msg, messages.MetadataMessage):
                            msg.properties['metric_name'] = msg.properties.get(
                                'sf_originatingMetric', ''
                            )
                            msg.properties.pop('sf_organizationID', None)
                            msg.properties.pop('computationId', None)
                            # Remove unused metadata fields
                            for key in self.sim_command_flow_metadata_fields_to_ignore:
                                msg.properties.pop(key, None)
                            meta_data[msg.tsid] = msg.properties
                            metadata_msg_count += 1
                            if metadata_msg_size == 0:
                                metadata_msg_size = sys.getsizeof(str(msg.properties))

                        elif isinstance(msg, messages.DataMessage):
                            if not msg.data.items():
                                continue
                            msg_time = sim_common.normalize_time(msg.logical_timestamp_ms)
                            self.old_data_delay = max(
                                self.old_data_delay, time.time() - msg_time
                            )
                            self.new_data_delay = min(
                                self.new_data_delay, time.time() - msg_time
                            )
                            data_msg_count += 1
                            mts_count += len(msg.data.items())
                            if data_msg_size == 0:
                                data_msg_size = sys.getsizeof(str(msg.data))
                            for k, v in msg.data.items():
                                if k in meta_data:
                                    flat_json = meta_data.get(k).copy()
                                    # Add new fields - meteric value, time
                                    flat_json['_value'] = v
                                    flat_json['_time'] = msg_time
                                    flat_json['sf_realm'] = self.sim_connection.realm
                                    flat_json['sf_organizationID'] = self.org_id
                                    flat_json['computationId'] = computation_id
                                    # _raw form is still required even after having the same
                                    # kv data in results
                                    # kv data in results is the simplest and performant way
                                    # to extract the interesting fields
                                    flat_json['_raw'] = json.dumps(flat_json, sort_keys=True)
                                    yield flat_json  # TABLE: return streamed output
                        else:
                            other_msg_count += 1

                    # if the format is 'raw'. Keep the default path.
                    else:
                        msg_time = time.time()
                        if isinstance(msg, messages.MetadataMessage):
                            metadata_msg_count += 1
                            if metadata_msg_size == 0:
                                metadata_msg_size = sys.getsizeof(str(msg.properties))
                        elif isinstance(msg, messages.DataMessage):
                            # there are empty datapoints when resolutionAdjustable=False.
                            # this logic is to skip the empty data points.
                            if not msg.data.items():
                                continue
                            data_msg_count += 1
                            mts_count += len(msg.data.items())
                            msg_time = sim_common.normalize_time(msg.logical_timestamp_ms)
                            self.old_data_delay = max(
                                self.old_data_delay, time.time() - msg_time
                            )
                            self.new_data_delay = min(
                                self.new_data_delay, time.time() - msg_time
                            )
                            if data_msg_size == 0:
                                data_msg_size = sys.getsizeof(str(msg.data))
                        else:
                            other_msg_count += 1

                        raw_json = msg.__dict__
                        raw_json['msg_type'] = msg.__class__.__name__

                        # RAW DATA: return streamed output as soon as it received
                        yield {
                            '_time': msg_time,
                            'msg_type': raw_json['msg_type'],
                            '_raw': json.dumps(raw_json)
                        }

                except Exception as e:
                    self.logger.error(
                        'status=error, action=process_signalflow_program_results_msg, '
                        'sub_command={0}, computation_id={1}, error_msg={2}, org_id={3}'.format(
                            self.sim_sub_command, computation_id, str(e),
                            self.sim_connection.org_id
                        ),
                        exc_info=True
                    )
        except Exception as e:
            self.logger.error(
                'status=error, action=process_signalflow_program_results, sub_command={0}, '
                'computation_id={1}, error_msg={2}, org_id={3}'.format(
                    self.sim_sub_command, computation_id, str(e), self.sim_connection.org_id
                ),
                exc_info=True
            )
            self.write_command_error(
                'Error processing SignalFlow program. error_msg={0}'.format(str(e))
            )
            return
        finally:
            flow_client.close()
            self.logger.info(
                'status=process, action=close_sim_client_connection, sub_command={0}, '
                'org_id={1}'.format(self.sim_sub_command, self.sim_connection.org_id)
            )
            self.break_watchdog = True

        self.logger.info(
            'status=complete, action=process_signalflow_program_results, sub_command={0} '
            'format={1}, metadata_msg_count={2}, metadata_msg_size={3}, data_msg_count={4}, '
            'data_msg_size={5}, mts_count={6}, other_msg_count={7}, computation_id={8}, '
            'old_data_delay={9}, new_data_delay={10}, org_id={11}'.format(
                self.sim_sub_command, format, str(metadata_msg_count), str(metadata_msg_size),
                str(data_msg_count), str(data_msg_size), str(mts_count), str(other_msg_count),
                computation_id, str(self.old_data_delay), str(self.new_data_delay),
                self.sim_connection.org_id
            )
        )
        if sim_flow_limit_reached:
            self.logger.error(
                'status=error, error_code=limit_reached, error_msg=sim flow search reached '
                'metadata message limit of {0}., action=process_signalflow_program_results, '
                'sub_command={1} sim_flow_limit_reached={2}, sim_flow_metadata_limit={0}, '
                'computation_id={3}, org_id={4}'.format(
                    str(metadata_msg_count), self.sim_sub_command, str(sim_flow_limit_reached),
                    computation_id, self.sim_connection.org_id
                )
            )
            self.write_warning(
                '"sim" flow search reached metadata message limit of {0}.'.format(
                    str(metadata_msg_count)
                )
            )
        self.logger.info(
            'status=complete, action=execute_sim_command, sub_command={0}, org_id={1}'.format(
                self.sim_sub_command, self.sim_connection.org_id
            )
        )

    #########################################################################
    # Common Functions ######################################################
    #########################################################################

    def write_command_error(self, message):
        message = 'Error in "sim" command: ' + message
        self.write_error(message)


dispatch(SIMCommand, sys.argv, sys.stdin, sys.stdout, __name__)
