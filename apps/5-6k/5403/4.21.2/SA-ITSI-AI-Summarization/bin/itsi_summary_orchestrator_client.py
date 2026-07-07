import json
import os
import re
import time
import uuid
import sys
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple, Set
from dateutil.parser import parse

# Add the "lib" directory to the Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Add the directory where this script resides to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from itsi_summary_timeseries_collector import (
    ITSISummaryTimeseriesCollector,
    ServiceAncestorFinder,
)
from steps_checked_manager import StepsCheckedManager
from itsi_ai_assistant_client import ITSIAIAssistantClient

import numpy as np
import pandas as pd
import constants
from util import setup_logging
from util.context_logging import get_context_logger, set_current_summarization_id
from util.spl_job_manager import SplJobManager


class ITSISummaryOrchestratorClient:
    def __init__(self, service, itsi_ai_assistant_client):
        self.service = service
        self.spl_job_manager = SplJobManager(service)
        self.timeseries_collector = ITSISummaryTimeseriesCollector(self)

        # Initialize context logger that automatically includes summarization ID
        logger = setup_logging.get_logger()
        self.logger = get_context_logger(logger)
        self.itsi_ai_assistant_client = itsi_ai_assistant_client

        # In production, the following five functions will be executed to fill their corresponding steps_checked fields:
        #
        # Field                              | Function                             | Type
        # -----------------------------------|--------------------------------------|--------
        # checked_impacted_items             | get_service_kpi_ids                  | List
        # checked_alerts                     | get_and_clean_alerts                 | Dict
        # checked_summary_data               | get_kpi_and_entity_ts                | Dict
        # checked_topology_data              | get_services_topology                | Dict
        # checked_service_impact_analysis    | collect_service_impact_analysis      | Dict
        # custom_queries_data                | get_and_clean_custom_queries         | List

        # Initialize the steps checked manager
        self.steps_checked_manager = StepsCheckedManager()

    """
    Call ITSI Summary Orchestrator to update status
    """

    def set_summary_status(self, summarization_id, status, error_message=""):
        if isinstance(error_message, str):
            update_args = self.get_update_status_args(
                summarization_id, status, error_message
            )
            self.call_tool(constants.UPDATE_SUMMARIZATION, update_args)
        else:
            self.logger.error(
                f"The error_message should be a string, but got: {type(error_message)}"
            )

    """
    Call ITSI Summary Orchestrator to update status to success & save summary to KV store
    """

    def save_summary(self, summarization_id, summarization):
        self.call_tool(
            constants.UPDATE_SUMMARIZATION,
            self.get_update_summary_args(summarization_id, summarization),
        )

    """
    Call GET on ITSI summary_action endpoint to get list of supported actions for this summarization_id
    """

    def get_tools_list(self) -> List[Dict[str, Any]]:
        """
        Get the list of supported tools for the ITSI Summary Orchestrator.
        This GET call will return a list of tools, each tool is a dictionary where the keys are tool's name,
        tool's arguments and tool's return_type.
        e.g:
            [
                {
                    "name": "get_services_topology",
                    "arguments": [
                        [
                            "summarization_id",
                            "str"
                        ]
                    ],
                    "return_type": "dict"
                },
                ...
            ]
        The safe_network_call will return None if the call fails, so we return an empty list `[]` in that case.
        """
        params = {
            constants.TARGET_TYPE: constants.EPISODE  # this parameter is required
        }
        return self.safe_network_call(self.service.get, **params) or []

    @staticmethod
    def check_valid_status(status):
        if status not in [
            constants.STATUS_INITIATED,
            constants.STATUS_IN_PROGRESS,
            constants.STATUS_SUCCESS,
            constants.STATUS_FAILED,
            constants.STATUS_TERMINATED,
        ]:
            raise ValueError(f"Invalid status code: {status}")

    @staticmethod
    def get_update_status_args(
        summarization_id: str, status: str, error_message: str = ""
    ) -> Dict[str, Any]:
        """
        Construct the arguments dictionary for updating the summary status.
        Includes error_message only if status is STATUS_FAILED.

        Args:
            summarization_id (str): The summarization ID.
            status (str): The status to set.
            error_message (str, optional): The error message if status is failed.

        Returns:
            Dict[str, Any]: The updated status constructed for the update_summarization ITSI API.
        """
        ITSISummaryOrchestratorClient.check_valid_status(status)
        summary_dict = {constants.STATUS: status}
        if status == constants.STATUS_FAILED and error_message:
            summary_dict[constants.ERROR_MESSAGE] = error_message
        return {
            constants.SUMMARIZATION_ID: summarization_id,
            constants.SUMMARIZATION: summary_dict,
        }

    @staticmethod
    def get_update_summary_args(summarization_id, summarization):
        return {
            constants.SUMMARIZATION_ID: summarization_id,
            constants.SUMMARIZATION: {
                constants.STATUS: constants.STATUS_SUCCESS,
                constants.SUMMARIZATION: summarization,
            },
        }

    """
    Use the ITSI summary_action endpoint to call a tool for a given summarization_id
    Example body:
    {
        "name": "get_services_topology",
        "args" : { "summarization_id": "12345"}
    }
    """

    def call_tool(self, tool_name, arguments):
        # The reason why we added the header `json_header = [("Content-Type", "application/json")]` is that:
        # when testing the call_tool function in the CO2 environment, the `safe_network_call` fails when the header is missing.
        # The idea to add header comes from the `submit_batch_document` function:
        # https://cd.splunkdev.com/rchristensen/main/-/blob/develop/qa/platform/functional/kvstore/local/suite_unit/test_unit.py
        json_header = [("Content-Type", "application/json")]
        body = {"name": tool_name, "args": arguments}
        return self.safe_network_call(
            self.service.post, headers=json_header, body=json.dumps(body)
        )

    """
    Use the ITSI summary_action endpoint to call a tool for severity mapping
    """

    def call_tool_get_severity(self):
        params = {
            "output_mode": "json",  # this parameter is required
        }
        return self.safe_network_call_get_severity(self.service.get, **params) or {}

    def extract_and_unescape_spl(
        self, data: Dict[str, str], spl_key: str = constants.SPL_KEY
    ) -> str:
        """
        Extracts the SPL string from a JSON-wrapped response and unescapes any escaped characters.

        Parameters:
        - data: Dict[str, str] - A JSON object that contains the "spl" field with escaped quotes.

        Returns:
        - str - The unescaped SPL query.
        """
        if spl_key in data:
            return data[spl_key]
        else:
            self.logger.error(f"'{spl_key}' key not found in the response data.")
            return ""

    """
    Call ITSI Summary Orchestrator to get all alerts for this summarization_id
    This function will also clean the alerts to make them more concise
    and easier to pass to the LLM.
    The alerts are sorted by time so the LLM can take the order into account
    (earlier alerts are more likely to be causal).
    The alerts are passed to the LLM as a string, with each alert on a new line.
    We also include the values of the single-valued columns, as this information may be useful for the root cause.
    """

    def get_and_clean_alerts(self, summarization_id: str) -> Dict[str, Any]:
        alert_info = {}
        try:
            # Call ITSI Summary Orchestrator to get all alerts for this summarization_id
            alerts_spl_json = self.call_tool(
                constants.GET_ALL_ALERTS, {constants.SUMMARIZATION_ID: summarization_id}
            )
            if not alerts_spl_json:
                self.logger.error(
                    f"{constants.GET_ALL_ALERTS} function return an empty alerts_spl_json"
                )
                raise Exception(
                    constants.ErrorMessage.ERROR_PAYLOAD_CONSTRUCTION_FAILED.value
                )

            # Run the alerts_spl to get the alerts
            alerts_spl = self.extract_and_unescape_spl(alerts_spl_json)
            if alerts_spl == "":
                self.logger.error("Failed to extract SPL from the response.")
                raise Exception(
                    constants.ErrorMessage.ERROR_PAYLOAD_CONSTRUCTION_FAILED.value
                )

            self.logger.info(f"Original SPL for alerts: {alerts_spl}")
            steps_checked_metadata = (
                self.steps_checked_manager.get_or_initialize_metadata(summarization_id)
            )
            alerts_spl_with_time_range = self.add_time(
                alerts_spl,
                steps_checked_metadata["episode_start_time"],
                steps_checked_metadata["episode_end_time"],
            )
            self.logger.info(
                f"SPL for alerts after adding time range: {alerts_spl_with_time_range}"
            )
            results, sid, error = self.spl_job_manager.run_query(
                alerts_spl_with_time_range, search_purpose="get all alerts"
            )
            if not results:
                self.logger.error(f"Failed to run query with sid {sid}: {error}")
                raise Exception(
                    constants.ErrorMessage.ERROR_PAYLOAD_CONSTRUCTION_FAILED.value
                )

            # Record the number of alerts to fill into the description for the `checked_alerts` field in steps_checked
            num_of_alerts = len(results)
            self.steps_checked_manager.update_num_alerts(
                summarization_id, num_of_alerts
            )

            self.logger.info(
                f"The original number of alerts found from the get_and_clean_alerts is: {num_of_alerts}"
            )
            # Convert search results to a df
            alerts_df = pd.DataFrame.from_records(results)
            self.logger.debug(f"Columns: {list(alerts_df.columns)}")

            # Make alerts more concise so we can input them to the LLM
            # Then add service, KPI, and entity information to the prompt
            alert_info = self.get_alerts_text_for_prompt(alerts_df)
            if not alert_info:
                return alert_info
            service_kpi_str = self.get_service_kpi_str(summarization_id)
            service_kpi_entity_info = ""
            if service_kpi_str:
                service_kpi_entity_info += service_kpi_str
            entity_str = self.get_entity_str(summarization_id)
            if entity_str:
                service_kpi_entity_info += "\n" + entity_str
            alert_info["service_kpi_entity_info"] = service_kpi_entity_info
            self.logger.debug(f"alert_info for prompt:\n{alert_info}")
            return alert_info

        finally:
            # Track the function execution result and record it to steps checked
            if "alerts" in alert_info:
                self.steps_checked_manager._record_function_status_for_steps_checked(
                    summarization_id, alert_info["alerts"]
                )
            else:
                self.steps_checked_manager._record_function_status_for_steps_checked(
                    summarization_id, ""
                )

    def get_service_kpi_str(self, summarization_id):
        """
        Add service and KPI information to the prompt for the summarization.
        This function is called to gather information about services and KPIs
        that are relevant to the summarization task.

        Args:
            summarization_ID (str): The ID of the summarization task.

        Returns:
            str: A string containing the service and KPI information.
        """
        # Get the service and KPI information
        service_kpi_str = ""

        # Note that I can't just call get_service_kpi_ids because that doesn't give me the service names
        # I need the service names and IDs, and the KPI names and IDs
        args = {
            constants.SUMMARIZATION_ID: summarization_id,
        }

        # Get service & KPI info
        res_dict = self.call_tool(constants.GET_IMPACTED_SERVICE_ID_AND_KPI_ID, args)
        # Response format:
        """
        {
            "impacted_services": [
                { "service_id": "id1", "service_name": "name" }
            ],
            "impacted_kpis": [
                { "kpi_id": "id", "kpi_name": "name", "service_id": "id1" }
            ]
        }
        """
        try:
            impacted_services = res_dict.get(constants.IMPACTED_SERVICES, [])
            impacted_kpis = res_dict.get(constants.IMPACTED_KPIS, [])

            # Format services
            if impacted_services:
                service_kpi_str += "Services:\n"
                for service in impacted_services:
                    service_id = service.get(constants.SERVICE_ID, "")
                    service_name = service.get(constants.SERVICE_NAME, "")
                    service_kpi_str += f"{service_id}: {service_name}\n"
                service_kpi_str += "\n"

            # Format KPIs
            if impacted_kpis:
                service_kpi_str += "KPIs:\n"
                for kpi in impacted_kpis:
                    kpi_id = kpi.get(constants.KPI_ID, "")
                    kpi_name = kpi.get(constants.KPI_NAME, "")
                    service_kpi_str += f"{kpi_id}: {kpi_name}\n"

        except Exception as e:
            self.logger.error(
                f"Failed to get service and KPI info from {constants.GET_IMPACTED_SERVICE_ID_AND_KPI_ID}: {e}"
            )

        return service_kpi_str

    def get_entity_str(self, summarization_id: str) -> str:
        # Get entity info
        args = {
            constants.SUMMARIZATION_ID: summarization_id,
        }
        res_dict = self.call_tool(constants.GET_IMPACTED_ENTITIES, args)
        """
        {
            "entries": [
                {
                    "entity_name": "amarillo2.usa.com",
                    "entity_id": "4d47137e-c3b7-4a04-9933-d9aa5eea618c"
                },
                {
                    "entity_name": "amarillo1.usa.com",
                    "entity_id": "5016d211-a09a-416d-8d30-398342dc37fa"
                },
                {
                    "entity_name": "amarillo.usa.com",
                    "entity_id": "4306891c-a33f-47b9-818d-dc1e14624ef2"
                }
            ]
        }
        """
        entity_str = ""

        try:
            impacted_entities = res_dict.get("entries", [])
            if impacted_entities:
                entity_str += "Entities:\n"
                for entity in impacted_entities:
                    entity_id = entity.get(constants.ENTITY_ID, "")
                    entity_name = entity.get(constants.ENTITY_NAME, "")
                    entity_str += f"{entity_id}: {entity_name}\n"
        except Exception as e:
            self.logger.error(
                f"Failed to get entity info from {constants.GET_IMPACTED_ENTITIES}: {e}"
            )

        return entity_str

    def get_severity_mappings(self) -> Dict[str, str]:
        self.logger.info("Starting to call call_tool_get_severity")
        get_severity_response = self.call_tool_get_severity()
        self.logger.info("Finished call_tool_get_severity")
        self.logger.debug(f"The get_severity_response is {get_severity_response}")
        if not get_severity_response:
            return {constants.SEVERITY_LABEL_INFO: 1}
        get_severity_entry_list = get_severity_response.get("entry", [])
        severity_mappings = {}
        for entry in get_severity_entry_list:
            severity_id = entry.get("name", constants.DEFAULT_SEVERITY_ID_CRITICAL)
            severity_label = entry.get("content", {}).get(
                "label", constants.SEVERITY_LABEL_CRITICAL
            )
            severity_mappings[severity_label] = str(severity_id)
        self.logger.info(
            f"At the end of the get_severity_mappings function, severity_mapping={severity_mappings}"
        )
        return severity_mappings

    def filter_large_episode_with_severity_and_map_id_to_level(self, alerts_df):
        # Start to filter alerts by severity
        severity_mappings = self.get_severity_mappings()

        # Step 1: Filter out alerts when their severity level is INFO
        # Check if the severity field exists
        if (
            constants.EVENT_IDENTIFIER_STRING not in alerts_df.columns
            or constants.SEVERITY_ID not in alerts_df.columns
        ):
            return alerts_df

        # Check if this is a large episode
        number_unique_event_identifier = alerts_df[
            constants.EVENT_IDENTIFIER_STRING
        ].nunique()
        self.logger.info(
            f"Number of unique event identifiers: {number_unique_event_identifier}, filtering alerts with severity."
        )
        if number_unique_event_identifier <= constants.LARGE_EPISODE_THRESHOLD:
            return alerts_df

        # Ensure SEVERITY_ID column is string format for consistent comparison
        alerts_df[constants.SEVERITY_ID] = alerts_df[constants.SEVERITY_ID].astype(str)
        # Filter out the alerts with "severity" equal to INFO level
        alerts_df = alerts_df[
            alerts_df[constants.SEVERITY_ID]
            != severity_mappings[constants.SEVERITY_LABEL_INFO]
        ]

        # Step 2: Map severity id to severity level
        severity_column = None

        # Determine which severity column to use
        if constants.SEVERITY_ID in alerts_df.columns:
            severity_column = constants.SEVERITY_ID
        elif "severity" in alerts_df.columns:
            severity_column = "severity"

        # If we found a severity column, map it to the severity label
        if severity_column:
            # Ensure severity values are strings for consistent comparison
            alerts_df[severity_column] = alerts_df[severity_column].astype(str)

            # Create a reverse mapping from severity ID to severity level
            reverse_severity_mapping = {v: k for k, v in severity_mappings.items()}

            # Map severity IDs to their corresponding labels
            alerts_df["severity_label"] = alerts_df[severity_column].map(
                reverse_severity_mapping
            )

            # Log warning for unmapped severity IDs
            unmapped_ids = alerts_df[alerts_df["severity_label"].isna()][
                severity_column
            ].unique()
            if len(unmapped_ids) > 0:
                self.logger.warning(
                    f"Some severity IDs could not be mapped to labels: {unmapped_ids} based on the mapping: {reverse_severity_mapping}"
                )

            alerts_df.drop(columns=[severity_column], inplace=True)
        return alerts_df

    def get_alerts_text_for_prompt(self, alerts_df: pd.DataFrame) -> str:
        # Filter to keep columns that are valuable for LLM prompt
        if alerts_df.empty:
            self.logger.error("No alerts found in DataFrame.")
            raise Exception(
                constants.ErrorMessage.ERROR_PAYLOAD_CONSTRUCTION_FAILED.value
            )

        # Define the specific columns to always retain for the LLM prompt
        self.logger.debug(
            f"Initial columns in alerts DataFrame: {list(alerts_df.columns)}"
        )

        # Step 0: Filter out the alerts with low severity when the number of the unique event identifiers in episode is greater than the threshold of LARGE_EPISODE_THRESHOLD
        alerts_df = self.filter_large_episode_with_severity_and_map_id_to_level(
            alerts_df
        )

        # Step 1: Apply general column filtering to remove unwanted columns
        columns_to_drop = self.get_columns_to_drop(alerts_df)
        self.logger.info(f"Columns to drop: {columns_to_drop}")
        alerts_df_filtered = alerts_df.drop(columns=columns_to_drop)

        # Step 2: Keep required columns that exist in the DataFrame
        existing_required_columns = [
            col
            for col in constants.REQUIRED_COLUMNS
            if col in alerts_df_filtered.columns
        ]
        self.logger.info(f"Required columns found: {existing_required_columns}")

        # Step 3: Identify additional columns that meet criteria for inclusion
        additional_columns = self._get_additional_valuable_columns(
            alerts_df_filtered, existing_required_columns
        )
        self.logger.info(f"Additional valuable columns found: {additional_columns}")

        # Step 4: Combine required and additional columns
        columns_to_keep = list(set(existing_required_columns + additional_columns))

        if not columns_to_keep:
            self.logger.warning(
                "No valuable columns found in alerts DataFrame. Using all remaining columns."
            )
            alerts_df = alerts_df_filtered.dropna(axis=1, how="any")
        else:
            # Filter to keep valuable columns
            alerts_df = alerts_df_filtered[columns_to_keep]

            # Fill EVENT_IDENTIFIER_STRING with "UNKNOWN" if it exists and has missing values
            if constants.EVENT_IDENTIFIER_STRING in alerts_df.columns:
                alerts_df[constants.EVENT_IDENTIFIER_STRING] = alerts_df[
                    constants.EVENT_IDENTIFIER_STRING
                ].fillna(constants.UNKNOWN)

            # Drop columns that have missing values (except EVENT_IDENTIFIER_STRING which we just filled)
            alerts_df = alerts_df.dropna(axis=1, how="any")

        self.logger.info(f"Total alerts after filtering: {len(alerts_df)}")
        self.logger.debug(f"Columns retained: {list(alerts_df.columns)}")

        single_value_columns = []
        if (
            len(alerts_df) > 1
        ):  # We don't want to drop all of the columns when there is only 1 row in the data frame
            # Drop columns that have only one value
            # This is to make the alerts more concise
            for col in alerts_df.columns:
                # Check if the column is not a list type and has only one unique value.
                # We check that all values in the column are not lists, because lists are not hashable and cannot be used with unique().
                # Exclude EVENT_IDENTIFIER_STRING and TIME_COLUMN from being dropped as they are needed for the logic
                if (
                    col
                    not in [constants.EVENT_IDENTIFIER_STRING, constants.TIME_COLUMN]
                    and alerts_df[col].apply(lambda x: not isinstance(x, list)).all()
                    and len(alerts_df[col].unique()) == 1
                ):
                    single_value_columns.append(col)
            alerts_df_no_single_value_columns = alerts_df.drop(
                columns=single_value_columns
            )
        else:
            alerts_df_no_single_value_columns = alerts_df

        # Prepare the alert info for the prompt
        # Sort the alerts by time so the LLM can take the order into account (earlier alerts are more likely to be causal)
        alerts_df_no_single_value_columns_sorted_by_time = (
            alerts_df_no_single_value_columns.sort_values(
                by=constants.TIME_COLUMN
            ).reset_index(drop=True)
        )

        self.logger.debug(
            f"Columns: {list(alerts_df_no_single_value_columns_sorted_by_time.columns)}"
        )

        event_identifier_string_mapping = []  # index:id; value:event identifier string
        timeline = {}  # key:unix timestamp; value:id
        alerts_list = []  # record the rows in the alerts field
        if (
            constants.EVENT_IDENTIFIER_STRING
            in alerts_df_no_single_value_columns_sorted_by_time.columns
        ):
            self.logger.info(
                f"Found {constants.EVENT_IDENTIFIER_STRING} column in the alerts data frame, will use it to map alerts to unique event identifiers."
            )
            # Map from unique value of event_identifier_string to integer representing that unique value
            unique_event_identifiers = alerts_df_no_single_value_columns_sorted_by_time[
                constants.EVENT_IDENTIFIER_STRING
            ].unique()
            self.logger.info(
                f"The original number of unique event identifier strings from the get_alerts_text_for_prompt is: {len(unique_event_identifiers)}"
            )

            reverse_mapping = {
                event_id: i
                for i, event_id in enumerate(unique_event_identifiers)
                if event_id != constants.UNKNOWN
            }

            # Include the mapping in the alerts text for reference
            for event_id, i in reverse_mapping.items():
                event_identifier_string_mapping.append(event_id)

            # Include each alert with its mapped integer and Unix timestamp
            alerts_df_no_single_value_columns_sorted_by_time = (
                alerts_df_no_single_value_columns_sorted_by_time[
                    alerts_df_no_single_value_columns_sorted_by_time[
                        constants.EVENT_IDENTIFIER_STRING
                    ]
                    != constants.UNKNOWN
                ]
            )
            for i, r in alerts_df_no_single_value_columns_sorted_by_time.iterrows():
                mapped_id = reverse_mapping[r[constants.EVENT_IDENTIFIER_STRING]]
                timestamp = r[constants.TIME_COLUMN]
                # Convert timestamp to Unix timestamp
                try:
                    unix_timestamp = self.convert_to_unix_timestamp(timestamp)
                    timeline[unix_timestamp] = mapped_id
                except Exception as e:
                    self.logger.warning(
                        f"Failed to convert timestamp {timestamp} to Unix timestamp: {e}. Skipping this alert."
                    )
                    continue  # Skip this alert if timestamp conversion fails

            # At the end, include one alert for each unique value of event_identifier_string
            # Throw out some fields here, like _time (because that'll be different for each alert with the same event_identifier_string)
            for event_id, i in reverse_mapping.items():
                unique_alert = alerts_df_no_single_value_columns_sorted_by_time[
                    alerts_df_no_single_value_columns_sorted_by_time[
                        constants.EVENT_IDENTIFIER_STRING
                    ]
                    == event_id
                ].iloc[0]
                unique_alert_fewer_fields = self.drop_unneeded_fields(unique_alert)
                self.logger.debug(
                    f"Unique alert {i} with event identifier {event_id}: {unique_alert_fewer_fields}"
                )
                alerts_list.append(unique_alert_fewer_fields)
        else:
            self.logger.warning("Event Identifier String is missing.")
            return {}

        # Also include the values of the single-valued columns, as this information may be useful for the root cause
        single_value_columns_text = ""
        if len(single_value_columns) > 0:
            single_value_columns_text += "Single-valued columns:\n"
            for c in single_value_columns:
                value = alerts_df.iloc[0][c]
                # Apply the same truncation logic as in drop_unneeded_fields
                value = ITSISummaryOrchestratorClient.truncate_string_if_long(value)
                single_value_columns_text += f"{c}: {value}\n"

        alert_info = {
            "event_identifier_string_mapping": event_identifier_string_mapping,
            "timeline": timeline,
            "alerts": pd.DataFrame(
                alerts_list
            ).to_csv(),  # Convert alert dataframe to string
            "single_value_columns": single_value_columns_text,
        }
        return alert_info

    def get_timeline_entry_for_alert(
        self, timestamp, mapped_id, current_date, timezone_info
    ):
        """
        Get a timeline entry for the alert with the given mapped_id.
        This is used to create a timeline entry for the alert in the summary.

        Args:
            mapped_id (int): The mapped ID of the alert.

        Returns:
            str: A string representing the timeline entry for the alert.
        """
        timeline_entry = ""
        date_from_row = ""
        timezone_info_from_row = ""

        # Parse the timestamp to extract components
        if isinstance(timestamp, str):
            # Extract timezone from current timestamp
            if "T" in timestamp and ("+" in timestamp or "-" in timestamp[-6:]):
                # Extract timezone (e.g., "-07:00" from "2025-06-10T09:19:15.000-07:00")
                if "+" in timestamp:
                    timezone_info_from_row = "+" + timestamp.split("+")[-1]
                else:
                    timezone_info_from_row = "-" + timestamp.split("-")[-1]

                # Compare with previous timezone_info and update if different
                if timezone_info != timezone_info_from_row:
                    timeline_entry += f"Timezone: {timezone_info_from_row}\n"

            # Extract date and time components
            if "T" in timestamp:
                date_from_row, time_part = timestamp.split("T")
                # Remove timezone and milliseconds from time part
                if "+" in time_part:
                    time_part = time_part.split("+")[0]
                elif "-" in time_part and len(time_part.split("-")) > 1:
                    time_part = time_part.split("-")[0]
                # Remove milliseconds
                if "." in time_part:
                    time_part = time_part.split(".")[0]

                # Include date only if it's different from the previous one
                if current_date != date_from_row:
                    timeline_entry += f"\nDate: {date_from_row}\n"

                timeline_entry += f"{time_part}: {mapped_id}\n"
            else:
                # Fallback for non-ISO format timestamps
                timeline_entry += f"{timestamp}: {mapped_id}\n"
        else:
            # Handle non-string timestamps
            timeline_entry += f"{timestamp}: {mapped_id}\n"

        return (timeline_entry, date_from_row, timezone_info_from_row)

    def drop_unneeded_fields(self, alert_row: pd.Series) -> Dict:
        """
        Comprehensive field filtering and cleaning for alert data.

        This function consolidates ALL field dropping logic in one place with clear separation:
        1. FIELD FILTERING: Remove unwanted fields based on names and types
        2. VALUE FILTERING: Remove fields based on content patterns
        3. VALUE TRANSFORMATION: Clean and transform remaining values

        Args:
            alert_row (pd.Series): A single alert row from a DataFrame.
        Returns:
            Dict: The cleaned and filtered alert data.
        """
        if alert_row.empty:
            return {}

        alert_data = alert_row.dropna().to_dict()

        # ===== PHASE 1: FIELD FILTERING =====
        filtered_data = self._filter_unwanted_fields(alert_data)

        # ===== PHASE 2: VALUE FILTERING =====
        value_filtered_data = self._filter_by_value_patterns(filtered_data)

        # ===== PHASE 3: VALUE TRANSFORMATION =====
        final_data = self._transform_values(value_filtered_data)

        return final_data

    # ===== PHASE 1: FIELD FILTERING =====
    def _filter_unwanted_fields(self, data: Dict) -> Dict:
        """
        Phase 1: Remove fields based on field names and basic data types.
        This handles all the "structural" filtering that doesn't depend on content analysis.
        """
        filtered = {}

        # Predefined columns to always drop (from constants.py + additional ones)
        # Combine with the original COLUMNS_TO_DROP from constants
        ALL_COLUMNS_TO_DROP = set(
            constants.COLUMNS_TO_DROP + constants.ADDITIONAL_COLUMNS_TO_DROP
        )

        for field_name, field_value in data.items():
            # Skip predefined unwanted columns
            if field_name in ALL_COLUMNS_TO_DROP:
                continue

            # Skip drilldown fields (using constants from constants.py)
            if any(
                field_name.startswith(prefix) for prefix in constants.DRILLDOWN_PREFIXES
            ):
                continue

            # Skip boolean fields
            if isinstance(field_value, bool) or str(field_value) in ("True", "False"):
                continue

            # Skip UUID fields (simple pattern check)
            if self._is_uuid_field(field_value):
                continue

            # Keep this field
            filtered[field_name] = field_value

        return filtered

    def _is_uuid_field(self, value: Any) -> bool:
        """Check if a value looks like a UUID."""
        if not isinstance(value, str):
            return False
        try:
            uuid.UUID(value.strip())
            return True
        except ValueError:
            return False

    # ===== PHASE 2: VALUE FILTERING =====
    def _filter_by_value_patterns(self, data: Dict) -> Dict:
        """
        Phase 2: Remove fields based on content pattern analysis.
        This handles all content-based filtering rules.
        """
        filtered = {}
        seen_values = {}

        for field_name, field_value in data.items():
            # Apply all pattern-based filters
            if self._should_drop_by_pattern(field_value):
                self.logger.debug(
                    f"Dropped field '{field_name}' due to pattern matching"
                )
                continue

            # Remove duplicate values (keep first occurrence)
            value_str = str(field_value).strip() if field_value is not None else ""
            if value_str in seen_values:
                continue  # Skip duplicate value

            # Keep this field
            seen_values[value_str] = field_name
            filtered[field_name] = field_value

        return filtered

    def _should_drop_by_pattern(self, value: Any) -> bool:
        """
        Centralized pattern checking for field values.
        Returns True if the field should be dropped based on its content.
        """
        # Check P-id pattern
        if self._is_pid(value):
            return True

        # Check digits/punctuation only (with exceptions)
        if self._is_only_digits_and_punctuation(value):
            return True

        # Check truncated URLs
        if self._is_truncated_url(value):
            return True

        return False

    # ===== PHASE 3: VALUE TRANSFORMATION =====
    def _transform_values(self, data: Dict) -> Dict:
        """
        Phase 3: Transform and clean the remaining field values.
        This handles value cleaning without removing fields.
        """
        transformed = {}
        clean_field_name_count_dt = {}  # Key: unique field name; Value: id
        for field_name, field_value in data.items():
            # Simplify nested field names
            clean_field_name = (
                self._simplify_nested_field_name(field_name)
                if "." in field_name
                else field_name
            )
            if clean_field_name in clean_field_name_count_dt:
                clean_field_name_count_dt[clean_field_name] += 1
                clean_field_name = (
                    clean_field_name
                    + "_"
                    + str(clean_field_name_count_dt[clean_field_name])
                )
            else:
                clean_field_name_count_dt[clean_field_name] = 0
            # Transform the value
            clean_value = self._clean_field_value(field_value)

            transformed[clean_field_name] = clean_value

        return transformed

    def _clean_field_value(self, value: Any) -> Any:
        """Clean and transform a single field value."""
        # Truncate long strings
        cleaned_value = ITSISummaryOrchestratorClient.truncate_string_if_long(value)

        # Handle multiple newlines
        if isinstance(cleaned_value, str) and self._has_multiple_newlines(
            cleaned_value
        ):
            cleaned_value = self._convert_newline_to_list(cleaned_value)

        return cleaned_value

    def _simplify_nested_field_name(self, field_name: str) -> str:
        """Simplify nested field names by keeping top 2 longest sub-field names."""
        stop_words = {"dev", "field", "fields", "key", "keys", "value", "values"}
        parts = [p for p in field_name.split(".") if p.lower() not in stop_words]
        if len(parts) <= 2:
            return ".".join(parts)

        # Sort parts by length (descending) and keep top 2
        sorted_parts = sorted(parts, key=len, reverse=True)[:2]
        return ".".join(sorted_parts)

    def _is_pid(self, value: Any) -> bool:
        """Check if a value contains P-id pattern (P- followed by digits)."""
        str_val = str(value).strip()
        return bool(re.search(r"P-\d+", str_val))

    def _is_only_digits_and_punctuation(self, value: Any) -> bool:
        """Check if a value contains only digits and punctuation."""
        str_val = str(value).strip()
        # Don't filter single characters (like severity codes)
        if len(str_val) == 1:
            return False
        # Don't filter numbers between 0-1 (like thresholds)
        if self._is_number_between_0_and_1(str_val):
            return False
        # Check if all characters are digits or punctuation
        return all(not c.isalpha() for c in str_val)

    def _is_number_between_0_and_1(self, value: str) -> bool:
        """Check if a string represents a number between 0 and 1 (including percentages)."""
        try:
            str_val = str(value).strip()

            # Handle percentage format (e.g., "50%")
            if str_val.endswith("%"):
                num = float(str_val.rstrip("%")) / 100
            else:
                num = float(str_val)

            return 0 <= num <= 1
        except (ValueError, TypeError):
            return False

    def _is_truncated_url(self, value: Any) -> bool:
        """Check if a value is a truncated URL."""
        str_val = str(value).strip()
        return str_val.startswith("https:") and str_val.endswith("...")

    def _has_multiple_newlines(self, value: Any) -> bool:
        """Check if a value contains multiple newlines."""
        str_val = str(value)
        return str_val.count("\n") >= 2 or str_val.count("\\n") >= 2

    def _convert_newline_to_list(self, value: Any) -> str:
        """Convert string with multiple newlines to comma-separated deduplicated list."""
        str_val = str(value)

        # Handle escaped newlines
        if "\\n" in str_val:
            str_val = str_val.replace("\\n", "\n")

        # Convert to comma-separated list if multiple newlines exist
        if str_val.count("\n") >= 2:
            # Split by newlines, remove duplicates while preserving order, filter out empty items
            items = []
            seen = set()
            for item in str_val.split("\n"):
                clean_item = item.strip()
                if clean_item and clean_item not in seen:
                    items.append(clean_item)
                    seen.add(clean_item)
            return ", ".join(items)
        return str_val

    @staticmethod
    def _convert_to_json_serializable(obj):
        """
        Convert pandas/numpy data types to JSON-serializable Python native types.

        Args:
            obj: The object to convert (can be dict, list, or individual value)

        Returns:
            JSON-serializable version of the object
        """

        if isinstance(obj, dict):
            return {
                key: ITSISummaryOrchestratorClient._convert_to_json_serializable(value)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [
                ITSISummaryOrchestratorClient._convert_to_json_serializable(item)
                for item in obj
            ]
        elif isinstance(obj, tuple):
            return tuple(
                ITSISummaryOrchestratorClient._convert_to_json_serializable(item)
                for item in obj
            )
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif hasattr(obj, "item"):  # Handle other numpy scalar types
            return obj.item()
        else:
            return obj

    """
    Call ITSI Summary Orchestrator to get episode for this summarization_id
    """

    def get_episode(self, summarization_id: str):
        # Call ITSI Summary Orchestrator to get episode for this summarization_id
        self.logger.info("Starting to get episode")
        episode_list = self.call_tool(
            constants.GET_EPISODE, {constants.SUMMARIZATION_ID: summarization_id}
        )
        if (
            not episode_list
            or not isinstance(episode_list, list)
            or len(episode_list) != 1
        ):
            self.logger.error(
                f"Failed to run query with {constants.GET_EPISODE}, return value was episode_list={episode_list}"
            )
            return None

        self.logger.info(f"Total episodes found: {len(episode_list)}")
        self.logger.debug(
            f"Got episode list successfully, the episode_list is: {episode_list}"
        )
        # Get the only json element from the episode_list
        return episode_list[0]

    def get_episode_time(self, summarization_id: str) -> Tuple[int, int]:
        """
        Extracts the episode features including episode starting_time and episode end_time.

        Parameters:
        - data: Dict[str, str] - A JSON object that contains the "summarization_id" field with escaped quotes.

        Returns:
        - Tuple[str]
        """
        episode_dict = self.get_episode(summarization_id)
        if not episode_dict:
            self.logger.error(
                "Failed to get episode, returning default start and end time."
            )
            return 0, 0

        """
        Example input format for the episode_dict:
        episode_dict = {
                "start_time": "1743763519.2123766",
                "last_time": "1743763519.2123766"
            }
        The timestamps are floats in string form, where the part before the dot ('.') is the Unix epoch time in seconds,
        and the part after the dot is the fractional seconds, we will skip them.
        By splitting on '.', we extract the first integer part representing seconds for further processing.
        """
        if "start_time" not in episode_dict or "last_time" not in episode_dict:
            raise KeyError("Missing 'start_time' or 'last_time' in the DataFrame")
        return int(episode_dict["start_time"].split(".")[0]), int(
            episode_dict["last_time"].split(".")[0]
        )

    def add_time(self, spl, episode_start_time: int, episode_end_time: int):
        # Both episode_start_time and episode_end_time are Unix timestamps in seconds.
        # Constants: ONE_HOUR_IN_SEC = 3600 seconds, ONE_SEC = 1 second
        #
        # Time range strategy:
        # - earliest: episode_start_time - 1 hour (to capture events leading up to the episode)
        # - latest: episode_end_time + 1 second (to ensure episode end events are included)
        #
        # Rationale for +1 second on latest:
        # Based on experimental testing, when earliest equals latest in Splunk SPL, no logs are returned,
        # indicating that the time boundaries may be exclusive rather than inclusive. Adding 1 second
        # ensures that events occurring exactly at episode_end_time are captured.
        time_str = f' earliest="{episode_start_time - constants.ONE_HOUR_IN_SEC}" latest="{episode_end_time + constants.ONE_SEC}" '

        stripped_spl = spl.lstrip()
        lower_spl = stripped_spl.lower()

        # For mstats searches, ensure earliest/latest options are inserted before the BY clause.
        if lower_spl.startswith("| mstats") and " by " in lower_spl:
            by_index = lower_spl.find(" by ")
            insertion_point = len(spl) - len(stripped_spl) + by_index
            result_spl = (
                spl[:insertion_point].rstrip() + time_str + spl[insertion_point:]
            )
        else:
            # For the SPL command to function correctly, the time control should be placed before the first pipe (|), if the SPL doesn't start with a pipe(|).
            index_of_pipe = -1
            if spl.startswith("|"):
                index_of_pipe = spl.find("|", 1)
            else:
                index_of_pipe = spl.find("|")

            if index_of_pipe != -1:
                result_spl = (
                    spl[:index_of_pipe].rstrip() + time_str + spl[index_of_pipe:]
                )
            else:
                result_spl = spl + time_str

        return result_spl

    def add_time_and_keywords(
        self,
        spl,
        episode_start_time: int,
        episode_end_time: int,
        fields: List,
        keywords_for_logs: List,
    ):
        # ONE_HOUR_IN_SEC = 3600; episode_start_time is a Unix timestamp (unit: seconds).
        # Subtracting 3600 gets the time 1 hour before the episode start.
        time_str = f' earliest="{episode_start_time - constants.ONE_HOUR_IN_SEC}" latest="{episode_end_time}" '
        if fields:
            # add the TIME_COLUMN(`_time` field) when custom fields exist, in order to construct the data string from DataFrame
            search_suffix = "| fields " + " ".join(fields + [constants.TIME_COLUMN])
        else:
            search_suffix = ""

        # Build keywords for search
        keywords_spl = " OR ".join(
            keywords_for_logs if keywords_for_logs else ["error", "warn"]
        )

        # Add search, cluster, table, and sort operations
        search_suffix += (
            f" | search {keywords_spl}"
            " | cluster showcount=true"
            f" | table {constants.CLUSTER_COUNT_KEY} {constants.RAW_COLUMN_KEY}"
            f" | sort -{constants.CLUSTER_COUNT_KEY}"
        )
        stripped_spl = spl.lstrip()
        lower_spl = stripped_spl.lower()

        if lower_spl.startswith("| mstats") and " by " in lower_spl:
            by_index = lower_spl.find(" by ")
            insertion_point = len(spl) - len(stripped_spl) + by_index
            result_spl = (
                spl[:insertion_point].rstrip() + time_str + spl[insertion_point:]
            )
        else:
            # For the SPL command to function correctly, the time control should be placed before the first pipe (|), if the SPL doesn't start with a pipe(|).
            index_of_pipe = -1
            if spl.startswith("|"):
                index_of_pipe = spl.find("|", 1)
            else:
                index_of_pipe = spl.find("|")

            if index_of_pipe != -1:
                result_spl = (
                    spl[:index_of_pipe].rstrip() + time_str + spl[index_of_pipe:]
                )
            else:
                result_spl = spl + time_str
        return result_spl + search_suffix

    def get_and_clean_custom_queries(
        self, summarization_id: str, request_id: str, alert_string: str
    ):
        """
        Call ITSI Summary Orchestrator to get custom queries for this summarization_id

        Parameters:
        - summarization_id (str): The unique identifier for the summarization task.
        - request_id (str): A unique request identifier that ensures consistent tracking between
                           the generate_summary and get_keywords_for_logs network calls, maintaining
                           proper tracing across related operations for the same summarization task.
        - alert_string (str): String containing alert information used for context when extracting
                             keywords via get_keywords_for_logs function to enhance SPL queries with
                             relevant search terms and improve log filtering.

        Returns:
        - Dict[str, Dict]

        Key: the SPL returned from `itsi_summary_orchestrator_client.call_tool`
        Value: A dictionary containing:
          - "title": Title of the SPL query
          - "description": Brief description of the SPL query
          - "types": A list of types.
          - "data_string": The data string cleaned and formatted based on the raw data returned by the `SplJobManager.run_query` API
        Example:
        {
            "SPL query string 1": {
                "title": "Title of SPL query 1",
                "description": "Description of SPL query 1",
                "types": ["is_service"]
                "data_string": data_string_1
            },
            "SPL query string 2": {
                "title": "Title of SPL query 2",
                "description": "Description of SPL query 2",
                "types": ["is_kpi_entity", "is_service"],
                "data_string": data_string_2
            },
            ...
        }
        """
        self.logger.info("starting get custom queries")
        steps_checked_metadata = self.steps_checked_manager.get_or_initialize_metadata(
            summarization_id
        )

        # Call ITSI Summary Orchestrator to get custom queries for this summarization_id
        custom_queries_json = self.call_tool(
            constants.GET_CUSTOM_QUERIES, {constants.SUMMARIZATION_ID: summarization_id}
        )
        if not custom_queries_json:
            self.logger.error(
                f"{constants.GET_CUSTOM_QUERIES} function return an empty custom_queries_json"
            )
            return {}
        self.logger.debug(f"custom_queries_json: {custom_queries_json}")
        data_string_dict = {}
        for data in custom_queries_json:
            if not data:
                continue
            # Prepare the logs text for the prompt.
            # Even the SPL is missing or failed to get valid response,
            # An empty string is retained to maintain the mapping order between user queries and their corresponding search results.
            text_for_prompt = ""

            # Pass through the types to the result of this function
            types = data.get(constants.TYPES_KEY, [])

            # Pass through the title and description to steps_checked
            title = data.get(constants.TITLE_KEY, "")
            description = data.get(constants.DESCRIPTION_KEY, "")

            basic_spl = self.extract_and_unescape_spl(data)
            start_time = time.time()
            self.logger.info(f"basic spl:{basic_spl}")
            if basic_spl:
                if not basic_spl.strip().startswith(
                    ("search", "|", "tstats", "inputlookup", "datamodel")
                ):
                    basic_spl = f"search {basic_spl}"
                keywords_for_logs = self.itsi_ai_assistant_client.get_keywords_for_logs(
                    alert_string, types, summarization_id, request_id
                )
                spl = self.add_time_and_keywords(
                    basic_spl,
                    steps_checked_metadata["episode_start_time"],
                    steps_checked_metadata["episode_end_time"],
                    fields=data.get(constants.FIELDS_KEY, []),
                    keywords_for_logs=keywords_for_logs,
                )
                self.logger.info(f"the real spl: {spl}")
                # Run the custom spl to get the logs
                results, sid, error = self.spl_job_manager.run_query(
                    spl, search_purpose=f"get custom queries for the spl titled {title}"
                )

                # When testing on CO2, we saw errors but still got results. So we don't treat the error as a failure (counter intuitive)
                # We only check if the results are empty. So we replaced `if error or not results: ` with `if not results: `.
                if not results:
                    if error:
                        self.logger.error(
                            f"Failed to run query on SPL: {spl}. The title of this SPL is: {title}"
                        )
                    else:
                        self.logger.error(
                            f"Got an empty result from SPL: {spl}. The title of this SPL is: {title}"
                        )

                    status = 0
                    self.logger.error(f"Failed to run query with sid {sid}: {error}")
                else:
                    logs_df = pd.DataFrame.from_records(results)
                    self.logger.info(f"len of logs_df:{len(logs_df)}")
                    for _, r in logs_df.iterrows():
                        text_for_prompt += (
                            f"Cluster count = {r[constants.CLUSTER_COUNT_KEY]}\n"
                        )
                        text_for_prompt += f"{r[constants.RAW_COLUMN_KEY]}\n"
                    self.logger.debug(
                        f"text_for_prompt out of the for loop: {text_for_prompt}"
                    )

                    status = -1
                    self.logger.info(f"Run SPL query {basic_spl} successfully.")

            else:
                status = 0
                types = []
                # We set a default basic SPL as empty string to record the missing SPL cases
                # In order to retained to maintain the mapping order between user queries and their corresponding search results.
                # If there is more than 1 missing basic spl, the order can not be maintain.
                basic_spl = ""
                self.logger.info(
                    f"'{constants.SPL_KEY}' key not found in the response data."
                )
            self.logger.info(
                f"SPL query {basic_spl} profiling: {time.time() - start_time} seconds"
            )

            steps_checked_metadata[constants.STEPS_CHECKED][
                constants.CUSTOM_QUERIES_DATA
            ].append(
                {
                    constants.TITLE_KEY: title,
                    constants.DESCRIPTION_KEY: description,
                    constants.TYPES_KEY: types,
                    constants.STATUS: status,
                }
            )
            self.logger.debug(
                f"In custom_queries, steps_checked[CUSTOM_QUERIES_DATA]:{steps_checked_metadata[constants.STEPS_CHECKED][constants.CUSTOM_QUERIES_DATA]}"
            )
            data_string_dict[basic_spl] = {
                constants.TITLE_KEY: title,
                constants.DESCRIPTION_KEY: description,
                constants.TYPES_KEY: types,
                constants.DATA_STRING_KEY: text_for_prompt,
            }

        if not data_string_dict:
            self.logger.error("Failed to extract SPL list from the response.")
        self.logger.debug(f"data_string_dict:{data_string_dict}")
        return data_string_dict

    def get_columns_to_drop(self, df):
        """
        Get the columns to drop from the DataFrame.
        """
        columns_to_drop = []
        for col in df.columns:
            if any(col.startswith(prefix) for prefix in constants.DRILLDOWN_PREFIXES):
                columns_to_drop.append(col)
        columns_to_drop.extend(constants.COLUMNS_TO_DROP)

        # Remove columns that are not in the DataFrame
        # This is to avoid KeyError when dropping columns
        columns_to_drop = [c for c in columns_to_drop if c in df.columns]

        return columns_to_drop

    """
    Construct the payload for the ITSI AI Assistant
    Should include alerts, time series correlation info, logs and steps_checked,
        - alert_string (minlen=1): A string containing the alerts.
        - correlations: A list of correlation info, each correlation is a dictionary with keys:
            - series: A list with length of 2, first is the leading series name, second is the lagging series name.
            - correlation: A float value representing the correlation between the two series.
            - lag: A string representing the lag between the two series using human readable string e.g. "1 hour", "2 days".
        - logs: A dictionary where the key is the SPL query string and the value is a dictionary containing:
            - title: User-provided title string
            - description: User-provided description string
            - types: A list of types for the logs.
            - data_string: A string containing the logs data
        - steps_checked: A string containing the steps checked
    """

    def construct_itsi_ai_assistant_payload(self, summarization_id, request_id):
        # Set the current summarization ID for logging context
        set_current_summarization_id(summarization_id)

        # Get episode start and end time
        get_episode_time_start_time = time.time()
        episode_start_time, episode_end_time = self.get_episode_time(summarization_id)
        get_episode_time_run_time = time.time() - get_episode_time_start_time
        self.logger.info(
            f"in payload profiling: Time taken to get_episode_time: {get_episode_time_run_time} seconds"
        )
        if episode_start_time == 0 and episode_end_time == 0:
            self.logger.error("Failed to get episode start and end time.")
            return {}

        # Store episode time into steps_checked_metadata
        update_episode_time_start_time = time.time()
        self.steps_checked_manager.update_episode_time(
            summarization_id, episode_start_time, episode_end_time
        )
        update_episode_time_run_time = time.time() - update_episode_time_start_time
        self.logger.info(
            f"in payload profiling: Time taken to update_episode_time: {update_episode_time_run_time} seconds"
        )
        # Get alerts
        alert_start_time = time.time()
        alert_info = self.get_and_clean_alerts(summarization_id)
        if not alert_info:
            self.logger.error(
                "Stopped constructing the whole payload because the alert_info is empty."
            )
            return {}
        alert_run_time = time.time() - alert_start_time
        self.logger.info(
            f"in payload profiling: Time taken for get_and_clean_alerts: {alert_run_time} seconds"
        )
        # Get time series correlation info

        # This steps_checked_metadata is only for logger debugging purpose.
        # It can be removed with the loggers for steps_checked_metadata after we confirm the steps_checked works.
        get_or_initialize_metadata_start_time = time.time()
        steps_checked_metadata = self.steps_checked_manager.get_or_initialize_metadata(
            summarization_id
        )
        get_or_initialize_metadata_run_time = (
            time.time() - get_or_initialize_metadata_start_time
        )
        self.logger.info(
            f"in payload profiling: Time taken to get_or_initialize_metadata: {get_or_initialize_metadata_run_time} seconds"
        )

        self.logger.info(
            f"in payload, before checked_impacted_items, steps_checked_metadata:{steps_checked_metadata}"
        )
        correlation_info_start_time = time.time()
        correlation_info = self.timeseries_collector.collect_and_compute_correlation(
            summarization_id
        )
        correlation_info_run_time = time.time() - correlation_info_start_time
        self.logger.info(
            f"in payload profiling: Time taken to collect_and_compute_correlation: {correlation_info_run_time} seconds"
        )

        # Get logs
        custom_queries_data_start_time = time.time()
        self.logger.debug(
            f"in payload, before custom_queries_data, steps_checked_metadata:{steps_checked_metadata}"
        )
        # Convert alert_info to string for passing to get_and_clean_custom_queries
        logs_dict = self.get_and_clean_custom_queries(
            summarization_id, request_id, json.dumps(alert_info)
        )
        custom_queries_data_run_time = time.time() - custom_queries_data_start_time
        self.logger.info(
            f"in payload profiling: Time taken to get_and_clean_custom_queries: {custom_queries_data_run_time} seconds"
        )

        # Prepare the sevice ids for get_services_topology and collect_service_impact_analysis
        service_ids, _ = self.get_service_kpi_ids(summarization_id)
        self.logger.info(
            f"Finished fetching the service_ids from get_service_kpi_ids: service_ids = {service_ids}. Now staring to call get_services_topology and collect_service_impact_analysis."
        )

        services_topology = {}
        service_impact_analysis = []
        if service_ids:
            # Get services topology
            self.logger.info(
                "in payload, after custom_queries_data, we run get_services_topology."
            )
            services_topology_start_time = time.time()
            # We dont add this since service topology is not for putting to LLM yet.
            # the topology can be empty dict, but we still return it faithfully.
            services_topology = self.get_services_topology(
                summarization_id, service_ids
            )
            services_topology_run_time = time.time() - services_topology_start_time
            self.logger.info(
                f"in payload profiling: Time taken to get_services_topology: {services_topology_run_time} seconds"
            )
            self.logger.debug(
                f"in payload, after get_services_topology function, services_topology:{services_topology}"
            )

            # Get service impact analysis
            self.logger.info(
                "in payload, after custom_queries_data, we run service_impact_analysis."
            )
            service_impact_analysis_start_time = time.time()
            service_impact_analysis = self.collect_service_impact_analysis(
                summarization_id, service_ids
            )
            service_impact_analysis_run_time = (
                time.time() - service_impact_analysis_start_time
            )
            self.logger.info(
                f"in payload profiling: Time taken to collect_service_impact_analysis: {service_impact_analysis_run_time} seconds"
            )
            self.logger.debug(
                f"in payload, after collect_service_impact_analysis function, service_impact_analysis:{service_impact_analysis}"
            )

        # Get steps_checked_metadata
        self.logger.debug(
            f"in payload, after custom_queries_data, steps_checked_metadata:{steps_checked_metadata}"
        )
        get_steps_checked_with_descriptions_start_time = time.time()
        steps_checked_with_updated_description = (
            self.steps_checked_manager.get_steps_checked_with_descriptions(
                summarization_id
            )
        )
        get_steps_checked_with_descriptions_run_time = (
            time.time() - get_steps_checked_with_descriptions_start_time
        )
        self.logger.info(
            f"in payload profiling: Time taken to get_steps_checked_with_descriptions: {get_steps_checked_with_descriptions_run_time} seconds"
        )
        self.logger.debug(
            f"in payload, after get_steps_checked_with_descriptions function, steps_checked_with_updated_description:{steps_checked_with_updated_description}"
        )
        res = {
            constants.ALERT_INFO: alert_info,
            constants.CORRELATIONS: correlation_info,
            constants.LOGS: logs_dict,
            constants.STEPS_CHECKED: steps_checked_with_updated_description,
            constants.SERVICES_TOPOLOGY: services_topology,
            constants.SERVICE_IMPACT_ANALYSIS: service_impact_analysis,
        }
        return res

    def safe_network_call(self, func_, **kwargs):
        try:
            response = func_(
                constants.ITSI_SUMMARY_ORCHESTRATOR_URI,
                owner=constants.ITSI_APP_OWNER,
                app=constants.ITSI_APP_NAME,
                **kwargs,
            )
            if response.status != 200:
                self.logger.error(f"Network call failed with status {response.status}")
                return None
            return json.loads(response.body.read())
        except (ConnectionError, OSError, IOError) as e:
            self.logger.error(f"Network connection error during network call: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(
                f"JSON parsing error while parsing the response: {str(e)}"
            )
            return None
        except Exception as e:
            self.logger.error(
                f"Unexpected exception occurred during network call: {str(e)}"
            )
            return None

    def safe_network_call_get_severity(self, func_, **kwargs):
        try:
            response = func_(
                constants.ITSI_GET_SEVERITY_URI,
                owner=constants.ITSI_APP_OWNER,
                app=constants.ITSI_APP_NAME,
                **kwargs,
            )
            if response.status != 200:
                self.logger.error(
                    f"Network call to get severity failed with status {response.status}"
                )
                return None
            return json.loads(response.body.read())
        except (ConnectionError, OSError, IOError) as e:
            self.logger.error(
                f"Network connection error during network call for severity mapping: {str(e)}"
            )
            return None
        except json.JSONDecodeError as e:
            self.logger.error(
                f"JSON parsing error while parsing the response for severity mapping: {str(e)}"
            )
            return None
        except Exception as e:
            self.logger.error(
                f"Unexpected exception occurred during network call for severity mapping: {str(e)}"
            )
            return None

    def get_service_kpi_ids(
        self, summarization_id: str
    ) -> Tuple[List[str], List[Dict[str, str]]]:
        """
        Retrieve service IDs and KPI IDs associated with the given summarization_id.
        This function calls ITSI tool `GET_IMPACTED_SERVICE_ID_AND_KPI_ID` to obtain impacted services and KPIs.
        The expected result format (res_dict) for calling ITSI tool GET_IMPACTED_SERVICE_ID_AND_KPI_ID is:
            {
                "impacted_services": [
                    { "service_id": "id1", "service_name": "name" }
                ],
                "impacted_kpis": [
                    { "kpi_id": "id", "kpi_name": "name", "service_id": "id1" }
                ]
            }
        Returns:
            A tuple containing:
            - A list of service IDs (List[str]) extracted from the "impacted_services" field.
            - A list of KPI info (List[Dict]), include kpi_id, kpi_name, service_id from the "impacted_kpis" field,
                where the service_id is the kpi associated with.
            If the tool call fails or the expected structure is not present, returns ([], []).
        """
        args = {
            constants.SUMMARIZATION_ID: summarization_id,
        }
        res_dict = self.call_tool(constants.GET_IMPACTED_SERVICE_ID_AND_KPI_ID, args)
        try:
            impacted_services = [
                service.get(constants.SERVICE_ID)
                for service in res_dict.get(constants.IMPACTED_SERVICES, [])
            ]
            impacted_kpis = res_dict.get(constants.IMPACTED_KPIS, [])

            # Get steps_checked_metadata for this summarization_id
            steps_checked_metadata = (
                self.steps_checked_manager.get_or_initialize_metadata(summarization_id)
            )

            # Even it's an empty list, we add "services" to the check_impacted_items field to record that it's checked successfully.
            if impacted_services is not None:
                steps_checked_metadata[constants.STEPS_CHECKED][
                    constants.CHECKED_IMPACTED_ITEMS
                ].append("services")
            if impacted_kpis is not None:
                steps_checked_metadata[constants.STEPS_CHECKED][
                    constants.CHECKED_IMPACTED_ITEMS
                ].append("kpis")
            return impacted_services, impacted_kpis
        except Exception:
            self.logger.error("Failed to get service_id and kpi_id")
            return [], []

    def get_kpi_and_entity_ts(
        self, summarization_id: str, service_ids: List[str]
    ) -> Tuple[Dict[str, List[pd.DataFrame]], Dict[str, set]]:
        """
        Retrieve KPI-level and entity-level time series data for the given summarization_id and list of service IDs.
        This function first calls ITSI tool `GET_TIMELINE_SPLS` to get SPL queries for each service,
        then executes those SPLs to collect time series data for both KPIs and entities.
        Also, it constructs a mapping from KPI/Entity identifiers to their associated service IDs, which is extracted from DataFrame.
        The response (spls_dict) from the ITSI tool is expected to be in the following format:
            {
                "service_id_1": {
                    "service_spl": "index=\"itsi_summary\" itsi_service_id=service_id_1...",
                    "kpi_spl": "index=\"itsi_summary\" itsi_service_id=service_id_1...",
                    "entity_spl": "index=\"itsi_summary\" itsi_service_id=service_id_1..."
                },
                "service_id_2": {...}
            }
        Returns:
            Tuple:
            - A dictionary with two keys:
                - "kpi": List[pd.DataFrame] of KPI-level time series.
                - "entity": List[pd.DataFrame] of entity-level time series.
            - A mapping from each KPI/entity ID to the set of service IDs it is associated with.
              This helps skip correlation between series from the same service.
              If the SPL fetch fails, returns (None, None).
        """
        result = (None, None)
        try:
            args = {
                constants.SUMMARIZATION_ID: summarization_id,
                constants.SERVICE_IDS: service_ids,
            }
            # storing the kpi and entity time series data
            pd_collection: Dict[str, List[pd.DataFrame]] = {
                constants.KPI_TS_KEY: [],
                constants.ENTITY_TS_KEY: [],
            }
            # storing the mapping between service_id and its kpiid and entity_title,
            # this is used to filter-out the kpi-entity correlations that belongs to same service
            kpi_entity_to_service_mapping = defaultdict(set)
            # Step 1: Fetch SPLs for each service
            spls_dict = self.call_tool(constants.GET_TIMELINE_SPLS, args)
            self.logger.info(
                f"SPL queries dictionary returned by get_timeline_spls API: {spls_dict}"
            )
            if not spls_dict:  # spls_dict could be None or an empty dict
                self.logger.error("Failed to get KPI and entity SPL")
                result = (None, None)
            else:
                # Step 2: Execute each SPL and collect results
                for service_id, spl_set in spls_dict.items():
                    # Run KPI SPL, collect corresponding df and the kpi to service mapping
                    self._collect_timeseries(
                        summarization_id=summarization_id,
                        level="kpi",
                        spl_key=constants.KPI_SPL,
                        collection_key=constants.KPI_TS_KEY,
                        spl_set=spl_set,
                        service_id=service_id,
                        spl_manager=self.spl_job_manager,
                        kpi_entity_to_service_mapping=kpi_entity_to_service_mapping,
                        pd_collection=pd_collection,
                    )
                    # Run Entity SPL, collect corresponding df and the entity to service mapping
                    self._collect_timeseries(
                        summarization_id=summarization_id,
                        level="entity",
                        spl_key=constants.ENTITY_SPL,
                        collection_key=constants.ENTITY_TS_KEY,
                        spl_set=spl_set,
                        service_id=service_id,
                        spl_manager=self.spl_job_manager,
                        kpi_entity_to_service_mapping=kpi_entity_to_service_mapping,
                        pd_collection=pd_collection,
                    )

                result = (pd_collection, kpi_entity_to_service_mapping)
        finally:
            # Track the function execution result and record it to steps checked
            self.steps_checked_manager._record_function_status_for_steps_checked(
                summarization_id, result
            )

        return result

    def _collect_timeseries(
        self,
        summarization_id: str,
        level: str,
        spl_key: str,
        collection_key: str,
        spl_set: Dict[str, str],
        service_id: str,
        spl_manager: SplJobManager,
        kpi_entity_to_service_mapping: Dict[str, Set[str]],
        pd_collection: Dict[str, List[pd.DataFrame]],
    ) -> None:
        """
        This helper function collects time series data for a given level (kpi or entity).
        It extracts the SPL query from the provided spl_set according to the key, and takes care of
        all the necessary logging and error handling. It also records the mapping from KPI/entity ID to its service ID
        Parameters:
            level (str): Indicates the data type, either "kpi" or "entity".
            spl_key (str): The key to extract the SPL string from spl_set (e.g., KPI_SPL or ENTITY_SPL).
            collection_key (str): The key to determine which list in pd_collection to append results to.
            spl_set (Dict[str, str]): A dictionary containing SPL strings keyed by level identifiers.
            service_id (str): The ID of the service associated with the SPL query.
            spl_manager (SplJobManager): An instance used to run SPL queries.
            kpi_entity_to_service_mapping (Dict[str, Set[str]]): Mapping from each KPI/entity ID to associated service IDs.
            pd_collection (Dict[str, List[pd.DataFrame]]): The dictionary where collected time series
                DataFrames are stored, organized by type ("kpi" or "entity").
        """

        # Extract the SPL query from the provided spl_set according to the key
        spl_query = self.extract_and_unescape_spl(spl_set, spl_key)
        # if spl is empty, log an error and return
        if not spl_query:
            self.logger.error(
                f"Failed to extract {level.upper()} SPL for service_id={service_id}"
            )
            return
        self.logger.info(f"Original SPL for _collect_timeseries: {spl_query}")
        steps_checked_metadata = self.steps_checked_manager.get_or_initialize_metadata(
            summarization_id
        )
        spl_query_with_time_range = self.add_time(
            spl_query,
            steps_checked_metadata["episode_start_time"],
            steps_checked_metadata["episode_end_time"],
        )
        # Only add the search filter for non-mstats queries
        # mstats has strict syntax requirements and doesn't preserve all fields,
        # so filtering for field existence doesn't work the same way
        if not spl_query.strip().lower().startswith("| mstats"):
            spl_query_with_time_range = (
                spl_query_with_time_range
                + " | search itsi_kpi_id=* alert_value=* entity_title=*"
            )
        self.logger.info(
            f"SPL for _collect_timeseries after adding time range {spl_query_with_time_range}"
        )
        records, sid, error = spl_manager.run_query(
            spl_query_with_time_range,
            search_purpose=f"get timeseries for {level} of the service {service_id}",
        )
        # record error when query running fails
        # When testing on CO2, we saw errors but still got results. So we don't treat the error as a failure (counter intuitive)
        # We only check if the results are empty. So we replaced `if error or not records: ` with `if not records: `.
        if not records:
            self.logger.error(
                f"{level.upper()} SPL query failed for sid={sid}, service_id={service_id}: {error}"
            )
            return
        # Convert the SPL result to a DataFrame
        df = self.parse_spl_result_to_df(
            records,
            timeseries_type=level,
            query_target=service_id,
            tool_name=constants.GET_TIMELINE_SPLS,
        )
        # only when the df is not None and not empty, we collect the data
        if df is not None and not df.empty:
            # collect the mapping from kpi/entity to service_id
            group_col = (
                constants.KPI_GROUP_COLUMN
                if level == "kpi"
                else constants.ENTITY_GROUP_COLUMN
            )
            unique_ids = df[group_col].unique()
            for unique_id in unique_ids:
                # Add the service_id to the mapping for this kpi or entity
                # unique_id is the kpi_id or entity_title
                # the service_id can not be None, as this df is from timeline query
                # which is based on the given service_id
                kpi_entity_to_service_mapping[unique_id].add(service_id)
            # collect the DataFrame into the pd_collection
            pd_collection[collection_key].append(df)

    def collect_service_impact_analysis(
        self, summarization_id: str, service_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Collects and returns the service impact analysis for a given summarization ID.
        This method retrieves the relevant service IDs and their topology for the provided summarization ID.
        It identifies the common ancestor services among the affected services and performs impact analysis
        for each ancestor. The results are aggregated and returned as a list of dictionaries.
        Args:
            summarization_id (str): The unique identifier for the summarization process.
        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing the service impact analysis results.
                each dictionary represents a kpi that is impacting the service.
                Each dictionary contains keys, "kpiid", "title", "severity", "urgency", "alert_value"
                "is_healthscore_calculate_by_entity_enabled", "service_id", "impact", and optionally "degraded_entities".
                where the degraded_entities is a list of dictionaries containing the alert_level, key, and title of the degraded entities.
            Returns an empty list if no service IDs or topology are found.
        """
        service_impact_analysis_results = []
        try:
            topology = self.get_services_topology(summarization_id, service_ids)
            if not topology or not topology.get("graphs"):
                self.logger.error(
                    "No service topology found. Cannot collect service impact analysis."
                )
                return []
            # In most of cases, the topology contains only one graph so the common_ancestors contains only one ancestor.
            # In rare cases, the topology contains multiple graphs, common_ancestors may contain multiple ancestors.
            common_ancestors = ServiceAncestorFinder.find_common_ancestors(
                service_ids, topology
            )
            self.logger.info(f"Common ancestors found: {common_ancestors}")

            for ancestor_service_id in common_ancestors:
                # For each common ancestor, we call get_service_impact_analysis to get the impact analysis
                # and update the service_impact_analysis_results list.
                res = self.get_service_impact_analysis(
                    summarization_id, ancestor_service_id
                )
                service_impact_analysis_results.extend(res)
            self.logger.info(
                f"Service impact analysis results: {service_impact_analysis_results}"
            )
            # We need to sort the results by SEVERITY.
            service_impact_analysis_results = sorted(
                service_impact_analysis_results,
                key=lambda x: x.get(
                    constants.SIA_RANKING_FIELD,
                    constants.DEFAULT_SEVERITY_FOR_MISSING_FIELD,
                ),
                reverse=True,
            )
            self.logger.debug(
                f"Sorted service impact analysis results: {service_impact_analysis_results}"
            )
            return service_impact_analysis_results

        finally:
            # Track the function execution result and record it to steps checked
            self.steps_checked_manager._record_function_status_for_steps_checked(
                summarization_id, service_impact_analysis_results
            )

    def get_service_impact_analysis(
        self, summarization_id: str, service_id: str, filter_required: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve service impact analysis for the given summarization_id and service_id.
        The return result is a dictionary containing a list of KPIs that are impacting the service.
        The ITSI side currently handles the earliest_time and latest_time by defaulting to the episode start and end time.
        The service impact analysis is dynamically changing, the current setting is returning the latest result in the time range.
        This function calls ITSI tool `GET_SERVICE_IMPACT_ANALYSIS` and expects the response to be in the following format:
            [
                {
                    "_key": "da-itsi-cp-splunk-observability-131aa705ac3ddbb0b0eea7da",
                    "is_healthscore_calculate_by_entity_enabled": 1,
                    "service_id": "da-itsi-cp-splunk-observability-browser-checks",
                    "title": "Response Time",
                    "urgency": 5,
                    "alert_value": "4685.571428571428",
                    "severity": 6,
                    "impact": 0,
                    "degraded_entities": [
                        {
                            "alert_level": 6,
                            "key": "50c34cea-2060-4f87-b357-4074dcdafa8c",
                            "title": "Splunk Tshirt Company"
                        },
                        ...
                    ]
                },...
            ]
        where the key `degraded_entities` is optional key.
        """
        self.logger.info(
            f"Starting to get_service_impact_analysis: service_id = {service_id}"
        )
        args = {
            constants.SUMMARIZATION_ID: summarization_id,
            constants.SERVICE_ID: service_id,
        }
        result = self.call_tool(constants.GET_SERVICE_IMPACT_ANALYSIS, args)
        if result is None:
            self.logger.error(
                f"Failed to get service impact analysis for service_id {service_id}."
            )
            result = []  # Reset result to an empty list to avoid returning a None
        if filter_required:
            result = self.filter_service_impact_analysis_result(result)
        return result

    def get_services_topology(
        self, summarization_id: str, service_ids: str
    ) -> Dict[str, Any]:
        """
        Retrieve the service topology for the given summarization_id and list of service_ids.
        The ITSI side filters the service topology and returns only the topology related to the services in the provided service_ids list.
        This function calls ITSI tool `GET_SERVICES_TOPOLOGY` and expects the response "res" to be in the following format:
            {
                "graphs": [
                    {
                        "id": "b41db8c0-4c40-4aa1-9488-7144f176ac3f",
                        "edges": [
                            {"source": "<node_id_1>", "target": "<node_id_2>"},
                            ...
                        ],
                        "vertices": [
                            {"id": "<node_id>", "title": "<service_name>", "nodeDepth": <depth>},
                            ...
                        ]
                    }
                ],
                "totalCount": 8,
                "visibleCount": 8,
                "depth": 3,
                "maxPossibleDepth": 3
            }
        Returns:
            A dictionary representing the service topology graph, including node and edge information.
            Returns None if the ITSI tool call fails.
        """
        # We add summarization_id here - just in case that the summarization_id from the function input parameter might be different to the summarization_id associated to self.logger
        self.logger.info(
            f"Starting to get_services_topology for service_ids = {service_ids}"
        )
        result = {}
        try:
            args = {
                constants.SUMMARIZATION_ID: summarization_id,
                constants.SERVICE_IDS: service_ids,
            }
            result = self.call_tool(constants.GET_SERVICES_TOPOLOGY, args)
            if result is None:
                self.logger.error(
                    f"Failed to get service topology for service_ids {service_ids}."
                )
                result = {}  # Reset result to an empty dict to avoid returning a None

        finally:
            # Track the function execution result and record it to steps checked
            self.steps_checked_manager._record_function_status_for_steps_checked(
                summarization_id, result
            )

        return result

    def parse_spl_result_to_df(
        self,
        spl_result: List[Any],
        timeseries_type: str,
        query_target: str,
        tool_name: str,
    ) -> Optional[pd.DataFrame]:
        """
        Convert SPL result records into a non-empty pandas DataFrame.

        Parameters:
            spl_result: List of result records returned from an SPL query.
            timeseries_type: Descriptive label for logging ("kpi" or "entity").
            query_target: The target of the SPL query (e.g., kpi_id or service_id or summarization_id).
            tool_name: Context info for logs (e.g., kpi_id or SPL string).

        Returns:
            A DataFrame if records exist and are valid, otherwise None.
        """
        if not spl_result:
            self.logger.error(
                f"No {timeseries_type} time series data found for {query_target} when calling {tool_name}"
            )
            return None
        try:
            df = pd.DataFrame.from_records(spl_result)
        except Exception as e:
            self.logger.error(
                f"Error converting {timeseries_type} SPL result to DataFrame for {query_target} when calling {tool_name}: {e}"
            )
            return None
        if df.empty:
            self.logger.info(
                f"{timeseries_type} time series is empty for {query_target} when calling {tool_name}"
            )
            return None
        return df

    def filter_service_impact_analysis_result(
        self, res: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter the service impact analysis result to only include KPIs with severity >= MEDIUM.
        Also rename the _key field to kpiid for better readability.
        """
        filtered_res = []
        for kpi_item in res:
            # if severity is not present, we skip this item
            severity = kpi_item.get(
                constants.SIA_RANKING_FIELD,
                constants.DEFAULT_SEVERITY_FOR_MISSING_FIELD,
            )
            try:
                severity_value = float(severity)
            except (ValueError, TypeError):
                self.logger.error(
                    f"Severity value '{severity}' is not valid in kpi_item: {kpi_item}. Skipping this item."
                )
                continue
            if severity_value < constants.KPISEVERITY.MEDIUM.value:
                continue
            # rename _key to kpiid to increase the readability of the result
            # _key should be always present in the kpi_item
            kpi_item[constants.KPI_ID] = kpi_item.pop(constants.KPI_KEY)
            filtered_res.append(kpi_item)
        return filtered_res

    @staticmethod
    def convert_to_unix_timestamp(time_string):
        """Convert human-readable timestamp to Unix timestamp."""
        dt = parse(time_string)
        return int(dt.timestamp())

    @staticmethod
    def truncate_string_if_long(value, max_length=100):
        """
        Truncate string values that are longer than the specified maximum length.

        Args:
            value: The value to potentially truncate
            max_length (int): Maximum allowed length before truncation (default: 100)

        Returns:
            The original value if it's not a string or shorter than max_length,
            otherwise a truncated string with "..." appended
        """
        if isinstance(value, str) and len(value) > max_length:
            return value[:max_length] + "..."
        return value

    def _get_additional_valuable_columns(
        self, df: pd.DataFrame, required_columns: list
    ) -> list:
        """
        Identify additional columns that are valuable for the LLM prompt.
        These columns should meet certain criteria like not being all NaN, not being UUID-like, etc.
        Single-valued columns are also included as they will be handled separately in the output.

        Args:
            df: The DataFrame to analyze
            required_columns: List of columns that are already required

        Returns:
            List of additional column names to include
        """
        additional_columns = []

        for col in df.columns:
            self.logger.info(f"Checking column: {col}")
            # Skip if already in required columns
            if col in required_columns:
                self.logger.info(
                    f"Skipping column {col} as it is already in required columns."
                )
                continue

            # Skip if column has no data or all NaN
            if df[col].isna().all():
                self.logger.info(f"Skipping column {col} as it has no data or all NaN.")
                continue

            # Skip columns that look like UUIDs or long hashes (typically not human-readable)
            if self._is_uuid_like_column(df[col]):
                self.logger.info(
                    f"Skipping column {col} as it looks like a UUID or long hash."
                )
                continue

            # Include all other columns (including single-valued ones)
            # Single-valued columns will be handled separately in the main method
            # Note: Long text values will be truncated later by truncate_string_if_long()
            additional_columns.append(col)

        return additional_columns

    @staticmethod
    def is_valid_uuid(val):
        """Check if a value is a valid UUID."""
        try:
            uuid.UUID(str(val))  # Convert to string first for robustness
            return True
        except ValueError:
            return False

    def _is_uuid_like_column(self, series: pd.Series) -> bool:
        """
        Check if a series contains UUID-like values.
        """
        # If the series is empty, return False
        if series.empty or series.isna().all():
            return False

        # Check a sample of non-null values
        sample_values = series.dropna().head(5)
        uuid_like_count = 0

        for value in sample_values:
            if self.is_valid_uuid(value):
                uuid_like_count += 1

        # If all sampled values look like UUIDs, consider the column UUID-like
        return uuid_like_count == len(sample_values)
