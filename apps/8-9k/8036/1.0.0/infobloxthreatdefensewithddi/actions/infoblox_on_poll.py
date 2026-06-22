# File: infoblox_on_poll.py
#
# Copyright 2025 Infoblox Inc.
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

from datetime import datetime, timezone

import phantom.app as phantom

import infoblox_consts as consts
from actions import BaseAction


class OnPoll(BaseAction):
    """Class to handle on poll action for DNS Security Events."""

    def execute(self, param=None):
        """Execute the on_poll action.

        Step 1: Check ingestion type from configuration
        Step 2: If DNS Security Events, process those events
        Step 3: If SOC Insights, process those events
        Step 4: Save checkpoint for future polling

        Args:
            param (dict): Parameters provided by Splunk SOAR
                - container_id (str, optional): ID of the container to ingest artifacts into
                - container_count (int, optional): Maximum number of containers to create
                - artifact_count (int, optional): Maximum number of artifacts to create per container
                - start_time (str, optional): Start time for polling
                - end_time (str, optional): End time for polling
        """
        self._connector.save_progress(consts.INFOBLOX_ON_POLL_START_MSG)
        self._connector.debug_print("In action handler for on_poll")

        # Process the standard parameters that may be provided by SOAR
        if param is None:
            param = {}

        config = self._connector.get_config()
        self._is_poll_now = self._connector.is_poll_now()
        self._state = self._connector._state

        # Get the ingestion type from the configuration
        ingestion_type = config.get("ingestion_type", "DNS Security Events")

        if ingestion_type == "DNS Security Events":
            self._connector.debug_print("This asset is configured to ingest DNS Security Events")
            # Process parameters for DNS Security Events polling
            ret_val = self._process_parameters(config)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            # Start the polling process for DNS Security Events
            ret_val, response = self._poll_dns_security_events()
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()
        elif ingestion_type == "SOC Insights":
            self._connector.debug_print("This asset is configured to ingest SOC Insights")
            self._connector.save_progress(consts.INFOBLOX_SOC_INSIGHTS_POLL_START)

            # Process parameters for SOC Insights polling
            ret_val = self._process_soc_insights_parameters(config)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            # Start the polling process for SOC Insights
            ret_val, response = self._poll_soc_insights()
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            self._connector.save_progress(consts.INFOBLOX_SOC_INSIGHTS_POLL_FINISH)
        else:
            self._connector.save_progress(f"Invalid ingestion type: {ingestion_type}")
            return self._action_result.set_status(phantom.APP_ERROR, f"Invalid ingestion type: {ingestion_type}")

        return self._action_result.set_status(phantom.APP_SUCCESS)

    def _process_parameters(self, config):
        """Process and validate parameters from the asset configuration.

        Args:
            config (dict): Asset configuration dictionary

        Returns:
            int: phantom.APP_SUCCESS or phantom.APP_ERROR
        """
        self._connector.debug_print("Processing parameters for DNS Security Events polling")

        # Initialize parameters from config, mapping user-friendly names to API parameter names
        # Only using the specified parameters

        # Filter parameters
        self._qname = config.get("queried_name", "")  # Query name
        self._policy_name = config.get("policy_name", "")  # Policy name
        self._threat_level = config.get("threat_level", "")  # Threat severity level
        self._threat_class = config.get("threat_class", "")  # Threat category
        self._threat_family = config.get("threat_family", "")  # Threat family
        self._threat_indicator = config.get("threat_indicator", "")  # Threat indicator
        self._policy_action = config.get("policy_action", "")  # Action performed
        self._feed_name = config.get("feed_name", "")  # Threat feed name
        self._network = config.get("network", "")  # Network name/endpoint
        self._limit = config.get("limit", 100)  # Number of results to return

        # Convert comma-separated strings to lists for parameters that accept multiple values
        multi_value_params = [
            "_qname",
            "_policy_name",
            "_threat_class",
            "_threat_family",
            "_threat_indicator",
            "_policy_action",
            "_feed_name",
            "_network",
        ]

        for param_name in multi_value_params:
            param_value = getattr(self, param_name)
            if param_value and isinstance(param_value, str):
                setattr(self, param_name, [x.strip() for x in param_value.split(",") if x.strip()])

        # Convert limit to integer
        try:
            self._limit = int(self._limit)
            if self._limit <= 0:
                self._limit = consts.DEFAULT_LIMIT
        except (ValueError, TypeError):
            self._limit = consts.DEFAULT_LIMIT

        return phantom.APP_SUCCESS

    def _poll_dns_security_events(self):
        """Poll for DNS Security Events from Infoblox.

        Constructs the API request, handles pagination, and processes the response.

        Returns:
            tuple: (phantom.APP_SUCCESS/APP_ERROR, API response data)
        """
        self._connector.save_progress("Polling for DNS Security Events")

        # Get the time range for polling
        t0, t1 = self._get_time_range()
        self._connector.debug_print(f"Polling time range: t0={t0}, t1={t1}")

        # Construct query parameters
        params = self._build_query_params(t0, t1)

        # Make the API request
        endpoint = consts.DNS_SECURITY_EVENTS_ENDPOINT
        ret_val, response = self._connector.util.make_rest_call(
            endpoint=endpoint, action_result=self._action_result, method="get", params=params
        )

        if phantom.is_fail(ret_val):
            self._connector.save_progress("Failed to fetch DNS security events")
            return ret_val, None

        # Process the response and create containers/artifacts
        ret_val = self._process_dns_security_events(response)
        if phantom.is_fail(ret_val):
            return ret_val, None

        return phantom.APP_SUCCESS, response

    def _get_time_range(self):
        """Determine the time range for polling based on configuration and state.

        For scheduled polling, uses the last event timestamp from state.
        For manual polling, uses a configured lookback period.
        For specific time ranges, uses the provided start_time and end_time parameters.

        Returns:
            tuple: (t0, t1) timestamps in seconds since epoch
        """
        current_time = int(datetime.utcnow().timestamp())

        if self._is_poll_now:
            # For manual polling, use the configured lookback period
            max_hours = self._connector.get_config().get("max_hours_backwards", 24)
            try:
                max_hours = int(max_hours)
                if max_hours <= 0:
                    max_hours = 24
            except (ValueError, TypeError):
                max_hours = 24

            t0 = current_time - (max_hours * 3600)
            t1 = current_time

        else:
            # For scheduled polling, use the last event time from state
            self._state = self._connector._state
            last_event_time = self._state.get("last_event_time", None)

            if not last_event_time:
                # If no previous state, use default lookback period
                max_hours = self._connector.get_config().get("max_hours_backwards", 24)
                try:
                    max_hours = int(max_hours)
                    if max_hours <= 0:
                        max_hours = 24
                except (ValueError, TypeError):
                    max_hours = 24

                t0 = current_time - (max_hours * 3600)
            else:
                # Use the last event time plus 1 second to avoid duplicates
                t0 = last_event_time + 1

            t1 = current_time

        return t0, t1

    def _build_query_params(self, t0, t1):
        """Build query parameters for the DNS security events API.

        Args:
            t0 (int): Start timestamp
            t1 (int): End timestamp

        Returns:
            dict: Query parameters dictionary
        """
        # Required parameters
        params = {
            "t0": t0,
            "t1": t1,
            "_limit": self._limit,  # Use underscore prefix as required by API
        }

        # Add filter parameters if provided - only using the specified parameters
        if self._qname:
            params["qname"] = ",".join(self._qname) if isinstance(self._qname, list) else self._qname

        if self._policy_name:
            params["policy_name"] = ",".join(self._policy_name) if isinstance(self._policy_name, list) else self._policy_name

        if self._threat_level and self._threat_level != "ALL":
            params["threat_level"] = self._threat_level
            # If 'ALL' is selected, don't add the parameter so the API returns all severity levels

        if self._threat_class:
            params["threat_class"] = ",".join(self._threat_class) if isinstance(self._threat_class, list) else self._threat_class

        if self._threat_family:
            params["threat_family"] = ",".join(self._threat_family) if isinstance(self._threat_family, list) else self._threat_family

        if self._threat_indicator:
            params["threat_indicator"] = ",".join(self._threat_indicator) if isinstance(self._threat_indicator, list) else self._threat_indicator

        if self._policy_action:
            params["policy_action"] = ",".join(self._policy_action) if isinstance(self._policy_action, list) else self._policy_action

        if self._feed_name:
            params["feed_name"] = ",".join(self._feed_name) if isinstance(self._feed_name, list) else self._feed_name

        if self._network:
            params["network"] = ",".join(self._network) if isinstance(self._network, list) else self._network

        return params

    def _process_dns_security_events(self, response):
        """Process the DNS security events response and create containers and artifacts.

        Args:
            response (dict): API response containing DNS security events

        Returns:
            int: phantom.APP_SUCCESS or phantom.APP_ERROR
        """
        if not response or "result" not in response:
            self._connector.save_progress("No DNS security events found in the response")
            return phantom.APP_SUCCESS

        events = response.get("result", [])
        if not events:
            self._connector.save_progress("No DNS security events found")
            return phantom.APP_SUCCESS

        self._connector.save_progress(f"Processing {len(events)} DNS security events")

        # Sort events by event_time to ensure proper checkpointing
        events.sort(key=lambda x: x.get("event_time", ""))

        # Process each event and create a container with artifacts
        for event in events:
            try:
                # Create a container for this event
                container_id = self._create_container_for_event(event)
                if not container_id:
                    continue

                # Create an artifact for this event
                artifact_id = self._create_artifact_for_event(event, container_id)
                if not artifact_id:
                    continue

                # Update the last event time for checkpointing
                event_time_str = event.get("event_time", "")
                if event_time_str:
                    try:
                        event_time = datetime.strptime(event_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                        event_time_utc = event_time.replace(tzinfo=timezone.utc)
                        event_timestamp = int(event_time_utc.timestamp())

                        # Update state with the latest timestamp
                        if not self._is_poll_now:
                            self._state["last_event_time"] = event_timestamp
                            self._connector._state = self._state
                            self._connector.save_state(self._state)
                    except Exception as e:
                        self._connector.debug_print(f"Error parsing event time: {e!s}")

            except Exception as e:
                self._connector.debug_print(f"Error processing event: {e!s}")
                continue

        self._connector.save_progress("Completed processing DNS security events")
        return phantom.APP_SUCCESS

    def _create_container_for_event(self, event):
        """Create a container for a DNS security event.

        Args:
            event (dict): DNS security event data

        Returns:
            int: Container ID if successful, None otherwise
        """

        # Generate a container name from the event data
        qname = event.get("qname", "")
        tclass = event.get("tclass", "")  # Threat class from API response
        severity = event.get("severity", "")  # Severity level

        # Apply the new naming convention
        container_name = f"{tclass} - {qname}" if tclass and qname else "Infoblox DNS Security Event"

        # Map severity to container severity using the constant from infoblox_consts
        container_severity = consts.SEVERITY_MAPPING.get(severity, "medium")

        event_time = event.get("event_time", "Unknown Time")
        qname = event.get("qname", "Unknown Domain")
        threat_level = event.get("severity", "Unknown")

        container_name = f"Infoblox DNS Security Event - {qname} - {event_time}"

        # Map severity to container severity
        severity_mapping = {"LOW": "low", "MEDIUM": "medium", "HIGH": "high", "CRITICAL": "high"}
        container_severity = severity_mapping.get(threat_level, "medium")

        # Generate a unique source data identifier
        source_data_id = f"{qname}_{event.get('device', '')}_{event.get('event_time', '')}"

        # Create the container JSON
        container_json = {
            "name": container_name,
            "description": f"DNS Security Event for Query {qname}",
            "source_data_identifier": source_data_id,
            "severity": container_severity,
            "label": self._connector.get_config()
            .get("ingest", {})
            .get("container_label"),  # Changed from 'security_event' to 'event' which is more standard
            "data": event,
        }

        # Save container and handle return values properly
        save_result = self._connector.save_container(container_json)

        if save_result and len(save_result) == 3:
            ret_val, message, container_id = save_result
            if phantom.is_success(ret_val):
                if message == "Duplicate container found":
                    self._connector.debug_print(f"Using existing container with ID: {container_id}")
                else:
                    self._connector.debug_print(f"Successfully created container with ID: {container_id}")
                return container_id
            else:
                self._connector.debug_print(f"Failed to create container: {message}")
        else:
            self._connector.debug_print("Unexpected return value from save_container")

        return None

    def _create_artifact_for_event(self, event, container_id):
        """Create an artifact for a DNS security event.

        Args:
            event (dict): DNS security event data
            container_id (int): The container ID to add the artifact to

        Returns:
            int: Artifact ID if successful, None otherwise
        """
        # Get key fields for the artifact
        qname = event.get("qname", "")
        qip = event.get("qip", "")

        # Determine the artifact type based on event data
        if qname:
            artifact_type = "DNS Name"
            artifact_cef_types = {"domainName": ["dns_domain"]}
        elif qip:
            artifact_type = "IP Address"
            artifact_cef_types = {"deviceAddress": ["ip"]}
        else:
            artifact_type = "DNS Security Event"
            artifact_cef_types = {}

        # Build CEF data with only non-empty fields
        # First create a dictionary with all possible fields
        temp_cef_data = {
            # Basic DNS Query Information
            "Query Name": qname,
            "Client IP": qip,
            "Device IP": event.get("device", ""),
            "Source": "Infoblox DNS Security",
            # DNS Query Details
            "Query Type": event.get("qtype", ""),
            "Response Code": event.get("rcode", ""),
            "Response Data": event.get("rdata", ""),
            # Threat Intelligence
            "Threat Class": event.get("tclass", ""),
            "Threat Family": event.get("tfamily", ""),
            "Threat Property": event.get("tproperty", ""),
            "Confidence": event.get("confidence", ""),
            "Threat Indicator": event.get("threat_indicator", ""),
            # Policy Information
            "Policy Action": event.get("policy_action", ""),
            "Policy Name": event.get("policy_name", ""),
            "Feed Type": event.get("feed_type", ""),
            "Feed Name": event.get("feed_name", ""),
            # Network Information
            "Network": event.get("network", ""),
            "User": event.get("user", ""),
            "User Groups": event.get("user_groups", ""),
            "Country": event.get("country", ""),
            "Private IP": event.get("private_ip", ""),
            "MAC Address": event.get("mac_address", ""),
            # Application Information
            "Application Name": event.get("app_name", ""),
            "Application Category": event.get("app_category", ""),
            "DNS View": event.get("dns_view", ""),
            "Endpoint Groups": event.get("endpoint_groups", ""),
            # Temporal Information
            "Event Time": event.get("event_time", ""),
            "Severity": event.get("severity", ""),
        }

        # Filter out empty fields
        cef_data = {response_key: response_value for response_key, response_value in temp_cef_data.items() if response_value}

        # Generate source data identifier for the artifact
        source_data_id = f"{qname}_{qip}_{event.get('event_time', '')}"

        # Create the artifact JSON
        artifact_json = {
            "name": (
                f"{event.get('tclass', '')} - {qname}" if event.get("tclass", "") and qname else "Infoblox DNS Security Event"
            ),  # New naming convention using actual field name from API
            "container_id": container_id,
            "source_data_identifier": source_data_id,
            "cef": cef_data,
            "cef_types": artifact_cef_types,
            "severity": consts.SEVERITY_MAPPING.get(event.get("severity", ""), "medium"),
            "data": event,
            "run_automation": True,
            "type": artifact_type,
        }

        # Use save_artifacts instead of save_artifact for better handling
        artifacts_list = [artifact_json]
        save_result = self._connector.save_artifacts(artifacts_list)

        if save_result and len(save_result) == 3:
            ret_val, message, ids = save_result
            if phantom.is_success(ret_val) and ids and len(ids) > 0:
                self._connector.debug_print(f"Successfully saved artifact with ID: {ids[0]}")
                return ids[0]
            else:
                self._connector.debug_print(f"Failed to save artifact: {message}")
        else:
            self._connector.debug_print("Unexpected return value from save_artifacts")

        return None

    def _process_soc_insights_parameters(self, config):
        """Process and validate parameters from the asset configuration for SOC Insights polling.

        Args:
            config (dict): Asset configuration dictionary

        Returns:
            int: phantom.APP_SUCCESS or phantom.APP_ERROR
        """
        self._connector.debug_print("Processing parameters for SOC Insights polling")

        # Initialize parameters from config for SOC Insights
        self._soc_status = config.get("soc_status", "")
        self._soc_threat_type = config.get("soc_threat_type", "")
        self._soc_priority = config.get("soc_priority", "")

        return phantom.APP_SUCCESS

    def _poll_soc_insights(self):
        """Poll for SOC Insights from Infoblox.

        Constructs the API request and processes the response.
        No checkpointing is used since the API doesn't support time-based filtering.
        Deduplication is handled via insightId using SOAR's built-in mechanisms.

        Returns:
            tuple: (phantom.APP_SUCCESS/APP_ERROR, API response data)
        """
        self._connector.save_progress("Polling for SOC Insights")

        # Construct query parameters
        params = self._build_soc_insights_query_params()

        # Make the API request
        endpoint = consts.SOC_INSIGHTS_ENDPOINT
        ret_val, response = self._connector.util.make_rest_call(
            endpoint=endpoint, action_result=self._action_result, method="get", params=params
        )

        if phantom.is_fail(ret_val):
            self._connector.save_progress("Failed to fetch SOC Insights")
            return ret_val, None

        # Validate response structure
        if not response or "insightList" not in response:
            self._connector.save_progress(consts.ACTION_SOC_INSIGHTS_EMPTY)
            return phantom.APP_SUCCESS, response

        insights = response.get("insightList", [])
        if not insights:
            self._connector.save_progress(consts.ACTION_SOC_INSIGHTS_EMPTY)
            return phantom.APP_SUCCESS, response

        self._connector.save_progress(consts.ACTION_SOC_INSIGHTS_SUCCESS.format(count=len(insights)))

        # Process the response and create containers/artifacts
        ret_val, containers_created = self._process_soc_insights(insights)
        if phantom.is_fail(ret_val):
            return ret_val, None

        self._connector.save_progress(consts.ACTION_SOC_INSIGHTS_CONTAINERS_CREATED.format(count=containers_created))

        return phantom.APP_SUCCESS, response

    def _build_soc_insights_query_params(self):
        """Build query parameters for the SOC Insights API.

        Returns:
            dict: Query parameters for API request
        """
        params = {}

        # Add filtering parameters if provided
        if self._soc_status:
            params["status"] = self._soc_status

        if self._soc_threat_type:
            params["threatType"] = self._soc_threat_type

        if self._soc_priority and self._soc_priority.lower() != "all":
            params["priority"] = self._soc_priority

        self._connector.debug_print(f"SOC Insights query parameters: {params}")
        return params

    def _process_soc_insights(self, insights):
        """Process the SOC Insights response and create containers and artifacts.

        Args:
            insights (list): List of SOC Insights from API response

        Returns:
            tuple: (phantom.APP_SUCCESS or phantom.APP_ERROR, containers_created_count)
        """
        if not insights:
            self._connector.save_progress("No SOC Insights found in the response")
            return phantom.APP_SUCCESS, 0

        self._connector.save_progress(f"Processing {len(insights)} SOC Insights")
        containers_created = 0

        # Process each insight and create a container with artifacts
        for i, insight in enumerate(insights):
            try:
                insight_id = insight.get("insightId")
                if not insight_id:
                    self._connector.debug_print("Skipping insight without insightId")
                    continue

                # Create a container for this insight
                container_result = self._create_container_for_insight(insight)
                self._connector.debug_print(f"Container result for insight {insight_id}: {container_result}")
                if container_result and len(container_result) > 2:
                    container_id = container_result[2]

                    containers_created += 1
                    self._connector.debug_print(consts.CONTAINER_CREATED_MSG.format(insight_id=insight_id))

                    # Create an artifact for this insight
                    artifact_id = self._create_artifact_for_insight(insight, container_id)
                    if artifact_id:
                        self._connector.debug_print(consts.ARTIFACT_CREATED_MSG.format(insight_id=insight_id))

                if (i + 1) % 10 == 0:
                    self._connector.save_progress(f"Processed {i + 1} of {len(insights)} insights")

            except Exception as e:
                self._connector.debug_print(f"Error processing insight {insight.get('insightId', 'unknown')}: {e!s}")
                continue

        self._connector.save_progress(f"Completed processing SOC Insights. Created {containers_created} new containers.")
        return phantom.APP_SUCCESS, containers_created

    def _create_container_for_insight(self, insight):
        """Create a container for a SOC Insight.

        Args:
            insight (dict): SOC Insight data

        Returns:
            int: Container ID if successful, None otherwise
        """
        try:
            # Generate container name as specified: threatType + '-' + tFamily
            threat_type = insight.get("threatType", "Unknown")
            t_family = insight.get("tFamily", "Unknown")
            container_name = f"{threat_type}-{t_family}"

            insight_id = insight.get("insightId", "")
            self._connector.debug_print(
                f"Creating container for insight {insight_id} with name {container_name} and priority {insight.get('priorityText', '')}"
            )
            # Map priority to container severity
            container_severity = self._map_priority_to_severity(insight.get("priorityText", ""))

            # Generate source data identifier using insightId for deduplication
            source_data_id = f"{consts.SOC_INSIGHTS_CONTAINER_SOURCE_ID_KEY}_{insight_id}"

            # Create the container JSON
            container_json = {
                "name": container_name,
                "description": f"SOC Insight: {threat_type} - {t_family}",
                "source_data_identifier": source_data_id,
                "severity": container_severity,
                "label": self._connector.get_config().get("ingest", {}).get("container_label"),
                "data": insight,
                "tags": ["infoblox", "soc_insights", threat_type.lower(), t_family.lower()],
            }

            return self._connector.save_container(container_json)

        except Exception as e:
            self._connector.debug_print(f"Error creating container: {e!s}")
            return None

    def _map_priority_to_severity(self, priority_text):
        """Map SOC Insight priority to Phantom container severity.

        Args:
            priority_text (str): Priority text from insight (LOW, INFO, MEDIUM, HIGH, CRITICAL)

        Returns:
            str: Phantom severity level
        """
        return consts.PHANTOM_SEVERITY_MAP.get(priority_text.upper())

    def _create_artifact_for_insight(self, insight, container_id):
        """Create an artifact for a SOC Insight.

        Args:
            insight (dict): SOC Insight data
            container_id (int): The container ID to add the artifact to

        Returns:
            int: Artifact ID if successful, None otherwise
        """
        try:
            insight_id = insight.get("insightId", "")
            threat_type = insight.get("threatType", "")
            t_family = insight.get("tFamily", "")

            # Determine the artifact type
            artifact_type = "SOC Insight Data"

            # Build CEF data with all available insight fields
            cef_data = {
                # Core Insight Information
                "Insight ID": insight_id,
                "Threat Class": insight.get("tClass", ""),
                "Threat Family": t_family,
                "Threat Type": threat_type,
                "Status": insight.get("status", ""),
                "Priority": insight.get("priorityText", ""),
                "Feed Source": insight.get("feedSource", ""),
                # Time Information
                "Started At": insight.get("startedAt", ""),
                "Date Changed": insight.get("dateChanged", ""),
                "Most Recent At": insight.get("mostRecentAt", ""),
                "Persistent Since": insight.get("persistentDate", ""),
                "Spreading Since": insight.get("spreadingDate", ""),
                # Event Statistics
                "Total Events": insight.get("numEvents", ""),
                "Blocked Events": insight.get("eventsBlockedCount", ""),
                "Unblocked Events": insight.get("eventsNotBlockedCount", ""),
                # Additional Info
                "Changed By": insight.get("changer", ""),
                "User Comment": insight.get("userComment", ""),
                "Device Vendor": "Infoblox",
                "Device Product": "Infoblox Cloud",
            }

            # Generate source data identifier for the artifact
            source_data_id = f"soc_insight_artifact_{insight_id}"

            artifact_severity = self._map_priority_to_severity(insight.get("priorityText", ""))

            # Create the artifact JSON
            artifact_json = {
                "name": f"SOC Insight Data - {threat_type}-{t_family}",
                "label": "soc_insight_data",
                "container_id": container_id,
                "source_data_identifier": source_data_id,
                "cef": cef_data,
                "type": artifact_type,
                "data": insight,
                "run_automation": True,
                "severity": artifact_severity,
                "tags": ["infoblox", "soc_insights"],
            }

            return self._connector.save_artifact(artifact_json)

        except Exception as e:
            self._connector.debug_print(f"Error creating artifact: {e!s}")
            return None
