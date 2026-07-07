import os
import sys
import time
import datetime
import json
import uuid

bin_dir = os.path.basename(__file__)

'''
'''
import import_declare_test

import os
import os.path as op
import sys
import time
import datetime
import json

import traceback
import requests
from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib import log
from solnlib.modular_input import checkpointer
from splunktaucclib.modinput_wrapper import base_modinput as base_mi
import requests
import util


# encoding = utf-8


class ModInputdynatrace_timeseries_single_metric(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        self.correlation_id = uuid.uuid4()
        super(ModInputdynatrace_timeseries_single_metric, self).__init__("splunk_ta_dynatrace",
                                                                         "dynatrace_timeseries_single_metric",
                                                                         use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputdynatrace_timeseries_single_metric, self).get_scheme()
        scheme.title = ("Dynatrace Timeseries Single Metric")
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
        scheme.add_argument(smi.Argument("dynatrace_metric", title="Dynatrace Metric",
                                         description="https://www.dynatrace.com/support/help/dynatrace-api/timeseries/how-do-i-fetch-the-metrics-of-monitored-entities/#available-timeseries",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("aggregation_type", title="Aggregation Type",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))

        return scheme

    def get_app_name(self):
        return "Splunk_TA_Dynatrace"

    def validate_input(self, definition):
        pass

    def collect_events(helper, ew):
        '''
        Verify SSL Certificate
        '''

        # opt_ssl_certificate_verification = helper.get_arg('ssl_certificate_verification')
        opt_ssl_certificate_verification = util.get_ssl_certificate_verification(helper)

        '''
        Force HTTPS
        '''

        dynatrace_account_input = helper.get_arg("dynatrace_account")
        dynatrace_tenant_input = dynatrace_account_input["username"]

        if dynatrace_tenant_input.find('https://') == 0:
            opt_dynatrace_tenant = dynatrace_tenant_input
        elif dynatrace_tenant_input.find('http://') == 0:
            opt_dynatrace_tenant = dynatrace_tenant_input.replace('http://', 'https://')
        else:
            opt_dynatrace_tenant = 'https://' + dynatrace_tenant_input

        '''
        '''

        opt_dynatrace_api_token = dynatrace_account_input["password"]
        opt_dynatrace_metric = helper.get_arg('dynatrace_metric')
        opt_aggregation_type = helper.get_arg('aggregation_type')
        opt_dynatrace_collection_interval = helper.get_arg('dynatrace_collection_interval')

        headers = {'Authorization': 'Api-Token {}'.format(opt_dynatrace_api_token),
                   'version': 'Splunk TA 1.0.3'}
        api_url = opt_dynatrace_tenant + '/api/v1/timeseries'
        parameters = {'queryMode': 'total',
                      'relativeTime': opt_dynatrace_collection_interval,
                      'aggregationType': opt_aggregation_type,
                      'timeseriesId': opt_dynatrace_metric
                      }
        hecTime = 0

        response = helper.send_http_request(api_url, "GET", headers=headers, parameters=parameters, payload=None,
                                            cookies=None, verify=opt_ssl_certificate_verification, cert=None,
                                            timeout=None, use_proxy=True)
        try:
            response.raise_for_status()
        except:
            helper.log_error(response.text)
            return

        data = response.json()
        z = json.dumps(data)
        x = json.loads(z)

        entityDict = x["result"]["entities"]
        timeseriesId = x["result"]["timeseriesId"]
        aggregationType = x["result"]["aggregationType"]
        unit = x["result"]["unit"]

        resultDict = {}

        for entityKeyList, results in x["result"]["dataPoints"].items():
            entities = entityKeyList.split(", ")

            for entity in entities:
                entityTypeName, entityId = entity.split("-")
                entityTypeLabel = entityTypeName.lower() + "Id"
                resultDict.update({entityTypeLabel: entityId})
                entityNameLabel = entityTypeName.lower() + "Name"
                resultDict.update({entityNameLabel: entityDict[entity]})

            for result in results:
                eventTimeStr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(result[0] / 1000))
                hecTime = result[0] / 1000
                resultValue = result[1]
                resultDict.update({"timestamp": eventTimeStr})
                resultDict.update({"value": resultValue})
                resultDict.update({"aggregation": aggregationType})
                resultDict.update({"unit": unit})
                resultDict.update({"timeseriesId": timeseriesId})

                HECEvent = json.dumps(resultDict, sort_keys=True)
                event = helper.new_event(data=HECEvent, time=hecTime, host=None, index=None, source=None,
                                         sourcetype=None, done=True, unbroken=True)
                ew.write_event(event)
                # print str(resultDict) + "\r\n\r\n"
                helper.log_debug(HECEvent)

        #   Save the name of the Dynatrace Server that this data came from
        event = helper.new_event(data='{"dynatrace_server":"' + opt_dynatrace_tenant + '"}', time=hecTime, host=None,
                                 index=None, source=None, sourcetype=None, done=True, unbroken=True)
        ew.write_event(event)

    def get_account_fields(self):
        account_fields = []
        account_fields.append("dynatrace_account")
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = []
        checkbox_fields.append("ssl_certificate_verification")
        return checkbox_fields

    def get_global_checkbox_fields(self):
        if self.global_checkbox_fields is None:
            checkbox_name_file = os.path.join(bin_dir, 'global_checkbox_param.json')
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error('Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields = []
        return self.global_checkbox_fields


if __name__ == "__main__":
    exitcode = ModInputdynatrace_timeseries_single_metric().run(sys.argv)
    sys.exit(exitcode)
