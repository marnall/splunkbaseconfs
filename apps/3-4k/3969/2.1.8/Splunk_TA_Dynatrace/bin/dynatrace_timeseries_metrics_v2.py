import os
import sys
import time
import uuid
from datetime import datetime, timedelta
import json
from pathlib import Path

bin_dir = os.path.basename(__file__)

'''
'''
import import_declare_test

import os
import os.path as op
import sys
import json

import traceback
from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib import log
from solnlib.modular_input import checkpointer
from splunktaucclib.modinput_wrapper import base_modinput  as base_mi 
import util
from util import Endpoint
from metrics_util import parse_metric_selectors_text_area
from dynatrace_types_37 import *



bin_dir = os.path.basename(__file__)

'''
'''


# encoding = utf-8


'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


class ModInputdynatrace_timeseries_metrics_v2(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        self.correlation_id = uuid.uuid4()
        super(ModInputdynatrace_timeseries_metrics_v2, self).__init__("splunk_ta_dynatrace", "dynatrace_timeseries_metrics_v2", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputdynatrace_timeseries_metrics_v2, self).get_scheme()
        scheme.title = ("Dynatrace Timeseries Metrics API v2")
        scheme.description = (
            "Go to the add-on\'s configuration UI and configure modular inputs under the Inputs menu.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        """
        For customized inputs, hard code the arguments here to hide argument detail from users.
        For other input types, arguments should be get from input_module. Defining new input types could be easier.
        """
        scheme.add_argument(smi.Argument("dynatrace_account", title="Dynatrace Account",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("dynatrace_collection_interval", title="Dynatrace Collection Interval",
                                         description="Relative timeframe passed to Dynatrace API. Timeframe of data to be collected at each polling interval.",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("dynatrace_metric_selectors_v2_textarea", title="Dynatrace Metric Selectors",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))

        return scheme

    def get_app_name(self):
        return "Splunk_TA_Dynatrace"

    def validate_input(helper, definition):
        """Implement your own validation logic to validate the input stanza configurations"""
        # This example accesses the modular input variable
        # dynatrace_tenant = definition.parameters.get('dynatrace_tenant', None)
        # dynatrace_api_token = definition.parameters.get('dynatrace_api_token', None)
        # dynatrace_collection_interval = definition.parameters.get('dynatrace_collection_interval', None)
        pass

    def collect_events(helper, ew):
        helper.log_debug('Beginning collect_events')

        dynatrace_account_input = helper.get_arg("dynatrace_account")
        dynatrace_tenant_input = dynatrace_account_input["username"]
        api_token = dynatrace_account_input["password"]
        index = helper.get_arg("index")

        tenant = util.parse_url(dynatrace_tenant_input)
        opt_dynatrace_collection_interval_minutes = int(helper.get_arg("dynatrace_collection_interval"))

        metric_selectors = parse_metric_selectors_text_area(helper.get_arg('dynatrace_metric_selectors_v2_textarea'))
        opt_ssl_certificate_verification = True

        helper.log_debug(f'verify_ssl: {opt_ssl_certificate_verification}')
        helper.log_debug(f'dynatrace_tenant: {tenant}')
        helper.log_debug(f'dynatrace_collection_interval_minutes: {opt_dynatrace_collection_interval_minutes}')
        helper.log_debug(f'metric_selectors: {metric_selectors}')

        metric_descriptor_list: List[MetricDescriptorCollection] = util.execute_session(Endpoint.METRICS, tenant, api_token, Params({}), metric_selectors, opt_helper=helper)

        metric_descriptor_mapping = {}
        for metric_descriptor in metric_descriptor_list:
            metrics = metric_descriptor.get('metrics')
            for metric in metrics:
                metric_id = metric.get('metricId')
                unit = metric.get('unit')
                aggregation_types = metric.get('aggregationTypes')
                metric_descriptor_mapping[metric_id] = (unit, aggregation_types)

        params = {'time': util.get_from_time(opt_dynatrace_collection_interval_minutes)}

        metric_data_list = list(
            util.execute_session(Endpoint.METRICS_QUERY, tenant, api_token, params, extra_params=metric_selectors, opt_helper=helper))

        for metric_data in metric_data_list:
            result = metric_data.get('result')
            resolution = metric_data.get('resolution')
            for metric_series_collection in result:
                metric_id = metric_series_collection.get('metricId')
                data = metric_series_collection.get('data')
                unit, aggregation_types = metric_descriptor_mapping.get(metric_id, (None, None))
                for metric_series in data:
                    dimensions = metric_series.get('dimensions')
                    dimension_map = metric_series.get('dimensionMap')
                    for timestamp, value in zip(metric_series.get('timestamps'), metric_series.get('values')):
                        event_data = {
                            'timestamp': timestamp,
                            'value': value,
                            'metric_id': metric_id,
                            'unit': unit,
                            'aggregation_types': aggregation_types,
                            'dynatraceTenant': tenant,
                            'resolution': resolution,
                            'dimensions': dimensions,
                            'dimension_map': dimension_map
                        }
                        serialized = json.dumps(event_data)
                        event = helper.new_event(data=serialized, time=timestamp, index=index)
                        ew.write_event(event)

    def get_account_fields(self):
        account_fields= []
        account_fields.append("dynatrace_account")
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields= []
        checkbox_fields.append("ssl_certificate_verification")
        return checkbox_fields

    def get_global_checkbox_fields(self):
        if self.global_checkbox_fields is None:
            checkbox_name_file= os.path.join(bin_dir, 'global_checkbox_param.json')
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields= json.load(fp)
                else:
                    self.global_checkbox_fields= []
            except Exception as e:
                self.log_error(
                    'Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields= []
        return self.global_checkbox_fields

if __name__ == "__main__":
    exitcode= ModInputdynatrace_timeseries_metrics_v2().run(sys.argv)
    sys.exit(exitcode)
