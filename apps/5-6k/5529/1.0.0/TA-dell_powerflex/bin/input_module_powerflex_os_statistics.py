# encoding = utf-8

import sys
import json

from input_module_powerflex_common import PowerFlexCommonDataCollector
from input_module_powerflex_common import timer

if sys.version_info[0] == 2:
    from python2_lib.concurrent.futures import ThreadPoolExecutor
else:
    from python3_lib.concurrent.futures import ThreadPoolExecutor


THREADS = 10


class PowerFlexStatisticsCollector(PowerFlexCommonDataCollector):
    """
    Statistics collector
    """
    def __init__(self, helper, event_writer):
        super(PowerFlexStatisticsCollector, self).__init__(helper, event_writer, 'ta_dell_powerflex_powerflex_os_statistics')

        self.instances_rest_endpoint = str(helper.get_arg('instances_rest_endpoint')).strip(" ").rstrip("/")
        if self.instances_rest_endpoint[0] != '/':
            self.instances_rest_endpoint = "/{}".format(self.instances_rest_endpoint)
        self.statistics_rest_endpoint = str(helper.get_arg('statistics_rest_endpoint')).strip(" ").rstrip("/")
        if self.statistics_rest_endpoint[0] != '/':
            self.statistics_rest_endpoint = "/{}".format(self.statistics_rest_endpoint)
        self.method = str(self.helper.get_arg('method')).strip(" ")

    def stats_data_collection(self, id):
        """
        Statistics data collection (thread for each instance)
        """
        try:
            # Request
            parsed_statistics_rest_endpoint = self.statistics_rest_endpoint.replace("{id}", id)
            stats_response = self.session_obj.request(url=parsed_statistics_rest_endpoint, method=self.method)

            if isinstance(stats_response, dict):
                # for /statistics endpoints
                # Add extra paramaters
                stats_response['id'] = str(id)
                stats_response['systemId'] = str(self.system_id)
                # Write events to Splunk
                event = self.helper.new_event(json.dumps(stats_response), time=None, host=self.host, index=self.index, source=self.source, sourcetype=self.sourcetype, done=True, unbroken=True)
                self.event_writer.write_event(event)
            elif isinstance(stats_response, list):
                # for other endpoints
                for element in stats_response:
                    event = self.helper.new_event(json.dumps(element), time=None, host=self.host, index=self.index, source=self.source, sourcetype=self.sourcetype, done=True, unbroken=True)
                    self.event_writer.write_event(event)
            else:
                raise Exception("Unsupported type of response type={}".format(str(type(stats_response))))
        except:
            self.logger.exception("Error while collecting statistics data for instance id={}".format(id))

    @staticmethod
    def validate_input(helper, definition):
        """Implement your own validation logic to validate the input stanza configurations"""
        # This example accesses the modular input variable
        # instances_rest_endpoint = definition.parameters.get('instances_rest_endpoint', None)
        # statistics_rest_endpoint = definition.parameters.get('statistics_rest_endpoint', None)
        pass

    @timer
    def collect_events(self):
        """
        Data collection function
        """
        try:
            _ = self.get_system_id()
            instance_list = self.session_obj.request(url=self.instances_rest_endpoint, method=self.method)

            id_list = []
            for instance in instance_list:
                id_list.append(instance.get('id'))

            # Garbage collect instance_list
            del instance_list

            if len(id_list) == 0:
                self.logger.info("No instance found.")
                return

            global THREADS
            if len(id_list) < THREADS:
                THREADS = len(id_list)

            with ThreadPoolExecutor(max_workers=THREADS) as executor:
                _ = executor.map(self.stats_data_collection, id_list)

            self.logger.info("No. of instances: {}".format(len(id_list)))
        except:
            self.logger.exception("Error while collecting data.")
