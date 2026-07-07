# Copyright 2022, 2024 IBM All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import logging.handlers
import os
import sys
from queue import Queue

# Do not change import order (Splunk is picky about import order, so if something doesn't work try switching them around)
from utils import helpers, logger
from utils.inputs import Inputs
from utils.worker import TaskParams, TaskType, Worker

# Splunk is picky about "." imports, so try to use from and import statements 
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from splunklib.modularinput.argument import Argument
from splunklib.modularinput.event import Event
from splunklib.modularinput.event_writer import EventWriter
from splunklib.modularinput.scheme import Scheme
from splunklib.modularinput.script import Script


class ModInput(Script):

    def get_scheme(self):
        """Retuns a scheme of inputs that the app will use"""

        ew = EventWriter(sys.stdout, sys.stderr)
        
        scheme = Scheme("GI Modular Input")
        scheme.use_external_validation = False
        scheme.use_single_instance = False
        scheme.description = "Modular Input for Guardium Insights"

        gi_host = Argument(Inputs.Keys.GIHost)
        gi_host.title = "GI Host URL"
        gi_host.data_type = Argument.data_type_string
        gi_host.description = "Host URL for Guardium Insights (Example: www.insights-machine.com)"
        gi_host.required_on_create = True
        gi_host.required_on_edit = True
        scheme.add_argument(gi_host)

        api_key = Argument(Inputs.Keys.APIKey)
        api_key.title = "GI API Key"
        api_key.data_type = Argument.data_type_string
        api_key.description = "API Key for Guardium Insights"
        api_key.required_on_create = True
        api_key.required_on_edit = True
        scheme.add_argument(api_key)

        past_events_days = Argument(Inputs.Keys.PastEventsDays)
        past_events_days.title = "PAST EVENTS DAYS"
        past_events_days.data_type = Argument.data_type_string
        past_events_days.description = "Numbers of days in the past to pull data from"
        past_events_days.required_on_create = True
        past_events_days.required_on_edit = True
        scheme.add_argument(past_events_days)

        pull_risks = Argument(Inputs.Keys.PullRisks)
        pull_risks.title = "Pull Risk Event Data"
        pull_risks.data_type = Argument.data_type_boolean
        pull_risks.description = "Specifies if risk events data should be pulled or not"
        pull_risks.required_on_create = True
        pull_risks.required_on_edit = True
        scheme.add_argument(pull_risks)

        pull_reports = Argument(Inputs.Keys.PullReports)
        pull_reports.title = "Pull Reports Data"
        pull_reports.data_type = Argument.data_type_boolean
        pull_reports.description = "Specifies if reports data should be pulled or not"
        pull_reports.required_on_create = True
        pull_reports.required_on_edit = True
        scheme.add_argument(pull_reports)

        risks_index = Argument(Inputs.Keys.RisksIndex)
        risks_index.title = "Risks Index Name"
        risks_index.data_type = Argument.data_type_string
        risks_index.description = "Specifies the index where risk events are stored"
        risks_index.required_on_create = True
        risks_index.required_on_edit = True
        scheme.add_argument(risks_index)

        reports_index = Argument(Inputs.Keys.ReportsIndex)
        reports_index.title = "Reports Index Name"
        reports_index.data_type = Argument.data_type_string
        reports_index.description = "Specifies the index where reports are stored"
        reports_index.required_on_create = True
        reports_index.required_on_edit = True
        scheme.add_argument(reports_index)

        return scheme
        

    def stream_events(self, _inputs, ew: EventWriter):

        log = logger.setup_logger(logging.INFO)       

        # Retrieves the session key and creates a Splunk service instance
        session_key = self._input_definition.metadata["session_key"] 
        service = helpers.retrieve_service(token=session_key)

        # Writing events as a method of logging to the index "gi_logs"
        log.info("Modular Input Call Initiated")

        # Parsing the inputs file to retrieve necessary fields
        inputs_file = str(os.path.dirname(os.path.dirname(__file__)) + '/local/inputs.conf')
        inputs = Inputs()

        try:
            inputs.read_file(filepath=inputs_file)
        except Exception as e:
            log.error(f"Failed to read inputs file: {e}")
            ew.write_event(Event(stanza="gi", data=str(e)))
            return
            
        # Retrieve the API key secret
        try:
            inputs.read_password(session_key=session_key)
        except Exception as e:
            log.error(f"Failed to read API key secret: {e}")
            ew.write_event(Event(stanza="gi", data=str(e)))
            return

        # Print the GI host being used
        gi_host_log = logger.gi_host_logger(logging.INFO)
        gi_host_log.info(inputs.gi_host)

        # Retrieve GI API client instance
        api_client = helpers.retrieve_api_client(
            host=inputs.gi_host, 
            api_key=inputs.api_key, 
            api_key_secret=inputs.api_key_secret, 
            verify=inputs.do_verify)

        # creating a dict of tuples to store the functions/params needed for the threads
        task_args: dict[TaskType, TaskParams] = {}

        # Add risk event related tasks if needed
        if inputs.do_pull_risks:    
            log.info(f"PULL_RISKS = true, retrieving index '{inputs.risks_index_name}' and adding task")
            risks_index = helpers.retrieve_index(inputs.risks_index_name, service, helpers.RISKS_COLLECTION_NAME)
            helpers.set_index_frozen_time(risks_index, inputs.retention_time)

            task_args[TaskType.INSERT_RISKS] = (risks_index, service, api_client, helpers.RISKS_COLLECTION_NAME, inputs.past_events_days)
            task_args[TaskType.REFRESH_RISKS] = (risks_index, service, api_client)

        # Add reports related tasks if needed
        if inputs.do_pull_reports:
            log.warning(f"PULL_REPORTS = true, but not supported")

        # Create a thread for each task and run them
        queue = Queue()
        for task in task_args: 
            worker = Worker(queue)
            worker.daemon = True
            worker.start()
            log.info(f"Queued task: {task}")
            queue.put([task, task_args[task]])

        # Waits till every thread in the queue has completed
        queue.join()

        ew.write_event(Event(stanza="gi", data="GI script completed"))
        log.info("Modular Input call complete")

    def validate_input(self, definition):
        pass

if __name__ == "__main__":
    sys.exit(ModInput().run(sys.argv))