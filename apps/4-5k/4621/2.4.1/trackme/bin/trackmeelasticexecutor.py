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
import re
import json
import threading

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# Networking imports
import urllib3

# Multithreading imports
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_elastic_sources_shared_executor.log" % splunkhome,
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

# Import Splunk libs
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
    trackme_return_elastic_exec_search,
    run_splunk_search,
    trackme_register_tenant_component_summary,
)

# import croniter
from croniter import croniter
from datetime import datetime


@Configuration(distributed=False)
class TrackMeElasticExecutor(GeneratingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
        validate=validators.Match("tenant_id", r".*"),
    )

    component = Option(
        doc="""
        **Syntax:** **component=****
        **Description:** The tracker component name to be executed.""",
        require=True,
        default=None,
        validate=validators.Match("component", r".*"),
    )

    margin_sec = Option(
        doc="""
        **Syntax:** **margin_sec=****
        **Description:** The time in seconds used as a margin when calculating the max runtime depending on the cron schedule.
        If the search is triggered every 5 minutes, the max runtime will be 5 minutes less the margin_sec value.
        """,
        require=False,
        default="60",
        validate=validators.Match("margin_sec", r"^\d*$"),
    )

    max_concurrent_searches = Option(
        doc="""
        **Syntax:** **max_concurrent_searches=****
        **Description:** The max number of searches to be executed in parallel, if set to a different value than the system default, this value wins.
        """,
        require=False,
        default=None,
        validate=validators.Match("max_concurrent_searches", r"^\d*$"),
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

    # use croniter to return the job dureation in seconds based on the cron schedule
    def cron_to_seconds(self, cron_expression):
        now = datetime.now()
        cron_iter = croniter(cron_expression, now)

        next_execution = cron_iter.get_next(datetime)
        previous_execution = cron_iter.get_prev(datetime)

        diff = next_execution - previous_execution
        return diff.total_seconds()

    # determinate if the job should be terminated
    def should_terminate(self, mainstart, max_runtime):
        current_runtime = float(time.time() - float(mainstart))
        if current_runtime >= int(max_runtime):
            logging.info(
                f'tenant_id="{self.tenant_id}" max_runtime="{max_runtime}" for the Elastic Shared job was reached with current_runtime="{round(current_runtime, 3)}", job will be terminated now'
            )
            return True

        return False

    # process the elastic object
    def process_elastic_object(
        self,
        object_value,
        report,
    ):
        # Extract object details
        object = object_value.get("object")
        search_constraint = object_value.get("search_constraint")
        search_mode = object_value.get("search_mode")
        elastic_index = object_value.get("elastic_index")
        elastic_sourcetype = object_value.get("elastic_sourcetype")
        earliest_time = object_value.get("earliest_time")
        latest_time = object_value.get("latest_time")
        tracker_runtime = object_value.get("tracker_runtime")
        elastic_report_root_search = object_value.get("elastic_report_root_search")

        # Convert the tracker_runtime epoch to a human readable format
        tracker_runtime_human = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(tracker_runtime)
        )
        logging.info(
            f'tenant_id="{self.tenant_id}", component="{self.component}", report="{report}", processing elastic object, object="{object}", last inspection with tracker_runtime="{tracker_runtime_human}", elastic_report_root_search="{elastic_report_root_search}"'
        )

        # Performance timer
        start = time.time()

        # Log execution info
        logging.info(
            f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object}", report="{report}", Executing Elastic Source entity, search_mode="{search_mode}", earliest="{earliest_time}", latest="{latest_time}"'
        )

        # Set search parameters
        kwargs_oneshot = {
            "earliest_time": earliest_time,
            "latest_time": latest_time,
            "output_mode": "json",
            "count": 0,
        }

        try:
            reader = run_splunk_search(
                self.service,
                elastic_report_root_search,
                kwargs_oneshot,
                24,
                5,
            )

            # Process search results
            for item in reader:
                if isinstance(item, dict):
                    # Calculate execution duration
                    exec_duration = round(time.time() - start, 3)

                    # Construct result data
                    result_data = {
                        "object": object,
                        "search_constraint": search_constraint,
                        "search_mode": search_mode,
                        "elastic_index": elastic_index,
                        "elastic_sourcetype": elastic_sourcetype,
                        "earliest_time": earliest_time,
                        "latest_time": latest_time,
                        "execution_status": "success",
                        "execution_search": elastic_report_root_search,
                        "execution_results": item,
                        "execution_duration": exec_duration,
                    }

                    # Yield results
                    return {
                        "_time": time.time(),
                        "_raw": result_data,
                        "object": object,
                        "search_constraint": search_constraint,
                        "search_mode": search_mode,
                        "elastic_index": elastic_index,
                        "elastic_sourcetype": elastic_sourcetype,
                        "earliest_time": earliest_time,
                        "latest_time": latest_time,
                        "execution_status": "success",
                        "execution_search": elastic_report_root_search,
                        "execution_results": item,
                        "execution_duration": exec_duration,
                    }

                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object}", report="{report}", Entity search successfully executed, status="success", run_time="{round(time.time() - start, 3)}"'
                )

        except Exception as e:
            # Log and raise exception for other errors
            msg = f'tenant_id="{self.tenant_id}", component="{self.component}", report="{report}", permanent search failure, exception="{e}"'
            logging.error(msg)
            raise Exception(msg)

    def run_parallel_searches(
        self,
        elastic_shared_records,
        mainstart,
        max_runtime,
        report,
        max_parallel_searches,
    ):
        with ThreadPoolExecutor(max_workers=int(max_parallel_searches)) as executor:
            # Dictionary to hold future to object_key mapping
            future_to_object_key = {}

            # Submit tasks to the executor
            for object_key, object_value in sorted(
                elastic_shared_records.items(),
                key=lambda x: x[1]["tracker_runtime"],
                reverse=False,
            ):
                # Submit the processing function to the executor
                future = executor.submit(
                    self.process_elastic_object,
                    object_value,
                    report,
                )
                future_to_object_key[future] = object_key

            # Continuously check for timeout and process completed futures
            while future_to_object_key:
                # Check if the process should be terminated due to timeout
                if self.should_terminate(mainstart, max_runtime):
                    # Cancel all running futures
                    for future in future_to_object_key:
                        future.cancel()
                    break

                # Process the completed futures
                done, _ = wait(
                    future_to_object_key, timeout=0.1, return_when=FIRST_COMPLETED
                )
                for future in done:
                    object_key = future_to_object_key.pop(future)
                    try:
                        process_results = future.result()
                        if process_results:
                            yield process_results
                        else:
                            yield {
                                "_time": time.time(),
                                "_raw": {
                                    "action": "failed",
                                    "response": "search returned no results.",
                                    "object_key": object_key,
                                    "report": report,
                                },
                            }
                    except Exception as exc:
                        logging.error(
                            f"Object {object_key} generated an exception: {exc}"
                        )

    def generate(self, **kwargs):
        if self:
            # performance counter
            mainstart = time.time()

            # Get request info and set logging level
            reqinfo = trackme_reqinfo(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
            )
            log.setLevel(reqinfo["logging_level"])

            # define a report name for logging purposes
            report = f"trackme_dsm_shared_elastic_tracker_tenant_{self.tenant_id}"

            # get the current report definition to calculate based on the cron schedule how long the elastic report can run
            savedsearch = self.service.saved_searches[report]
            savedsearch_cron_schedule = savedsearch.content["cron_schedule"]

            # get the cron_exec_sequence_sec
            try:
                cron_exec_sequence_sec = float(
                    self.cron_to_seconds(savedsearch_cron_schedule)
                )
                # round the float to the nearest integer
                cron_exec_sequence_sec = round(cron_exec_sequence_sec)
            except Exception as e:
                cron_exec_sequence_sec = 0

            # if we have value for cron_exec_sequence_sec>0, set a max_runtime to margin_sec seconds less than the cron_exec_sequence_sec
            if cron_exec_sequence_sec > 0:
                max_runtime = cron_exec_sequence_sec - int(self.margin_sec)
            else:
                max_runtime = 300 - int(self.margin_sec)

            # log debug
            logging.debug(
                f'savedsearch_cron_schedule="{savedsearch_cron_schedule}", cron_exec_sequence_sec="{cron_exec_sequence_sec}", max_runtime was set to "{max_runtime}"'
            )

            # eval the job level max concurrent searches
            job_max_concurrent_searches = None

            # get system level
            system_max_concurrent_searches = int(
                reqinfo["trackme_conf"]["splk_general"][
                    "splk_general_elastic_max_concurrent"
                ]
            )

            if not self.max_concurrent_searches:
                job_max_concurrent_searches = int(system_max_concurrent_searches)
            else:
                job_max_concurrent_searches = int(self.max_concurrent_searches)

            # Get the session key
            session_key = self._metadata.searchinfo.session_key

            # elastic shared collection
            collection_name = f"kv_trackme_dsm_elastic_shared_tenant_{self.tenant_id}"
            collection = self.service.kvstore[collection_name]

            # tenant dsm collection
            collection_dsm_name = f"kv_trackme_dsm_tenant_{self.tenant_id}"
            collection_dsm = self.service.kvstore[collection_dsm_name]

            # Get all records from the elastic shared collection
            records = collection.data.query()

            # create a dict to store the elastic shared records
            elastic_shared_records = {}

            # log start
            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", report="{report}", Elastic Sources shared job started, max_concurrent_searches={job_max_concurrent_searches}, margin_sec={self.margin_sec}'
            )

            # proceed if we have records
            count_processed = 0

            if records:
                # Loop through Elastic records
                for record in records:
                    logging.debug(f'record="{record}"')
                    object_key = record.get("_key")
                    object = record.get("object")
                    search_constraint = record.get("search_constraint")
                    search_mode = record.get("search_mode")
                    elastic_index = record.get("elastic_index")
                    elastic_sourcetype = record.get("elastic_sourcetype")
                    earliest_time = record.get("earliest")
                    latest_time = record.get("latest")

                    # attempt to retrieve the value of tracker_runtime from the dsm collection
                    try:
                        dsm_record = collection_dsm.data.query(
                            query=json.dumps({"object": object})
                        )[0]
                        logging.debug(f'dsm_record="{dsm_record}"')
                        tracker_runtime = float(dsm_record.get("tracker_runtime"))
                    except Exception as e:
                        tracker_runtime = 0

                    # define the report root search depending on various conditions
                    elastic_report_root_search = None

                    #
                    # Set the search depending on its language
                    #

                    try:
                        elastic_report_root_search = trackme_return_elastic_exec_search(
                            search_mode,
                            search_constraint,
                            object,
                            elastic_index,
                            elastic_sourcetype,
                            self.tenant_id,
                            "True",
                            "none",
                        )
                        logging.info(
                            f'elastic_report_root_search="{elastic_report_root_search}"'
                        )
                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object}", failed to retrieve the execution search code, exception="{e}"'
                        )

                        elastic_report_root_search = None

                    if not elastic_report_root_search:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object}", could not retrieve the execution search, is this record corrupted?'
                        )

                    else:
                        # if the search is a raw search but doesn't start with the search keyword, fix this automatically
                        if not re.search(
                            r"^search\s", elastic_report_root_search
                        ) and not re.search(r"^\s{0,}\|", elastic_report_root_search):
                            elastic_report_root_search = (
                                f"search {elastic_report_root_search}"
                            )

                        # add to the dict
                        elastic_shared_records[object_key] = {
                            "object": object,
                            "search_constraint": search_constraint,
                            "search_mode": search_mode,
                            "elastic_index": elastic_index,
                            "elastic_sourcetype": elastic_sourcetype,
                            "earliest_time": earliest_time,
                            "latest_time": latest_time,
                            "tracker_runtime": tracker_runtime,
                            "elastic_report_root_search": elastic_report_root_search,
                        }

                # log the dict
                logging.debug(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", report="{report}", elastic_shared_records="{json.dumps(elastic_shared_records, indent=4)}"'
                )

                # Initialize the generator to handle parallel processing
                process_results_generator = self.run_parallel_searches(
                    elastic_shared_records,
                    mainstart,
                    max_runtime,
                    report,
                    job_max_concurrent_searches,
                )

                # Iterate over the generator to process results as they complete
                count_processed = 0
                for process_results in process_results_generator:
                    count_processed += 1
                    yield process_results

                #
                #  end of loop
                #

            # end
            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", report="{report}", Elastic Sources shared job successfully executed, status="success", run_time="{round(time.time() - mainstart, 3)}", entities_count="{count_processed}"'
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
                    self.tenant_id,
                    self.component,
                ),
            )
            thread.start()

            # Call the component register
            trackme_register_tenant_object_summary(
                session_key,
                self._metadata.searchinfo.splunkd_uri,
                self.tenant_id,
                "splk-dsm",
                f"trackme_dsm_shared_elastic_tracker_tenant_{self.tenant_id}",
                "success",
                time.time(),
                str(time.time() - mainstart),
                "The report was executed successfully",
                "-5m",
                "now",
            )

            # yield if we have no records to be processed
            if not len(records) > 0:
                yield {
                    "_time": time.time(),
                    "_raw": {
                        "action": "success",
                        "response": "There are no shared Elastic records to be processed for now.",
                    },
                }


dispatch(TrackMeElasticExecutor, sys.argv, sys.stdin, sys.stdout, __name__)
