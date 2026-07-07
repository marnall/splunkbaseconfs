#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import os
import sys
import time
import json
import threading

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# Networking imports
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_replica_executor.log" % splunkhome,
    mode="a",
    maxBytes=10000000,
    backupCount=1,
)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(filename)s %(funcName)s %(lineno)d %(message)s"
)
logging.Formatter.converter = time.gmtime
filehandler.setFormatter(formatter)
log = logging.getLogger()  # root logger - Good to get it only once.
for hdlr in log.handlers[:]:  # remove the existing file handlers
    if isinstance(hdlr, logging.FileHandler):
        log.removeHandler(hdlr)
log.addHandler(filehandler)  # set the new handler
# set the log level to INFO, DEBUG as the default is ERROR
log.setLevel(logging.INFO)

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# import trackme libs
from trackme_libs import (
    trackme_reqinfo,
    trackme_register_tenant_object_summary,
    run_splunk_search,
    trackme_register_tenant_component_summary,
)

# import trackme libs croniter
from trackme_libs_croniter import cron_to_seconds


@Configuration(distributed=False)
class ReplicaExecutor(GeneratingCommand):
    tenants_filter_list = Option(
        doc="""
        **Syntax:** **tenants_filter_list=****
        **Description:** Optional list of tenants to be processed, if not set, all tenants are processed, you can use * to explicitly mean all.""",
        require=False,
        default="*",
        validate=validators.Match("tenants_filter_list", r"^.*$"),
    )

    max_runtime_sec = Option(
        doc="""
        **Syntax:** **max_runtime_sec=****
        **Description:** The max runtime for the job in seconds, defaults to 5 minutes less 15 seconds of margin.""",
        require=False,
        default="300",
        validate=validators.Match("max_runtime_sec", r"^\d*$"),
    )

    def register_component_summary_async(
        self, session_key, splunkd_uri, tenant_id, component
    ):
        try:
            summary_register_response = trackme_register_tenant_component_summary(
                session_key,
                splunkd_uri,
                tenant_id,
                component,
            )
            logging.debug(
                f'function="trackme_register_tenant_component_summary", response="{json.dumps(summary_register_response, indent=2)}"'
            )
        except Exception as e:
            logging.error(
                f'failed to register the component summary with exception="{str(e)}"'
            )

    def generate(self, **kwargs):
        if self:
            # performance counter
            start = time.time()

            # Track execution times
            execution_times = []
            average_execution_time = 0

            # Get request info and set logging level
            reqinfo = trackme_reqinfo(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
            )
            log.setLevel(reqinfo["logging_level"])

            # max runtime
            max_runtime = int(self.max_runtime_sec)

            # Retrieve the search cron schedule
            savedsearch_name = "trackme_replica_executor"
            savedsearch = self.service.saved_searches[savedsearch_name]
            savedsearch_cron_schedule = savedsearch.content["cron_schedule"]

            # get the cron_exec_sequence_sec
            try:
                cron_exec_sequence_sec = int(cron_to_seconds(savedsearch_cron_schedule))
            except Exception as e:
                logging.error(
                    f'failed to convert the cron schedule to seconds, error="{str(e)}"'
                )
                cron_exec_sequence_sec = max_runtime

            # the max_runtime cannot be bigger than the cron_exec_sequence_sec
            if max_runtime > cron_exec_sequence_sec:
                max_runtime = cron_exec_sequence_sec

            logging.info(
                f'max_runtime="{max_runtime}",  savedsearch_name="{savedsearch_name}", savedsearch_cron_schedule="{savedsearch_cron_schedule}", cron_exec_sequence_sec="{cron_exec_sequence_sec}"'
            )

            # Get the session key
            session_key = self._metadata.searchinfo.session_key

            # performance counter
            search_start_time = time.time()

            # optional CSV list of tenants to be processed
            if self.tenants_filter_list:
                if self.tenants_filter_list == "*":
                    tenants_filter_list = []
                else:
                    if not isinstance(self.tenants_filter_list, list):
                        tenants_filter_list = self.tenants_filter_list.split(",")
                    else:
                        tenants_filter_list
            else:
                tenants_filter_list = []

            # vtenants collection
            collection_name = "kv_trackme_virtual_tenants"
            collection = self.service.kvstore[collection_name]

            collection_records = []
            collection_records_keys = set()

            end = False
            skip_tracker = 0
            while end == False:
                process_collection_records = collection.data.query(skip=skip_tracker)
                if len(process_collection_records) != 0:
                    for item in process_collection_records:
                        if item.get("_key") not in collection_records_keys:
                            collection_records.append(item)
                            collection_records_keys.add(item.get("_key"))
                    skip_tracker += len(process_collection_records)
                else:
                    end = True

            # store the list of searches to be processed in a new array
            replica_reports_process_list = []

            # loop
            for record in collection_records:
                tenant_id = record["tenant_id"]
                tenant_status = record["tenant_status"]

                current_time = time.time()
                elapsed_time = current_time - start

                # Optionally filter tenants
                process_tenant = False
                if tenants_filter_list:
                    if tenant_id in tenants_filter_list:
                        process_tenant = True
                else:
                    process_tenant = True

                # do take into account disabled tenants
                if tenant_status == "disabled":
                    process_tenant = False

                if process_tenant:
                    try:
                        tenant_replica_objects = json.loads(
                            record["tenant_replica_objects"]
                        )
                        replica_reports = tenant_replica_objects["reports"]
                        logging.debug(
                            f'tenant_id="{tenant_id}", replica_reports="{json.dumps(replica_reports, indent=2)}"'
                        )

                        # loop
                        for replica_report in replica_reports:
                            if "_wrapper_" in replica_report:
                                logging.info(
                                    f'tenant_id="{tenant_id}", adding replica_report="{replica_report}" to the list of replica reports to be processed'
                                )
                                replica_reports_process_list.append(replica_report)

                    except Exception as e:
                        logging.debug(
                            f'There are no replica reports to be processed for the tenant_id="{tenant_id}", nothing to do.'
                        )

            #
            # Process replica trackers
            #

            # for reporting purposes
            results_record = []

            # set kwargs
            kwargs_oneshot = {
                "earliest_time": "-5m",
                "latest_time": "now",
                "count": 0,
                "output_mode": "json",
            }

            # Initialize sum of execution times and count of iterations
            total_execution_time = 0
            iteration_count = 0

            # Other initializations
            max_runtime = int(self.max_runtime_sec)

            # loop and proceed
            for replica_report_process in replica_reports_process_list:

                # iteration start
                iteration_start_time = time.time()

                # performance counter
                search_start_time = time.time()

                # set the search
                search = f'| savedsearch "{replica_report_process}"'

                # get tenant_id
                tenant_id = replica_report_process.split("_")[-1]

                # get component
                component_suffix = replica_report_process.split("_")[1]
                component = f"splk-{component_suffix}"

                # run search
                try:
                    reader = run_splunk_search(
                        self.service,
                        search,
                        kwargs_oneshot,
                        24,
                        5,
                    )

                    search_results = []
                    for item in reader:
                        if isinstance(item, dict):
                            logging.debug(f'search_results="{item}"')
                            # store results
                            search_results.append(item)

                    # run_time
                    run_time = round((time.time() - search_start_time), 3)

                    # store results
                    results_record.append(
                        {
                            "tenant": tenant_id,
                            "action": "success",
                            "replica_report": replica_report_process,
                            "results": search_results,
                            "run_time": run_time,
                        }
                    )

                    # Call the component register
                    trackme_register_tenant_object_summary(
                        session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        tenant_id,
                        component,
                        replica_report_process,
                        "success",
                        time.time(),
                        run_time,
                        "The report was executed successfully",
                        "-5m",
                        "now",
                    )

                except Exception as e:
                    # Call the component register
                    msg = f'report="{replica_report_process}", search failed with exception="{str(e)}"'
                    logging.error(msg)
                    # store results
                    results_record.append(
                        {
                            "tenant": tenant_id,
                            "action": "failure",
                            "replica_report": replica_report_process,
                            "exception": msg,
                        }
                    )
                    # Call the component register
                    trackme_register_tenant_object_summary(
                        session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        tenant_id,
                        component,
                        replica_report_process,
                        "failure",
                        time.time(),
                        run_time,
                        msg,
                        "-5m",
                        "now",
                    )

                #
                # Call the trackme_register_tenant_component_summary
                #

                # Use threading to do an async call to the register summary without waiting for it to complete
                thread = threading.Thread(
                    target=self.register_component_summary_async,
                    args=(
                        session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        tenant_id,
                        component,
                    ),
                )
                thread.start()

                # Calculate the execution time for this iteration
                iteration_end_time = time.time()
                execution_time = iteration_end_time - iteration_start_time

                # Update total execution time and iteration count
                total_execution_time += execution_time
                iteration_count += 1

                # Calculate average execution time
                if iteration_count > 0:
                    average_execution_time = total_execution_time / iteration_count
                else:
                    average_execution_time = 0

                # Check if there is enough time left to continue
                current_time = time.time()
                elapsed_time = current_time - start
                if elapsed_time + average_execution_time + 15 >= max_runtime:
                    logging.info(
                        f'max_runtime="{max_runtime}" is about to be reached, current_runtime="{elapsed_time}", job will be terminated now'
                    )
                    break

            # yield
            run_time = round((time.time() - start), 3)

            if results_record:
                yield {
                    "_time": time.time(),
                    "_raw": {
                        "process": "trackmereplicaexecutor",
                        "run_time": run_time,
                        "results": results_record,
                    },
                }

            else:
                yield {
                    "_time": time.time(),
                    "_raw": {
                        "process": "trackmereplicaexecutor",
                        "run_time": run_time,
                        "results": "There are no replica trackers to be executed currently, you can safety disable the execution of this search if you wish to do so.",
                    },
                }

            # perf counter for the entire call
            logging.info(
                f'trackmereplicaexecutor has terminated, run_time="{run_time}", results="{json.dumps(results_record, indent=2)}"'
            )


dispatch(ReplicaExecutor, sys.argv, sys.stdin, sys.stdout, __name__)
