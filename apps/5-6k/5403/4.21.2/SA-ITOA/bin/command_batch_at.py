#!/usr/bin/env python

# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
import sys
import time
import logging
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
from ITOA.setup_logging import setup_logging
from ITOA.itoa_common import is_feature_enabled
from itsi.objects.itsi_at_incremental_values import ItsiAtIncrementalValues
from itsi.objects.itsi_kpi_entity_threshold import ItsiKpiEntityThreshold
from itsi.objects.itsi_kpi_at_info import ItsiKpiAtInfo
from itsi.objects.itsi_service import ItsiService
from SA_ITOA_app_common.solnlib.conf_manager import ConfManager
from SA_ITOA_app_common.splunklib.binding import HTTPError
from SA_ITOA_app_common.splunklib.results import ResultsReader
from SA_ITOA_app_common.splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from at_utils.utils import divide_into_batches, generate_at_search, generate_entity_at_search, AT_SCALE_DOWN_FACTORS

logger = setup_logging("itsi_batch_at_command.log", "itsi.batchat.command", level=logging.INFO)


@Configuration()
class BatchAtCommand(StreamingCommand):
    """
    BatchAtCommand is a StreamingCommand custom search command that will batch adaptive thresholding searches into
    smaller subsearches.

    itsibatchat will process a list of KPI IDs indentified by 'itsi_kpi_id', group them by batch_size specified
    in itsi_settings.conf and scaled down to the option set for training window. Results of the subsearches will be
    passed through as the results of this command.
    """
    training_window = Option(
        doc="Training window to use for the adaptive thresholding search. Options are -7d, -14d, -30d, or -60d",
        require=False,
        default='-7d'
    )
    entitylevelthreshold = Option(
        doc="Run batchat with entity level AT",
        require=False,
        default=False
    )
    getcollectiondata = Option(
        doc="Get data from collection rather if data not available as records",
        require=False,
        default=False
    )
    log_level = Option(
        doc="Log Level for itsibatchat command",
        require=False,
        default="INFO"
    )
    kpi_level_batch_size = 1000
    entity_level_batch_size = 500
    max_wait_time = 3600
    kpi_id_key = 'kpi_id'
    batches = []
    incremental_values_enabled = False

    def get_batch_settings(self):
        """
        Fetches batch size and timeout from itsi_settings.conf
        """
        try:
            cfm = ConfManager(self.service.token, 'SA-ITOA')
            conf = cfm.get_conf('itsi_settings')
            apply_at_settings = conf.get('applyat')
            batch_size_key = 'kpi_level_batch_size'
            default_batch_size = self.kpi_level_batch_size
            if self.entitylevelthreshold:
                batch_size_key = 'entity_level_batch_size'
                default_batch_size = self.entity_level_batch_size
            self.batch_size = int(
                int(apply_at_settings.get(batch_size_key, default_batch_size)) / AT_SCALE_DOWN_FACTORS[self.training_window]
            )
            self.max_wait_time = int(apply_at_settings.get('batch_timeout', 3600))
        # pylint:disable=broad-exception-caught
        except Exception as e:
            logger.exception(e)
            logger.error(
                'Failed to fetch batch settings for adaptive thresholding, '
                'using default value of 1000 for batch_size and 3600 for batch_timeout.')

    def run_search(self, search, use_incremental_method=False):
        """
        Runs the search command

        @type: str
        @param search: the search to run

        @type: boolean
        @param use_incremental_method: flag indicating if incremental method is being applied
        """
        try:
            earliest_time = '-1d@d' if use_incremental_method else self.training_window + '@d'
            search_job = self.service.jobs.create(
                search, earliest_time=earliest_time, latest_time='@d'
            )
            logger.info(
                f'Created adaptive thresholding search job with earliest_time={earliest_time} and '
                f'latest_time=@d with incremental mode {"enabled" if use_incremental_method else "disabled"}'
            )
        except HTTPError as e:
            raise Exception(
                f'Error when running adaptive thresholding search "{search}". Error: {e}'
            )
        return search_job

    def wait_for_job(self, searchjob, maxtime=-1):
        """
        Wait up to maxtime seconds for searchjob to finish.  If maxtime is
        negative (default), waits forever.  Returns true, if job finished.

        @type: splunklib.client.Job
        @param searchjob: the search job to wait on

        @type: int
        @param maxtime: the amount to time to wait
        """
        pause = 0.2
        lapsed = 0.0
        while not searchjob.is_done():
            time.sleep(pause)
            lapsed += pause
            if maxtime >= 0 and lapsed > maxtime:
                break
        return searchjob.is_done()

    def setup(self):
        """
        Setup required for batching adaptive thresholding searches
        """
        if self.training_window not in ['-7d', '-14d', '-30d', '-60d']:
            raise Exception("Invalid option for training window.")
        self.get_batch_settings()
        self.incremental_values_enabled = is_feature_enabled('itsi-at-incremental-learning', self.service.token)
        logger.debug(
            f'Setup for batching adaptive thresholding searches: {{training window:'
            f'{self.training_window}, batch_size: {self.batch_size}, batch_timeout: {self.max_wait_time}}}.'
        )
        if ( self.service.username == ''):
            self.service.username = 'nobody'

    def fetch_records(self):
        """
        Fetch KPI or Entity records from collection for objects having AT enabled and matches training window
        """
        if self.entitylevelthreshold:
            return ItsiKpiEntityThreshold(self.service.token, self.service.username).get_bulk("nobody", filter_data={
                "adaptive_thresholds_is_enabled": True,
                "adaptive_thresholding_training_window": self.training_window
            }, fields=["kpi_id", "_key", "entity_key", "entity_title", "time_variate_thresholds_specification"])
        self.kpi_id_key = '_key'
        return ItsiKpiAtInfo(self.service.token, self.service.username).get_bulk("nobody", filter_data={
            "adaptive_thresholding_training_window": self.training_window
        }, fields=["_key", "adaptive_thresholding_training_window"])

    def fetch_incremental_values(self, records):
        """
        Fetch incremental values from collection to compare against records
        """
        if self.getcollectiondata or self.entitylevelthreshold:
            _keys = [record['_key'] for record in records]
        else:
            _keys = [record['kpi_id'] for record in records]
        key_filter = {"$or" : [{"_key": key} for key in _keys]}
        at_inc_val_int = ItsiAtIncrementalValues(self.service.token, self.service.username)
        return at_inc_val_int.get_bulk('nobody', filter_data=key_filter)

    def validate_incremental_method(self, record, incremental_values):
        """
        Processes the ids into the batched searches needed to run adaptive
        thresholding accounting for incremental values validation

        @type: dict
        @param record: the kpi record to validate

        @type: list
        @param incremental_values: incremental values collection

        @rtype: bool
        @return: boolean set to true if incremental method is valid for the record
        """
        def compare_values(key, prop, incr_policy, kpi_policy):
            incr_get = incr_policy.get(key, None)
            kpi_policy_get = kpi_policy.get(key, None)
            if incr_get and kpi_policy_get:
                if incr_policy.get(key).get(prop, None) is not None and kpi_policy.get(key).get(prop, None) is not None:
                    if incr_policy.get(key).get(prop) == kpi_policy.get(key).get(prop):
                        return True
            logger.info(f'{prop} field does not match between incremental values ({incr_get}) and kpi ({kpi_policy_get}) for {key}')
            return False

        def compare_dynamic_params(key, incr_policy, kpi_policy, is_aggregate=True):
            incr_get = incr_policy.get(key, None)
            kpi_policy_get = kpi_policy.get(key, None)
            if not incr_get or not kpi_policy_get:
                logger.info(f'Could not find policy {key} in incremental or kpi policies')
                return False
            threshold_type = 'aggregate_thresholds' if is_aggregate else 'entity_thresholds'
            if not incr_policy.get(key).get('dynamic_params', None) or not kpi_policy.get(key).get(threshold_type, None):
                logger.info(f'Could not find dynamic params for policy {key} in incremental or kpi policies')
                return False
            kpi_threshold_levels = sorted(kpi_policy.get(key).get(threshold_type).get('thresholdLevels'), key=lambda x: x['dynamicParam'])
            incr_dynamic_params = sorted(incr_policy.get(key).get('dynamic_params'), key=lambda x: x['dynamicParam'])
            if len(kpi_threshold_levels) != len(incr_dynamic_params):
                logger.info(f'Number of dynamic params do not match for {key} in incremental and kpi policies')
                return False
            for i in range(len(kpi_threshold_levels)):
                if kpi_threshold_levels[i]['severityValue'] != incr_dynamic_params[i]['severityValue'] or \
                        kpi_threshold_levels[i]['dynamicParam'] != incr_dynamic_params[i]['dynamicParam']:
                    logger.info(f'Dynamic param values do not match for {key} in incremental and kpi policies')
                    return False
            return True

        def compare_at_settings(key, obj, incremental_value):
            if obj.get('aggregate_outlier_detection_enabled') != incremental_value.get('aggregate_outlier_detection_enabled'):
                logger.info(f'Outlier detection enabled state does not match the incremental values for {key}.')
                return False
            elif obj.get('adaptive_thresholding_training_window') != incremental_value.get('adaptive_thresholding_training_window'):
                logger.info(f'Adaptive thresholding training window does not match the incremental values for {key}.')
                return False
            elif incremental_value.get('aggregate_outlier_detection_enabled') and \
                    (obj.get('outlier_detection_algo') != incremental_value.get('outlier_detection_algo')
                        or obj.get('outlier_detection_sensitivity') != incremental_value.get('outlier_detection_sensitivity')):
                logger.info(f'Outlier detection settings do not match the incremental values for {key}.')
                return False
            return True
        if self.getcollectiondata or self.entitylevelthreshold:
            _key = record['_key']
        else:
            _key = record['kpi_id']
        for incr_val in incremental_values:
            if incr_val.get('_key') == _key:
                time_variate_thresholds_specification = None
                if self.entitylevelthreshold:
                    try:
                        kpi_entity_threshold = ItsiKpiEntityThreshold(self.service.token, self.service.username).get('nobody', record['_key'])
                        if not compare_at_settings(_key, kpi_entity_threshold, incr_val):
                            return False
                        time_variate_thresholds_specification = kpi_entity_threshold.get('time_variate_thresholds_specification', None)
                    except Exception as e:
                        logger.error(e)
                else:
                    itsi_service_int = ItsiService(self.service.token, self.service.username)
                    try:
                        kpi = itsi_service_int.get_kpi('nobody', _key)
                        if not compare_at_settings(_key, kpi, incr_val):
                            return False
                        time_variate_thresholds_specification = kpi.get('time_variate_thresholds_specification', None)
                    except Exception as e:
                        logger.error(e)
                if time_variate_thresholds_specification:
                    time_policies = time_variate_thresholds_specification.get('policies')
                    kpi_policies = {key: time_policies.get(key) for key in time_policies if time_policies.get(key).get('policy_type') != 'static'}
                    incr_val_policies = incr_val.get('policies', {})
                    if len(incr_val_policies.keys()) != len(kpi_policies.keys()):
                        incr_size = len(incr_val_policies.keys())
                        kpi_policy_size = len(kpi_policies.keys())
                        logger.info(f'Number of non-static policies for incremental ({incr_size}) and kpi ({kpi_policy_size}) do not match for {_key}.')
                        return False
                    for policy_id in kpi_policies.keys():
                        if not compare_values(policy_id, 'policy_type', incr_val_policies, kpi_policies) or \
                                not compare_values(policy_id, 'time_blocks', incr_val_policies, kpi_policies) or \
                                not compare_dynamic_params(policy_id, incr_val_policies, kpi_policies, not self.entitylevelthreshold):
                            # Return false at the first instance of discrepancy
                            return False

                    # All comparison was True return True
                    return True
        logger.info(f'Incremental values not found for {_key}. New incremental values will be generated during applyat search.')
        return False

    def pre_processing(self, records):
        """
        Processes the ids into the batched searches needed to run adaptive
        thresholding accounting for incremental values validation

        @type: generator
        @param records: the data passed in to custom search command
        """
        if self.incremental_values_enabled:
            invalidated_records = []
            validated_records = []
            incremental_values = self.fetch_incremental_values(records)
            for record in records:
                is_validated = self.validate_incremental_method(record, incremental_values)
                if is_validated:
                    validated_records.append(record)
                else:
                    invalidated_records.append(record)
            logger.info(f'Validated record size {len(validated_records)}, invalidated record size {len(invalidated_records)}')
            invalidated_batches = list(divide_into_batches(invalidated_records, self.batch_size))
            validated_batches = list(divide_into_batches(validated_records, self.batch_size, True))
            self.batches = invalidated_batches + validated_batches
        else:
            self.batches = list(divide_into_batches(records, self.batch_size))

    def stream(self, records):
        """
        Configures batch size, groups KPI IDs by batch size, then runs applyat sub-searches for each batch.
        Results of the sub-searches will be passed through to outer search.

        Note: Splunk will send in the KPI IDs in batches of 50,000
        Refer to docs for more details https://docs.splunk.com/DocumentationStatic/PythonSDK/1.6.5/searchcommands.html

        @type: generator
        @param records: the results passed in to the search command
        """
        logger.info(f"Setting up itsibatchat command log level to {self.log_level}")
        logger.setLevel(self.log_level)
        logger.info(f'Begin batching adaptive thresholding applyat searches for {"entities" if self.entitylevelthreshold else "kpis"} of training window {self.training_window}')
        self.setup()
        objects = list(records)
        # Fetch data from collection if command has been used without inputlookup command to stream data
        if not objects and self.getcollectiondata:
            objects = self.fetch_records()
        if len(objects) == 0:
            logger.info("No records to process")
            return
        self.pre_processing(objects)
        batch_num = 1
        for batch, use_incremental_method in self.batches:
            if self.entitylevelthreshold:
                search = generate_entity_at_search(batch, use_incremental_method, self.log_level)
            else:
                kpi_ids = [i[self.kpi_id_key] for i in batch]
                search = generate_at_search(kpi_ids, use_incremental_method, self.log_level)
            search_job = None
            if not search:
                raise Exception("Cannot get AT search from objects list")
            try:
                logger.info(
                    f'Begin adaptive thresholding applyat search for batch {batch_num} out of {len(self.batches)}.'
                )
                start_time = time.time()
                search_job = self.run_search(search, use_incremental_method)
                is_done = self.wait_for_job(search_job, self.max_wait_time)
                end_time = time.time()
                if is_done:
                    logger.info(
                        f'Completed adaptive thresholding applyat search for batch {batch_num} out of '
                        f'{len(self.batches)} which took {end_time - start_time} seconds.'
                    )
                else:
                    logger.error(
                        f'Timed out adaptive Thresholding with search id {search_job.name} '
                        f'for {batch_num} out of {len(self.batches)}.'
                    )
            except Exception as e:
                logger.exception(e)
                if search_job:
                    logger.error(
                        f'Batched adaptive thresholding search with search id {search_job.name} failed to run '
                        f'for {batch_num} out of {len(self.batches)}.'
                    )
                else:
                    logger.error(
                        'Failed to create batched adaptive thresholding search '
                        f'for {batch_num} out of {len(self.batches)}.'
                    )
            if search_job:
                rr = ResultsReader(search_job.results())
                # pass through the results of the sub searches
                for result in rr:
                    if isinstance(result, dict):
                        yield result
            batch_num += 1
        logger.info(f'Completed batching adaptive thresholding applyat searches for {batch_num - 1} batches of {"entities" if self.entitylevelthreshold else "kpis"}')


dispatch(BatchAtCommand, sys.argv, sys.stdin, sys.stdout, __name__)
