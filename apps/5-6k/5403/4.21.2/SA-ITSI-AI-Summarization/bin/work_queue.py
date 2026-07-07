import os
import sys
from typing import Optional, List, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Add the directory where this script resides to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from splunklib.binding import HTTPError

from constants import (
    ITSI_SUMMARY_WORK_QUEUE,
    ITSI_SUMMARY_WORKER_LOGGER_NAME,
    STATUS_INITIATED,
    KVSTORE_KEY,
    STATUS,
    CREATED_AT,
    UPDATED_AT,
    ATTEMPTS,
    STATUS_IN_PROGRESS,
    STATUS_SUCCESS, STATUS_FAILED, PRIORITY, PRIORITY_LOW
)

from util import setup_logging, base_util
from util.context_logging import get_context_logger, set_current_summarization_id

class WorkQueue:
    """
    A reusable class to manage ITSI summarization requests stored in a Splunk KV Store collection.
    This queue is backed by a KV Store collection, supporting basic operations such as enqueue, dequeue, status updates, and purging old items.

    Example usage:
        # Initialize the work queue with an authenticated Splunk service instance
        work_queue = WorkQueue(self.service)

        # Enqueue a new summarization request
        work_queue.enqueue("123")

        # Dequeue summarization requests
        items = work_queue.dequeue(limit=5)

        # Mark an item as successful
        work_queue.mark_status("123", STATUS_SUCCESS)

        # Purge old items
        purged_count = work_queue.purge_old_records(retention_period_hours=2)
    """

    def __init__(self, service: Any, collection_name: str = ITSI_SUMMARY_WORK_QUEUE) -> None:
        """
        Initialize the WorkQueue with the given Splunk SDK service and collection name.

        Args:
            service (splunklib.client.Service): An authenticated Splunk service instance.
            collection_name (str): KV Store collection name for the queue.
        """
        self.service = service
        self.collection_name = collection_name
        logger = setup_logging.get_logger(ITSI_SUMMARY_WORKER_LOGGER_NAME)
        self.logger = get_context_logger(logger)
        self.collection = self._initialize_collection()

    def _initialize_collection(self) -> Any:
        """
        Initialize or retrieve the KV Store collection.

        Returns:
            splunklib.client.Collection: A reference to the KV Store collection.
        """
        try:
            kvstore = self.service.kvstore
            if self.collection_name not in kvstore:
                self.logger.info(f"KV Store collection '{self.collection_name}' not found. Creating it.")
                return kvstore.create(self.collection_name)
            return kvstore[self.collection_name]
        except Exception as e:
            self.logger.exception(f"Failed to initialize KV Store collection '{self.collection_name}': {e}")
            raise

    def enqueue(self, summarization_id: str, priority: int = PRIORITY_LOW, request_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Enqueue a new summarization request into the KV Store-backed work queue.

        Args:
            summarization_id (str): Unique summarization ID (used as the document key).
            priority (int, optional): Priority of the item (default is PRIORITY_LOW).
            request_id (str, optional): Unique request ID for tracing.

        Returns:
            dict | None: The inserted document, or None if insertion fails.
        """
        set_current_summarization_id(summarization_id)
        if not self._is_valid_summarization_id(summarization_id):
            self.logger.warning("enqueue() called with invalid or empty summarization_id.")
            return None

        current_time_epoch = base_util.get_utc_now()
        work_item = {
            KVSTORE_KEY: summarization_id,
            STATUS: STATUS_INITIATED,
            CREATED_AT: current_time_epoch,
            UPDATED_AT: current_time_epoch,
            ATTEMPTS: 0,
            PRIORITY: priority
        }
        
        # Add request_id if provided
        if request_id:
            work_item["request_id"] = request_id
            
        try:
            self.collection.data.batch_save(work_item)
            self.logger.info(f"Enqueued summarization task with priority '{priority}' with request_id={request_id} successfully.")
            return work_item
        except HTTPError as e:
            self.logger.exception(f"Splunk HTTP error while enqueuing: {e.status} - {e.reason} with request_id={request_id}")
        except Exception as e:
            self.logger.exception(f"Unexpected error while enqueuing: {str(e)} with request_id={request_id}")
        return None

    def dequeue(self, limit: int = 1, priority: int = PRIORITY_LOW, max_attempts: Optional[int] = None) -> List[
        Dict[str, Any]]:
        """
        Dequeues up to `limit` pending summarization ID from the queue and marks them as in_progress.
        Optionally filters out items that have exceeded max_attempts.

        Args:
            limit (int): Number of summarization IDs to dequeue.
            priority (int): Priority of the summarization ID to dequeue.
            max_attempts (int, optional): Only dequeue items with attempts less than this number.

        Returns:
            List[dict]: List of dequeued and updated work items. Empty list if none found.

        Explanation:
        - max_attempts: This parameter is useful for controlling the number of times an item can be dequeued and processed.
          If an item has been attempted more than the specified max_attempts, it will be excluded from the dequeue operation.
          This helps in preventing infinite retries on items that may be problematic. Such items can be deleted from the queue
          via the saved search that runs periodically.
        """
        try:
            query = {STATUS: STATUS_INITIATED, PRIORITY: priority}

            if max_attempts is not None:
                # Query only summarization IDs with fewer than `max_attempts` attempts
                query["$or"] = [
                    {ATTEMPTS: {"$lt": max_attempts}},  # attempts field exists and < max
                    {ATTEMPTS: {"$exists": False}}  # or attempts field not yet set
                ]

            pending_items = self.collection.data.query(query=query, sort=CREATED_AT, count=limit)

            if not pending_items:
                self.logger.info("No pending items found in work queue.")
                return []

            now = base_util.get_utc_now()
            updated_items = []

            for item in pending_items:
                summarization_id = item[KVSTORE_KEY]
                set_current_summarization_id(summarization_id)
                request_id = item.get("request_id", "unknown")
                updated_doc = {
                    STATUS: STATUS_IN_PROGRESS,
                    UPDATED_AT: now,
                    ATTEMPTS: item.get(ATTEMPTS, 0) + 1
                }
                self.collection.data.update(summarization_id, updated_doc)
                self.logger.info(f"Dequeued with request_id={request_id} as in_progress")
                item.update(updated_doc)
                updated_items.append(item)

            return updated_items

        except HTTPError as e:
            self.logger.exception(f"Splunk HTTP error during dequeue: {e.status} - {e.reason}")
        except Exception as e:
            self.logger.exception(f"Unexpected error during dequeue: {str(e)}")

        return []

    def mark_status(self, summarization_id: str, status: int) -> bool:
        """
        Marks the specified KV Store summarization ID with the given status.

        Args:
            summarization_id (str): Unique summarization ID in the work queue.
            status (int): Status to mark the summarization ID with (e.g., 2 (STATUS_SUCCESS), 3 (STATUS_FAILED)).

        Returns:
            bool: True if the item was updated successfully.

        Raises:
            ValueError: If the input arguments are invalid.
            RuntimeError: If the update operation fails.
        """
        if not self._is_valid_summarization_id(summarization_id):
            raise ValueError("Invalid or empty summarization_id provided.")

        if status not in [STATUS_SUCCESS, STATUS_FAILED, STATUS_IN_PROGRESS]:
            raise ValueError(f"Invalid status: {status}")

        self._validate_status(status)

        set_current_summarization_id(summarization_id)
        try:
            current_time_epoch = base_util.get_utc_now()
            self.collection.data.update(summarization_id, {
                STATUS: status,
                UPDATED_AT: current_time_epoch
            })
            self.logger.info(f"Marked summarization status as {status}.")
            return True

        except HTTPError as e:
            self.logger.exception(
                f"KV Store HTTP error while updating status: {e.status} - {e.reason}")
            raise RuntimeError(f"HTTP error while updating status: {e.reason}") from e

        except Exception as e:
            self.logger.exception(f"Unexpected error while updating status: {str(e)}")
            raise RuntimeError(f"Unexpected error: {str(e)}") from e

    def get_by_summarization_id(self, summarization_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a record from the work queue by Summarization ID.

        Args:
            summarization_id (str): Unique identifier for the record in the work queue.

        Returns:
            dict | None: The retrieved item, or None if not found.
        """
        if not isinstance(summarization_id, str) or not summarization_id.strip():
            self.logger.warning("get_by_summarization_id() called with invalid or empty summarization_id.")
            return None

        try:
            record = self.collection.data.query_by_id(summarization_id)
            if record:
                self.logger.info(f"Retrieved item from the work queue")
                return record
            else:
                self.logger.info(f"Record from the work queue can not be found.")
                return None

        except HTTPError as e:
            self.logger.exception(f"KV Store HTTP error while retrieving item': {e.status} - {e.reason}")
        except Exception as e:
            self.logger.exception(f"Unexpected error while retrieving item: {str(e)}")

        return None

    def purge_stale_records(self, retention_period_hours: int = 48) -> int:
        """
        Remove stale successful, failed, and in-progress Summarization IDs from the queue.

        Args:
            retention_period_hours (int, optional): The retention period in hours. Summarization IDs older than this will be purged.

        Returns:
            int: Number of items purged.
        """
        try:
            # Calculate the cutoff time in epoch
            current_time_epoch = base_util.get_utc_now()
            cutoff_time_epoch = current_time_epoch - (retention_period_hours * 3600)

            self.logger.info(f"Purging records older than epoch time: {cutoff_time_epoch}")

            # Query for items older than the cutoff time
            query = {
                UPDATED_AT: {"$lt": cutoff_time_epoch}
            }

            # Retrieve old items
            old_items = self.collection.data.query(query=query)
            purged_count = 0

            # Check the status of each item and delete if it matches the specified statuses
            for item in old_items:
                try:
                    # Ensure the UPDATED_AT value is less than cutoff_time_epoch
                    if item[UPDATED_AT] < cutoff_time_epoch:
                        self.logger.info(f"Deleting item with ID: {item[KVSTORE_KEY]} and UPDATED_AT: {item[UPDATED_AT]}")
                        self._validate_status(item[STATUS])
                        self.collection.data.delete_by_id(item[KVSTORE_KEY])
                        purged_count += 1
                    else:
                        self.logger.warning(
                            f"Skipping record with UPDATED_AT: {item[UPDATED_AT]} as it is not older than cutoff_time_epoch.")
                except ValueError:
                    self.logger.warning(f"Skipping item with invalid status: {item[STATUS]}")

            self.logger.info(f"Purged {purged_count} old records from the queue.")
            return purged_count

        except HTTPError as e:
            self.logger.exception(f"Splunk HTTP error during purge: {e.status} - {e.reason}")
        except Exception as e:
            self.logger.exception(f"Unexpected error during purge: {str(e)}")

        return 0

    @staticmethod
    def _validate_status(status: int) -> None:
        """
        Validates if the given status is one of the predefined valid statuses.

        Args:
            status (int): The status to validate.

        Raises:
            ValueError: If the status is not valid.
        """
        valid_statuses = [STATUS_SUCCESS, STATUS_FAILED, STATUS_IN_PROGRESS]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")

    @staticmethod
    def _is_valid_summarization_id(summarization_id: str) -> bool:
        """
        Verifies if the given summarization ID is valid.

        A valid summarization ID must be a non-empty string with no leading or trailing whitespace.

        Args:
            summarization_id (str): The summarization ID to verify.

        Returns:
            bool: True if the summarization ID is valid, False otherwise.
        """
        return isinstance(summarization_id, str) and bool(summarization_id.strip())
