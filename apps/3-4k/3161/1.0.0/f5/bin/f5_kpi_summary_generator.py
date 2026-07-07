#!/usr/bin/env python
#
# Copyright 2013 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys
import time
from splunklib.modularinput import *
import splunklib.results as results

MAIN_LOOP_ERROR_DELAY = 10

top_level_searches = {
    "host": '| tstats count from datamodel="bigip-tmsh-system_status" where host="FILTER" by all.devicegroup host index| rename all.* as * | rename devicegroup as where1, host as where2',
    "application": '| tstats count from datamodel="dropdown" where all.app="FILTER" by all.tenant all.app index| rename all.* as * | rename tenant as where1, app as where2'
}

kpi_searches = dict(host=['`calc_host_cpu_health("WHERE2")`  | `format_kpi_summary("WHERE1", "WHERE2", "INDEX", "f5_host_kpi")`',
                          '`calc_host_uptime_health("WHERE2")` | `format_kpi_summary("WHERE1", "WHERE2", "INDEX", "f5_host_kpi")`',
                          '`calc_host_mem_health("WHERE2")` | `format_kpi_summary("WHERE1", "WHERE2", "INDEX", "f5_host_kpi")`',
                          '`calc_host_disk_queue_health("WHERE2")` | `format_kpi_summary("WHERE1", "WHERE2", "INDEX", "f5_host_kpi")`',
                          '`calc_host_disk_space_health("WHERE2")` | `format_kpi_summary("WHERE1", "WHERE2", "INDEX", "f5_host_kpi")`',
                          '`calc_host_interface_health("WHERE2")` | `format_kpi_summary("WHERE1", "WHERE2", "INDEX", "f5_host_kpi")`',
                          '`calc_host_failover_health("WHERE2")`  | `format_kpi_summary("WHERE1", "WHERE2", "INDEX", "f5_host_kpi")`',
                          '`calc_host_event_health("WHERE2")` | `format_kpi_summary("WHERE1", "WHERE2", "INDEX", "f5_host_kpi")`'],
                    application=['`calc_app_pool_member_health("WHERE1", "WHERE2")` | `format_kpi_summary("WHERE1", "WHERE2", "INDEX", "f5_app_kpi")`',
                                 '`calc_app_server_latency_health("WHERE1", "WHERE2")` | `format_kpi_summary("WHERE1", "WHERE2", "INDEX", "f5_app_kpi")`',
                                 '`calc_app_virtual_cpu_health("WHERE1", "WHERE2")` | `format_kpi_summary("WHERE1", "WHERE2", "INDEX", "f5_app_kpi")`',
                                 '`calc_app_uptime_health("WHERE1", "WHERE2")` | `format_kpi_summary("WHERE1", "WHERE2", "INDEX", "f5_app_kpi")`',
                                 '`calc_app_tcp_errors_health("WHERE1", "WHERE2")` | `format_kpi_summary("WHERE1", "WHERE2", "INDEX", "f5_app_kpi")`',
                                 '`calc_app_response_codes_health("WHERE1", "WHERE2")` | `format_kpi_summary("WHERE1", "WHERE2", "INDEX", "f5_app_kpi")`'])


class F5HealthGenerator(Script):

    def get_scheme(self):
        scheme = Scheme("F5 Health KPI Summary Generator")

        scheme.description = "Generates F5 Application and Host Health KPI Summary data."
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        kpi_type_argument = Argument("kpi_type")
        kpi_type_argument.title = "KPI Type"
        kpi_type_argument.data_type = Argument.data_type_number
        kpi_type_argument.description = "What type of KPI to generate. MUST be either application or host!"
        kpi_type_argument.required_on_create = True
        scheme.add_argument(kpi_type_argument)

        freq_argument = Argument("frequency")
        freq_argument.title = "Frequency"
        freq_argument.data_type = Argument.data_type_number
        freq_argument.description = "How often to generate F5 health summary data in seconds. Recommend 1200 (20 minutes)"
        freq_argument.required_on_create = True
        scheme.add_argument(freq_argument)

        filter_argument = Argument("host_filter")
        filter_argument.title = "Host Filter"
        filter_argument.data_type = Argument.data_type_string
        filter_argument.description = "Hosts that should have F5 health summary data generated (use * to include all hosts)."
        filter_argument.required_on_create = True
        scheme.add_argument(filter_argument)

        filter_argument = Argument("app_filter")
        filter_argument.title = "Application Filter"
        filter_argument.data_type = Argument.data_type_string
        filter_argument.description = "Applications that should have F5 health summary data generated (use * to include all applications)."
        filter_argument.required_on_create = True
        scheme.add_argument(filter_argument)

        return scheme

    def validate_input(self, validation_definition):
        frequency = float(validation_definition.parameters["frequency"])
        kpi_type = validation_definition.parameters["kpi_type"]

        if kpi_type not in ["application", "host"]:
            raise ValueError("kpi_type must be either application or host - found %s" % kpi_type)

        if frequency < 300 or frequency > 86000:
            raise ValueError("frequency should not be less than 5 minutes or more than 24 hours - found %f" % frequency)

    def stream_events(self, inputs, ew):

        # Go through each input for this modular input
        for input_name, input_item in inputs.inputs.iteritems():

            kpi_type = input_item["kpi_type"]
            frequency = float(input_item["frequency"])
            host_filter = input_item["host_filter"]
            app_filter = input_item["app_filter"]

            ew.log("INFO", "F5 Health KPI Frequency found - %f" % frequency)
            ew.log("INFO", "F5 Host Filter found - %s" % host_filter)
            ew.log("INFO", "F5 Application Filter found - %s" % app_filter)

            while True:
                try:
                    kwargs_export = {"earliest_time": "-24h@h",
                                     "latest_time": "now",
                                     "search_mode": "normal"}

                    where_filter = host_filter if kpi_type == "host" else app_filter
                    template_query = top_level_searches[kpi_type]
                    template_query = template_query.replace("FILTER", where_filter)
                    ew.log("INFO", "message=F5 - executing top level %s KPI search %s" % (kpi_type, template_query))

                    templatesearch_results = self.service.jobs.export(template_query, **kwargs_export)
                    reader = results.ResultsReader(templatesearch_results)
                    job_count = 0
                    start = time.time()

                    for result in reader:
                        if isinstance(result, results.Message):
                            ew.log("INFO", "%s f5_kpi_message=%s" % (kpi_type, result))
                        else:
                            try:
                                for search in kpi_searches[kpi_type]:
                                    search = search.replace("WHERE1", result['where1'])
                                    search = search.replace("WHERE2", result['where2'])
                                    search = search.replace("INDEX", result['index'])

                                    ew.log("INFO", "message=F5 running KPI search f5_kpi_search=%s" % search)
                                    kpi_search_results = self.service.jobs.export(search, **kwargs_export)
                                    kpireader = results.ResultsReader(kpi_search_results)
                                    for kpi_result in kpireader:
                                        if isinstance(result, results.Message):
                                            ew.log("INFO", "%s F5_KPI_Message=%s" % (kpi_type, kpi_result))
                                        elif isinstance(result, dict):
                                            ew.log("INFO", "%s F5_KPI_Result=%s" % (kpi_type, kpi_result))
                                    job_count += 1
                            except Exception as e:
                                ew.log("ERROR", "F5 Health Summary Generator: Error in processing KPI for %s (%s)" % (result, e.message))
                    stop = time.time()
                    elapsed = stop-start
                    ew.log("INFO", "message=F5 KPI Generation complete f5_kpi_type=%s f5_kpi_time=%s  f5_kpi_jobs=%s" % (kpi_type, elapsed, job_count))

                except Exception as e:
                    time.sleep(MAIN_LOOP_ERROR_DELAY)
                    ew.log("ERROR", "F5 Health Summary Generator: Error in generating %s health summary data: %s" % (kpi_type, e.message))
                    continue

                sleep_time = frequency - elapsed
                if sleep_time < 0:
                    ew.log("ERROR", "F5 KPI Generation %s taking longer than frequency %s! Took %s seconds longer than it should. Adjusting next run time."
                           % (kpi_type, frequency, sleep_time))

                    # Sleep just until we hit the next "frequency" boundary (noodletoad)
                    sleep_time = frequency - (sleep_time % frequency)

                ew.log("INFO", "F5 KPI Generation %s sleeping for %s seconds" % (kpi_type, sleep_time))
                time.sleep(sleep_time)

if __name__ == "__main__":
    sys.exit(F5HealthGenerator().run(sys.argv))
