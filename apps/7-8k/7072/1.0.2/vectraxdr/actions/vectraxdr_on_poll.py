"""Class for on poll action."""
# File: vectraxdr_on_poll.py
#
# Copyright (c) 2023-2025 Vectra
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

from datetime import datetime, timedelta

import phantom.app as phantom
import requests

import vectraxdr_consts as consts
from actions import BaseAction


class OnPollAction(BaseAction):
    """Class to handle on poll action."""

    def _validate_severity(self, action_result, configs):
        """Validate severity.

        :param action_result: object of ActionResult class
        :param artifacts: Dictionary of configuration

        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR), low(severity value), medium(severity value)
        """
        low = configs.get("urgency_score_low_threshold", consts.VECTRA_DEFAULT_URGENCY_SCORE_LOW_THRESHOLD)
        ret_val, _ = self._connector.util._validate_integer(action_result, low, "low threshold value", False)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status(), None, None

        medium = configs.get("urgency_score_medium_threshold", consts.VECTRA_DEFAULT_URGENCY_SCORE_MEDIUM_THRESHOLD)
        ret_val, _ = self._connector.util._validate_integer(action_result, medium, "Medium threshold value", False)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status(), None, None

        if low >= medium:
            return action_result.set_status(phantom.APP_ERROR, consts.VECTRA_INVALID_SEVERITY), None, None
        return action_result.set_status(phantom.APP_SUCCESS), low, medium

    def _get_severity(self, low, medium, score):
        """Return severity level using entity score.

        :param low: severity value for lower range
        :param medium: severity value for medium range
        :param medium: entity score

        :return: severity value
        """
        if score <= low:
            severity = "low"
        elif score <= medium:
            severity = "medium"
        else:
            severity = "high"

        return severity

    def _map_to_soar_keys(self, label, name, cef_types, sdi, cef, severity):
        """Map entity fields with SOAR keys.

        :param label: label of artifact
        :param name: name of artifact
        :param cef_types: cef_types of artifact
        :param sdi: source data identifier of artifact
        :param data: data of artifact
        :param cef: cef of artifact
        :param severity: severity of artifact

        :return: Mapped artifact
        """
        artifact = {"label": label, "name": name, "cef_types": cef_types, "source_data_identifier": sdi, "cef": cef, "severity": severity}

        return artifact

    def _get_identifier(self, object, has_type=True):
        """Map entity fields with SOAR keys.

        :param label: object(entity/detection/assignment)
        :param has_type: if the object has type field

        :return: identifier
        """
        identifier = str(object.get("id", "N/A"))
        if has_type:
            identifier = f"{object.get('type', 'N/A')}-{identifier}"
        return identifier

    def _create_entity_artifacts(self, entity, severity):
        """Create artifacts of entity, detection, and assignment.

        :param entity: Entity object
        :param severity: Severity value(low, medium, high)

        :return: List of artifact
        """
        artifacts = list()
        detections = entity.pop("detections", [])
        assignments = entity.pop("assignments", [])
        if detections:
            label = "Detection"
            for detection in detections:
                identifier = self._get_identifier(detection)
                cef_types = consts.VECTRA_CEF_TYPES["detection"]
                artifacts.append(self._map_to_soar_keys(label, "Detection Artifact", cef_types, identifier, detection, severity))

        for assignment in assignments:
            identifier = self._get_identifier(assignment, False)
            cef_types = consts.VECTRA_CEF_TYPES["assignment"]
            artifacts.append(self._map_to_soar_keys("Assignment", "Assignment Artifact", cef_types, identifier, assignment, severity))

        identifier = self._get_identifier(entity)
        artifacts.append(self._map_to_soar_keys("Entity", "Entity Artifact", consts.VECTRA_CEF_TYPES["entity"], identifier, entity, severity))
        return artifacts

    def _ingest_artifacts(self, artifacts, container_name, severity, sdi):
        """Ingest artifacts into the Phantom server.

        :param artifacts: list of artifacts
        :param container_name: name of the container in which data will be ingested
        :param severity: severity of the container
        :param sdi: source data identifier of container

        :return: ret_val
        """
        self._connector.debug_print(f"Ingesting {len(artifacts)} artifacts for {container_name} container with {severity} severity")

        container = {"name": container_name, "description": "Entity ingested from Vectra", "source_data_identifier": sdi, "severity": severity}
        ret_val, message, cid = self._connector.save_container(container)

        if message == "Duplicate container found" and not self._connector.is_poll_now():
            self._connector._dup_entities += 1

        self._connector.debug_print(f"save_container returns, ret_val: {ret_val}, reason: {message}, id: {cid}")
        if phantom.is_fail(ret_val):
            return self._connector.action_result.set_status(phantom.APP_ERROR, message)

        for artifact in artifacts:
            artifact["container_id"] = cid

        ret_val, message, ids = self._connector.save_artifacts(artifacts)
        self._connector.debug_print(f"save_artifacts returns, value: {ret_val}, reason: {message}, ids: {ids}")
        if phantom.is_fail(ret_val):
            return self._action_result.set_status(phantom.APP_ERROR, message)
        return self._action_result.set_status(phantom.APP_SUCCESS)

    def _get_on_poll_start_time(self, configs):
        """Return start time for on poll.

        :param configs: Dictionary of configuration parameter

        :return: ret_val(phantom.APP_SUCCESS/phantom.APP_ERROR), start_time
        """
        ret_val = True

        start_time_from_state = self._connector.state.get(consts.VECTRA_LAST_MODIFIED_TIMESTAMP_IN_STATE)
        if not self._connector.is_poll_now() and start_time_from_state:
            ret_val = self._connector.util._check_date_format(self._action_result, start_time_from_state)
            return ret_val, start_time_from_state

        start_time_from_config = configs.get("on_poll_start_time")
        if start_time_from_config:
            ret_val = self._connector.util._check_date_format(self._action_result, start_time_from_config)
            return ret_val, start_time_from_config

        time_before_3_days_from_now = (datetime.now() - timedelta(days=3)).isoformat(timespec="seconds")
        return ret_val, time_before_3_days_from_now

    def _get_filters_for_entity(self, configs, on_poll_start_time):
        """Return filter for entity.

        :param configs: Dictionary of configuration parameter
        :param on_poll_start_time: Start time for on poll

        :return: params
        """
        params = {"last_modified_timestamp_gte": on_poll_start_time, "ordering": "last_modified_timestamp"}

        is_entity_prioritized = configs.get("is_entity_prioritized", "True").lower()
        if is_entity_prioritized in consts.VECTRA_VALID_PRIORITIZED_LIST:
            if is_entity_prioritized != "all":
                params["is_prioritized"] = is_entity_prioritized.lower() == "true"
        else:
            return self._action_result.set_status(phantom.APP_ERROR, "Please provide valid value for prioritize parameter"), None

        entity_type = configs.get("entity_type", "All").lower()
        if entity_type in consts.VECTRA_VALID_ENTITY_TYPES:
            if entity_type != "all":
                params["entity_type"] = entity_type
        else:
            return self._action_result.set_status(phantom.APP_ERROR, "Please provide valid value for entity type parameter"), None

        tags = configs.get("entity_tags")
        if tags:
            tags = self._connector.util._sanitize_comma_separated_values(tags)
            if tags:
                params["tags"] = tags

        return phantom.APP_SUCCESS, params

    def _get_detection_filters(self, configs):
        """Return filter for detection.

        :param configs: Dictionary of configuration parameter

        :return: ret_val(phantom.APP_SUCCESS/phantom.APP_ERROR), filters (Dict)
        """
        filters = {"state": "active"}

        detection_category = configs.get("detection_category")

        if detection_category:
            if detection_category in consts.VECTRA_DETECTION_CATEGORIES_MAPPING:
                if detection_category != "All":
                    filters["detection_category"] = consts.VECTRA_DETECTION_CATEGORIES_MAPPING[detection_category]
            else:
                return self._action_result.set_status(phantom.APP_ERROR, "Please provide valid value for detection category"), None

        detection_type = configs.get("detection_type")
        if detection_type:
            filters["detection_type"] = detection_type

        return True, filters if filters != dict() else None

    def object_dedup(self, entity, detection_ids, assignment_ids, entity_id):
        """Run deduplication on detections.

        :param entity: Entity
        :param detection_ids:List of detection is

        :return: ret_val(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        label = self._connector.config.get("ingest", {}).get("container_label")
        sdi = self._get_identifier(entity)
        base_url = self._connector._get_phantom_base_url()
        self._connector.debug_print(f"Got SDI and label respectively are {sdi}, {label}")
        url = f"{base_url}{consts.VECTRA_CONTAINER_ENDPOINT}"

        params = {"_filter_source_data_identifier": f"'{sdi}'", "_filter_label": f"'{label}'"}

        r = requests.get(url, params=params, verify=False)  # nosemgrep
        data = r.json().get("data", [])

        # Given entity dose not exist at this moment
        if not data:
            return

        cid = data[0].get("id")
        url = f"{base_url}{consts.VECTRA_ARTIFACT_ENDPOINT}"
        params = {"_filter_container_id": cid}
        r = requests.get(url, params=params, verify=False)  # nosemgrep

        for artifact in r.json().get("data", []):
            id_from_container = artifact.get("cef", {}).get("id")
            label = artifact.get("label")
            id_from_container = str(id_from_container)

            delete_detection = label == "detection" and id_from_container in detection_ids
            delete_assignment = label == "assignment" and id_from_container in assignment_ids
            delete_entity = label == "entity" and id_from_container == entity_id

            if delete_detection or delete_assignment or delete_entity:
                url = f"{base_url}{consts.VECTRA_ARTIFACT_ENDPOINT}/{artifact.get('id')}"
                r = requests.delete(url, verify=False)  # nosemgrep

                self._connector.debug_print(f"Message from server {r.text}")
                if r.status_code != 200:
                    self._connector.save_progress("Couldn't delete the artifact, kindly check user role. For more info refer readme.")
                    return

    def execute(self):
        """Execute the on poll action."""
        self._connector.save_progress("Executing Polling")
        configs = self._connector.config

        ret_val, low, medium = self._validate_severity(self._action_result, configs)
        if phantom.is_fail(ret_val):
            self._connector.save_progress(self._action_result.get_message())
            return self._action_result.set_status(phantom.APP_ERROR)

        if self._connector.is_poll_now():
            max_allowed_container = configs.get("manual_max_allowed_container", consts.VECTRA_DEFAULT_MAX_ALLOWED_CONTAINERS)
        else:
            max_allowed_container = configs.get("schedule_max_allowed_container", consts.VECTRA_DEFAULT_MAX_ALLOWED_CONTAINERS)

        ret_val, _ = self._connector.util._validate_integer(self._action_result, max_allowed_container, "Max container allowed", False)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        run_limit = max_allowed_container
        total_ingested = 0

        while True:
            self._connector._dup_entities = 0

            ret_val, on_poll_start_time = self._get_on_poll_start_time(configs)
            if phantom.is_fail(ret_val):
                self._connector.save_progress(self._action_result.get_message())
                return self._action_result.set_status(phantom.APP_ERROR)

            self._connector.save_progress(f"On poll start time is {on_poll_start_time}")

            # Get entities
            ret_val, params = self._get_filters_for_entity(configs, on_poll_start_time)
            if phantom.is_fail(ret_val):
                self._connector.save_progress(self._action_result.get_message())
                return self._action_result.set_status(phantom.APP_ERROR)

            self._connector.send_progress("Getting Entities....")
            url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_LIST_ENTITIES}"
            ret_val, entities = self._connector.util._paginator(self._action_result, url, params=params, limit=max_allowed_container)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            for entity in entities:
                # Get detections
                self._connector.send_progress("Getting Detections....")
                ret_val, detection_ids = self._connector.util._get_detection_ids_from_entity(self._action_result, entity, str)
                if phantom.is_fail(ret_val):
                    return self._action_result.get_status()

                if detection_ids:
                    detection_ids = ",".join(detection_ids)
                    ret_val, filters = self._get_detection_filters(configs)
                    if phantom.is_fail(ret_val):
                        return self._action_result.get_status()

                    ret_val, response = self._connector.util._get_detections(self._action_result, detection_ids, filters)
                    if phantom.is_fail(ret_val):
                        return self._action_result.get_status()
                    entity["detections"] = response
                    self._connector.debug_print("Got total {} detections".format(len(entity.get("detections", []))))

                # Get assignments
                self._connector.send_progress("Getting Assignments....")
                ret_val, response = self._connector.util._get_assignments(self._action_result, entity)
                if phantom.is_fail(ret_val):
                    return self._action_result.get_status()

                entity["assignments"] = response
                self._connector.debug_print("Got total {} assignments".format(len(entity.get("assignments", []))))

                assignment_ids = []
                for assignment in entity.get("assignments", []):
                    aid = assignment.get("id")
                    if aid:
                        assignment_ids.append(str(aid))

                entity_id = str(entity.get("id"))
                # Keep only latest data of given id at a time
                self.object_dedup(entity, detection_ids, assignment_ids, entity_id)

            for entity in entities:
                urgency_score = entity.get("urgency_score", consts.VECTRA_DEFAULT_URGENCY_SCORE)
                severity = self._get_severity(low, medium, urgency_score)

                self._connector.debug_print("Try to create artifacts")
                # Create artifacts
                artifacts = self._create_entity_artifacts(entity, severity)

                # Save artifacts
                self._connector.debug_print("Try to ingest artifacts")
                container_name = entity.get("name")
                sdi = self._get_identifier(entity)
                ret_val = self._ingest_artifacts(artifacts, container_name, severity, sdi)
                if phantom.is_fail(ret_val):
                    return self._action_result.get_status()

            self._connector.debug_print(f"value of total_ingested is {total_ingested!s}")
            total_ingested += max_allowed_container - self._connector._dup_entities
            self._connector.debug_print(
                f"Value of max_allowed_container is {max_allowed_container!s}, "
                f"duplicates is {self._connector._dup_entities}, run_limit is {run_limit}"
            )
            self._connector.save_progress(f"Got total {len(entities)} entities")

            if entities and not self._connector.is_poll_now():
                self._connector.state[consts.VECTRA_LAST_MODIFIED_TIMESTAMP_IN_STATE] = entities[-1][
                    consts.VECTRA_LAST_MODIFIED_TIMESTAMP_IN_STATE
                ]

            if total_ingested >= run_limit:
                break

            next_cycle_repeat_entity = 0
            last_entity_time = entities[-1][consts.VECTRA_LAST_MODIFIED_TIMESTAMP_IN_STATE]
            for entity in reversed(entities):
                if entity[consts.VECTRA_LAST_MODIFIED_TIMESTAMP_IN_STATE] == last_entity_time:
                    next_cycle_repeat_entity += 1
                else:
                    break

            remaining_entities = run_limit - total_ingested
            max_allowed_container = next_cycle_repeat_entity + remaining_entities

        return self._action_result.set_status(phantom.APP_SUCCESS)
