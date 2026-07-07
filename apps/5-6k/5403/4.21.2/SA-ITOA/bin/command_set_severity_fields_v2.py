#!/usr/bin/env python

# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import time

from splunk.util import normalizeBoolean
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from ITOA.setup_logging import logger
from ITOA.itoa_common import is_string_numeric
from itsi.set_severity_fields import SetSeverityFields, CollectKpiInfo
from ITOA.event_management.notable_event_kpi_alert import NotableEventKPIAlert
from itsi.objects.itsi_kpi_state_cache import ItsiKPIStateCache
from SA_ITOA_app_common.splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option, validators


@Configuration()
class SetSeverityFieldsCommand(EventingCommand):

    serviceid = Option(
        doc=''' "serviceID" and "kpiID" are required
        ''')

    kpiid = Option(
        doc=''' "serviceID" and "kpiID" are required
        ''')

    kpibasesearch = Option(
        doc=''' "kpibasesearch" is required
        ''')

    handle_no_data = Option(
        doc=''' Flag to avoid no data scenario and max event generation
        ''',
        validate=validators.Boolean())

    generate_max_severity_event = Option(
        validate=validators.Boolean())

    fill_data_gaps = Option(
        doc='''Flag to fill in data gaps (N/A values) for KPI with a custom value or last non-N/A value,
        as per the option selected by user while configuring KPI
        ''',
        validate=validators.Boolean())

    output_secgrp = Option(
        validate=validators.Boolean())

    is_time_series = Option(
        doc='''Flag which tells, if the events being injected to the command are time-series (backfill case) or not.
        ''',
        validate=validators.Boolean())

    is_service_max_severity_event_field = 'is_service_max_severity_event'
    is_service_aggregate_field = 'is_service_aggregate'
    is_fill_data_gap_field = 'is_filled_gap_event'
    is_custom_threshold_event_field = 'is_custom_threshold_event'

    def setup(self):

        self.validate_search_args()

        self.session_key = self.metadata.searchinfo.session_key

        # TODO at some point refactor identification of fields to add to the result set
        # Its currently littered and saved in addition to being split into fields_to_add and new_fieldnames
        self.fields_to_add = ['alert_severity', 'alert_color', 'alert_level', 'kpiid', 'serviceid']
        self.new_fieldnames = [
            'alert_value',
            'alert_error',
            'kpi',
            'alert_period',
            'urgency',
            'kpibasesearch',
            'is_service_in_maintenance',
            'is_all_entities_in_maintenance',
            'is_entity_in_maintenance'
        ]

        # kpiid
        self.kpibasesearchid = self.kpibasesearch

        self.output_secgrp = normalizeBoolean(self.output_secgrp if self.output_secgrp else False)

        # Flag which tells, if the events being injected to the command are time-series (backfill case) or not.
        # NOTE: It is necessary to pass time-series events (example, backfill) in sorted
        # format (by _time) to the set_severity_fields command, for the command to correctly
        # generate max severity event for each timestamp.
        self.is_time_series = normalizeBoolean(self.is_time_series if self.is_time_series else False)
        default_no_data_max_event = False

        default_fill_data_gap = False
        if self.kpibasesearchid is not None:
            logger.info('Initialized setseverityfield with serviceid=%s kpiid=%s', self.serviceid, self.kpiid)
            default_no_data_max_event = True
            self.fields_to_add.append('kpibasesearch')
            default_fill_data_gap = True
            # we do not support generation of max severity events for time-series events from shared base search.
            self.is_time_series = False
        else:
            logger.info('Initialized setseverityfield with kpibasesearchid=%s', self.kpibasesearchid)

        if self.output_secgrp:
            self.fields_to_add.append('sec_grp')
            logger.info('Initialize and add sec_grp to the setseverityfield output')
        # Flag to avoid no data scenario and max event generation
        self.is_handle_no_data = normalizeBoolean(self.handle_no_data or default_no_data_max_event)
        # Flag to fill in data gaps (N/A values) for KPI with a custom value or last
        # non-N/A value, as per the option selected by user while configuring KPI
        self.is_fill_data_gaps = normalizeBoolean(self.fill_data_gaps or default_fill_data_gap)
        self.is_generate_max_result = normalizeBoolean(self.generate_max_severity_event or default_no_data_max_event)
        self.is_custom_threshold_event = False

        # Field needs to be added for max severity event and no data scenario
        if self.is_handle_no_data or self.is_generate_max_result:
            self.fields_to_add.append(self.is_service_max_severity_event_field)
            self.fields_to_add.append(self.is_service_aggregate_field)

        # field need to be added for filled data gap event
        if self.is_fill_data_gaps:
            self.fields_to_add.append(self.is_fill_data_gap_field)

        self.collect_kpi_data = CollectKpiInfo(self.session_key)

        self.set_severity_fields = SetSeverityFields(self.is_handle_no_data,
                                                     self.is_generate_max_result,
                                                     self.metadata.searchinfo.earliest_time)

        self.notable_event_kpi_alert = NotableEventKPIAlert(self.session_key)
        self.kpi_state_cache_object = ItsiKPIStateCache(self.session_key, 'nobody')
        self.kpi_state_cache_object_list = self.kpi_state_cache_object.get_bulk('nobody')
        self.kpi_state_cache_objects_dict = {cache['_key']: cache for cache in self.kpi_state_cache_object_list}

        # Keep track of updated state cache objects. It should update only updated objects in the kvstore
        self.updated_kpi_state_cache_keys = set()

        self.kpidata = {}
        self.kpi_entity_thresholds = {}
        self.servicedata = {}
        self.kpi_base_search = {}

        self.kpi_alerting_rule = {}
        self.kpi_alerts = []
        # We need this for kpi base searches to determine when we have a no-data scenario
        # Coming in with data
        # We currently don't need to do this at the kpi level because all of the entities filtering
        # Is done at the service level
        self.passedServices = set()
        self.lastTime = None

    def validate_search_args(self):
        """
        Validate search argument
        @return: None
        """

        if self.kpibasesearch is None and self.kpiid is None and self.serviceid is None:
            raise ValueError("Invalid options passed to command; must have service and kpi or kpi base search")

        if self.kpibasesearch is None:
            # Validate the kpiid and the serviceid if we are NOT using the kpibasesearch
            if self.kpiid is None:
                raise ValueError("Invalid kpiid argument")

            if self.serviceid is None:
                raise ValueError('Invalid serviceid argument')

    def get_itsi_meta_data(self, is_max_result_event=False):
        """
        Return dict with kpiid and serviceid

        @type is_max_result_event: boolean
        @param is_max_result_event: pass to true if this meta data belong to max value events of service
        @rtype: dict
        @return: return dict
        """
        meta_data = {
            'kpiid': self.kpiid,
            'serviceid': self.serviceid
        }
        if self.kpibasesearchid:
            meta_data['kpibasesearch'] = self.kpibasesearchid
        if self.is_generate_max_result:
            meta_data[self.is_service_max_severity_event_field] = 1 if is_max_result_event else 0
        meta_data[self.is_custom_threshold_event_field] = 1 if self.is_custom_threshold_event else 0

        return meta_data

    def _write_max_severity_event_per_timestamp(self, curr_timestamp):
        """
        For each timestamp, get max severity event and write it to buffer.

        NOTE 1: Logic assumes injected events to be sorted by time
             2: This method should only be used for single KPI cases (not shared base search).
                As currently, command only supports processing of time-series (backfill case)
                kind of events for single KPI.

        @type curr_timestamp: basestring
        @param curr_timestamp: timestamp of current event
        @return:
        """
        if self.is_time_series:
            # last timestamp max severity event would be written by post_processing method
            max_severity_event, last_timestamp = self.set_severity_fields.get_max_value_event_per_timestamp(
                curr_timestamp, self.kpiid)
            if max_severity_event:
                if 'alert_value' not in max_severity_event:
                    # No data case with no alert_value field, just
                    # populate the field with a default value
                    max_severity_event.update({'alert_value': 'N/A'})
                max_severity_event.update(self.get_itsi_meta_data(is_max_result_event=True))
                max_severity_event = self.add_fields_to_result(max_severity_event,
                                                               self.new_fieldnames + self.fields_to_add)
                return max_severity_event
            else:
                logger.warning('Could not get max value event for service=%s kpi=%s at timestamp=%s',
                               self.serviceid, self.kpiid, last_timestamp)
                return None
        return None

    def _get_value_and_write(self, result, kpidata):
        """
        Call get_severity_info and get severity value for given result set (alert_value)

        @type result: dict
        @param result: dict which hold alert_value information

        @type kpidata: dict or single object
        @param kpidata: kpi meta data

        @return: None
        """
        if self.is_fill_data_gaps:
            result[self.is_fill_data_gap_field] = 0

        if isinstance(kpidata, dict) and self.kpibasesearchid is not None:
            # This is the shared base search KPI scenario
            # So take the search result and look to see which entity it references
            last_time = result.get("_time", None)
            is_service_aggregate = normalizeBoolean(result.get("is_service_aggregate", False))
            is_all_entities_in_maintenance = normalizeBoolean(result.get("is_entity_in_maintenance", False))
            if last_time is not None:
                self.lastTime = last_time

            svc_id = result.get('serviceid')
            svc_data = kpidata.get(svc_id)
            if not svc_data or not svc_id:
                logger.debug('Found search results for service: %s, but this service has been deleted', svc_id)
            else:
                # Add this to indicate that we have seen the service and therefore the kpi
                self.passedServices.add(svc_id)

                if is_service_aggregate:
                    result.update(
                        {'is_all_entities_in_maintenance': is_all_entities_in_maintenance}
                    )

                for kpi in svc_data['kpis']:
                    metric = kpi.get('base_search_metric')
                    if metric is None:
                        continue
                    alert_value = result.get('alert_value_' + metric)

                    metric_object = self.kpi_base_search.get('metrics', {}).get(metric, {})
                    # overwrite data gaps (N/A values) alert_value to non-N/A values,
                    # if "fill_gaps" field for metric in shared base search is set to "custom_value"
                    if self.is_fill_data_gaps:
                        fill_data_gap, data_gap_value = self.collect_kpi_data.handle_filling_of_data_gaps(
                            alert_value, metric_object
                        )
                        if fill_data_gap:
                            # fill in the alert_value for data gap before computing severities for events.
                            alert_value = data_gap_value
                            # set below field, to differentiate between non-gap and filled in data gap events
                            result[self.is_fill_data_gap_field] = 1
                            if alert_value == 'N/A':
                                result['alert_error'] = 'No alert_value found for metric %s.' % metric
                        else:
                            result[self.is_fill_data_gap_field] = 0

                    if alert_value is None or alert_value == '':
                        result["alert_value"] = "N/A"
                        result["alert_error"] = "No alert_value found for metric %s." % metric
                    else:
                        result["alert_value"] = alert_value

                    # Check for the count override
                    if not is_string_numeric(result["alert_value"]) and \
                            self.collect_kpi_data.check_kpi_for_count_override(kpi):
                        # We need to set the value to 0 because it is a count of nothing
                        result["alert_value"] = 0

                    values = self.set_severity_fields.get_severity_info(result, kpi=kpi, service_info=svc_data,
                                                                        kpi_entity_thresholds=self.kpi_entity_thresholds)
                    # For an active custom threshold window, mark the events to not be calculated by AD
                    if kpi.get('active_custom_threshold_window', ''):
                        self.is_custom_threshold_event = True
                    self.serviceid = svc_id
                    self.kpiid = kpi.get('_key')
                    result.update(values)
                    is_service_in_maintenance = normalizeBoolean(result.get('is_service_in_maintenance'))
                    result.update({"alert_period": kpi.get("alert_period"),
                                   "kpi": kpi.get("title"),
                                   "urgency": kpi.get("urgency") if not is_service_in_maintenance else 0,
                                   "serviceid": self.serviceid  # It's for ITOA-5345, prevents serviceid leakage
                                   })
                    if self.output_secgrp:
                        result.update({"sec_grp": kpi.get("sec_grp")})

                    result.update(self.get_itsi_meta_data())
                    result = self.add_fields_to_result(result, self.new_fieldnames + self.fields_to_add)
                    yield result
                    # Check feature flag before checking KPI alerting condition
                    if self.is_service_aggregate_field in result and result.get(self.is_service_aggregate_field) == '1':
                        self._check_kpi_alert_condition(kpi, svc_id, values)

        elif self.serviceid is not None and self.kpiid is not None:
            # This is the standard KPI handling scenario
            if not is_string_numeric(result.get("alert_value")) and \
                    self.collect_kpi_data.check_kpi_for_count_override(self.kpidata):
                # We need to set the value to 0 because it is a count of nothing
                result["alert_value"] = 0

            # overwrite data gaps (N/A values) alert_value to non-N/A values,
            # if "fill_gaps" field for KPI is set to "custom_value"
            if self.is_fill_data_gaps:
                fill_data_gap, data_gap_value = self.collect_kpi_data.handle_filling_of_data_gaps(
                    result.get('alert_value'), self.kpidata
                )
                if fill_data_gap:
                    # fill in the alert_value for data gap before computing severities for events.
                    result['alert_value'] = data_gap_value
                    # set below field, to differentiate between non-gap and filled in data gap events
                    result[self.is_fill_data_gap_field] = 1
                else:
                    result[self.is_fill_data_gap_field] = 0

            self.servicedata['in_maintenance'] = (self.servicedata.get(
                'in_maintenance',
                False) or normalizeBoolean(result.get('is_service_in_maintenance', False)))
            values = self.set_severity_fields.get_severity_info(result, kpi=self.kpidata, service_info=self.servicedata,
                                                                kpi_entity_thresholds=self.kpi_entity_thresholds)
            # For an active custom threshold window, mark the events to not be calculated by AD
            if self.kpidata.get('active_custom_threshold_window', ''):
                self.is_custom_threshold_event = True
            result.update(values)
            result.update(self.get_itsi_meta_data())
            if 'alert_value' not in result:
                # no alert_value fields most likely means no data, thus set to 'N/A'
                result.update({'alert_value': 'N/A'})
            if self.output_secgrp:
                result.update({'sec_grp': self.servicedata.get('sec_grp')})
            result = self.add_fields_to_result(result, self.new_fieldnames + self.fields_to_add)
            yield result

            # Check feature flag before checking KPI alerting condition
            if self.is_service_aggregate_field in result and result.get(self.is_service_aggregate_field) == '1':
                # The current KPI severity value is stored in values dict,
                # hence check if an alter needs to be raised based on the rules set by the user
                self._check_kpi_alert_condition(self.kpidata, self.serviceid, values)
        else:
            # This is the we have no idea what this data is scenario
            result["alert_value"] = "N/A"
            result["alert_error"] = "No matching services found for entity."
            result = self.add_fields_to_result(result, self.new_fieldnames + self.fields_to_add)
            yield result

    def _check_kpi_alert_condition(self, kpi, service_id, kpi_severity_info):
        """
        Higher level function that compares the prev KPI severity value stored in KVstore,
        compares with the current KPI severity value and check if the custom rules set by the user matches,
        and triggers an alert if the condition matches
        @param kpi: KPI object dict
        @param service_id: Service id
        @param kpi_severity_info: dict having current KPI severity value
        @return:
        """
        alerting_enabled = kpi.get('aggregate_thresholds_alert_enabled', False)
        if alerting_enabled:
            kpiid = kpi.get("_key")
            curr_kpi_alert_severity = kpi_severity_info['alert_severity']
            kpi_state_cache = self.kpi_state_cache_objects_dict.get(kpiid)
            if kpi_state_cache is None:
                self.kpi_state_cache_objects_dict.update({kpiid: {"_key": kpiid,
                                                                  "cache_severity": curr_kpi_alert_severity}})
                self.updated_kpi_state_cache_keys.add(kpiid)
            else:
                prev_kpi_alert_severity = kpi_state_cache['cache_severity']
                trigger_alert = self._check_alert_condition(kpiid, prev_kpi_alert_severity, curr_kpi_alert_severity)
                if trigger_alert:
                    logger.debug("Alert triggered. Current severity: %s Previous severity: %s",
                                 curr_kpi_alert_severity, prev_kpi_alert_severity)
                    alert_data = self._construct_alert_data(kpi, service_id, prev_kpi_alert_severity,
                                                            curr_kpi_alert_severity, kpi_severity_info['alert_level'])
                    self.kpi_alerts.append(alert_data)

                self.kpi_state_cache_objects_dict[kpiid]["cache_severity"] = curr_kpi_alert_severity
                self.updated_kpi_state_cache_keys.add(kpiid)

    def _check_alert_condition(self, kpiid, prev_kpi_alert_severity, curr_kpi_alert_severity):
        """
        Check if the custom rules set by the user matches the KPI severity change
        @param kpiid:
        @param prev_kpi_alert_severity:
        @param curr_kpi_alert_severity:
        @return:
        """
        if kpiid in self.kpi_alerting_rule:
            alert_rules = self.kpi_alerting_rule[kpiid]
            if alert_rules == 'any' and prev_kpi_alert_severity != curr_kpi_alert_severity:
                return True
            if curr_kpi_alert_severity in alert_rules:
                alert_severity_from = alert_rules[curr_kpi_alert_severity]
                if prev_kpi_alert_severity in alert_severity_from:
                    return True
        return False

    def _construct_alert_data(self, kpi, service_id, prev_severity, curr_severity, alert_level):
        """
        Construct the alert data
        @param kpi: KPI object
        @param service_id: Service id
        @param prev_severity: Previous KPI severity value
        @param curr_severity: Current KPI severity value
        @return:
        """
        alert_data = {
            "itsi_service_id": service_id,
            "itsi_service_title": kpi.get("service_title"),
            "itsi_kpi_id": kpi.get("_key"),
            "itsi_kpi_title": kpi.get("title"),
            "alert_type": "KPI alert",
            "prev_severity": prev_severity,
            "severity": curr_severity,
            "alert_level": alert_level,
            "_time": time.time()
        }
        return alert_data

    def _send_alerts(self, alerts):
        if alerts:
            self.notable_event_kpi_alert.transform_to_kpi_events(alerts)

    def _process_kpi_data_alerting_object(self):
        """
        This function process the KPI data stored in the variable self.kpidata
        Takes the custom alerting rules in the KPI object and extract them to consumable form
        """
        if self.kpibasesearchid is None:
            self._process_kpi_alerting_info(self.kpidata)
        else:
            for svc_id in list(self.kpidata.keys()):
                svc_kpis = self.kpidata.get(svc_id)
                if not svc_kpis or not svc_id:
                    logger.debug('Found search results for service: %s, but this service has been deleted', svc_id)
                else:
                    for kpi in svc_kpis['kpis']:
                        self._process_kpi_alerting_info(kpi)

    def _process_kpi_alerting_info(self, kpi):
        """
        Check for each KPI object, the alerting flag value to take action
        @param kpi: KPI dict
        @return:
        """
        alerting_enabled = kpi.get('aggregate_thresholds_alert_enabled', False)
        # KPI altering is enabled for KPI
        if alerting_enabled:
            # Check if user has set custom rules
            custom_alert = kpi.get('aggregate_thresholds_custom_alert_enabled', False)
            if custom_alert:
                rules = kpi.get("aggregate_thresholds_custom_alert_rules")
                self.kpi_alerting_rule[kpi.get("_key")] = self._format_custom_alert_rules(rules)
            else:
                # No custom rules set by user, so alert is raised for any severity change in KPI
                self.kpi_alerting_rule[kpi.get("_key")] = 'any'

    def _format_custom_alert_rules(self, custom_rules):
        """
        Format the custom rules in the KPI object to a form that can be consumed
        @param custom_rules: List of dict items, each item representing one rule
        @return:
        """
        formated_custom_rules = {}
        for rule in custom_rules:
            formated_custom_rules[rule.get("change_to")] = rule.get("change_from")
        return formated_custom_rules

    def pre_processing(self):
        """
        Collect kpi meta from kv store (one time task)
        @return:
        """
        if self.kpibasesearchid is not None:
            # Gather the KPI data from the base search
            self.kpidata, self.kpi_base_search = self.collect_kpi_data.get_kpis_from_shared_base(self.kpibasesearchid)
            if self.kpidata is None:
                logger.warning("Could not find kpi data, could be called by preview before kpi or service creation,"
                               " kpibasesearchid=%s", self.kpibasesearchid)
                # Avoid failure in run and post_processing
                self.kpidata = {}
                return
            kpis_with_entity_level_thresholding = []
            for service_id in self.kpidata.keys():
                for kpi in self.kpidata[service_id].get('kpis', []):
                    if kpi.get('is_entity_level_thresholding', None):
                        kpis_with_entity_level_thresholding.append(kpi.get('_key'))
            if len(kpis_with_entity_level_thresholding) > 0:
                self.kpi_entity_thresholds = self.collect_kpi_data.get_bulk_kpi_entity_thresholds(kpis_with_entity_level_thresholding)
        else:  # We are getting info for a single KPI
            kpidata, servicedata = self.collect_kpi_data.get_kpi(self.serviceid, self.kpiid)
            if kpidata is None:
                logger.warning("Could not find kpi data, could be called by preview before kpi or service creation,"
                               " kpiid=%s, serviceid=%s", self.kpiid, self.serviceid)
            else:
                self.kpidata = kpidata
                if self.kpidata.get('is_entity_level_thresholding', None):
                    self.kpi_entity_thresholds = self.collect_kpi_data.get_kpi_entity_thresholds(self.kpiid)
                self.servicedata = servicedata

        self._process_kpi_data_alerting_object()

    def _execute_chunk_v2(self, process, chunk):
        """
        Overriding _execute_chunk_v2() of search_command.py

        Issue: ITSI-18991	[Blocked on SDK] "No data scenario" is not being handled in Set severity fields
        Reason: Using splunk-sdk-1.6.15 search command is not getting triggered when there are no events
        Workaround: Track whether the transform method got executed or not; if not, call it with an empty record list
        """
        self.handle_no_results = True
        super(SetSeverityFieldsCommand, self)._execute_chunk_v2(process, chunk)
        if self.handle_no_results:
            self._record_writer.write_records(process([]))

    def add_fields_to_result(self, result, fields):
        """
        Add missing fields in the result event
        @param result: event
        @param fields: Fields needs to be in event
        @return: updated result
        """
        for field in fields:
            if field not in result:
                result[field] = ''
        return result

    def transform(self, records):
        """
        Generator function that processes and yields event records to the Splunk events pipeline.
        @return: None
        """
        self.handle_no_results = False
        self.setup()
        self.pre_processing()

        # As 'records' is a generator object, track if there are items in it or not?
        # if not, flag no_items_in_records to True
        no_items_in_records = True
        for record in records:
            no_items_in_records = False
            max_event = self._write_max_severity_event_per_timestamp(record.get('_time'))
            if max_event:
                yield max_event.copy()
            for result in self._get_value_and_write(record, self.kpidata):
                yield result.copy()
        if no_items_in_records and self.is_handle_no_data:
            if self.kpibasesearchid is None:
                logger.info("No data scenario for kpiid=%s, serviceid=%s", self.kpiid, self.serviceid)
                result = {'alert_value': 'N/A', 'is_service_aggregate': '1'}
                for result in self._get_value_and_write(result, self.kpidata):
                    yield result.copy()
            else:
                logger.info("No data scenario for kpibasesearchid=%s", self.kpibasesearchid)
                for svc_id in list(self.kpidata.keys()):
                    result = {'alert_value': 'N/A', 'is_service_aggregate': '1', 'serviceid': svc_id}
                    for result in self._get_value_and_write(result, self.kpidata):
                        yield result.copy()

        self._send_alerts(self.kpi_alerts)

        for result in self.post_processing():
            yield result.copy()

    def update_kpi_state_cache(self):
        """
        Update locally maintained list of KPI state cache into the KVStore
        """
        if self.kpi_state_cache_objects_dict and self.updated_kpi_state_cache_keys:
            updated_list = [value for key, value in self.kpi_state_cache_objects_dict.items()
                            if key in self.updated_kpi_state_cache_keys]
            self.kpi_state_cache_object.save_batch(
                'nobody',
                updated_list,
                True,
            )

    def post_processing(self):
        """
        Perform post processing
        @return: None
        """
        if self.is_generate_max_result and self.kpibasesearchid is None:
            self.update_kpi_state_cache()
            logger.debug("setseverityfields post processing for serviceid=%s kpiid=%s", self.serviceid, self.kpiid)
            # In case of time series (backfill case) kind of events (is_time_series==True),
            # below code generates last max severity event for the KPI (for last timestamp).
            max_result = self.set_severity_fields.get_max_value_event(self.kpiid)
            if max_result:
                if 'alert_value' not in max_result:
                    # No data case with no alert_value field, just populate the field with a default value
                    max_result.update({'alert_value': 'N/A'})
                if self.output_secgrp:
                    max_result.update({'sec_grp': self.servicedata.get('sec_grp')})
                max_result = self.add_fields_to_result(max_result, self.fields_to_add)
                max_result.update(self.get_itsi_meta_data(is_max_result_event=True))
                yield max_result
            else:
                logger.warning("Could not get max value event for service=%s kpi=%s", self.serviceid, self.kpiid)
            return

        elif self.kpibasesearchid is not None and self.is_generate_max_result:
            logger.debug("setseverityfields post processing for kpibasesearchid=%s", self.kpibasesearchid)
            # Deal with any kpis that had no matching events due to entity rules
            # Saw exception where self.kpidata is NoneType
            existing_matches = set(self.kpidata.keys()) if self.kpidata else set()
            empty_services = existing_matches.difference(self.passedServices)
            for svc_id in empty_services:
                result = {'alert_value': 'N/A',
                          'is_service_aggregate': '1',
                          'entity_title': 'service_aggregate',
                          'entity_key': 'service_aggregate',
                          'is_entity_defined': 0,
                          'serviceid': svc_id}
                if self.lastTime is not None:
                    result['_time'] = self.lastTime
                result = self.add_fields_to_result(result, self.new_fieldnames + self.fields_to_add)

                for result in self._get_value_and_write(result, self.kpidata):
                    yield result

            self.update_kpi_state_cache()
            # Fire off one event per kpi
            if not isinstance(self.kpidata, dict):
                return
            last_service = -1
            if self.kpidata is not None and len(self.kpidata) > 0:
                last_service = list(self.kpidata.keys())[-1]
            for svc_id, svc_data in self.kpidata.items():
                kpis = svc_data.get("kpis")
                if not isinstance(kpis, list):
                    logger.error("Critical error, kpis invalid for serviceid=%s", svc_id)
                    continue
                for kpi in kpis:
                    self.kpiid = kpi['_key']
                    logger.debug("max severity chunk on kpiid=%s", self.kpiid)

                    if svc_id == last_service and self.kpiid == kpis[-1]['_key']:
                        # If we are on the very last KPI, then set the finished flag
                        logger.debug("final chunk on kpiid=%s", self.kpiid)
                    self.serviceid = svc_id
                    max_result = self.set_severity_fields.get_max_value_event(self.kpiid)
                    if max_result:
                        max_result["kpi"] = kpi.get("title")
                        is_service_in_maintenance = normalizeBoolean(max_result.get('is_service_in_maintenance', False))
                        max_result["urgency"] = kpi.get("urgency") if not is_service_in_maintenance else 0
                        if self.output_secgrp:
                            max_result['sec_grp'] = kpi.get('sec_grp')
                        max_result = self.add_fields_to_result(max_result, self.fields_to_add)
                        max_result.update(self.get_itsi_meta_data(is_max_result_event=True))

                        yield max_result
                    else:
                        logger.warning("Could not get max value event for kpi=%s serviceid=%s using kpibasesearchid=%s",
                                       self.kpiid,
                                       svc_id,
                                       self.kpibasesearchid)


def main():
    dispatch(SetSeverityFieldsCommand, sys.argv, sys.stdin, sys.stdout)


if __name__ == "__main__":
    main()
