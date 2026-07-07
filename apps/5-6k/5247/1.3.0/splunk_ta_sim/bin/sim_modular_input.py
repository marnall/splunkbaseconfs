# Copyright (C) 2005-2020 Splunk Inc. All Rights Reserved.
# from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
import time
import json
import re
import logging
import uuid
import threading
from multiprocessing.pool import ThreadPool

current_path = os.path.dirname(__file__)
sys.path.append(os.path.join(current_path, '..', 'libs'))
sys.path.append(os.path.join(current_path, '..', 'libs', 'external'))

from solnlib.modular_input import ModularInput  # noqa: E402
import noah_event_writer  # noqa: E402
import stack_info  # noqa: E402
from splunklib.client import Service  # noqa: E402
import logger_manager  # noqa: E402

import sim_common  # noqa: E402
from signalfx.signalflow import SignalFlowClient, messages, sse  # noqa: E402


class SIMModularInput(ModularInput):
    """
    Class that implements all the required steps. See method `do_run`.
    """
    # Constants
    SPLUNK_SIM_CONF_NAME = 'sim'
    SPLUNK_SIM_CONF_API_STANZA_NAME = 'sim_api'
    SIM_MOD_INPUT_METADATA_FIELDS_TO_IGNORE_IN_MATERIALIZED_VIEW = (
        'sf_createdOnMs,sf_isPreQuantized,sf_key,sf_metric,sf_type,'
        'sf_singletonFixedDimensions, sf_originatingMetric'
    )
    SIM_MOD_INPUT_METADATA_FIELDS_TO_IGNORE_IN_OPTIMIZED_VIEW = (
        'sf_createdOnMs,sf_isPreQuantized,sf_metric,sf_type,sf_singletonFixedDimensions'
    )
    SIM_FLOW_LIMIT_MSG_CODE = 'FIND_LIMITED_RESULT_SET'
    MAX_BACKFILL_TIME = 3600000
    MAX_DELAY = 900000
    MIN_DELAY = 2000
    SPLUNK_MODULARINPUT_COLLECTION = (
        'https://127.0.0.1:{}/servicesNS/nobody/splunk_ta_sim/storage/collections/data/'
        'sim_modularinputs'
    )
    SPLUNK_MODULARINPUT_URL = (
        'https://127.0.0.1:{}/services/data/inputs/sim_modular_input?output_mode=json'
    )

    # internal class variables
    sim_api_url = None
    sim_api_token = None
    sim_realm = 'us0'
    sim_flow_client = None
    sim_mod_input_retry_wait_time = 3
    sim_mod_input_retry_count = 3

    # modular input properties
    title = 'Splunk Infrastructure Monitoring Data Streams'
    description = (
        'Streams Infrastructure Monitoring metrics data into Splunk using SignalFlow programs.'
    )
    app = 'splunk_ta_sim'
    name = 'sim_modular_input'
    use_single_instance = False
    use_kvstore_checkpointer = False
    stop_mod_input_when_one_computation_fails = False
    backfill_timestamp_update_frequency = 5
    detail_log_frequency = 5

    # modular input conf init
    sim_mod_input_enable_materialized_view = 1
    sim_mod_input_store_to_metric_index = 1
    index = 'sim_metrics'
    sourcetype = 'stash'
    use_hec_event_writer = False
    hec_input_name = 'sim_modular_input'
    msg_last_seen = time.time()

    def extra_arguments(self):
        return [
            {
                'name': 'org_id',
                'title': 'Organization ID',
                'description': (
                    'Provide the Infrastructure Monitoring Organization ID to '
                    'fetch metrics data from.'
                )
            },
            {
                'name': 'signal_flow_programs',
                'title': 'SignalFlow Program',
                'description': (
                    'Provide a SignalFlow program to stream Infrastructure Monitoring '
                    'metrics data into Splunk.'
                )
            },
            {
                'name': 'additional_meta_data_flag',
                'title': 'Additional Metadata Flag',
                'description': (
                    'If 1, the metrics stream results contain full metadata. Defaults to 0.'
                )
            },
            {
                'name': 'sim_modinput_restart_interval_seconds',
                'title': 'Restart Interval for Modular Input',
                'description': (
                    'Only applies when data is not being received. The default value is '
                    '3600s(1 hour), maximum value is 86400s(24 hours) and minimum is '
                    '900s(15 minutes). Setting this to -1 disables the restart interval.'
                )
            },
            {
                'name': 'metric_resolution',
                'title': 'Metric Resolution',
                'description': (
                    'The interval for retrieving data in milliseconds. Default enables '
                    'the system to determine the resolution. Set this to a static value '
                    'to hardcode the interval for your data.'
                )
            },
            {
                'name': 'sim_max_delay',
                'title': 'Max wait time for delayed data',
                'description': (
                    'The default of -1 calculates optimal return time based on your lag '
                    'history and waits for delayed data before returning. To override '
                    'defaults, set the maximum time you\'re willing to wait for delayed '
                    'data, using a value between 2000 ms and 900000 ms. Data arriving '
                    'after that set time is not retrieved.'
                )
            },
        ]

    def do_run(self, stanzas_config):
        """
        This is the method called by splunkd when mod input is enabled.
        @type stanzas_config: dict
        @param stanzas_config: input config for all stanzas passed down by splunkd.
        """
        flow_programs_thread_pool = None
        self.mod_input_instance_name = ''
        self.modularinput_collection = 'sim_modularinputs'

        try:

            if len(stanzas_config) == 0:
                # if no stanzas are present, The feature is disabled.
                return

            self.stanza_name = next(iter(stanzas_config.keys()))
            self.stanza_config = next(iter(stanzas_config.values()))
            if '//' in self.stanza_name:
                self.mod_input_instance_name = (self.stanza_name.split('//')[1]).strip()
            else:
                self.mod_input_instance_name = self.stanza_name

            # Initialize Logger
            level = self.stanza_config.get("log_level", "INFO").upper()
            if level not in ["ERROR", "WARN", "WARNING", "INFO", "DEBUG"]:
                level = "INFO"
            formatter_str = self.stanza_config.get(
                "log_format",
                '%(asctime)s, Level=%(levelname)s, Pid=%(process)s, '
                'RequestId=%(request_id)s, Logger=%(name)s, File=%(filename)s, '
                'Line=%(lineno)s, %(message)s'
            )
            log_filename = 'splunk_ta_sim_' + self.mod_input_instance_name.replace(' ', '_')
            self.logger = logger_manager.setup_logging(
                self.__class__.__name__, log_filename, formatter=formatter_str
            )
            self.logger.addFilter(self.LoggerContextFilter())
            self.logger.setLevel(logging.getLevelName(level))
            self.logger.info(
                "SIMModularInput action=setting_logger status=completed log_level={} "
                "log_filename={} stanza_config={}".format(level, log_filename, self.stanza_config)
            )

            # TODO: Wait 20 sec. for the splunk to initialize all its internal services - KV store
            time.sleep(20)

            if self.mod_input_instance_name == 'Cleanup_Disabled_Modinput_Data':
                # Below line of code executes a watcher of modular inputs, which would delete all
                # stale timestamps stored for disabled/deleted/modified sim modinputs
                self.cleanup_timestamps_of_stale_modinputs()
                return

            self.service = Service(
                scheme=self.server_scheme, host=self.server_host,
                port=self.server_port, token=self.session_key, owner='nobody'
            )
            self.org_id = self.stanza_config.get('org_id', None)

            self.logger.info(
                'status=start, instance_name={0}, stanzas_config={1}, org_id={2}'.format(
                    self.mod_input_instance_name, json.dumps(stanzas_config), self.org_id
                )
            )

            try:
                self.max_delay = int(self.stanza_config.get('sim_max_delay', -1))
            except (TypeError, ValueError):
                self.max_delay = None

            if self.max_delay == -1:
                self.max_delay = None

            if self.max_delay and self.max_delay > self.MAX_DELAY:
                self.logger.info(
                    'The Max wait time for delayed data can have maximum value of {}ms, '
                    'using {} instead of {}'.format(
                        self.MAX_DELAY, self.MAX_DELAY, self.max_delay
                    )
                )
                self.max_delay = self.MAX_DELAY
            elif self.max_delay and self.max_delay < self.MIN_DELAY:
                self.logger.info(
                    'The Max wait time for delayed data can have minimum value of {}ms, '
                    'using {} instead of {}'.format(
                        self.MIN_DELAY, self.MIN_DELAY, self.max_delay
                    )
                )
                self.max_delay = self.MIN_DELAY

            try:
                self.metric_resolution = int(self.stanza_config.get('metric_resolution', -1))
            except (TypeError, ValueError):
                self.metric_resolution = -1

            self.resolution_adjustable = False
            if self.metric_resolution == -1:
                self.resolution_adjustable = True
                self.metric_resolution = None

            try:
                self.sim_modinput_restart_interval_seconds = int(
                    self.stanza_config.get('sim_modinput_restart_interval_seconds')
                )
                # Max delay user can expect for this configuration is 24hrs
                # and Minimum value will be 15mins.
                restart_interval = self.sim_modinput_restart_interval_seconds
                if restart_interval > 86400:
                    self.logger.info(
                        'The Maximum value of Restart Interval for Modular Input can have is '
                        '86400s which is 24hrs, using 86400s for the restart instead of {}'.format(
                            restart_interval
                        )
                    )
                    self.sim_modinput_restart_interval_seconds = 86400
                elif restart_interval < 900 and restart_interval != -1:
                    self.logger.info(
                        'The Minimum value of Restart Interval for Modular Input can have is '
                        '900s which is 15min, using 900s for the restart instead of {}'.format(
                            self.sim_modinput_restart_interval_seconds
                        )
                    )
                    self.sim_modinput_restart_interval_seconds = 900
            except (TypeError, ValueError) as e:
                self.logger.error(
                    "Error while fetching sim_modinput_restart_interval_seconds error {} "
                    "falling back to the default value 3600s".format(str(e)),
                    exc_info=True
                )
                self.sim_modinput_restart_interval_seconds = 3600

            try:
                self.additional_meta_data_flag = bool(
                    int(self.stanza_config.get('additional_meta_data_flag', 0))
                )
            except (TypeError, ValueError):
                self.additional_meta_data_flag = 0

            try:
                self.logger.info(
                    'status=start, instance_name={0}, org_id={1}, '
                    'action=get_sim_connection'.format(
                        self.mod_input_instance_name, self.org_id
                    )
                )
                self.sim_connection = sim_common.SIMConnection(self.service, self.org_id)
                self.org_id = self.sim_connection.org_id
                self.sim_realm = self.sim_connection.realm
                self.logger.info(
                    'status=complete, action=get_sim_connection, instance_name={0}, org_id={1}, '
                    'is_default={2}, org_name={3}, realm={4}, '
                    'access_token=*************{5}'.format(
                        self.mod_input_instance_name, self.sim_connection.org_id,
                        self.sim_connection.is_default, self.sim_connection.org_name,
                        self.sim_connection.realm, self.sim_connection.access_token[-4:]
                    )
                )
            except Exception as e:
                self.logger.error(
                    'status=error, instance_name={0}, org_id={1}, action=get_sim_connection, '
                    'error_msg={2}'.format(
                        self.mod_input_instance_name, self.org_id, str(e)
                    ),
                    exc_info=True
                )
                return

            # Initialization: Splunk Infrastructure Monitoring Flow Mod Input
            self.logger.info(
                'status=start, action=initialize, instance_name={0}, org_id={1}, '
                'realm={2}'.format(
                    self.mod_input_instance_name, self.org_id, self.sim_realm
                )
            )

            # fetch the value of backfill_timestamp from sim_modularinputs collection
            try:
                query = {"title": self.mod_input_instance_name}
                response = self.modularinput_collection_data(request_type="GET", query_params=query)
                self.logger.info(
                    'check if backfill timestamp is present for the modinput {}'.format(
                        self.mod_input_instance_name
                    )
                )
                if response.status_code == 200 and json.loads(response.content):
                    self.backfill_timestamp = json.loads(response.content)[0].get(
                        'last_timestamp_fetch'
                    )
                    self.modinput_key = json.loads(response.content)[0].get('_key')
                    self.logger.info(
                        'Backfill timestamp is present for the modinput {} {}'.format(
                            self.mod_input_instance_name, self.backfill_timestamp
                        )
                    )
                else:
                    self.backfill_timestamp = int(time.time() * 1000)
                    self.logger.info(
                        'Backfill timestamp is NOT present for the modinput {} '
                        'fetching data from currenttime'.format(self.mod_input_instance_name)
                    )
                    modinput_data = {
                        "title": self.mod_input_instance_name,
                        "last_timestamp_fetch": self.backfill_timestamp
                    }
                    response = self.modularinput_collection_data(
                        request_type="POST", modinput_data=modinput_data
                    )
                    self.modinput_key = json.loads(response.content).get('_key')
            except Exception as e:
                self.logger.info(
                    "status=error, action=Fetch backfill_timestamp from collection, "
                    "error_msg = {}".format(str(e)),
                    exc_info=True
                )

            self.sim_api_conf_stanza = sim_common.get_conf_stanza(
                self.service, self.SPLUNK_SIM_CONF_NAME, self.SPLUNK_SIM_CONF_API_STANZA_NAME
            )
            materialized_default = self.SIM_MOD_INPUT_METADATA_FIELDS_TO_IGNORE_IN_MATERIALIZED_VIEW
            optimized_default = self.SIM_MOD_INPUT_METADATA_FIELDS_TO_IGNORE_IN_OPTIMIZED_VIEW
            self.sim_mod_input_metadata_fields_to_ignore_in_materialized_view = [
                x.strip() for x in self.sim_api_conf_stanza.get(
                    'sim_mod_input_metadata_fields_to_ignore_in_materialized_view',
                    materialized_default
                ).split(',')
            ]
            self.sim_mod_input_metadata_fields_to_ignore_in_optimized_view = [
                x.strip() for x in self.sim_api_conf_stanza.get(
                    'sim_mod_input_metadata_fields_to_ignore_in_optimized_view',
                    optimized_default
                ).split(',')
            ]
            self.sim_mod_input_retry_wait_time = int(
                self.sim_api_conf_stanza.get('sim_mod_input_retry_wait_time', 5)
            )
            self.sim_mod_input_retry_count = int(
                self.sim_api_conf_stanza.get('sim_mod_input_retry_count', 3)
            )
            self.stop_mod_input_when_one_computation_fails_flag = int(
                self.sim_api_conf_stanza.get(
                    'sim_mod_input_stop_mod_input_when_one_computation_fails', 0
                )
            )
            self.sim_api_signal_flow_use_sse = int(
                self.sim_api_conf_stanza.get('sim_api_signal_flow_use_sse', 0)
            )
            self.sim_api_proxy_url = self.sim_api_conf_stanza.get('sim_api_proxy_url', None)

            # modular input conf setup
            self.sim_mod_input_store_to_metric_index = int(
                self.sim_api_conf_stanza.get(
                    'sim_mod_input_store_to_metric_index',
                    self.sim_mod_input_store_to_metric_index
                )
            )
            self.sim_mod_input_enable_materialized_view = int(
                self.sim_api_conf_stanza.get(
                    'sim_mod_input_enable_materialized_view',
                    self.sim_mod_input_enable_materialized_view
                )
            )
            self.index = self.stanza_config.get('index', self.index)
            self.sourcetype = self.stanza_config.get('sourcetype', self.sourcetype)

            # send the data to metric index only when materialized view is enabled
            if not self.sim_mod_input_enable_materialized_view:
                self.sim_mod_input_store_to_metric_index = 0
            # create hec token only when the mod input required to send the data to metric index
            if self.sim_mod_input_store_to_metric_index:
                self.use_hec_event_writer = True
                self.hec_global_settings_schema = True

            # Get SignalFlow Programs from KV Store
            self.signalflow_programs = [
                x.strip() for x in self.stanza_config.get('signal_flow_programs', '').split('|')
                if x
            ]
            # Remove first and last double quotes and Remove empty SignalFlow Programs from list
            self.signalflow_programs = [
                y.strip() for y in [
                    re.sub(r'^"|"$', '', x) for x in self.signalflow_programs if x
                ] if y.strip()
            ]

            self.logger.info(
                'status=complete, action=initialize, instance_name={0}, org_id={1}, index={2}, '
                'enable_materialized_view={3}, store_to_metric_index={4}, '
                'use_hec_event_writer={5}, metric_resolution={6}, additional_meta_data_flag={7}, '
                'backfill_timestamp={8}, signalflow_programs={9}, '
                'signalflow_computation_count={10}, sim_realm={11}, sim_stream_api_url={12}, '
                'sim_api_token=*******{13}, sim_api_conf_stanza={14},'.format(
                    self.mod_input_instance_name, self.org_id, self.index,
                    str(self.sim_mod_input_enable_materialized_view),
                    str(self.sim_mod_input_store_to_metric_index),
                    str(self.use_hec_event_writer), str(self.metric_resolution),
                    str(self.additional_meta_data_flag), str(self.backfill_timestamp),
                    ' | '.join(self.signalflow_programs), len(self.signalflow_programs),
                    self.sim_realm, self.sim_connection.sim_stream_url,
                    self.sim_connection.access_token[-4:], json.dumps(self.sim_api_conf_stanza)
                )
            )

            flow_programs_thread_pool = None
            if len(self.signalflow_programs) > 1:
                # Run Signal Flow Programs in multi thread pool
                pool_process_size = len(self.signalflow_programs)
                self.logger.info(
                    'status=start, action=initialize_flow_programs_thread_pool, instance_name={0}, '
                    'org_id={1}, pool_process_size={2}'.format(
                        self.mod_input_instance_name, self.org_id, str(pool_process_size)
                    )
                )
                flow_programs_thread_pool = ThreadPool(pool_process_size)
                self.logger.info(
                    'status=start, action=execute_flow_programs_thread_pool, instance_name={0}, '
                    'org_id={1}'.format(self.mod_input_instance_name, self.org_id)
                )
                flow_programs_thread_pool.map(self.run_signalflow_program, self.signalflow_programs)
                self.logger.info(
                    'status=complete, action=execute_flow_programs_thread_pool, instance_name={0}, '
                    'org_id={1}'.format(self.mod_input_instance_name, self.org_id)
                )
            elif len(self.signalflow_programs) == 1:
                self.run_signalflow_program(self.signalflow_programs[0])

        except Exception as e:
            self.logger.error(
                'status=error, instance_name={0}, org_id={1}, error_msg={2}'.format(
                    self.mod_input_instance_name, self.org_id, str(e)
                ),
                exc_info=True
            )
        finally:
            if flow_programs_thread_pool is not None:
                flow_programs_thread_pool.terminate()
                self.logger.info(
                    'status=complete, action=terminate_flow_programs_thread_pool, '
                    'instance_name={0}, org_id={1}'.format(
                        self.mod_input_instance_name, self.org_id
                    )
                )
                flow_programs_thread_pool.close()
                self.logger.info(
                    'status=complete, action=close_flow_programs_thread_pool, instance_name={0}, '
                    'org_id={1}'.format(self.mod_input_instance_name, self.org_id)
                )

            self.logger.info(
                'status=stop, instance_name={0}, org_id={1}, stanza_config={2}'.format(
                    self.mod_input_instance_name, self.org_id, json.dumps(self.stanza_config)
                )
            )

    # Run: Splunk Infrastructure Monitoring Flow Mod Input
    # TODO: make sure the ever run is thread safe. don't set any external class variables.
    def run_signalflow_program(self, signalflow_program):

        thread_id = uuid.uuid4().hex
        sim_flow_client = None
        retry_count = 0
        backfill_timestamp = self.backfill_timestamp

        # Create event writer based on stack type
        self.writer = self.get_event_writer()

        # watchdog_bark will stop the modular input execution if the data is delayed more than
        # the configured time interval.
        # Eg: self.sim_modinput_restart_interval_seconds = 900
        # if the data is delayed more then 900 secs the modular input will stop.
        def watchdog_bark():
            self.logger.info(
                "Watchdog for the {} started, will shutdown the modularinput in {} seconds "
                "if data stops coming".format(
                    self.mod_input_instance_name, self.sim_modinput_restart_interval_seconds
                )
            )
            self.break_watchdog = False
            while True:
                if self.break_watchdog:
                    break
                try:
                    current_time = time.time()
                    time_diff = int(current_time - self.msg_last_seen)
                    restart_interval = int(self.sim_modinput_restart_interval_seconds)
                    if time_diff > restart_interval:
                        self.logger.info(
                            'Data from modular input has been delayed for more than configured '
                            'time interval {}-secs, exiting the modularinput'.format(
                                self.sim_modinput_restart_interval_seconds
                            )
                        )
                        sim_flow_client.close()
                        self.logger.error(
                            'Sim modularinput {} timed out after {} seconds'.format(
                                self.mod_input_instance_name,
                                self.sim_modinput_restart_interval_seconds
                            )
                        )
                        os._exit(1)
                    time.sleep(5)
                except Exception as e:
                    self.logger.info(
                        "status=complete, action=Error while executing watchdog_bark method, "
                        "error_msg = {}".format(str(e)),
                        exc_info=True
                    )
                    break

        if int(self.sim_modinput_restart_interval_seconds) != -1:
            watchdog = threading.Thread(target=watchdog_bark)
            watchdog.start()

        # Retry Loop
        while retry_count < self.sim_mod_input_retry_count and not self.stop_mod_input_when_one_computation_fails:
            try:
                self.logger.info(
                    'status=start, action=run_signalflow_program, instance_name={0}, org_id={1}, '
                    'thread_id={2}, signalflow_program="{3}",retry_count={4}'.format(
                        self.mod_input_instance_name, self.org_id, thread_id,
                        signalflow_program, str(retry_count)
                    )
                )

                # Initialize Signal Flow Client
                self.logger.info(
                    'status=start, action=initialize_sim_flow_client, thread_id={0}, org_id={1}, '
                    'retry_count={2}, url={3}, use_sse={4}, proxy_url={5}'.format(
                        thread_id, self.org_id, str(retry_count),
                        self.sim_connection.sim_stream_url, str(self.sim_api_signal_flow_use_sse),
                        str(self.sim_api_proxy_url)
                    )
                )
                if self.sim_api_signal_flow_use_sse:
                    sim_flow_client = SignalFlowClient(
                        token=self.sim_connection.access_token,
                        endpoint=self.sim_connection.sim_stream_url,
                        transport=sse.SSETransport,
                        proxy_url=self.sim_api_proxy_url
                    )
                else:
                    sim_flow_client = SignalFlowClient(
                        token=self.sim_connection.access_token,
                        endpoint=self.sim_connection.sim_stream_url,
                        proxy_url=self.sim_api_proxy_url
                    )
                self.logger.info(
                    'status=complete, action=initialize_sim_flow_client, thread_id={0}, '
                    'org_id={1}, retry_count={2}'.format(
                        thread_id, self.org_id, str(retry_count)
                    )
                )

                # Create computation for Signal Flow Program
                computation = sim_flow_client.execute(
                    signalflow_program, start=backfill_timestamp,
                    resolution=self.metric_resolution, max_delay=self.max_delay,
                    withDerivedMetadata=self.additional_meta_data_flag,
                    resolutionAdjustable=self.resolution_adjustable
                )
                self.logger.info(
                    'status=complete, action=create_signalflow_program_computation, '
                    'thread_id={0}, org_id={1}, retry_count={2}, max_delay={3}, '
                    'resolutionAdjustable={4}, metric_resolution={5}'.format(
                        thread_id, self.org_id, str(retry_count), self.max_delay,
                        self.resolution_adjustable, self.metric_resolution
                    )
                )

                # Stream Signal Flow Program computation Results
                process_results_error_count = 0
                data_msg_count, empty_data_msg_count = 0, 0
                metadata_msg_count, mts_count = 0, 0
                other_msg_count = 0
                computation_id = ''
                meta_data = {}
                mts_delay = 0
                self.logger.info(
                    'status=start, action=stream_sim_flow_program_results, thread_id={0}, '
                    'org_id={1}, retry_count={2}'.format(thread_id, self.org_id, str(retry_count))
                )

                for msg in computation.stream():
                    self.msg_last_seen = time.time()
                    if self.stop_mod_input_when_one_computation_fails:
                        break
                    retry_count = 0
                    events = []
                    message_type = msg.__class__.__name__
                    try:
                        if isinstance(msg, messages.MetadataMessage):
                            metadata_msg_count += 1
                            if self.sim_mod_input_enable_materialized_view:
                                # Optimize the proc memory: by removing the common data
                                # (sf_organizationID, computationId) from the in-memory
                                # metadata dict.
                                msg.properties.pop('sf_organizationID', None)
                                msg.properties.pop('computationId', None)

                                # rename the sf_originatingMetric to metric_name
                                # (splunk metric name field)
                                msg.properties['metric_name'] = msg.properties.get(
                                    'sf_originatingMetric', None
                                )

                                # Remove unused metadata fields
                                fields_to_ignore = (
                                    self.sim_mod_input_metadata_fields_to_ignore_in_materialized_view
                                )
                                for key in fields_to_ignore:
                                    msg.properties.pop(key, None)
                                meta_data[msg.tsid] = msg.properties
                            else:
                                fields_to_ignore = (
                                    self.sim_mod_input_metadata_fields_to_ignore_in_optimized_view
                                )
                                for key in fields_to_ignore:
                                    msg.properties.pop(key, None)
                                raw_json = msg.properties
                                raw_json['md_id'] = computation_id + '.' + msg.tsid
                                raw_json['sf_realm'] = self.sim_realm
                                events.append(self.writer.create_event(
                                    data=json.dumps(raw_json), source='sim_metadata',
                                    sourcetype=self.sourcetype, index=self.index
                                ))
                        elif isinstance(msg, messages.DataMessage):
                            if not msg.data.items():
                                empty_data_msg_count += 1
                                continue
                            data_msg_count += 1
                            mts_in_data_msg = len(msg.data.items())
                            mts_count += mts_in_data_msg
                            event_time = sim_common.normalize_time(msg.logical_timestamp_ms)
                            mts_delay = time.time() - event_time
                            backfill_timestamp = msg.logical_timestamp_ms
                            modinput_data = {
                                "title": self.mod_input_instance_name,
                                "last_timestamp_fetch": backfill_timestamp
                            }
                            self.modularinput_collection_data(
                                request_type="POST",
                                query_params=str(self.modinput_key),
                                modinput_data=modinput_data
                            )

                            for k, v in msg.data.items():
                                if self.sim_mod_input_enable_materialized_view:
                                    if k in meta_data:
                                        fields = meta_data.get(k).copy()
                                        fields['_value'] = v
                                        fields['sf_realm'] = self.sim_realm
                                        # Optimize the proc memory: by adding the common data
                                        # (sf_organizationID, sf_resolutionMs, computationId)
                                        # at output generation time.
                                        fields['sf_organizationID'] = self.org_id
                                        fields['sf_resolutionMs'] = self.metric_resolution
                                        fields['computationId'] = computation_id
                                        if self.sim_mod_input_store_to_metric_index:
                                            events.append(self.writer.create_event(
                                                data={}, time=event_time, source='sim',
                                                sourcetype=self.sourcetype, index=self.index,
                                                fields=fields
                                            ))
                                        else:
                                            events.append(self.writer.create_event(
                                                data=json.dumps(fields), time=event_time,
                                                source='sim', sourcetype=self.sourcetype,
                                                index=self.index
                                            ))
                                else:
                                    flat_json = {}
                                    flat_json['md_id'] = computation_id + '.' + k
                                    flat_json['_value'] = v
                                    events.append(self.writer.create_event(
                                        data=json.dumps(flat_json), time=event_time,
                                        source='sim_mts', sourcetype=self.sourcetype,
                                        index=self.index
                                    ))

                            if data_msg_count % self.detail_log_frequency == 0:
                                self.logger.info(
                                    'status=running, action=stream_sim_flow_program_results, '
                                    'instance_name={0}, org_id={1}, thread_id={2}, '
                                    'signalflow_program="{3}", computation_id={4}, '
                                    'message_type={5}, metadata_msg_count={6}, data_msg_count={7}, '
                                    'mts_count={8}, other_msg_count={9}, data_msg_timestamp={10}, '
                                    'empty_data_msg_count={11}, retry_count={12}, '
                                    'mts_in_data_msg={13}, mts_delay={14}'.format(
                                        self.mod_input_instance_name, self.org_id, thread_id,
                                        signalflow_program, computation_id, message_type,
                                        str(metadata_msg_count), str(data_msg_count),
                                        str(mts_count), str(other_msg_count),
                                        str(msg.logical_timestamp_ms), str(empty_data_msg_count),
                                        str(retry_count), str(mts_in_data_msg), str(mts_delay)
                                    )
                                )
                            else:
                                self.logger.info(
                                    'status=running, action=stream_sim_flow_program_results, '
                                    'instance_name={0}, org_id={1}, thread_id={2}, '
                                    'computation_id={3}, message_type={4}, '
                                    'metadata_msg_count={5}, data_msg_count={6}, mts_count={7}, '
                                    'other_msg_count={8}, data_msg_timestamp={9}, '
                                    'empty_data_msg_count={10}, mts_in_data_msg={11}, '
                                    'mts_delay={12}'.format(
                                        self.mod_input_instance_name, self.org_id, thread_id,
                                        computation_id, message_type, str(metadata_msg_count),
                                        str(data_msg_count), str(mts_count), str(other_msg_count),
                                        str(msg.logical_timestamp_ms), str(empty_data_msg_count),
                                        str(mts_in_data_msg), str(mts_delay)
                                    )
                                )
                        else:
                            other_msg_count += 1
                            if isinstance(msg, messages.JobStartMessage):
                                computation_id = msg.handle

                            # Check for SIM Limit reached message
                            msg_code = None
                            if msg.message:
                                msg_code = msg.message.get('messageCode', None)
                            is_info_msg = isinstance(msg, messages.InfoMessage)
                            is_limit_code = msg_code == self.SIM_FLOW_LIMIT_MSG_CODE
                            if is_info_msg and msg.message and is_limit_code:
                                self.logger.error(
                                    'status=error, error_code=limit_reached, '
                                    'error_msg=SignalFlow Program reached metadata message limit '
                                    'of {0}., action=stream_sim_flow_program_results, '
                                    'instance_name={1}, org_id={2}, thread_id={3}, '
                                    'signalflow_program="{4}", computation_id={5}, '
                                    'message_type={6}, message={7}, metadata_msg_count={8}, '
                                    'data_msg_count={9}, mts_count={10}, other_msg_count={11}, '
                                    'retry_count={12}'.format(
                                        str(metadata_msg_count), self.mod_input_instance_name,
                                        self.org_id, thread_id, signalflow_program,
                                        computation_id, message_type, json.dumps(msg.__dict__),
                                        str(metadata_msg_count), str(data_msg_count),
                                        str(mts_count), str(other_msg_count), str(retry_count)
                                    )
                                )
                            else:
                                self.logger.info(
                                    'status=running, action=stream_sim_flow_program_results, '
                                    'instance_name={0}, org_id={1}, thread_id={2}, '
                                    'signalflow_program="{3}", computation_id={4}, '
                                    'message_type={5}, message={6}, metadata_msg_count={7}, '
                                    'data_msg_count={8}, mts_count={9}, other_msg_count={10}, '
                                    'retry_count={11}'.format(
                                        self.mod_input_instance_name, self.org_id, thread_id,
                                        signalflow_program, computation_id, message_type,
                                        json.dumps(msg.__dict__), str(metadata_msg_count),
                                        str(data_msg_count), str(mts_count), str(other_msg_count),
                                        str(retry_count)
                                    )
                                )

                        if events:
                            self.writer.write_events(events)

                    except Exception as e:
                        process_results_error_count += 1
                        self.logger.error(
                            'status=error, action=stream_sim_flow_program_results, '
                            'instance_name={0}, org_id={1}, thread_id={2}, error_msg={3}, '
                            'computation_id={4}, message_type={5}, metadata_msg_count={6}, '
                            'data_msg_count={7}, mts_count={8}, other_msg_count={9}, '
                            'retry_count={10}, process_results_error_count={11}'.format(
                                self.mod_input_instance_name, self.org_id, thread_id, str(e),
                                computation_id, message_type, str(metadata_msg_count),
                                str(data_msg_count), str(mts_count), str(other_msg_count),
                                str(retry_count), str(process_results_error_count)
                            ),
                            exc_info=True
                        )
                        if process_results_error_count >= self.sim_mod_input_retry_count:
                            break

                self.logger.info(
                    'status=complete, action=stream_sim_flow_program_results, instance_name={0}, '
                    'org_id={1}, thread_id={2}, computation_id={3}, metadata_msg_count={4}, '
                    'data_msg_count={5}, mts_count={6}, other_msg_count={7}, '
                    'retry_count={8}'.format(
                        self.mod_input_instance_name, self.org_id, thread_id, computation_id,
                        str(metadata_msg_count), str(data_msg_count), str(mts_count),
                        str(other_msg_count), str(retry_count)
                    )
                )
                # EXIT THE RETRY LOOP
                break

            except Exception as e:
                self.logger.error(
                    'status=error, action=run_signalflow_program, instance_name={0}, org_id={1}, '
                    'thread_id={2}, retry_count={3}, error_msg={4}'.format(
                        self.mod_input_instance_name, self.org_id, thread_id,
                        str(retry_count), str(e)
                    ),
                    exc_info=True
                )
                retry_count += 1
                # TODO: wait x sec. before retry.
                time.sleep(self.sim_mod_input_retry_wait_time * retry_count)
                self.logger.info(
                    'status=retry, action=run_signalflow_program, thread_id={0}, org_id={1}, '
                    'retry_count={2}'.format(thread_id, self.org_id, str(retry_count))
                )

        if sim_flow_client is not None:
            sim_flow_client.close()
            self.logger.info(
                'status=complete, action=close_sim_flow_client, thread_id={0}, org_id={1}, '
                'retry_count={2}'.format(thread_id, self.org_id, str(retry_count))
            )
        # Need to stop the watchdog_bark function which is running in separate thread,
        # else this run_signalflow_program function will not exit normally.
        self.break_watchdog = True
        flag = self.stop_mod_input_when_one_computation_fails_flag
        self.stop_mod_input_when_one_computation_fails = flag or self.stop_mod_input_when_one_computation_fails
        self.logger.info(
            'status=complete, action=run_signalflow_program, thread_id={0}, org_id={1}, '
            'retry_count={2}'.format(thread_id, self.org_id, str(retry_count))
        )

    def modularinput_collection_data(self, request_type, query_params=None, modinput_data=None):
        """
        This function is responsible for making any REST calls to the sim_modular_inputs
        collection
        """
        import requests
        headers = {
            'Authorization': 'Splunk {}'.format(self.session_key),
            'Content-Type': 'application/json'
        }
        host_url = self.SPLUNK_MODULARINPUT_COLLECTION.format(self.server_port)
        try:
            if request_type == 'GET':
                if query_params:
                    host_url = host_url + '?query={}'.format(json.dumps(query_params))
                response = requests.get(
                    host_url,
                    headers=headers,
                    verify=False
                )
                return response
            elif request_type == 'DELETE':
                if query_params:
                    host_url = host_url + '?query={}'.format(json.dumps(query_params))
                response = requests.delete(
                    host_url,
                    headers=headers,
                    verify=False
                )
            else:
                if query_params:
                    host_url = host_url + "/" + str(query_params)
                response = requests.post(
                    host_url,
                    json=modinput_data,
                    headers=headers,
                    verify=False
                )
                return response
        except Exception as e:
            self.logger.error(
                'status=error, action={0} error_msg={1}'.format(request_type, str(e)),
                exc_info=True
            )

    def get_modular_input_data(self):
        """
        This function is responsible for making any REST calls to Splunk Infrastructure
        Monitoring Data Streams page.
        """
        import requests
        try:
            headers = {
                'Authorization': 'Splunk {}'.format(self.session_key),
                'Content-Type': 'application/json'
            }

            host_url = self.SPLUNK_MODULARINPUT_URL.format(self.server_port)
            self.logger.info('Getting all splunk modular inputs: {}'.format(host_url))
            response = requests.get(
                host_url,
                headers=headers,
                verify=False
            )
            return response
        except Exception as e:
            self.logger.error(
                'status=error, Error while accessing modularinput page, error_msg={}'.format(
                    str(e)
                ),
                exc_info=True
            )

    #########################################################################
    # Common Functions ######################################################
    #########################################################################

    class LoggerContextFilter(logging.Filter):
        """
        This is a filter which injects command invocation instance UUID in the logs.
        """
        request_id = uuid.uuid4().hex

        def filter(self, record):
            record.request_id = self.request_id
            return True

    # This function does the cleanup of disabled and stale timestamps of modular inputs
    # which are stored in collection - sim_modularinputs
    def cleanup_timestamps_of_stale_modinputs(self):
        self.logger.info(
            'Starting the cleanup of stale modularinputs from sim_modularinputs collection'
        )
        try:
            response = self.modularinput_collection_data(request_type="GET")
            if not json.loads(response.content):
                self.logger.info('There are no modular input timestamps to clear')
                return

            timestamp_modinput_set = set()
            for mod_input in response.json():
                timestamp_modinput_set.add(mod_input.get("title"))

            response = self.get_modular_input_data()

            # Below for loop will Remove all the active sim_modularinputs from the set
            # timestamp_modinput_set
            for mod_input in response.json().get("entry"):
                if mod_input.get("content").get("disabled") is False:
                    self.logger.info(
                        'Removing modular input: {} from set'.format(mod_input.get("name"))
                    )
                    modinput_name = mod_input.get("name")
                    if modinput_name in timestamp_modinput_set:
                        timestamp_modinput_set.remove(modinput_name)

            if not timestamp_modinput_set:
                self.logger.info('There are no modular input timestamps to clear')
                return

            self.logger.info('Modular inputs to be deleted: {}'.format(timestamp_modinput_set))

            # Query to form for delete - query={"$or": [{"title":"MOD_INPUT1"},{"title":"MOD"}]}
            modinputs_to_delete = []
            for mod in timestamp_modinput_set:
                query = {}
                query['title'] = mod
                modinputs_to_delete.append(query)
            final_query = {}
            final_query['$or'] = modinputs_to_delete
            self.modularinput_collection_data(request_type="DELETE", query_params=final_query)
            self.logger.info(
                'Cleanup of modular inputs {} completed successfully.'.format(
                    timestamp_modinput_set
                )
            )

        except Exception as e:
            self.logger.error(
                'status=error, action=cleanup_timestamps_of_stale_modinputs, '
                'error_msg={}'.format(str(e)),
                exc_info=True
            )

    def get_event_writer(self):
        """This method returns event writer based on stack type.
        If the stack is Classic or on-prem, it returns an object of HECEventWriter.
        If the stack is Noah, it returns an object of NoahHECEventWriter.

        Returns:
            obj: Returns event writer object.
        """
        self._stack_info = stack_info.StackInfo(self.session_key)
        if self._stack_info.is_noah_stack:
            self.logger.debug('Detected Noah Stack. Creating NoahHECEventWriter.')
            hec_input_name = ":".join([self.app, self.hec_input_name])
            return noah_event_writer.NoahHECEventWriter(hec_input_name, self.session_key)
        self.logger.debug('Detected Non-Noah Stack. Creating HECEventWriter.')
        return self.event_writer


if __name__ == "__main__":
    worker = SIMModularInput()
    worker.execute()
