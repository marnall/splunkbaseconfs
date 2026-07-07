import os
import sys
from typing import Dict, Any, List, TYPE_CHECKING
import time
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import (
    ITSI_SUMMARY_WORKER_LOGGER_NAME,
    SUMMARIZATION_ID,
    STATUS,
    SUMMARY_TASK_STATUS_FAILED,
    SUMMARY_TASK_STATUS_SUCCESS,
    STATUS_IN_PROGRESS,
    STATUS_FAILED,
    STATUS_SUCCESS,
    SUMMARY_RESPONSE,
    ErrorMessage,
)
from util import setup_logging
from util.context_logging import get_context_logger, set_current_summarization_id

if TYPE_CHECKING:
    from itsi_summary_orchestrator_client import ITSISummaryOrchestratorClient
    from itsi_ai_assistant_client import ITSIAIAssistantClient
    from work_queue import WorkQueue


class SummarizationTaskHandler:
    """
    A class to handle the processing of summarization tasks based on summarization IDs.
    """

    def __init__(self, work_queue: "WorkQueue", orchestrator_client: "ITSISummaryOrchestratorClient",
                 itsi_ai_assistant_client: "ITSIAIAssistantClient") -> None:
        """
        Initialize the TaskHandler.

        Args:
            work_queue (WorkQueue): An instance of the WorkQueue to manage task statuses.
            orchestrator_client (ITSISummaryOrchestratorClient): An instance of ITSISummaryOrchestratorClient
                                                                 to interact with ITSI summary orchestrator service.
            itsi_ai_assistant_client (ITSIAIAssistantClient): An instance of SCSSummarizationServiceClient
                                                        to interact with the SCS summary generation service.
        """
        self.work_queue = work_queue
        self.orchestrator_client = orchestrator_client
        self.scs_client = itsi_ai_assistant_client
        # Initialize context logger that automatically includes summarization ID
        logger = setup_logging.get_logger(ITSI_SUMMARY_WORKER_LOGGER_NAME)
        self.logger = get_context_logger(logger)

    @staticmethod
    def check_valid_summarization_id(summarization_id):
        """
        Check if a summarization ID is valid

        Requirements:
        - Length must be 24
        - Contains only digits (0-9) and lowercase letters (a-z)
        - No uppercase letters, punctuation, or other characters

        Args:
            summarization_id (str): The ID string to check

        Returns:
            bool: True if ID is valid, False if invalid

        Or we can use a simple checking:

        return isinstance(summarization_id, str) and summarization_id.strip():
        """
        # Check if it's a string
        if not isinstance(summarization_id, str):
            return False

        # Check if length is 24
        if len(summarization_id) != 24:
            return False

        # Check if it contains only digits and lowercase letters
        # Use regex pattern ^[0-9a-z]{24}$ to match only digits and lowercase letters with length 24
        pattern = r'^[0-9a-z]{24}$'
        if not re.match(pattern, summarization_id):
            return False

        return True

    def handle_summarization_task(self, summarization_id: str, request_id: str = None) -> Dict[str, Any]:
        """
        Handle the processing of a single summarization task based on the summarization ID.

        For each summarization task, the process involves:
        1. Calling the ITSI summarization action endpoint to retrieve the list of ITSI-managed tools
           associated with the summarization ID.
        2. Using these tools to collect data and construct a prompt by processing the gathered data.
        3. Sending the constructed prompt to the SCS service endpoint to generate the summary with RCA.
        4. Updating the summarization ID's status in the work queue.
        5. Sending the generated summary response back to ITSI.

        Args:
            summarization_id (str): The unique identifier for the summarization task.
            request_id (str, optional): The unique request identifier for tracing.

        Returns:
            dict: A dictionary containing the result of the task processing, including the
                  summarization ID and its status.

        Raises:
            Exception: If an error occurs during task processing, the exception is re-raised
                       after marking the task as failed.
        """
        set_current_summarization_id(summarization_id)
        # Check whether the summarization id is valid at the very beginning of the task
        if SummarizationTaskHandler.check_valid_summarization_id(summarization_id):
            self.logger.info("The summarization_id is valid. Starting to handle summarization task.")
        else:
            self.logger.error("The summarization_id is invalid. Please enter another valid summarization id.")
            return {
                SUMMARIZATION_ID: summarization_id,
                STATUS: SUMMARY_TASK_STATUS_FAILED,
                "error": f"Invalid summarization_id: {summarization_id}"
            }

        try:
            # Mark the task as in-progress in the work queue and orchestrator
            self.logger.info(f"Request {request_id}: Starting task")
            start_time = time.time()
            self.work_queue.mark_status(summarization_id, status=STATUS_IN_PROGRESS)
            self.orchestrator_client.set_summary_status(summarization_id, status=STATUS_IN_PROGRESS)

            # Construct a payload
            payload_construct_start_time = time.time()

            payload = self.orchestrator_client.construct_itsi_ai_assistant_payload(summarization_id, request_id)

            payload_construct_time = time.time() - payload_construct_start_time
            self.logger.info(f"Request {request_id} profiling: Payload constructed in {payload_construct_time} seconds")
            if not payload:
                self.logger.error(f"Request {request_id}: No payload constructed")
                self.work_queue.mark_status(summarization_id, status=STATUS_FAILED)
                self.orchestrator_client.set_summary_status(summarization_id, status=STATUS_FAILED, error_message=ErrorMessage.ERROR_PAYLOAD_CONSTRUCTION_FAILED.value)
                # Clean up the steps_checked_metadata for failed payload construction
                self.orchestrator_client.steps_checked_manager.cleanup_metadata(summarization_id)
                return {
                    SUMMARIZATION_ID: summarization_id,
                    STATUS: SUMMARY_TASK_STATUS_FAILED,
                    "error": f"No payload constructed for summarization id str {summarization_id}"
                }

            summary_generation_start_time = time.time()
            # Send the prompt to the SCS service endpoint to generate the summary and RCA
            summary_response = self._generate_summary(payload, summarization_id, request_id)
            summary_generation_time = time.time() - summary_generation_start_time
            self.logger.info(f"Request {request_id} profiling: Summary generated in {summary_generation_time} seconds")

            # Mark the task as successful in the work queue and orchestrator,
            # and save the summary response to the KV store
            self.work_queue.mark_status(summarization_id, status=STATUS_SUCCESS)
            # Clean up the steps_checked_metadata from the orchestrator client to avoid accumulated data
            self.orchestrator_client.steps_checked_manager.cleanup_metadata(summarization_id)
            self.orchestrator_client.save_summary(summarization_id, summary_response)

            total_time = time.time() - start_time
            self.logger.info(f"Request {request_id} profiling: Task completed successfully in {total_time} seconds")
            # Return the result of the task processing
            return {
                SUMMARIZATION_ID: summarization_id,
                STATUS: SUMMARY_TASK_STATUS_SUCCESS,
                SUMMARY_RESPONSE: summary_response
            }
        except Exception as e:
            # Handle exceptions by marking the task as failed
            self.logger.exception(f"Request {request_id}: Error processing")
            self.work_queue.mark_status(summarization_id, status=STATUS_FAILED)
            self.orchestrator_client.set_summary_status(summarization_id, status=STATUS_FAILED, error_message=ErrorMessage.ERROR_LLM_CALL_FROM_SCS_FAILED.value)
            # Clean up the steps_checked and metadata for failed tasks as well to avoid accumulated data
            self.orchestrator_client.steps_checked_manager.cleanup_metadata(summarization_id)
            raise e

    def _generate_summary(self, payload: Dict[str, Any], summarization_id: str, request_id: str) -> Dict[str, Any]:
        """
        Send the payload to the SCS service endpoint to generate the summary and RCA.

        Args:
            payload (Dict[str, Any]): The payload to send to the SCS service.
            summarization_id (str): The summarization ID for context logging and tracing.
            request_id (str, optional): The unique request identifier for tracing.

        Returns:
            dict: The response from the SCS service containing the summary and RCA.

        Raises:
            Exception: If the SCS service call fails or returns an error.
        """
        return self.scs_client.generate_summary(payload, summarization_id, request_id)
