# encoding = utf-8

import gzip
import json
from datetime import datetime, timedelta
from constants import DEFAULT_DAILY_CONNECTIONS_BACKTRACK_DAYS, DC_STATES
from logger import LogLevel, Logger
from enum import Enum

__author__ = 'Alberto'


class TaskStatus(Enum):
    """An enumeration of task status."""

    NEW = 'NEW'
    IN_PROGRESS = 'IN_PROGRESS'
    DONE = 'DONE'
    FAILED = 'FAILED'
    PROCESSED = 'PROCESSED'


class DailyConnectionsManager:
    """A class for managing daily connections from the Guardicore management server."""

    def __init__(self, helper, ew, guardicore_utils):
        self.helper = helper
        self.ew = ew
        self.log = Logger(helper).log
        self.utils = guardicore_utils
        self.collect_allowed_connections = self.utils.is_allowed_configured(helper.get_arg("policy_verdict"))
        self.maximum_task_retries_per_date = int(self.helper.get_arg("maximum_task_retries_per_date"))
        self.tasks_statuses = self.utils.get_env_checkpoint(DC_STATES) or {}

    def collect_daily_connections(self):
        """Collects daily connections from the Guardicore management server."""
        self.update_tasks()
        unprocessed_dates = self.get_unprocessed_dates()

        if self.tasks_statuses and len(unprocessed_dates) == 0:
            self.log(LogLevel.INFO,
                     "All dates have already been processed. No new events for daily connections until tomorrow")
            return

        self.log(LogLevel.INFO, f"Collecting daily connections for {len(unprocessed_dates)} dates")

        for date in unprocessed_dates:
            task = self.tasks_statuses.get(date)

            if task.get("status") != TaskStatus.IN_PROGRESS.value:
                task = self.create_daily_task(date)

            if "error_code" in task and task.get("error_code") == "DocumentNotFound":
                self.tasks_statuses[date].update({"status": TaskStatus.PROCESSED.value})
                self.utils.save_env_checkpoint(DC_STATES, self.tasks_statuses)
                continue

            self.process_daily_task(date, task.get("task_id"))

    def get_unprocessed_dates(self):
        """
        Returns all tasks in the dictionary that are not in PROCESSED state.

        Returns:
            list: A list of dates that have not been processed.
        """
        return [date for date, status in self.tasks_statuses.items()
                if status.get("status") != TaskStatus.PROCESSED.value]

    def get_all_dates(self):
        """
        Get a list of dates in the format "%Y_%m_%d".

        This function retrieves the start and end dates if provided in input arguments,
        otherwise, it defaults to a date calculated by subtracting the default backtrack days
        from the current UTC date. The end date is set to the current UTC date.

        Returns:
            list: A list of dates in the format "%Y_%m_%d".
        """
        start_date_input = self.helper.get_arg("start_date")
        end_date_input = self.helper.get_arg("end_date")
        current_utc_date = datetime.utcnow()

        if start_date_input:
            start_date = datetime.strptime(start_date_input, "%Y/%m/%d")
        else:
            start_date = current_utc_date - timedelta(days=DEFAULT_DAILY_CONNECTIONS_BACKTRACK_DAYS)

        if end_date_input:
            end_date = datetime.strptime(end_date_input, "%Y/%m/%d")
        else:
            end_date = current_utc_date

        total_days = (end_date - start_date).days
        if end_date != current_utc_date:
            total_days += 1

        date_range = [(start_date + timedelta(days=x)).strftime("%Y_%m_%d") for x in range(total_days)]

        self.log(
            LogLevel.INFO,
            "Checking daily connection data for dates: {}",
            date_range
        )

        return date_range

    def update_tasks(self):
        """
        Update the tasks_statuses dictionary to include all dates within the range from start to end dates.

        Ensures each date in the range is included in the tasks_statuses dictionary.
        Processes retries for failed tasks and removes tasks outside the range if they are processed.
        """

        current_date_range = self.get_all_dates()

        for date in current_date_range:
            if date not in self.tasks_statuses:
                self.tasks_statuses[date] = {}

        for date, task in list(self.tasks_statuses.items()):
            task_status = task.get("status")

            if task_status == TaskStatus.FAILED.value:
                self.handle_retries(date, task)

        self.utils.save_env_checkpoint(DC_STATES, self.tasks_statuses)
        self.log(LogLevel.DEBUG, "task_statuses: {}", self.tasks_statuses)

    def handle_retries(self, date, task):
        """
        Handle retries for a failed task. If the maximum retries is reached, skip the date.
        """
        retries = task.get("retries", 0)
        task_id = task.get("task_id")

        if retries < self.maximum_task_retries_per_date:
            retries += 1
            self.log(LogLevel.INFO, "Will retry task {} for date {} in current run. Attempt {}", task_id, date, retries)
            self.tasks_statuses[date].update({"retries": retries})
        else:
            self.tasks_statuses[date].update({"status": TaskStatus.PROCESSED.value})
            self.log(LogLevel.ERROR, "Marking task {} for date {} as PROCESSED after {} attempts",
                     task_id, date, retries)

    def create_daily_task(self, date):
        """
        Create a daily task for the given date.

        Returns:
            The result of the request to create the daily task.
        """
        payload = {"index_day": date}
        if not self.collect_allowed_connections:
            payload.update({"filters": {"policy_verdict": ["blocked_by_source", "blocked_by_destination",
                                                           "alerted_by_management", "alerted_by_management"]}})

        return self.utils.request("daily_connections/task", method="POST", payload=payload, api_v4=True)

    def process_daily_task(self, date, task_id):
        """Wait and process the daily task, then download connections if available."""
        response = self.utils.request(f"daily_connections/task/{task_id}", api_v4=True)
        task_status = response.get("status")
        connections_count = response.get("connections_count", 0)
        self.tasks_statuses[date].update(response)

        if task_status == TaskStatus.DONE.value:
            if connections_count > 0:
                self.log(LogLevel.INFO, "Task {} completed with {} connections for date {}", task_id,
                         connections_count, date)
                self.download_and_process_connections(task_id, date, connections_count)
                self.log(LogLevel.INFO, "Finished processing daily connections for date {}", date)
            elif connections_count == 0:
                self.log(LogLevel.WARNING, "Task {} completed but no connections found for date {}", task_id, date)

            self.tasks_statuses[date].update({"status": TaskStatus.PROCESSED.value})

        elif task_status == TaskStatus.FAILED.value:
            logs = response.get("logs", "No reason provided")
            self.log(LogLevel.ERROR, "Task {} failed for date {}. Reason: {}", task_id, date, logs)
        else:
            self.log(LogLevel.INFO, "Task {} for date {} is in status '{}'. Processing on the next run",
                     task_id, date, task_status)

        self.utils.save_env_checkpoint(DC_STATES, self.tasks_statuses)

    def process_connection(self, conn):
        """Process a connection and write it to the Splunk index."""
        conn["data_type"] = "connection"
        conn["count"] = conn["count"] if "count" in conn else 1
        conn["rule_display_name"] = "RUL-{}".format(conn["policy_rule"][:8])
        conn["verdict"] = self.utils.get_verdict(conn)
        conn["exported_timestamp"] = self.utils.set_log_exported_timestamp(conn["slot_start_time"])
        self.utils.write_event(conn)

    def download_and_process_connections(self, task_id, date, connection_count):
        """Download and process the connections from the completed task."""

        response = self.utils.request(f"daily_connections/task/{task_id}/download", api_v4=True, raw_response=True)
        self.log(LogLevel.INFO, "Starting to download and process the GZIP file task {} for date {}...", task_id, date)
        processed_lines = 0
        with gzip.GzipFile(fileobj=response) as gzipped_file:
            percentage = 0
            for line in gzipped_file:
                try:
                    decoded_line = line.decode('utf-8')
                    json_line = json.loads(decoded_line)
                    self.process_connection(json_line)

                    processed_lines += 1
                    current_percentage = round((processed_lines * 100 / connection_count))
                    if current_percentage % 10 == 0 and percentage < current_percentage:
                        percentage = current_percentage
                        self.log(LogLevel.INFO, "Processing daily connections... {}% complete", percentage)
                except json.JSONDecodeError:
                    self.log(LogLevel.ERROR, "Skipping invalid line: {}", json_line)
                    continue
                except Exception as e:
                    # Log any other unexpected errors and continue
                    self.log(LogLevel.ERROR, "Unexpected error processing line: {}. Error: {}", decoded_line, str(e))
                    raise
