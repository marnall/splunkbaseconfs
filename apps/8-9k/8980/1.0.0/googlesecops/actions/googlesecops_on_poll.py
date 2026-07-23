# File: googlesecops_on_poll.py
#
# Copyright (c) 2026 Google LLC
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

import json
import time
from datetime import UTC, datetime, timedelta

import phantom.app as phantom

import googlesecops_consts as consts
from actions import BaseAction  # pylint: disable=import-error,no-name-in-module


# Date format constant to avoid duplication
DATE_FORMAT_RFC3339 = "%Y-%m-%dT%H:%M:%S.%fZ"


class OnPollAction(BaseAction):
    """On Poll action for streaming detection alerts."""

    def execute(self):
        """
        Execute on_poll action to ingest detection alerts using streaming API.

        Returns:
            phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("on poll"))

        poll_config = self._get_poll_configuration()

        ret_val = self._start_streaming_ingestion(
            poll_config["max_results"],
            poll_config["is_poll_now"],
            poll_config["poll_timeout"],
        )

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        return self._action_result.set_status(phantom.APP_SUCCESS)

    def _get_poll_configuration(self):
        """Get poll configuration based on poll type."""
        is_poll_now = self._connector.is_poll_now()

        if is_poll_now:
            self._connector.save_progress("Running POLL NOW (50 minute timeout)")
            max_results = self._connector.client.max_results_poll_now
        else:
            self._connector.save_progress("Running scheduled/interval poll (50 minute timeout)")
            max_results = self._connector.client.max_results_scheduled_poll
        poll_timeout = consts.POLL_TIMEOUT

        self._connector.save_progress(f"Max results: {max_results}")

        return {
            "is_poll_now": is_poll_now,
            "max_results": max_results,
            "poll_timeout": poll_timeout,
        }

    def _start_streaming_ingestion(
        self,
        max_results,
        is_poll_now,
        poll_timeout,
    ):
        """
        Start streaming connection and ingest detections.

        Args:
            max_results: Maximum number of detections to ingest
            is_poll_now: Whether this is a POLL NOW run
            poll_timeout: Maximum time in seconds for this poll (50 min)

        Returns:
            phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        # Initialize rule filtering attributes
        self._excluded_rule_ids = set()
        self._included_rule_ids = set()
        self._excluded_rule_names = set()
        self._included_rule_names = set()

        # Build streaming endpoint URL
        stream_url = f"{self._connector.client.base_url}/legacy:legacyStreamDetectionAlerts"

        self._connector.save_progress(f"Connecting to streaming endpoint: {stream_url}")

        page_token, page_start_time, previous_start_time = self._setup_pagination(is_poll_now)
        request_body = self._build_request_body(page_token, page_start_time, max_results)
        self._configure_rule_filters()

        return self._make_streaming_request(
            stream_url,
            request_body,
            max_results,
            is_poll_now,
            previous_start_time,
            poll_timeout,
        )

    def _setup_pagination(self, is_poll_now):
        """Setup pagination parameters based on poll type."""
        if not is_poll_now:
            return self._setup_scheduled_poll_pagination()
        return self._setup_poll_now_pagination()

    def _setup_scheduled_poll_pagination(self):
        """
        Setup pagination for scheduled poll with priority logic:
        1. If page_token is present in state → use it
        2. Else if page_start_time is present in state → use it
        3. Else use start_time from config params
        """
        state = self._connector._state
        previous_start_time = state.get("page_start_time")

        if previous_start_time:
            self._connector.debug_print(f"Initial start_time from state: {previous_start_time}")

        # Priority 1: Check for page_token in state
        page_token = state.get("page_token")
        if page_token:
            self._connector.save_progress("Resuming with page token from state")
            self._connector.debug_print(f"Using page_token")
            return page_token, "", previous_start_time

        # Priority 2: Check for page_start_time in state
        page_start_time = state.get("page_start_time")
        if page_start_time:
            self._connector.save_progress(f"Resuming from page_start_time in state: {page_start_time}")
            return None, page_start_time, previous_start_time

        # Priority 3: Use start_time from config params
        page_start_time = self._get_configured_or_default_start_time("scheduled polling")
        return None, page_start_time, previous_start_time

    def _get_configured_or_default_start_time(self, poll_type):
        """Get configured start_time or default to 1 day ago. Validates that start_time is not more than 7 days in the past."""
        page_start_time = self._connector.client.start_time

        if not page_start_time:
            self._connector.debug_print("[on_poll] No start_time configured, defaulting to last 1 day")
            start_dt = datetime.now(UTC) - timedelta(days=1)
        else:
            # Validate that configured start_time is not more than 7 days in the past
            ret_val, start_dt = self._connector.validator.validate_time_parameter(
                self._action_result,
                page_start_time,
                "start_time",
                allow_future=False,
                max_days_past=7,
            )

            if phantom.is_fail(ret_val):
                self._connector.save_progress("Configured start_time is more than 7 days in the past or invalid. Using last 1 day instead.")
                start_dt = datetime.now(UTC) - timedelta(days=1)

            api_limit = datetime.now(UTC) - timedelta(days=7) + timedelta(minutes=1)
            if start_dt < api_limit:
                self._connector.save_progress("start_time is at the 7-day API boundary; adjusting by 1 minute to stay within limit.")
                start_dt = api_limit

        page_start_time = start_dt.strftime(DATE_FORMAT_RFC3339)
        self._connector.save_progress(f"Using start time {page_start_time} for {poll_type}")
        return page_start_time

    def _setup_poll_now_pagination(self):
        """Setup pagination for poll now."""
        configured_time = self._connector.client.start_time_poll_now or self._connector.client.start_time

        if not configured_time:
            self._connector.debug_print("[on_poll] No start_time configured for poll_now, defaulting to last 1 day")
            start_dt = datetime.now(UTC) - timedelta(days=1)
        else:
            ret_val, start_dt = self._connector.validator.validate_time_parameter(
                self._action_result,
                configured_time,
                "start_time",
                allow_future=False,
                max_days_past=7,
            )

            if phantom.is_fail(ret_val):
                self._connector.save_progress("Configured start_time is more than 7 days in the past or invalid. Using last 1 day instead.")
                start_dt = datetime.now(UTC) - timedelta(days=1)

            # Apply buffer so the timestamp never sits exactly on the 7-day boundary
            # by the time the API processes the request (connection setup + latency).
            api_limit = datetime.now(UTC) - timedelta(days=7) + timedelta(minutes=5)
            if start_dt < api_limit:
                self._connector.save_progress("start_time is at the 7-day API boundary; adjusting by 5 minutes to stay within limit.")
                start_dt = api_limit

        page_start_time = start_dt.strftime(DATE_FORMAT_RFC3339)
        self._connector.save_progress(f"Using start time {page_start_time} for poll now.")
        return None, page_start_time, None

    def _build_request_body(self, page_token, page_start_time, max_results):
        """Build request body for streaming API."""
        request_body = {}

        if page_token:
            request_body["pageToken"] = page_token
        elif page_start_time:
            request_body["pageStartTime"] = page_start_time

        batch_size = min(max_results, consts.DEFAULT_BATCH_SIZE)
        request_body["detectionBatchSize"] = batch_size
        return request_body

    def _configure_rule_filters(self):
        """Configure rule ID and name filters."""
        rule_ids = self._connector.client.rule_ids_for_ingestion
        exclude_rule_ids = self._connector.client.exclude_rule_ids

        if rule_ids and rule_ids != ["-"]:
            if exclude_rule_ids:
                self._excluded_rule_ids = set(rule_ids)
                self._connector.save_progress(f"Will exclude detections with rule IDs: {rule_ids}")
            else:
                self._included_rule_ids = set(rule_ids)
                self._connector.save_progress(f"Will include only detections with rule ids: {rule_ids}")

        rule_names = self._connector.client.rule_names_for_ingestion
        exclude_rule_names = self._connector.client.exclude_rule_names

        if rule_names and rule_names != ["-"]:
            if exclude_rule_names and rule_ids and not exclude_rule_ids:
                self._connector.save_progress("Warning: Excluding rule names while including rule IDs may produce unexpected results.")

            if exclude_rule_names:
                self._excluded_rule_names = set(rule_names)
                self._connector.save_progress(f"Will exclude detections with rule names: {rule_names}")
            else:
                self._included_rule_names = set(rule_names)
                self._connector.save_progress(f"Will include only detections with rule names: {rule_names}")

    def _make_streaming_request(
        self,
        stream_url,
        request_body,
        max_results,
        is_poll_now,
        previous_start_time,
        poll_timeout,
    ):
        """Make streaming request and handle response."""
        try:
            with self._connector.client.http_client.post(
                url=stream_url,
                stream=True,
                json=request_body if request_body else None,
                timeout=poll_timeout,
            ) as response:
                if response.status_code != 200:
                    return self._handle_error_response(response)

                return self._process_stream(
                    response,
                    max_results,
                    is_poll_now,
                    previous_start_time,
                    poll_timeout,
                )

        except Exception as e:
            error_msg = self._connector.utils._get_error_message_from_exception(e)
            self._connector.save_progress(f"Error establishing streaming connection: {error_msg}")
            return self._action_result.set_status(phantom.APP_ERROR, error_msg)

    def _handle_error_response(self, response):
        """Handle error response from streaming API."""
        error_msg = f"Connection refused with status={response.status_code}"
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", error_msg)
        except Exception:
            error_msg = f"{error_msg}, error={response.text}"

        if response.status_code == 403:
            return self._action_result.set_status(
                phantom.APP_ERROR,
                f"Permission denied (403): {error_msg}",
            )
        elif response.status_code == 401:
            return self._action_result.set_status(
                phantom.APP_ERROR,
                f"Unauthorized (401): {error_msg}",
            )
        else:
            return self._action_result.set_status(
                phantom.APP_ERROR,
                f"HTTP {response.status_code}: {error_msg}",
            )

    def _parse_stream(self, response):
        """
        Parse streaming response containing detection batches.
        Based on GoogleSecOpsStreamingAPI.py parse_stream implementation.

        Args:
            response: The response object from the streaming API

        Yields:
            Dictionary representations of each detection batch
        """
        try:
            if response.encoding is None:
                response.encoding = "utf-8"

            for line in response.iter_lines(decode_unicode=True, delimiter="\r\n"):
                if not line:
                    continue
                # Trim all characters before first opening brace, and after last closing brace
                # Example: "  {'key1': 'value1'},  " -> "{'key1': 'value1'}"
                json_string = "{" + line.split("{", 1)[1].rsplit("}", 1)[0] + "}"
                yield json.loads(json_string)

        except Exception as e:
            # Return error batch similar to Chronicle's pattern
            yield {
                "error": {
                    "code": 503,
                    "status": "UNAVAILABLE",
                    "message": f"Exception caught while reading stream response: {e!s}",
                }
            }

    def _process_stream(
        self,
        response,
        max_results,
        is_poll_now,
        previous_start_time=None,
        poll_timeout=None,
    ):
        """
        Process streaming response and ingest detections.
        Uses line-by-line batch processing similar to GoogleSecOpsStreamingAPI.py.

        Args:
            response: Streaming HTTP response object
            max_results: Maximum detections to process
            is_poll_now: Whether this is POLL NOW
            previous_start_time: Initial start_time from state for comparison
            poll_timeout: Maximum time in seconds for this poll

        Returns:
            phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        if poll_timeout is None:
            poll_timeout = consts.POLL_TIMEOUT

        self._connector.save_progress(f"Stream connection established. Processing detections (timeout: {poll_timeout / 60:.0f} minutes)...")

        stream_state = self._init_stream_state()

        try:
            for batch in self._parse_stream(response):
                # Check timeout
                if self._check_timeout(stream_state, poll_timeout):
                    break

                # Log idle status
                self._log_idle_status(stream_state)

                # Handle special batch types
                if self._handle_error_batch(batch):
                    break

                if self._handle_heartbeat_batch(batch, stream_state, is_poll_now, previous_start_time):
                    continue

                # Extract continuation tokens
                self._extract_continuation_tokens(batch, stream_state)

                # Handle empty batches
                if self._handle_empty_batch(batch, stream_state, is_poll_now, previous_start_time):
                    continue

                # Process detections
                should_break = self._process_batch_detections(
                    batch,
                    stream_state,
                    max_results,
                    is_poll_now,
                    previous_start_time,
                )

                if should_break:
                    break

        except Exception as e:
            self._handle_stream_error(e, stream_state, is_poll_now, previous_start_time)

        self._finalize_stream_state(stream_state, is_poll_now, previous_start_time)

        return self._build_stream_summary(stream_state)

    def _init_stream_state(self):
        """Initialize stream processing state."""
        return {
            "detection_count": 0,
            "heartbeat_count": 0,
            "last_page_token": None,
            "last_page_start_time": None,
            "poll_start_time": time.time(),
            "skipped_detections": 0,
            "last_activity_time": time.time(),
            "last_idle_log_time": time.time(),
            "idle_log_interval": 30,
            "total_containers_created": 0,
            "total_artifacts_created": 0,
        }

    def _check_timeout(self, stream_state, poll_timeout):
        """Check if poll timeout has been reached."""
        elapsed_time = time.time() - stream_state["poll_start_time"]
        if elapsed_time >= poll_timeout:
            self._connector.save_progress(f"Poll timeout reached ({poll_timeout / 60:.0f} minutes). Closing connection gracefully.")
            return True
        return False

    def _log_idle_status(self, stream_state):
        """Log idle status periodically when no detections received."""
        current_time = time.time()
        time_since_last_detection = current_time - stream_state["last_activity_time"]
        time_since_last_log = current_time - stream_state["last_idle_log_time"]

        if time_since_last_detection >= stream_state["idle_log_interval"] and time_since_last_log >= stream_state["idle_log_interval"]:
            self._connector.save_progress(
                f"Waiting for detections... (idle for {int(time_since_last_detection)}s, "
                f"total detections: {stream_state['detection_count']}, heartbeats: {stream_state['heartbeat_count']})"
            )
            stream_state["last_idle_log_time"] = current_time

    def _handle_error_batch(self, batch):
        """Handle error batches from the stream."""
        if "error" in batch:
            error_info = batch.get("error", {})
            error_code = error_info.get("code", "unknown")
            error_msg = error_info.get("message", "Unknown error")
            self._connector.save_progress(f"Received error batch: [{error_code}] {error_msg}")
            return True
        return False

    def _handle_heartbeat_batch(self, batch, stream_state, is_poll_now, previous_start_time):
        """Handle heartbeat batches from the stream."""
        if "heartbeat" in batch:
            stream_state["heartbeat_count"] += 1
            self._connector.debug_print(f"Received heartbeat #{stream_state['heartbeat_count']}")

            if "nextPageStartTime" in batch:
                stream_state["last_page_start_time"] = batch["nextPageStartTime"]
                # Heartbeat with nextPageStartTime indicates boundary between windows.
                # Clear any stale page token so next cycle starts from page_start_time.
                stream_state["last_page_token"] = None
                self._connector.debug_print(f"pageStartTime from heartbeat: {stream_state['last_page_start_time']}")
                if not is_poll_now:
                    self._save_state(
                        page_start_time=stream_state.get("last_page_start_time"),
                        is_poll_now=is_poll_now,
                        previous_start_time=previous_start_time,
                    )
            return True
        return False

    def _extract_continuation_tokens(self, batch, stream_state):
        """Extract continuation tokens from batch."""
        next_page_token = batch.get("nextPageToken")
        next_page_start_time = batch.get("nextPageStartTime")

        if next_page_token:
            stream_state["last_page_token"] = next_page_token
            self._connector.debug_print(f"Received nextPageToken")

        # nextPageStartTime without nextPageToken means end-of-page window.
        # Clear token so the next cycle uses page_start_time.
        if next_page_start_time and not next_page_token:
            stream_state["last_page_start_time"] = next_page_start_time
            stream_state["last_page_token"] = None
            self._connector.debug_print(f"Received nextPageStartTime: {stream_state['last_page_start_time']}")
        elif next_page_start_time and next_page_token:
            self._connector.debug_print("Received both nextPageToken and nextPageStartTime; prioritizing nextPageToken for continuation.")

    def _handle_empty_batch(self, batch, stream_state, is_poll_now, previous_start_time):
        """Handle batches without detections."""
        if "detections" not in batch:
            self._connector.debug_print("Received batch without detections (state update only)")
            if not is_poll_now and (stream_state.get("last_page_token") or stream_state.get("last_page_start_time")):
                self._save_state(
                    page_token=stream_state.get("last_page_token"),
                    page_start_time=stream_state.get("last_page_start_time"),
                    is_poll_now=is_poll_now,
                    previous_start_time=previous_start_time,
                )
            return True
        return False

    def _process_batch_detections(
        self,
        batch,
        stream_state,
        max_results,
        is_poll_now,
        previous_start_time,
    ):
        """Process detections in a batch."""
        detections_array = batch.get("detections", [])
        self._connector.debug_print(f"Received batch with {len(detections_array)} detections")

        if detections_array:
            stream_state["last_activity_time"] = time.time()

        batch_detections = []
        for detection_obj in detections_array:
            if not self._is_valid_detection(detection_obj):
                stream_state["skipped_detections"] += 1
                self._connector.debug_print(f"Skipped invalid detection #{stream_state['detection_count'] + stream_state['skipped_detections']}")
                continue

            if not self._should_ingest_detection(detection_obj):
                stream_state["skipped_detections"] += 1
                continue

            stream_state["detection_count"] += 1
            batch_detections.append(detection_obj)

            self._connector.save_progress(f"Received detection #{stream_state['detection_count']}")

            if stream_state["detection_count"] >= max_results:
                self._connector.save_progress(f"Reached max results limit ({max_results}). Stopping ingestion.")
                break

        if batch_detections:
            self._ingest_batch(batch_detections, stream_state)

        if not is_poll_now and (stream_state.get("last_page_token") or stream_state.get("last_page_start_time")):
            self._save_state(
                page_token=stream_state.get("last_page_token"),
                page_start_time=stream_state.get("last_page_start_time"),
                is_poll_now=is_poll_now,
                previous_start_time=previous_start_time,
            )

        return stream_state["detection_count"] >= max_results

    def _ingest_batch(self, batch_detections, stream_state):
        """Ingest a batch of detections."""
        self._connector.save_progress(f"Ingesting batch of {len(batch_detections)} detection(s)...")
        ret_val = self._ingest_detections(batch_detections)

        if phantom.is_success(ret_val):
            summary = self._action_result.get_summary()
            stream_state["total_containers_created"] += summary.get("total_containers_created", 0)
            stream_state["total_artifacts_created"] += summary.get("total_artifacts_created", 0)
            self._connector.debug_print(
                f"Batch ingested successfully. Containers: {summary.get('total_containers_created', 0)}, "
                f"Artifacts: {summary.get('total_artifacts_created', 0)}"
            )
        else:
            self._connector.debug_print(f"Failed to ingest batch of {len(batch_detections)} detections")

    def _handle_stream_error(self, error, stream_state, is_poll_now, previous_start_time):
        """Handle errors during stream processing."""
        error_msg = self._connector.utils._get_error_message_from_exception(error)
        self._connector.save_progress(error_msg)

        if not is_poll_now and (stream_state.get("last_page_token") or stream_state.get("last_page_start_time")):
            self._connector.save_progress("Saving checkpoint before error recovery...")
            self._save_state(
                page_token=stream_state.get("last_page_token"),
                page_start_time=stream_state.get("last_page_start_time"),
                is_poll_now=is_poll_now,
                previous_start_time=previous_start_time,
            )

    def _finalize_stream_state(self, stream_state, is_poll_now, previous_start_time):
        """Finalize stream state and save checkpoint."""
        if not is_poll_now and (stream_state.get("last_page_token") or stream_state.get("last_page_start_time")):
            self._save_state(
                page_token=stream_state.get("last_page_token"),
                page_start_time=stream_state.get("last_page_start_time"),
                is_poll_now=is_poll_now,
                previous_start_time=previous_start_time,
            )

    def _build_stream_summary(self, stream_state):
        """Build and return stream processing summary."""
        self._connector.save_progress(
            f"Stream processing complete. Total detections: {stream_state['detection_count']}, "
            f"Skipped: {stream_state['skipped_detections']}, Heartbeats: {stream_state['heartbeat_count']}"
        )

        if stream_state["detection_count"] > 0:
            self._action_result.set_summary(
                {
                    "total_detections_ingested": stream_state["detection_count"],
                    "total_containers_created": stream_state["total_containers_created"],
                    "total_artifacts_created": stream_state["total_artifacts_created"],
                }
            )
            return self._action_result.set_status(
                phantom.APP_SUCCESS,
                f"Successfully ingested {stream_state['detection_count']} detection(s) across {stream_state['total_containers_created']} container(s)",
            )
        else:
            if stream_state["heartbeat_count"] == 0 and stream_state["detection_count"] == 0 and stream_state["skipped_detections"] == 0:
                self._connector.save_progress("No response from API")
            else:
                self._connector.save_progress("No detections to ingest")

            self._action_result.set_summary(
                {
                    "total_detections_ingested": 0,
                    "total_containers_created": 0,
                    "total_artifacts_created": 0,
                }
            )
            return self._action_result.set_status(phantom.APP_SUCCESS, "No detections found")

    def _ingest_detections(self, detections):
        """
        Ingest detections as Splunk SOAR containers and artifacts.
        Creates a separate container for each detection.

        Args:
            detections: List of detection objects to ingest

        Returns:
            phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        self._connector.save_progress(f"Ingesting {len(detections)} detections...")

        containers_created = 0
        artifacts_created = 0
        default_severity = self._connector.client.default_severity

        for detection_data in detections:
            try:
                container = self._create_container(detection_data, default_severity)
                artifact = self._create_artifact(detection_data, default_severity)

                if not artifact:
                    self._connector.debug_print("No artifact created for detection, skipping container")
                    continue

                container["artifacts"] = [artifact]
                ret_val, message, container_id = self._connector.save_container(container)

                if phantom.is_fail(ret_val):
                    self._connector.debug_print(f"Failed to save container for detection: {message}")
                    continue

                containers_created += 1
                artifacts_created += 1
                self._connector.debug_print(f"Created container {container_id} for detection: {container['source_data_identifier']}")

            except Exception as e:
                error_msg = self._connector.utils._get_error_message_from_exception(e)
                self._connector.debug_print(f"Error ingesting detection: {error_msg}")
                continue

        self._set_ingestion_summary(len(detections), containers_created, artifacts_created)
        return self._action_result.set_status(phantom.APP_SUCCESS)

    def _set_ingestion_summary(self, total_detections, containers_created, artifacts_created):
        """Set the ingestion summary."""
        summary = {
            "total_detections_ingested": total_detections,
            "total_containers_created": containers_created,
            "total_artifacts_created": artifacts_created,
        }
        self._action_result.set_summary(summary)
        self._connector.save_progress(f"Ingestion complete. Containers: {containers_created}, Artifacts: {artifacts_created}")

    def _create_container(self, detection, default_severity):
        """
        Create a container from detection data with format: 'rule_name: detection_id'.

        Args:
            detection: Detection object
            detection_details: Detection details object
            default_severity: Default severity if not specified
            rule_name: Rule name (optional, will be extracted if not provided)

        Returns:
            dict: Container dictionary
        """
        detection_data = detection.get("detection", {})
        detection_details = detection_data[0] if detection_data and isinstance(detection_data, list) else {}
        rule_id = detection_details.get("ruleId", "unknown")
        rule_name = detection_details.get("ruleName", "Unknown Rule")
        alert_state = detection_details.get("alertState", "UNKNOWN")
        detection_time = detection.get("detectionTime", "")
        rule_type = detection.get("type", "")
        detection_id = detection.get("id", "unknown")

        # Map severity: informational/low->low, medium->medium, high/critical->high
        severity_map = {
            "INFORMATIONAL": "low",
            "LOW": "low",
            "MEDIUM": "medium",
            "HIGH": "high",
            "CRITICAL": "high",
        }
        severity = detection_details.get("severity", "")
        container_severity = severity_map.get(severity.upper(), default_severity)

        container = {
            "name": f"{rule_name}: {detection_id}",
            "description": f"Rule ID: {rule_id}, Rule Type: {rule_type}, Alert State: {alert_state}",
            "source_data_identifier": detection_id,
            "severity": container_severity,
            "start_time": detection_time,
        }

        return container

    def _create_artifact(self, detection, default_severity):
        """
        Create a single artifact from detection data with proper CEF keys.

        Args:
            detection: Detection object
            detection_details: Detection details object

        Returns:
            dict: Artifact dictionary
        """
        # Extract time window information
        detection_data = detection.get("detection", {})
        detection_details = detection_data[0] if detection_data and isinstance(detection_data, list) else {}
        time_window = detection_details.get("timeWindow", {})
        time_window_start_time = time_window.get("startTime", "")
        time_window_end_time = time_window.get("endTime", "")

        # Map severity: informational/low->low, medium->medium, high/critical->high
        severity_map = {
            "INFORMATIONAL": "low",
            "LOW": "low",
            "MEDIUM": "medium",
            "HIGH": "high",
            "CRITICAL": "high",
        }
        severity = detection_details.get("severity", "")
        artifact_severity = severity_map.get(severity.upper(), default_severity)

        # Create artifact with required CEF keys
        cef_fields = {
            "detection_id": detection.get("id"),
            "creation_time": detection.get("createdTime"),
            "detection_time": detection.get("detectionTime"),
            "detection_type": detection.get("type"),
            "time_window_start_time": time_window_start_time,
            "time_window_end_time": time_window_end_time,
            "rule_version": detection_details.get("ruleVersion"),
            "alert_state": detection_details.get("alertState"),
            "rule_type": detection_details.get("ruleType"),
            "severity": detection_details.get("severity"),
        }

        # Add riskScore as a CEF field if present
        risk_score = detection_details.get("riskScore")
        if risk_score is not None:
            cef_fields["riskScore"] = risk_score

        # Add outcomes as CEF fields in the form of outcome_{key}
        outcomes = detection_details.get("outcomes", [])
        for outcome in outcomes:
            outcome_key = outcome.get("key")
            outcome_value = outcome.get("value")
            if outcome_key and outcome_value is not None:
                cef_fields[f"outcome_{outcome_key}"] = outcome_value

        # Add detectionFields as CEF fields in the form of detection_field_{key}
        detection_fields = detection_details.get("detectionFields", [])
        for detection_field in detection_fields:
            field_key = detection_field.get("key")
            field_value = detection_field.get("value")
            if field_key and field_value is not None:
                cef_fields[f"detection_field_{field_key}"] = field_value

        artifact = {
            "name": f"Detection: {detection_details.get('ruleName', 'Unknown')}",
            "label": "detection",
            "severity": artifact_severity,
            "cef": cef_fields,
            "source_data_identifier": f"{detection.get('id')}",
            "data": detection,
        }

        return artifact

    def _is_valid_detection(self, detection_obj):
        """
        Validate that detection object has required structure.

        Args:
            detection_obj: Detection object from API

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Check for detection wrapper
            if "detection" not in detection_obj:
                return False

            detection = detection_obj.get("detection", [])

            # Check for detection array (should be a list)
            if not isinstance(detection, list):
                return False

            # Check that list is not empty
            if not detection:
                return False

            # Check for required fields in detection_obj
            if "id" not in detection_obj:
                return False

            return True

        except Exception:
            return False

    def _should_ingest_detection(self, detection_obj):
        """
        Check if detection should be ingested based on rule name and rule ID filters.
        Priority: rule_name filtering takes precedence over rule_id filtering.

        Args:
            detection_obj: Detection object from API

        Returns:
            bool: True if should ingest, False if should skip
        """
        try:
            detection = detection_obj.get("detection", [])
            # detection is a list, get the first element
            detection_details = detection[0] if detection else {}

            rule_name = detection_details.get("ruleName", "")
            rule_id = detection_details.get("ruleId", "")

            # Debug: Log rule ID and name for filtering
            self._connector.debug_print(f"Checking detection - Rule ID: '{rule_id}', Rule Name: '{rule_name}'")

            # Priority 1: Check rule_name filters first
            # If filter_exclude_rule_names is True and rule name is in the filter list, skip it
            if self._excluded_rule_names and rule_name in self._excluded_rule_names:
                self._connector.debug_print(f"Skipping detection with excluded rule name: {rule_name}")
                return False

            # If filter_exclude_rule_names is False and rule name is not in the filter list, skip it
            if self._included_rule_names and rule_name not in self._included_rule_names:
                self._connector.debug_print(f"Skipping detection with non-included rule name: {rule_name}")
                return False

            if self._excluded_rule_ids and rule_id in self._excluded_rule_ids:
                self._connector.debug_print(f"Skipping detection with excluded rule ID: {rule_id}")
                return False

            if hasattr(self, "_included_rule_ids") and self._included_rule_ids and rule_id not in self._included_rule_ids:
                self._connector.debug_print(f"Skipping detection with non-included rule ID: {rule_id}")
                return False

            return True

        except Exception as e:
            error_msg = self._connector.utils._get_error_message_from_exception(e)
            self._connector.debug_print(f"Error checking detection filters: {error_msg}. Including detection.")
            return True

    def _save_state(
        self,
        is_poll_now,
        page_token=None,
        page_start_time=None,
        previous_start_time=None,  # NOSONAR
    ):
        """
        Save checkpoint to state.
        This ensures state is saved BEFORE ingestion to prevent data loss.

        Logic:
        - If page_token is received: update it in state and use it in the next cycle.
        - If only page_start_time is received:
          - clear page_token from state
          - update page_start_time only if it differs from stored value

        Args:
            page_token: Page token from API response
            page_start_time: Page start time from API response
            is_poll_now: Whether this is POLL NOW (don't save state)
            previous_start_time: Initial start_time from state for comparison
        """
        if is_poll_now:
            return

        state = self._connector._state
        state_updated = False

        # pageToken takes priority for continuation.
        if page_token:
            if state.get("page_token") != page_token:
                state["page_token"] = page_token
                state_updated = True
                self._connector.debug_print(f"Saved checkpoint")
        elif page_start_time:
            if "page_token" in state:
                state.pop("page_token", None)
                state_updated = True
                self._connector.debug_print("Cleared pageToken because nextPageStartTime was received.")

            current_start_time = state.get("page_start_time")
            if page_start_time != current_start_time:
                state["page_start_time"] = page_start_time
                state_updated = True
                self._connector.debug_print(f"Saved checkpoint: pageStartTime={page_start_time} (changed from {current_start_time})")
            else:
                self._connector.debug_print(f"Skipping pageStartTime update: unchanged ({page_start_time})")

        # Only save state if something was updated
        if state_updated:
            self._connector.save_state(state)
