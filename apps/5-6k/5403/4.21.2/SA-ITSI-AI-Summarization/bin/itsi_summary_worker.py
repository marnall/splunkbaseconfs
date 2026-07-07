import os
import signal
import sys
import time
import json
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from splunklib.modularinput import Script, Scheme, Argument
from util.dependency_checker import (
    DependencyStatus,
    ensure_runtime_dependencies,
    should_skip_dependency_check,
)
from constants import (
    ITSI_SUMMARY_WORKER_LOGGER_NAME,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY,
    KVSTORE_KEY
)
from work_queue import WorkQueue
from util import setup_logging
from util.splunk_util import SplunkUtil
from util.context_logging import get_context_logger, set_current_summarization_id
from summarization_task_handler import SummarizationTaskHandler
from summarization_task_executor import SummarizationTaskExecutor

# Run PSC dependency check before the modular input handshake to avoid ExecProcessor errors.
if should_skip_dependency_check():
    _INITIAL_DEPENDENCY_STATUS = DependencyStatus(ok=True)
else:
    _INITIAL_DEPENDENCY_STATUS = ensure_runtime_dependencies()


class ITSISummaryWorker(Script):
    """
    Modular input for processing ITSI episode summarization requests.
    Implements the workflow for asynchronous processing of summarization requests,
    fetching episode data, generating summaries via AI, and updating ITSI.
    """

    def __init__(self):
        super().__init__()
        self._shutdown_flag = False
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        self._dependency_status: Optional[DependencyStatus] = _INITIAL_DEPENDENCY_STATUS

        # Initialize context logger that automatically includes summarization ID
        logger = setup_logging.get_logger(ITSI_SUMMARY_WORKER_LOGGER_NAME)
        self.logger = get_context_logger(logger)

    def get_scheme(self):
        """
        Define the scheme for the modular input.
        """
        scheme = Scheme("ITSI AI Assistant Summarization Workflow")
        scheme.description = "Processes episode summarization requests from ITSI Orchestrator"
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        scheme.add_argument(Argument(
            name="priority",
            title="Priority of the input (0 for low, 1 for high)",
            description="Priority of the input (0 for low, 1 for high)",
            data_type=Argument.data_type_number,
            required_on_create=False,
        ))
        return scheme

    def stream_events(self, inputs, event_writer):
        """
        Main execution method that Splunk calls to collect events.
        """
        dependency_status = self._ensure_runtime_dependencies()

        if not dependency_status.ok:
            self.logger.warning(dependency_status.message)
            if dependency_status.details:
                self.logger.debug(f"Dependency error details: {dependency_status.details}")
            self.logger.info("ITSI Summary Worker is exiting gracefully because dependencies are missing.")
            return

        for input_name, input_params in list(inputs.inputs.items()):
            self.logger.info(f"Starting ITSI AI Assistant Worker for instance: {input_name}")
            priority = input_params.get(PRIORITY, PRIORITY_LOW)
            priority = self._validate_priority(priority)
            self.logger.info(f"Priority for instance {input_name}: {priority}")
            self._process_events(priority)

    def _process_events(self, priority):
        """
        Process events based on the priority.

        The following instances are initialized just once for the lifetime of the modular input script:
        - work_queue: Manages the queue of summarization tasks to be processed.
        - orchestrator_client: Handles communication with the ITSI Orchestrator.
        - itsi_ai_assistant_client: Interacts with the SCS summarization service.
        - task_handler: Manages the logic for handling summarization tasks.
        - executor: Executes the summarization tasks using the task handler and work queue.
        """
        work_queue = WorkQueue(self.service)

        system_user_service = SplunkUtil.get_splunk_system_user_service(self.service)

        from itsi_summary_orchestrator_client import ITSISummaryOrchestratorClient
        from itsi_ai_assistant_client import ITSIAIAssistantClient

        try:
            itsi_ai_assistant_tenant_url = SplunkUtil.get_itsi_ai_assistant_base_url(system_user_service)
        except Exception:
            self.logger.error("Failed to determine tenant specific ITSI AI Assistant URL")
            return

        itsi_ai_assistant_client = ITSIAIAssistantClient(itsi_ai_assistant_tenant_url, service=self.service)

        orchestrator_client = ITSISummaryOrchestratorClient(self.service, itsi_ai_assistant_client)

        task_handler = SummarizationTaskHandler(work_queue=work_queue, orchestrator_client=orchestrator_client,
                                                itsi_ai_assistant_client=itsi_ai_assistant_client)
        task_executor = SummarizationTaskExecutor(task_handler=task_handler.handle_summarization_task,
                                                  work_queue=work_queue)

        # Start the work queue processing loop
        # This loop will run until a shutdown signal is received which typically happens when splunkd shuts down
        while not self._shutdown_requested():
            self._process_work_queue(priority, work_queue, task_executor)
            time.sleep(1)  # Sleep for a short duration to avoid busy waiting especially when no items are in the queue

    def _ensure_runtime_dependencies(self) -> DependencyStatus:
        if self._dependency_status is None:
            if should_skip_dependency_check():
                self._dependency_status = DependencyStatus(ok=True)
            else:
                self._dependency_status = ensure_runtime_dependencies(self.logger)
        return self._dependency_status

    def _validate_priority(self, priority):
        """
        Validate and convert the priority value.
        """
        try:
            priority = int(priority)
        except ValueError:
            self.logger.warning(f"Priority must be an integer. Using default priority: {PRIORITY_LOW}")
            return PRIORITY_LOW

        if priority not in [PRIORITY_LOW, PRIORITY_HIGH]:
            self.logger.warning(f"Invalid priority value: {priority}. Using default priority: {PRIORITY_LOW}")
            return PRIORITY_LOW

        return priority

    def _process_work_queue(self, priority, work_queue, task_executor):
        """
        Process the requests saved in KV Store queue.
        """
        try:
            if priority == PRIORITY_HIGH:
                self.logger.info("Processing high priority items.")
                self._process_summarization_ids(PRIORITY_HIGH, work_queue, task_executor)
            else:
                self.logger.info("Processing low priority items.")
                self._process_summarization_ids(PRIORITY_LOW, work_queue, task_executor)
        except Exception as e:
            self.logger.exception(f"Error processing work queue: {str(e)}")

    def _process_summarization_ids(self, priority, work_queue, task_executor):
        """
        Process summarization IDs from the work queue using SummarizationTaskExecutor.

        Args:
            priority (int): Priority level (e.g., PRIORITY_HIGH or PRIORITY_LOW).
            work_queue (WorkQueue): The work queue instance.
            task_executor (SummarizationTaskExecutor): The task executor instance.
        """
        try:
            limit = 1
            if priority == PRIORITY_HIGH:
                limit = 1
            elif priority == PRIORITY_LOW:
                limit = 5
            summarization_ids_req_id_map = {}
            dequeued_items = work_queue.dequeue(limit=limit, priority=priority)  # Returns a list of kvstore records

            for item in dequeued_items:
                # Extract summarization_id from the kvstore record
                summarization_id = item.get(KVSTORE_KEY)
                # Extract the request_id from the item if available
                request_id = item.get("request_id", "unknown")
                if summarization_id:
                    summarization_ids_req_id_map[summarization_id] = request_id

            if summarization_ids_req_id_map:
                self.logger.info(f"Submitting {priority} priority tasks: {summarization_ids_req_id_map}")

                # Set context for each summarization task
                for summarization_id in summarization_ids_req_id_map.keys():
                    set_current_summarization_id(summarization_id)
                    self.logger.info(f"Processing task for summarization {summarization_id}")

                task_executor.process(summarization_ids_req_id_map)
            else:
                self.logger.info(f"No {priority} priority tasks available.")
        except Exception as e:
            self.logger.exception(f"Error processing {priority} priority tasks: {str(e)}")

    def _shutdown_requested(self):
        """
        Check if a shutdown has been requested.
        """
        return self._shutdown_flag

    def _handle_shutdown_signal(self, signum, frame):
        """
        Signal handler to set the shutdown flag.

        Args:
            signum (int): The signal number received.
            frame (frame object): The current stack frame (or None).

        This method is called when a shutdown signal (e.g., SIGTERM or SIGINT) is received.
        It sets the _shutdown_flag to True, indicating that a shutdown has been requested.
        """
        self.logger.info(f"Received shutdown signal: {signum}")
        self._shutdown_flag = True


if __name__ == "__main__":
    sys.exit(ITSISummaryWorker().run(sys.argv))
