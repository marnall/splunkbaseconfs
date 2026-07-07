import concurrent.futures
import os
import sys
from typing import Callable, List, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import (
    ITSI_SUMMARY_WORKER_LOGGER_NAME,
    SUMMARIZATION_ID,
    STATUS,
    STATUS_IN_PROGRESS,
    STATUS_SUCCESS,
    STATUS_FAILED,
    SUMMARY_TASK_STATUS_FAILED, SUMMARY_RESPONSE
)
from util import setup_logging
from util.context_logging import get_context_logger, set_current_summarization_id


class SummarizationTaskExecutor:
    """
    A class for managing and executing the processing of ITSI summarization IDs in parallel using threads.

    This class acts as a coordinator for processing tasks, delegating the actual processing logic to a
    user-defined `task_handler`. It interacts with a `WorkQueue` to manage the status of summarization
    IDs and ensures that tasks are executed concurrently with a configurable number of threads.
    """

    def __init__(self, task_handler: Callable[[str, str], Dict[str, Any]], work_queue: Any, max_threads: int = 5) -> None:
        """
        Initialize the ITSISummaryProcessor.

        Args:
        task_handler (callable): A user-defined function to process each summarization ID and request ID.
        work_queue (WorkQueue): An instance of the `WorkQueue` class to manage summarization ID statuses.
        max_threads (int): The maximum number of threads to use for parallel processing.
        """
        if not callable(task_handler):
            raise ValueError("task_handler must be callable.")
        if not work_queue:
            raise ValueError("work_queue instance is required.")
        if not isinstance(max_threads, int) or max_threads <= 0:
            raise ValueError("max_threads must be a positive integer.")

        self.task_handler = task_handler
        self.work_queue = work_queue
        self.max_threads = max_threads

        # Initialize context logger that automatically includes summarization ID
        logger = setup_logging.get_logger(ITSI_SUMMARY_WORKER_LOGGER_NAME)
        self.logger = get_context_logger(logger)

    def process(self, summarization_ids: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a list of summarization IDs in parallel.

        Args:
            summarization_ids (Dictionary): Dictionary of summarization ID:request_id.

        Returns:
        list: A list of dictionaries, where each dictionary contains the following keys:
            - summarization_id (str): The ID of the summarization task.
            - status (str): The status of the task, e.g., "success" or "failed".
            - summary_response (Dict[str, Any], optional): The response from the summarization task handler. It is None if the task failed.
            - error (str, optional): The error message if the task failed. It is None if the task succeeded.

            Example:
                [
                    {
                        "summarization_id": "id1",
                        "status": "success",
                        "summary_response": {"summary": "generated summary"},
                        "error": None
                    },
                    {
                        "summarization_id": "id2",
                        "status": "failed",
                        "summary_response": None,
                        "error": "Error message"
                    }
                ]
                """
        if not isinstance(summarization_ids, dict) or not all(isinstance(sid, str) for sid in summarization_ids.keys()):
            raise ValueError("summarization_ids must be a dictionary with string keys.")

        results: List[Dict[str, Any]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            future_to_id = {executor.submit(self._process_and_update, sid, request_id): sid for sid, request_id in summarization_ids.items()}
            for future in concurrent.futures.as_completed(future_to_id):
                summarization_id = future_to_id[future]
                try:
                    result = future.result()
                    results.append(self._create_result_dict(
                        summarization_id=result.get(SUMMARIZATION_ID),
                        status=result.get(STATUS),
                        summary_response=result.get(SUMMARY_RESPONSE),
                        error=None
                    ))
                except Exception as e:
                    self.logger.exception(f"Error processing: {str(e)}")
                    results.append(self._create_result_dict(
                        summarization_id=summarization_id,
                        status=SUMMARY_TASK_STATUS_FAILED,
                        summary_response=None,
                        error=str(e)
                    ))
        # These results are primarily used for unit test verification and debugging,
        # and may also be leveraged for telemetry logging in the future.
        return results

    def _process_and_update(self, summarization_id: str, request_id: str = None) -> Dict[str, Any]:
        """
        Handle a summarization ID and update its status in the WorkQueue.
        This method is called by the thread pool executor to process each summarization ID.
        It marks the summarization ID as in-progress, calls the task handler, and then updates the status.
        If an error occurs, it marks the summarization ID as failed.

        Args:
            summarization_id (str): The summarization ID to process.
            request_id (str, optional): The request ID for tracing.

        Returns:
            dict: The result of processing.
        """
        if not isinstance(summarization_id, str):
            raise ValueError("summarization_id must be a string.")

        try:
            # Set the summarization context for this thread
            set_current_summarization_id(summarization_id)

            # Mark as in-progress
            self.work_queue.mark_status(summarization_id, status=STATUS_IN_PROGRESS)
            result = self.task_handler(summarization_id, request_id)
            # Mark as success
            self.work_queue.mark_status(summarization_id, status=STATUS_SUCCESS)
            return result
        except Exception as e:
            # Mark as failed
            self.work_queue.mark_status(summarization_id, status=STATUS_FAILED)
            self.logger.exception(f"Failed to process: {str(e)}")
            raise e

    def _create_result_dict(self, summarization_id: str, status: str, summary_response: Any = None,
                            error: str = None) -> \
            Dict[str, Any]:
        return {
            SUMMARIZATION_ID: summarization_id,
            STATUS: status,
            SUMMARY_RESPONSE: summary_response,
            "error": error
        }
