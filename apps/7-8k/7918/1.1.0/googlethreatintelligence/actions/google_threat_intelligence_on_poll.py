# File: google_threat_intelligence_on_poll.py
#
# Copyright 2025-2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

import phantom.app as phantom
import phantom.rules as phantom_rules

import google_threat_intelligence_consts as consts
from actions import BaseAction


class OnPoll(BaseAction):
    """Class to handle on poll action."""

    def execute(self):
        """Execute on poll action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.ON_POLL_START_MSG.format("Google Threat Intelligence"))
        self.config = self._connector.get_config()
        ret_val = self.__validate_params()
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        ingestion_type = self.config.get("ingestion_type")

        if ingestion_type == "IOC Stream":
            self._connector.debug_print("This asset is configured to ingest IOC Stream")
            ret_val, response = self.handle_polling_IOC_events()
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()
            return self._action_result.set_status(phantom.APP_SUCCESS)

        elif ingestion_type == "ASM Issues":
            self._connector.debug_print("This asset is configured to ingest ASM issues")
            ret_val, response = self.handle_polling_ASM_events()
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()
            return self._action_result.set_status(phantom.APP_SUCCESS)

        elif ingestion_type == "DTM Alerts":
            self._connector.debug_print("This asset is configured to ingest DTM alerts")
            ret_val, response = self.handle_polling_DTM_events()
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()
            return self._action_result.set_status(phantom.APP_SUCCESS)

        else:
            self._connector.save_progress("Ingestion is not enabled for this asset")
            self._connector.debug_print("Ingestion is not enabled for this asset")

    def handle_polling_IOC_events(self):
        """
        Handle polling for IOC events.

        This method will retrieve IOC events from the API, create a container for each day
        and add artifacts for the current day container.

        Args:
            None

        Returns:
            tuple: A tuple containing the status (success/failure) and the response
        """
        query_params = self.__get_query_params()
        endpoint, method = consts.IOC_ON_POLL_ENDPOINT, "get"

        limit = self.config.get("limit")
        days = self.config.get("days")

        # Check if this is a manual poll or scheduled poll
        self._is_poll_now = self._connector.is_poll_now()

        # Get the current time in Unix timestamp (seconds)
        now = int(time.time())

        # Get the current day string from the timestamp
        current_day = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%d")

        self._state = self._connector._state

        # For scheduled polls, use the last notification date from state
        if not self._is_poll_now:
            # Get the last notification date from state, or use default interval if not available
            last_notification_date = self._state.get("last_notification_date")
            if last_notification_date:
                # Add this timestamp to query parameters
                query_params["filter"] = f"{query_params.get('filter', '')} date:{last_notification_date}+".strip()
            else:
                if days:
                    days = int(days)
                    default_time = now - (24 * 60 * 60 * days)
                formatted_timestamp = self._connector.util.convert_unix_to_utc(default_time)

                query_params["filter"] = f"{query_params.get('filter', '')} date:{formatted_timestamp}+".strip()
        else:
            # For manual polls, use the last 1 hour
            manual_time = now - (60 * 60)
            self._connector.save_progress(f"Ingesting last 1 hour IOC events for manual polling")
            formatted_timestamp = self._connector.util.convert_unix_to_utc(manual_time)
            query_params["filter"] = f"{query_params.get('filter', '')} date:{formatted_timestamp}+".strip()
        ret_val, response = self.__make_rest_call(url=endpoint, method=method, param=query_params, limit=limit)

        if phantom.is_fail(ret_val):
            self._connector.debug_print("API call failed")
            return self._action_result.get_status(), None

        # Process the response
        return self._handle_response_for_IOC(response, current_day)

    def _handle_response_for_IOC(self, response, current_day):
        """
        Process the API response and create containers and artifacts.

        Args:
            response (dict): The API response containing hunting notifications
            current_day (str): The current day in YYYY-MM-DD format

        Returns:
            int: phantom.APP_SUCCESS or phantom.APP_ERROR
        """
        # Check if we have data in the response
        data = response

        if not data:
            self._connector.debug_print("No data found in response")
            return phantom.APP_SUCCESS, None

        # Get stored information from state
        stored_day = self._state.get("current_day", "")
        current_container_id = self._state.get("current_container_id")

        if current_container_id:
            current_container_id = self._ensure_container_exists(current_container_id, stored_day)
            self._state["current_container_id"] = current_container_id

        # Check if we need a new container (different day or poll_now)
        if not current_container_id or stored_day != current_day:
            # Create a new container for today

            if current_container_id and stored_day != current_day:
                stored_date = datetime.strptime(stored_day, "%Y-%m-%d")
                current_date = datetime.strptime(current_day, "%Y-%m-%d")

                # If there's more than one day difference, handle intermediate days
                if (current_date - stored_date).days > 1:
                    # Store the previous day (day before current)
                    prev_date = current_date - timedelta(days=1)
                    prev_day = prev_date.strftime("%Y-%m-%d")

                    # Create container for previous day if it doesn't exist
                    prev_container_id = self._create_container(prev_day)
                    if prev_container_id:
                        self._state["previous_day_container_id"] = prev_container_id
                        self._state["previous_day"] = prev_day
                else:
                    # Normal case - just one day difference
                    self._state["previous_day_container_id"] = current_container_id
                    self._state["previous_day"] = stored_day

            current_container_id = self._create_container(current_day)
            if not current_container_id:
                self._connector.debug_print("Failed to create container for the day")
                return phantom.APP_ERROR, None

            # Update state with new container ID
            self._state["current_container_id"] = current_container_id
            self._state["current_day"] = current_day
            self._connector.debug_print(f"Created new container for {current_day}")

        # Get the last processed notification date from state
        last_notification_date = self._state.get("last_notification_date")

        # Get previous day information
        previous_day = self._state.get("previous_day", "")
        previous_day_container_id = self._state.get("previous_day_container_id")

        if previous_day_container_id:
            previous_day_container_id = self._ensure_container_exists(previous_day_container_id, previous_day)
            self._state["previous_day_container_id"] = previous_day_container_id

        # Track artifacts created for each day
        current_day_count = 0
        previous_day_count = 0

        # Process to remove objects that were ingested in previous runs to avoid duplicates
        if data and len(data) > 0:
            last_obj_date = data[-1].get("context_attributes", {}).get("notification_date")
            if last_obj_date:
                last_obj_date_utc = self._connector.util.convert_unix_to_utc(last_obj_date)
                if last_notification_date and last_obj_date_utc and last_notification_date == last_obj_date_utc:
                    count = self._get_duplicate_count(last_notification_date)
                    if count > 0:
                        data = data[:-count]
                        self._connector.debug_print(f"Removed {count} duplicate objects")

        # Process each file in the response
        for notification in reversed(data):
            # Determine which container to use based on notification date
            container_id = current_container_id  # Default to current day

            notification_timestamp = notification.get("context_attributes", {}).get("notification_date")
            if notification_timestamp and previous_day_container_id:
                try:
                    # Convert timestamp to date string in YYYY-MM-DD format
                    notification_date_str = datetime.fromtimestamp(notification_timestamp, tz=timezone.utc).strftime("%Y-%m-%d")

                    # If notification is from previous day and we have a previous day container, use it
                    if notification_date_str == previous_day:
                        container_id = previous_day_container_id
                except (ValueError, TypeError, OverflowError) as e:
                    self._connector.debug_print(f"Error converting timestamp {notification_timestamp}: {e!s}")
                    # If error, use current day container

            notification = self._convert_all_date_fields_to_utc(notification)

            # Create artifact in the appropriate container
            artifact_id = self._create_artifact(notification, container_id)
            if artifact_id:
                # Track which day's container we added to
                if container_id == current_container_id:
                    current_day_count += 1
                else:
                    previous_day_count += 1
            else:
                self._connector.debug_print(f"Failed to create artifact for notification: {notification.get('id', 'unknown')}")

        # Log creation counts
        if current_day_count > 0:
            self._connector.debug_print(f"Created {current_day_count} artifacts in container for current day {current_day}")

        if previous_day_count > 0:
            self._connector.debug_print(f"Created {previous_day_count} artifacts in container for previous day {previous_day}")

        # Get the notification date from the first object for checkpointing
        if not self._is_poll_now and data and len(data) > 0:
            first_object = data[0]
            notification_date = first_object.get("context_attributes", {}).get("notification_date")
            if notification_date:
                self._state["last_notification_date"] = notification_date
                self._connector.state = self._state
                self._connector.save_state(self._state)

                self._connector.debug_print(f"Updated checkpoint to notification_date: {notification_date}")

        # Log summary
        total_artifacts = current_day_count + previous_day_count
        self._connector.save_progress(f"Created {total_artifacts} artifacts across containers")

        return phantom.APP_SUCCESS, None

    def handle_polling_ASM_events(self):
        days = self.config.get("days")
        limit = self.config.get("limit")
        search_string = self.config.get("search_string", "")

        # Check if this is a manual poll or scheduled poll
        self._is_poll_now = self._connector.is_poll_now()
        self._state = self._connector._state

        # Format the search string
        search_string_formatted = self._connector.util.clean_search_string(search_string)
        # Get the last seen after value from days
        last_seen_after_value = self._connector.util.build_last_seen_after(days=days)

        # For scheduled polls, use the last seen after from state
        if not self._is_poll_now:
            # Get the last seen after from state, or use default interval if not available
            last_seen_after = self._state.get("last_seen_after")
            if last_seen_after:
                # Add this timestamp to query parameters
                search_string = f"{search_string_formatted} last_seen_after:{last_seen_after}"
            else:
                # Last seen after value to be calculated from days
                search_string = f"{search_string_formatted} last_seen_after:{last_seen_after_value}"
        else:
            # Last seen after value to be calculated from hours
            last_seen_after_value = self._connector.util.build_last_seen_after(hours=1)
            self._connector.save_progress(f"Ingesting last 1 hour ASM events for manual polling")
            search_string = f"{search_string_formatted} last_seen_after:{last_seen_after_value}"

        self._connector.debug_print(f"[on_poll] search_string: {search_string}")

        params = {"page_size": limit}

        headers = self.__get_headers()
        # Build the endpoint
        endpoint, method = f"{consts.ASM_ON_POLL_ENDPOINT}/{quote(search_string)}", "get"
        ret_val, response = self.__make_rest_call(url=endpoint, method=method, headers=headers, param=params)

        if phantom.is_fail(ret_val):
            self._connector.debug_print("API call failed")
            return self._action_result.get_status(), None

        # Process the response
        return self._handle_response_for_ASM(response)

    def _handle_response_for_ASM(self, response):
        """
        Process the API response and create containers and artifacts.

        Args:
            response (dict): The API response containing hunting notifications

        Returns:
            int: phantom.APP_SUCCESS or phantom.APP_ERROR
        """
        self._connector.save_progress(consts.INGESTION_START_MESSAGE)
        self._connector.debug_print(consts.INGESTION_START_MESSAGE)

        # Check if we have data in the response
        data = response
        if not data.get("result", None):
            self._connector.debug_print("Search completed! No data found in response")
            return phantom.APP_SUCCESS, None
        total_hits = data.get("result", {}).get("total_hits")
        self._connector.debug_print(f"Total ASM issue/hits fetched while polling: {total_hits}")
        if not total_hits:
            self._connector.debug_print("Search completed! No data found in response")
            return phantom.APP_SUCCESS, None

        hits = data.get("result", {}).get("hits")

        for data in hits:
            container_json = self.__get_ingest_container_json(data)
            status, message, container_id = self.__ingest_container(container_json)

            if message and message == "Duplicate container found":
                container_status = container_json.get("status")
                self._connector.util.update_container_status(container_id, container_status)

            if phantom.is_fail(status):
                self._connector.debug_print(consts.CONTAINER_ERROR_MESSAGE.format(container_id, message))
                continue

            artifacts = self.__get_ingest_artifacts_payload(data, container_id)
            status, message = self.__ingest_artifacts(artifacts, container_id)

            if phantom.is_fail(status):
                self._connector.debug_print(consts.ARTIFACT_ERROR_MESSAGE.format(message))
                continue

        # Get the last_seen_after from the last object for checkpointing
        if not self._is_poll_now and hits and len(hits) > 0:
            first_object = hits[-1]
            last_seen_after_timestamp = first_object.get("last_seen")
            if last_seen_after_timestamp:
                # Store the last_seen_after value instate file
                self._state["last_seen_after"] = last_seen_after_timestamp
                self._connector.state = self._state
                self._connector.save_state(self._state)

                self._connector.debug_print(f"Updated checkpoint to last_seen_after: {last_seen_after_timestamp}")

        return phantom.APP_SUCCESS, None

    def handle_polling_DTM_events(self):
        """
        Handle polling for DTM events.

        This method will retrieve DTM alerts from the API, create containers and artifacts
        for each alert and update the checkpoint with the latest alert time.

        Returns:
            tuple: A tuple containing the status (success/failure) and the response
        """
        query_params = self.__get_dtm_query_params()
        endpoint, method = consts.DTM_ON_POLL_ENDPOINT, "get"

        limit = self.config.get("limit")

        # Current time in UTC
        now = datetime.now(timezone.utc)

        self._is_poll_now = self._connector.is_poll_now()

        # Load state for checkpointing
        self._state = self._connector._state

        # Check if this is a manual poll or scheduled poll
        if not self._is_poll_now:
            last_alert_time = self._state.get("last_alert_time")

            # Check if checkpoint is available
            if last_alert_time:
                self._connector.debug_print(f"Found checkpoint for DTM alerts: {last_alert_time}")
                query_params["since"] = last_alert_time
            else:
                self._connector.debug_print("No checkpoint found for DTM alerts")
                days = self.config.get("days")

                # Subtract days
                historical_data_to_collect = now - timedelta(days=days)

                # Convert to RFC3339 format with 'Z'
                rfc3339_time = historical_data_to_collect.isoformat().replace("+00:00", "Z")

                self._connector.debug_print(f"Collecting alerts of last {days} days. Setting since to: {rfc3339_time}")
                query_params["since"] = rfc3339_time
        else:
            self._connector.save_progress(f"Ingesting last 1 hour DTM alerts for manual polling")
            self._connector.debug_print("This is a manual poll for DTM alerts, fetching alerts from the last hour.")
            historical_data_to_collect = now - timedelta(hours=1)
            rfc3339_time = historical_data_to_collect.isoformat().replace("+00:00", "Z")
            query_params["since"] = rfc3339_time

        ret_val, response = self.__make_rest_call(url=endpoint, method=method, limit=limit, param=query_params)
        if phantom.is_fail(ret_val):
            self._connector.debug_print("API call failed")
            return self._action_result.get_status(), None

        # Process the response
        self._connector.debug_print(f"Total DTM alerts fetched in this poll: {len(response)}")
        return self._handle_response_for_DTM(response)

    def _handle_response_for_DTM(self, data):
        """
        Process the API response and create containers and artifacts.

        Args:
            data (dict): The API response containing DTM alerts

        Returns:
            int: phantom.APP_SUCCESS or phantom.APP_ERROR
        """
        if not data:
            self._connector.debug_print("No data found in response")
            return phantom.APP_SUCCESS, None

        latest_alert_time = data[0].get("created_at")
        for alert in reversed(data):
            alert_id = alert.get("id")
            alert_title = alert.get("title")
            alert_description = alert.get("alert_summary")
            alert_severity = alert.get("severity")
            alert_status = alert.get("status")
            container_status = consts.DTM_STATUS_MAPPING.get(alert_status, "new")
            container_data = {
                "name": f" GTI - {alert_title}",
                "description": alert_description,
                "source_data_identifier": alert_id,
                "severity": alert_severity,
                "status": container_status,
            }
            ret_val, message, container_id = self._connector.save_container(container_data)
            if phantom.is_fail(ret_val):
                self._connector.debug_print(f"Failed to create container: {message}")
                return None
            if message and message == "Duplicate container found":
                self._connector.debug_print(f"Container already exists, skipping ingestion for alert: {alert_id}")
                continue
            dtm_cef = self.__get_cef_dtm(alert)
            artifact_data = {
                "container_id": container_id,
                "name": alert_title,
                "description": alert_description,
                "source_data_identifier": alert.get("id"),
                "severity": alert_severity,
                "cef": dtm_cef,
                "data": alert,
                "run_automation": True,
            }
            ret_val, message, artifact_id = self._connector.save_artifact(artifact_data)

            if phantom.is_fail(ret_val):
                self._connector.debug_print(f"Failed to create artifact: {message}")
                return None

        if not self._is_poll_now:
            self._connector.debug_print(f"Checkpointing last alert time for DTM alerts: {latest_alert_time}")
            self._state["last_alert_time"] = latest_alert_time
            self._connector.state = self._state
            self._connector.save_state(self._state)
        return phantom.APP_SUCCESS, None

    def _create_container(self, day):
        """
        Create a container for a specific day.

        Args:
            day (str): The day in YYYY-MM-DD format

        Returns:
            int: Container ID if successful, None otherwise
        """
        container = {
            "name": f"GTI IOC Stream - {day} UTC",
            "description": f"GTI hunting notifications for {day}.",
            "source_data_identifier": f"gti_{day}",
            "data": {"day": day},
        }

        ret_val, message, container_id = self._connector.save_container(container)

        if phantom.is_fail(ret_val):
            self._connector.debug_print(f"Failed to create container: {message}")
            return None

        return container_id

    def _create_artifact(self, data, container_id):
        """
        Create an artifact from a file notification.

        Args:
            data (dict): The data from the API response
            container_id (int): The container ID to add the artifact to

        Returns:
            int: Artifact ID if successful, None otherwise
        """
        data_id = data.get("id")
        if not data_id:
            return None

        # Get attributes
        attributes = data.get("attributes", {})

        artifact = {
            "name": f"GTI Entity - {attributes.get('meaningful_name', data_id)}",
            "container_id": container_id,
            "source_data_identifier": data_id,
            "cef": self._remove_fields(data),
            "data": data,
            "run_automation": True,
        }

        # Save the artifact
        ret_val, message, artifact_id = self._connector.save_artifact(artifact)

        if phantom.is_fail(ret_val):
            self._connector.debug_print(f"Failed to create artifact: {message}")
            return None

        return artifact_id

    def __get_cef_dtm(self, alert):
        """
        Create a CEF data for a DTM alert.

        Args:
            alert (dict): The DTM alert data.

        Returns:
            dict: The CEF data for the alert.
        """
        cef = {
            "Alert ID": alert.get("id"),
            "Alert Type": alert.get("alert_type"),
            "Alert Title": alert.get("title"),
            "Alert Summary": alert.get("alert_summary"),
            "Alert Status": alert.get("status"),
            "AI Doc Summary": alert.get("ai_doc_summary"),
            "Aggregated Under ID": alert.get("aggregated_under_id"),
            "Monitor ID": alert.get("monitor_id"),
            "Tags": alert.get("tags"),
            "Confidence": alert.get("confidence"),
            "Created Date": alert.get("created_at"),
            "Updated Date": alert.get("updated_at"),
        }
        return cef

    def __get_ingest_container_json(self, data):
        """
        Create a container JSON from response data till max limit.

        Args:
            data (dict): The response data containing the necessary information.

        Returns:
            dict: The container JSON with the following keys:
                - name (str): The name of the container.
                - data (dict): The data containing the uid and id.
                - description (str): The description of the container.
                - source_data_identifier (str): The source data identifier.
                - label (str): The container label.
        """
        # Create container JSON from response data till max limit
        pretty_name = data.get("summary", {}).get("pretty_name")
        description = data.get("description")
        hit_id = data.get("id")
        severity = data.get("summary", {}).get("severity")
        container_severity = consts.SEVERITY_MAPPING.get(severity, "Medium")
        status = data.get("summary", {}).get("status")
        hit_uid = data.get("uid")
        container_json = {
            "name": f"GTI - {pretty_name}",
            "data": {"uid": hit_uid, "id": hit_id},
            "description": f"GTI - {description}",
            "source_data_identifier": f"gti_{hit_uid}",
            "severity": container_severity,
            "status": consts.ASM_STATUS_MAPPING.get(status, "Open"),
            "label": self._connector.get_config().get("ingest", {}).get("container_label"),
        }

        return container_json

    def __ingest_container(self, container_json):
        """
        Save a container using the provided container JSON.

        Args:
            container_json (dict): The JSON representation of the container.

        Returns:
            tuple: A tuple containing the following:
                - ret_val (int): The return value indicating the success or failure of the operation.
                - message (str): A message describing the result of the operation.
                - container_id (int): The ID of the saved container, or None if the operation failed.
        """
        ret_val, message, container_id = self._connector.save_container(container_json)

        return ret_val, message, container_id

    def __get_ingest_artifacts_payload(self, data, container_id):
        """
        Create artifacts payload from the response data till max limit.

        Args:
            data (dict): The response data.
            container_id (int): The ID of the container.

        Returns:
            list: A list of artifacts with the following keys:
                - name (str): The name of the artifact.
                - container_id (int): The ID of the container.
                - source_data_identifier (str): The source data identifier.
                - cef (dict): The Common Event Format (CEF) data.
                - data (dict): The response data.

        """
        # Create artifacts payload from the response data till max limit

        summary = data.get("summary")
        hit_uid = data.get("uid")
        pretty_name = data.get("summary", {}).get("pretty_name")
        description = data.get("description")
        severity = data.get("summary", {}).get("severity")
        artifact_severity = consts.SEVERITY_MAPPING.get(severity, "Medium")
        first_seen = data.get("first_seen")
        name = data.get("name")
        category = data.get("summary", {}).get("category")
        status = data.get("summary", {}).get("status")
        collection = data.get("collection")
        entity_name = data.get("entity_name")
        entity_type = data.get("entity_type")
        confidence = data.get("summary", {}).get("confidence")
        last_seen = data.get("last_seen")
        tags = data.get("tags")
        uid = data.get("uid")
        dynamic_id = data.get("dynamic_id")
        upstream = data.get("upstream")

        artifacts = [
            {
                "name": f"GTI - {pretty_name}",
                "container_id": container_id,
                "source_data_identifier": f"gti_{hit_uid}",
                "cef": {
                    "Description": description,
                    "Severity (GTI)": severity,
                    "Discovered date": first_seen,
                    "Issue Name": name,
                    "Category": category,
                    "Status": status,
                    "Collection": collection,
                    "Affected Entity": entity_name,
                    "Entity Type": entity_type,
                    "Confidence": confidence,
                    "Last Seen": last_seen,
                    "Tags": tags,
                    "Issue ID": uid,
                    "Dynamic ID": dynamic_id,
                    "Upstream": upstream,
                    "Summary": summary,
                },
                "severity": artifact_severity,
                "data": data,
                "run_automation": True,
            }
        ]

        return artifacts

    def __ingest_artifacts(self, artifacts, container_id):
        """
        Update any existing artifacts with the same source_data_identifier and ingest the list of artifacts into the
        given container_id.

        Args:
            artifacts (list): List of dictionaries with keys related to artifact
            container_id (int): ID of the container to ingest artifacts into

        Returns:
            tuple: A tuple containing the following:
                - ret_val (int): The return value indicating the success or failure of the operation.
                - message (str): A message describing the result of the operation.
        """
        artifact_mapping = self._connector.util._get_artifact_of_container_id(container_id)
        for artifact in artifacts:
            artifact_id = artifact_mapping.get(artifact.get("source_data_identifier"))
            if artifact_id:
                self._connector.util._update_artifact(artifact_id, artifact)
                return phantom.APP_SUCCESS, "Artifact Updated"
            artifact["container_id"] = container_id

        ret_val, message, resp = self._connector.save_artifacts(artifacts)
        self._connector.debug_print(f"save_artifacts returns, value: {ret_val}, reason: {message}, ids: {resp}")

        return ret_val, message

    def __validate_params(self):
        """Validate parameters"""

        if "container_count" in self._param:
            ret_val, value = self._connector.validator.validate_integer(
                self._action_result,
                self._param.get("container_count"),
                "container_count",
            )

            if not ret_val:
                return ret_val

            self._param["container_count"] = value

        if "artifact_count" in self._param:
            ret_val, value = self._connector.validator.validate_integer(self._action_result, self._param.get("artifact_count"), "artifact_count")

            if not ret_val:
                return ret_val

            self._param["artifact_count"] = value

        if "limit" in self.config:
            ret_val, value = self._connector.validator.validate_integer(self._action_result, self.config.get("limit"), "limit")

            if not ret_val or (value <= 0 and value > 1000):
                self._connector.debug_print(
                    "WARNING",
                    f"Invalid limit parameter: {self.config.get('limit')} -  Must be between 1 and 1000. Using default limit of 1000.",
                )
                self.config["limit"] = 1000
            else:
                self.config["limit"] = value
        else:
            self._connector.debug_print("Limit Parameter not set. Using default limit of 1000.")
            self.config["limit"] = 1000

        if "days" in self.config:
            ret_val, value = self._connector.validator.validate_integer(self._action_result, self.config.get("days"), "days")

            if not ret_val or (value <= 0 and value > 5):
                self._connector.debug_print(
                    "WARNING",
                    f"Invalid days parameter: {self.config.get('days')} -  Must be between 1 and 5. Using default limit of 5.",
                )
                self.config["days"] = 5
            else:
                self.config["days"] = value
        else:
            self._connector.debug_print("Days Parameter not set. Using default days of 5.")
            self.config["days"] = 5

        return True

    def __get_headers(self):
        """Get request header"""
        headers = {"PROJECT-ID": "project-id"}
        default_values = {}

        payload = {}
        for key, value in headers.items():
            if value in self._param:
                payload[key] = self._param[value]
            elif value in default_values:
                payload[key] = default_values[value]

        return payload

    def __get_query_params(self):
        """Get request query parameters"""
        query_params = {
            "descriptors_only": "descriptors_only",
            "filter": "filter",
        }
        payload = {}
        for key, value in query_params.items():
            if value in self.config:
                if value == "filter" and self.config[value]:
                    # Remove any filter that starts with "date:"
                    cleaned_filters = " ".join([f for f in self.config[value].split() if not f.startswith("date:")])
                    if cleaned_filters:
                        payload[key] = cleaned_filters
                        self._connector.debug_print(
                            "Removed date from the filter. Data will be fetched according to the days provided in the 'days' parameter."
                        )
                else:
                    payload[key] = self.config[value]

        return payload

    def __get_dtm_query_params(self):
        """Get request query parameters for DTM"""
        query_params = {
            "size": "size",
            "monitor_id": "monitor_id",
            "status": "status",
            "alert_type": "alert_type",
            "search": "search",
            "match_value": "match_value",
            "tags": "tags",
            "severity": "severity",
            "mscore_gte": "mscore_gte",
        }
        config = self._connector.get_config()
        payload = {}
        for gti_param, soar_param in query_params.items():
            if soar_param in config:
                if isinstance(config[soar_param], str) and "," in config[soar_param]:
                    self._connector.debug_print(f"Found comma in DTM parameter '{soar_param}', value: '{config[soar_param]}'")
                    self._connector.debug_print("Converting comma-separated string to list for parameter")
                    payload[gti_param] = [x.strip() for x in config[soar_param].split(",")]
                else:
                    payload[gti_param] = config[soar_param]

        # Fixed values
        payload["sort"] = "created_at"
        payload["order"] = "desc"
        payload["refs"] = "true"
        return payload

    def __make_rest_call(self, url, method, limit=None, headers=None, param=None, body=None):
        """Invoke API"""
        args = {
            "endpoint": url,
            "action_result": self._action_result,
            "method": method.lower(),
            "headers": headers or {},
        }

        if param:
            args["endpoint"] = f"{args['endpoint']}?{urlencode(param, doseq=True)}"
            self._connector.debug_print(f"Calling {args['endpoint']},")

        if body:
            args["json"] = body

        ingestion_type = self.config.get("ingestion_type")
        if ingestion_type == "DTM Alerts":
            return self._connector.util._paginator_dtm(limit=limit, **args)
        elif ingestion_type == "ASM Issues":
            return self._connector.util.make_rest_call(**args)
        return self._connector.util._paginator(limit=limit, is_on_poll=True, **args)

    def _get_duplicate_count(self, last_notification_date):
        """
        Retrieves the number of duplicate items based on the provided last notification date.

        Args:
            last_notification_date (str): The last notification date to filter the items.

        Returns:
            int: The number of duplicate items. Returns 0 if the API call fails.
        """
        query_params = {}
        query_params["filter"] = query_params["filter"] = f"{query_params.get('filter', '')} date:{last_notification_date}".strip()

        endpoint, method = consts.IOC_ON_POLL_ENDPOINT, "get"

        ret_val, response = self.__make_rest_call(url=endpoint, method=method, param=query_params)

        if phantom.is_fail(ret_val):
            return 0
        return len(response)

    def _convert_all_date_fields_to_utc(self, data):
        """
        Recursively convert all date fields to UTC format throughout the entire JSON structure.

        Args:
            data: The data structure (dict, list, or value) to process

        Returns:
            The updated data structure with all date fields converted to UTC
        """
        # Date field names to look for
        date_fields = [
            "last_analysis_date",
            "creation_date",
            "last_modification_date",
            "last_submission_date",
            "first_submission_date",
            "notification_date",
            "first_seen_itw_date",
            "last_dns_records_date",
            "last_seen_itw_date",
            "last_update_date",
            "expiration_date",
            "last_https_certificate_date",
            "event_date",
            "whois_date",
        ]

        # Handle dictionaries
        if isinstance(data, dict):
            for key, value in data.items():
                # Check if this key is a date field
                if key in date_fields and value:
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                    data[key] = self._connector.util.convert_unix_to_utc(value)
                # Recursively process nested objects
                elif isinstance(value, (dict, list)):
                    data[key] = self._convert_all_date_fields_to_utc(value)

        # Handle lists
        elif isinstance(data, list):
            for i, item in enumerate(data):
                data[i] = self._convert_all_date_fields_to_utc(item)

        return data

    def _ensure_container_exists(self, container_id, day):
        """
        Check if a container with the given container_id exists. If it does not exist, create a new container with the given day.

        Args:
            container_id (str): The ID of the container to check.
            day (str): The day to use when creating a new container.

        Returns:
            str: The ID of the container, either the existing one or the newly created one.
        """

        container_info = phantom_rules.get_container(container_id)
        if container_info is None:
            self._connector.debug_print(f"Cannot find container with id {container_id}")
            self._connector.debug_print(f"Created new container for {day}")
            container_id = self._create_container(day)
            return container_id

        return container_id

    def _remove_fields(self, json_data):
        """Remove specified fields from the JSON data."""

        IOC_STREAM_NOTIFICATIONS_ATTRIBUTES_REMOVAL = [
            "attributes.crowdsourced_context",
            "attributes.html_meta",
            "attributes.threat_names",
            "attributes.tags",
            "attributes.outgoing_links",
            "attributes.last_analysis_results",
            "attributes.names",
            "attributes.pe_info",
            "attributes.detectiteasy",
            "attributes.popularity_ranks",
            "attributes.whois",
            "attributes.last_https_certificate",
            "attributes.last_dns_records",
            "attributes.popular_threat_classification.popular_threat_category",
            "attributes.popular_threat_classification.popular_threat_name",
        ]

        # Create a deep copy to avoid modifying the original
        data = json_data.copy()

        def remove_field(obj, path_parts):
            # Base case: we've reached the last part of the path
            if len(path_parts) == 1:
                if path_parts[0] in obj:
                    del obj[path_parts[0]]
                return

            # Recursive case: navigate deeper into the object
            key = path_parts[0]
            if key in obj and isinstance(obj[key], dict):
                # This call modifies obj[key] in place, which is a reference within data
                remove_field(obj[key], path_parts[1:])

        # Process each path to remove
        for path in IOC_STREAM_NOTIFICATIONS_ATTRIBUTES_REMOVAL:
            remove_field(data, path.split("."))

        return data
