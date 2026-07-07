# File: vectrandr_on_poll.py
#
# Copyright (c) 2024-2025 Vectra
#
# This unpublished material is proprietary to Vectra.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Vectra.
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

from datetime import datetime, timedelta, timezone

import phantom.app as phantom

import vectrandr_consts as consts
from actions import BaseAction


class OnPollAction(BaseAction):
    """Class to handle on poll action."""

    def validate_date_format(self, action_result, input_date, is_state=False):
        """Check date format."""
        try:
            if len(input_date) == 10:  # Assuming date format 'YYYY-MM-DD'
                input_date += "T00:00:00Z"

            # Parse the input date string with the specified format
            date_object = datetime.strptime(input_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

            # Check if the parsed date is greater than or equal to '1970-01-01T00:00:00Z'
            # and less than or equal to the current time
            if date_object < datetime(1970, 1, 1, tzinfo=timezone.utc):
                return action_result.set_status(phantom.APP_ERROR, consts.VECTRA_UTC_SINCE_TIME_ERROR)
            elif date_object > datetime.now(tz=timezone.utc):
                return action_result.set_status(phantom.APP_ERROR, consts.VECTRA_GREATER_EQUAL_TIME_ERROR)
        except Exception as e:
            err_txt = self._connector.util._get_error_message_from_exception(e)
            if is_state:
                internal_message = "'state file'"
            else:
                internal_message = "'on_poll_start_time' configuration parameter"
            message = f"Invalid date string received in {internal_message}. Error\
                occurred while checking date format. {err_txt}"
            return action_result.set_status(phantom.APP_ERROR, message)
        return phantom.APP_SUCCESS

    def _get_on_poll_start_time(self, config):
        """Get on poll start time."""
        is_poll_now = self._connector.is_poll_now()
        start_time_from_state = self._connector.state.get(consts.VECTRA_LAST_DETECTION_TIMESTAMP_IN_STATE)
        if not is_poll_now and start_time_from_state:
            ret_val = self.validate_date_format(self._action_result, start_time_from_state, is_state=True)
            if not phantom.is_fail(ret_val):
                return ret_val, start_time_from_state
            self._connector.save_progress("Invalid datetime format provided in state file")
            self._connector.save_progress("Resetting state file")
            self._connector.state.pop(consts.VECTRA_LAST_DETECTION_TIMESTAMP_IN_STATE, None)
            return ret_val, start_time_from_state

        start_time_from_cofig = config.get("on_poll_start_time")
        if start_time_from_cofig:
            ret_val = self.validate_date_format(self._action_result, start_time_from_cofig)
            return ret_val, start_time_from_cofig

        self._connector.save_progress("Configuring the start time for polling to be three days from now")
        time_before_3_days_from_now = (datetime.now() - timedelta(days=3)).isoformat(timespec="seconds")
        return self._action_result.set_status(phantom.APP_SUCCESS), time_before_3_days_from_now

    def _get_entity_url(self, entity_type):
        """Get entity url."""
        if entity_type not in consts.VECTRA_VALID_ENTITIES:
            return self._action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_INVALID_ENTITY)
        entity_type = consts.ENTITY_TYPE_MAPPING[entity_type]

        url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_POLL_ENTITY_ENDPOINT.format(entity_type=entity_type)}"

        return phantom.APP_SUCCESS, url

    def _get_entity_filters(self, config, on_poll_start_time):
        """Get entity filters."""
        params = {
            "last_detection_timestamp_gte": on_poll_start_time,
            "ordering": "last_detection_timestamp",
            "state": "active",
        }

        ret_val, entity_tags = self._connector.util._extract_ids_from_params(
            self._action_result, "entity_tags", config.get("entity_tags", ""), False, False
        )
        if phantom.is_fail(ret_val):
            return self._action_result.get_status(), None

        ret_val, certainty = self._connector.util._validate_integer(
            self._action_result, config.get("certainty", 0), "certainty score", True, max_value=100
        )
        if phantom.is_fail(ret_val):
            return self._action_result.get_status(), None

        ret_val, threat = self._connector.util._validate_integer(
            self._action_result, config.get("threat", 0), "threat score", True, max_value=100
        )
        if phantom.is_fail(ret_val):
            return self._action_result.get_status(), None

        # if parameter is present then add it into the request params

        if entity_tags:
            params["tags"] = entity_tags
        if certainty:
            params["certainty_gte"] = certainty
        if threat:
            params["threat_gte"] = threat

        return phantom.APP_SUCCESS, params

    def _get_detection_filters(self, entity_id, entity_type, detection_category, detection_type):
        """Get detection filters"""
        query_string = ""
        if entity_type == "host":
            query_string = f'detection.src_{entity_type}.id:{entity_id} AND detection.state:"active"'
        elif entity_type == "account":
            query_string = f'detection.src_linked_{entity_type}.id:{entity_id} AND detection.state:"active"'

        if detection_category:
            if detection_category not in consts.VECTRA_DETECTION_CATEGORIES_MAPPING:
                return self._action_result.set_status(phantom.APP_ERROR, "Please provide valid value for detection category"), None
            elif detection_category != "All":
                query_string += f" AND detection.detection_category:{consts.VECTRA_DETECTION_CATEGORIES_MAPPING[detection_category]}"

        if detection_type:
            query_string += f' AND detection.detection_type:"{detection_type}"'

        return phantom.APP_SUCCESS, query_string

    def _get_identifier(self, object, entity_type=None):
        """Map entity fields with SOAR keys.

        :param label: object(entity/detection/assignment)
        :param has_type: if the object has type field

        :return: identifier
        """
        identifier = str(object.get("id"))
        if entity_type:
            identifier = f"{entity_type}-{identifier}"
        return identifier

    def _map_to_soar_keys(self, label, name, cef_types, sdi, cef, severity):
        """
        _map_to_soar_keys maps the given parameters to a dictionary with specific keys.

        :param label: str - The label to be assigned to the dictionary.
        :param name: str - The name to be assigned to the dictionary.
        :param cef_types: dict - A list of cef types to be assigned to the dictionary.
        :param sdi: str - The source data identifier to be assigned to the dictionary.
        :param cef: dict - The cef to be assigned to the dictionary.
        :param severity: str - The severity to be assigned to the dictionary.

        :return: dict - A dictionary containing the mapped parameters with specific keys.
        """
        return {"label": label, "name": name, "cef_types": cef_types, "source_data_identifier": sdi, "cef": cef, "severity": severity}

    def _create_artifacts(self, entity, severity, entity_type):
        """Create artifacts of entity, detection, and assignment."""
        artifacts = list()
        detections = entity.pop("detections", [])
        assignment = entity.pop("assignment", None)

        for detection in detections:
            identifier = self._get_identifier(detection)
            # remove unwanted _doc_modified_ts from the detection
            detection.pop("_doc_modified_ts", None)
            cef_types = consts.VECTRA_CEF_TYPES["detection"]
            artifacts.append(self._map_to_soar_keys("Detection", "Detection Artifact", cef_types, identifier, detection, severity))

        if assignment:
            identifier = self._get_identifier(assignment)
            cef_types = consts.VECTRA_CEF_TYPES["assignment"]
            artifacts.append(self._map_to_soar_keys("Assignment", "Assignment Artifact", cef_types, identifier, assignment, severity))

        identifier = self._get_identifier(entity, entity_type)
        artifacts.append(self._map_to_soar_keys("Entity", "Entity Artifact", consts.VECTRA_CEF_TYPES["entity"], identifier, entity, severity))

        return artifacts

    def _ingest_artifacts(self, artifacts, container_name, severity, sdi):
        """Ingest artifacts into SOAR."""
        self._connector.debug_print(f"Ingesting {len(artifacts)} artifacts for {container_name} container with {severity} severity")

        container = {"name": container_name, "description": "Entity ingested from Vectra", "source_data_identifier": sdi, "severity": severity}
        ret_val, message, cid = self._connector.save_container(container)

        if message == "Duplicate container found" and not self._connector.is_poll_now():
            self._connector._dup_entities += 1

        self._connector.debug_print(f"save_container returns, ret_val: {ret_val}, reason: {message}, id: {cid}")
        if phantom.is_fail(ret_val):
            return self._action_result.set_status(phantom.APP_ERROR, message)

        artifact_mapping = self._connector.util._get_artifact_of_container_id(cid)
        for artifact in artifacts:
            artifact_id = artifact_mapping.get(artifact.get("source_data_identifier"))
            if artifact_id:
                self._connector.util._delete_artifact(artifact_id)
            artifact["container_id"] = cid

        if artifacts:
            ret_val, message, ids = self._connector.save_artifacts(artifacts)
            self._connector.debug_print(f"save_artifacts returns, value: {ret_val}, reason: {message}, ids: {ids}")
            if phantom.is_fail(ret_val):
                return self._action_result.set_status(phantom.APP_ERROR, message)

        return phantom.APP_SUCCESS

    def execute(self):
        """Execute the on poll action."""
        self._connector.save_progress("Executing Polling")
        config = self._connector.config

        if self._connector.is_poll_now():
            max_allowed_container = config.get("manual_max_allowed_container", consts.VECTRA_DEFAULT_MAX_ALLOWED_CONTAINERS)
        else:
            max_allowed_container = config.get("schedule_max_allowed_container", consts.VECTRA_DEFAULT_MAX_ALLOWED_CONTAINERS)

        ret_val, _ = self._connector.util._validate_integer(self._action_result, max_allowed_container, "Max container allowed", False)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        container_limit = max_allowed_container
        total_ingested = 0

        while True:
            self._connector._dup_entities = 0

            ret_val, on_poll_start_time = self._get_on_poll_start_time(config)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            self._connector.save_progress(f"On poll start time is {on_poll_start_time}")

            entity_type = config.get("entity_type", "Host").lower()
            detection_category = config.get("detection_category", "All")
            detection_type = config.get("detection_type")
            # Getting filter for the entity
            ret_val, url = self._get_entity_url(entity_type)
            if phantom.is_fail(ret_val):
                self._connector.save_progress(self._action_result.get_message())
                return self._action_result.get_status()

            ret_val, params = self._get_entity_filters(config, on_poll_start_time)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            self._connector.send_progress("Getting Entities....")

            ret_val, entities = self._connector.util._paginator(self._action_result, url, params=params, limit=max_allowed_container)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            for entity in entities:
                # Get detection
                self._connector.send_progress("Getting Detections....")

                entity_id = entity.get("id")
                ret_val, query_string = self._get_detection_filters(entity_id, entity_type, detection_category, detection_type)
                if phantom.is_fail(ret_val):
                    return self._action_result.get_status()

                detection_url = f"{consts.VECTRA_API_2_2_VERSION}{consts.VECTRA_SEARCH_DETECTIONS_ENDPOINT}"
                ret_val, detections = self._connector.util._paginator(self._action_result, detection_url, params={"query_string": query_string})
                if phantom.is_fail(ret_val):
                    return self._action_result.get_status()

                entity["detections"] = detections
                self._connector.debug_print("Got total {} detections".format(len(entity.get("detections", []))))

            for entity in entities:
                # by default severity will be None from API
                severity = entity.get("severity") or "low"

                container_name = entity.get("name")
                sdi = self._get_identifier(entity, entity_type)

                self._connector.debug_print("creating artifacts")
                artifacts = self._create_artifacts(entity, severity, entity_type)

                self._connector.debug_print("ingesting artifacts")
                ret_val = self._ingest_artifacts(artifacts, container_name, severity, sdi)
                if phantom.is_fail(ret_val):
                    return self._action_result.get_status()

            total_ingested += max_allowed_container - self._connector._dup_entities

            self._connector.debug_print(
                f"Value of max_allowed_container is {max_allowed_container!s}, duplicates is \
                    {self._connector._dup_entities}, run_limit is {container_limit}"
            )
            self._connector.save_progress(f"Got total {len(entities)} entities")

            if entities and not self._connector.is_poll_now():
                # save the last modified timestamp into the state file
                self._connector.state[consts.VECTRA_LAST_DETECTION_TIMESTAMP_IN_STATE] = entities[-1][
                    consts.VECTRA_LAST_DETECTION_TIMESTAMP_IN_STATE
                ]

            if total_ingested >= container_limit:
                break

            next_cycle_repeat_entity = 0
            last_entity_time = entities[-1][consts.VECTRA_LAST_DETECTION_TIMESTAMP_IN_STATE]
            for entity in reversed(entities):
                if entity[consts.VECTRA_LAST_DETECTION_TIMESTAMP_IN_STATE] == last_entity_time:
                    next_cycle_repeat_entity += 1
                else:
                    break

            remaining_entities = container_limit - total_ingested
            max_allowed_container = next_cycle_repeat_entity + remaining_entities

        return self._action_result.set_status(phantom.APP_SUCCESS)
