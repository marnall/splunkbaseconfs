#!/usr/bin/env python
# Copyright (C) 2015-2019 Splunk Inc. All Rights Reserved.
from exec_anaconda import exec_anaconda_or_die

exec_anaconda_or_die()

import os
import conf

from util.param_util import is_truthy, parse_args, convert_params
from util.telemetry_util import (
    log_uuid,
    log_fit_time,
    log_app_details,
    log_partial_fit,
    Timer,
    log_fit_container_time,
)
from util import command_util
from util.dsdl_container_loader import ContainerConf

import cexc
from chunked_controller import ChunkedController
from cexc import BaseChunkHandler, CommandType
from ai_commander.ai_commander_util import AICommanderUtil
from dsdl.docker_util import read_container_hpa_enabled

logger = cexc.get_logger('fit')
messages = cexc.get_messages_logger()


class FitCommand(cexc.BaseChunkHandler):
    """FitCommand uses ChunkedController & one of two processors to fit models.

    The FitCommand can use either the FitBatchProcessor or the FitPartialProcessor,
    which is chosen based on the presence of the partial_fit parameter.
    """

    @staticmethod
    def handle_arguments(getinfo):
        """Take the getinfo metadata and return controller_options.

        Args:
            getinfo (dict): getinfo metadata from first chunk

        Returns:
            controller_options (dict): options to be passed to controller
            partial_fit (bool): boolean flag to indicate partial fit
        """
        if len(getinfo['searchinfo']['raw_args']) == 0:
            raise RuntimeError('First argument must be an "algorithm"')

        raw_options = parse_args(getinfo['searchinfo']['raw_args'][1:])
        controller_options, partial_fit = FitCommand.handle_raw_options(raw_options)
        controller_options['algo_name'] = getinfo['searchinfo']['args'][0]
        log_app_details(getinfo['searchinfo'].get('app'))
        return controller_options, partial_fit

    @staticmethod
    def handle_raw_options(controller_options):
        """Load command specific options.

        Args:
            controller_options (dict): options from handle_arguments
        Returns:
            controller_options (dict): dict of controller options
            partial_fit (dict): boolean flag for partial fit
        """
        controller_options['processor'] = 'FitBatchProcessor'
        partial_fit = False

        if 'params' in controller_options:
            try:
                fit_params = convert_params(
                    params=controller_options['params'],
                    ignore_extra=True,
                    bools=['apply', 'partial_fit'],
                )
            except ValueError as e:
                raise RuntimeError(str(e))

            if 'apply' in fit_params:
                controller_options['apply'] = fit_params['apply']
                del controller_options['params']['apply']

                if 'model_name' not in controller_options and not fit_params['apply']:
                    raise RuntimeError('You must save a model if you are not applying it.')

            if 'partial_fit' in fit_params:
                partial_fit = fit_params['partial_fit']
                del controller_options['params']['partial_fit']

        if partial_fit:
            log_partial_fit()
            controller_options['processor'] = 'FitPartialProcessor'

        return controller_options, partial_fit

    def _setup_watchdog(self):
        """Initialize and start watchdog"""
        self.watchdog = command_util.get_watchdog(
            self.controller.resource_limits['max_fit_time'],
            self.controller.resource_limits['max_memory_usage_mb'],
            os.path.join(self.getinfo['searchinfo']['dispatch_dir'], 'finalize'),
        )
        self.watchdog.start()

    def setup(self):
        """Get options, start controller and return command type.

        Returns:
            (dict): get info response (command type) and required fields
        """
        self.controller_options, self.partial_fit = self.handle_arguments(self.getinfo)
        # Initialize container telemetry holder; populated only for AITKContainer
        self._fit_container_telemetry = None
        if self.controller_options.get('algo_name') == 'AITKContainer':
            hpa_enabled = 0
            container_id = None
            cluster_type = None
            auth_mode = None
            min_replicas = None
            max_replicas = None
            min_cpu = None
            max_cpu = None
            min_memory = None
            max_memory = None
            try:
                searchinfo = self.getinfo['searchinfo']
                logger.debug("The search info in fit is: {}".format(searchinfo))
                model_name = self.controller_options.get(
                    'model_name'
                ) or self.controller_options.get('model')
                logger.debug("The model name in fit is: {}".format(model_name))
                # Determine which stanza to use for container metadata
                stanza_name = model_name if model_name else "__dev__"
                if model_name:
                    logger.debug("The model name in fit is: {}".format(model_name))
                    hpa_enabled = 1 if read_container_hpa_enabled(searchinfo, model_name) else 0
                    logger.debug("The hpa enabled in fit is: {}".format(hpa_enabled))
                try:
                    container_conf = ContainerConf(searchinfo, "dsdl_container")
                    stanza = container_conf.get_stanza(stanza_name)
                    # If the specific model stanza is missing, fall back to __dev__
                    if not stanza and stanza_name != "__dev__":
                        stanza = container_conf.get_stanza("__dev__")
                    if stanza:
                        container_id = (stanza.get("id") or "").strip()
                        logger.debug("The container id in fit is: {}".format(container_id))
                        cluster_type = (stanza.get("cluster") or "").strip()
                        logger.debug("The cluster type in fit is: {}".format(cluster_type))
                        # If the cluster type is kubernetes, also read auth_mode from container_connections
                        if cluster_type and cluster_type.lower() == "kubernetes":
                            try:
                                conn_conf = ContainerConf(searchinfo, "container_connections")
                                conn_stanza = conn_conf.get_stanza(cluster_type)
                                if conn_stanza:
                                    auth_mode = (conn_stanza.get("auth_mode") or "").strip()
                                    logger.debug(
                                        "The auth_mode in fit is: {}".format(auth_mode)
                                    )
                            except Exception:
                                logger.debug(
                                    "Unable to read auth_mode from container_connections for cluster_type %s",
                                    cluster_type,
                                )
                        # When HPA is enabled, also capture min/max replicas and cpu_threshold from dsdl_container
                        if hpa_enabled:
                            min_replicas = (stanza.get("min_replicas") or "").strip()
                            max_replicas = (stanza.get("max_replicas") or "").strip()
                            logger.debug(
                                "The HPA settings in fit are: min_replicas=%s, max_replicas=%s, cpu_threshold=%s",
                                min_replicas,
                                max_replicas,
                            )
                        # Always capture CPU and memory limits from dsdl_container when present
                        min_cpu = (stanza.get("min_cpu") or "").strip()
                        max_cpu = (stanza.get("max_cpu") or "").strip()
                        min_memory = (stanza.get("min_memory") or "").strip()
                        max_memory = (stanza.get("max_memory") or "").strip()
                        logger.debug(
                            "The resource limits in fit are: min_cpu=%s, max_cpu=%s, min_memory=%s, max_memory=%s",
                            min_cpu,
                            max_cpu,
                            min_memory,
                            max_memory,
                        )
                except Exception:
                    logger.debug(
                        "Unable to read container metadata from dsdl_container.conf for stanza %s",
                        stanza_name,
                    )
            except Exception:
                pass
            # Store telemetry details to be logged after the fit is complete
            self._fit_container_telemetry = {
                'hpa_enabled': hpa_enabled,
                'container_id': container_id,
                'cluster_type': cluster_type,
                'auth_mode': auth_mode,
                'min_replicas': min_replicas,
                'max_replicas': max_replicas,
                'min_cpu': min_cpu,
                'max_cpu': max_cpu,
                'min_memory': min_memory,
                'max_memory': max_memory,
            }
            is_user_eligible = AICommanderUtil(
                searchinfo=self.getinfo['searchinfo']
            ).check_user_role_eligibility(required_capabilities=['fit_mltkcontainer'])
            if not is_user_eligible:
                raise RuntimeError(
                    'User does not have permission to run fit for AITKContainer.'
                )
        self.controller = ChunkedController(self.getinfo, self.controller_options)
        required_fields = self.controller.get_required_fields()
        return {'type': CommandType.EVENTS, 'required_fields': required_fields}

    def get_output_body(self):
        """Collect output body from controller.

        Returns:
            (str): body
        """
        return self.controller.output_results()

    def handler(self, metadata, body):
        """Main handler we override from BaseChunkHandler.

        Args:
            metadata (dict): metadata information
            body (str): data payload from CEXC

        Returns:
            (dict): metadata to be sent back to CEXC
            output_body (str): data payload to be sent back to CEXC
        """
        if command_util.should_early_return(metadata):
            return {'type': CommandType.EVENTS}

        if command_util.is_getinfo_chunk(metadata):
            return self.setup()

        if self.getinfo.get('preview', False):
            logger.debug('Not running in preview.')
            return {'finished': True}

        if not self.watchdog:
            self._setup_watchdog()

        finished_flag = metadata.get('finished', False)

        self.controller.load_data(body)

        # Partial fit should *always* execute on every chunk.
        # Non partial fit will execute on the last chunk.
        if self.partial_fit or finished_flag:
            self.controller.execute()
            output_body = self.get_output_body()
        else:
            output_body = None

        if finished_flag:
            self.controller.finalize()
            # Gracefully terminate watchdog
            if self.watchdog.started:
                self.watchdog.join()

        # Log container-related fit telemetry (including CSV size) once the search is finished
        if finished_flag and getattr(self, '_fit_container_telemetry', None):
            csv_size = getattr(self.controller, '_csv_input_bytes', None)
            t = self._fit_container_telemetry
            model_name = self.controller_options.get(
                'model_name'
            ) or self.controller_options.get('model')
            # Get the full algo_name from controller (e.g., AITKContainer.binary_nn_classifier) instead of base algo_name
            full_algo_name = getattr(
                self.controller, 'algo_name', None
            ) or self.controller_options.get('algo_name')
            log_fit_container_time(
                0.0,
                t.get('hpa_enabled', 0),
                full_algo_name,
                t.get('container_id'),
                t.get('cluster_type'),
                t.get('auth_mode'),
                t.get('min_replicas'),
                t.get('max_replicas'),
                t.get('min_cpu'),
                t.get('max_cpu'),
                t.get('min_memory'),
                t.get('max_memory'),
                csv_size,
                model_name,
            )

        # Our final farewell
        self.log_performance_timers()
        return ({'finished': finished_flag}, output_body)

    def log_performance_timers(self):
        logger.debug(
            "read_time=%f, handle_time=%f, write_time=%f, "
            "csv_parse_time=%f, csv_render_time=%f"
            % (
                self._read_time,
                self._handle_time,
                self._write_time,
                self.controller._csv_parse_time,
                self.controller._csv_render_time,
            )
        )


if __name__ == "__main__":
    logger.debug("Starting fit.py.")
    do_profile = is_truthy(conf.get_mlspl_prop('profile', 'default', 'n'))

    if do_profile:
        import cProfile
        import pstats

        pr = cProfile.Profile()
        pr.enable()

    with Timer() as t:
        FitCommand(handler_data=BaseChunkHandler.DATA_RAW).run()

    if do_profile:
        from io import StringIO

        pr.disable()
        s = StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats(10)
        ps = pstats.Stats(pr, stream=s).sort_stats('time')
        ps.print_stats(10)
        logger.info("PROFILE: %s", s.getvalue())

    log_uuid()
    log_fit_time(t.interval)
    logger.debug("Exiting gracefully. Byee!!")
