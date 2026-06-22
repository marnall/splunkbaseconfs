# Copyright (c) 2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
from datetime import datetime, timedelta, timezone

import dateutil.parser
import phantom.app as phantom
from incydr.enums.file_events import EventAction
from incydr.enums.sessions import SortKeys

from code42v3_consts import DEFAULT_ARTIFACT_COUNT, DEFAULT_CONTAINER_COUNT


class Code42v3OnPoll:
    def __init__(self, connector, client, state):
        self._connector = connector
        self._client = client
        self._state = state or {}

    def _get_date_parameters(self):
        # returns start date and end date for the poll.
        config = self._connector.get_config()
        now_utc = datetime.now(timezone.utc)
        last_time = self._get_saved_last_time()

        if last_time is None:  # first run. No last time found.
            self._connector.debug_print(f"no last time found, getting initial poll start date: {config.get('initial_poll_start_date')}")
            start_dt, start_err = self._coerce_to_datetime(config.get("initial_poll_start_date"))
            end_dt, end_err = self._coerce_to_datetime(config.get("initial_poll_end_date"))
            error = None
            if start_err or end_err:
                msgs = []
                if start_err:
                    msgs.append(f"start: {start_err}")
                if end_err:
                    msgs.append(f"end: {end_err}")
                error = ValueError("; ".join(msgs))
            return start_dt, end_dt, error
        else:  # subsequent runs. Last time found.
            self._connector.debug_print(f"last time found, setting start date to last time: {last_time}")
            start_dt, start_err = self._coerce_to_datetime(last_time)
            end_dt = now_utc
            return start_dt, end_dt, start_err

    def _save_last_time(self, session_time):
        # saves the last time of the session to the state.
        dt, err = self._coerce_to_datetime(session_time)
        if err or not dt:
            return
        self._state["last_time"] = dt.timestamp()
        self._connector.save_state(self._state)

    def _get_saved_last_time(self):
        return self._state.get("last_time", None)

    @staticmethod
    def parse_datetime(date_str):
        date_time_obj = dateutil.parser.parse(date_str)
        if date_time_obj.utcoffset():
            date_time_obj = date_time_obj.replace(tzinfo=timezone.utc) - date_time_obj.utcoffset()
        else:
            date_time_obj = date_time_obj.replace(tzinfo=timezone.utc)
        return date_time_obj

    def _coerce_to_datetime(self, value):
        if value is None:
            return None, None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc), None
            return value.astimezone(timezone.utc), None
        if isinstance(value, (int, float)):
            timestamp = value / 1000 if value > 1_000_000_000_000 else value
            return datetime.fromtimestamp(timestamp, tz=timezone.utc), None
        if isinstance(value, str):
            try:
                return self.parse_datetime(value), None
            except Exception as exc:
                return None, ValueError(f"Unable to parse datetime value '{value}': {exc}")
        return None, ValueError(f"Invalid datetime value: {value}")

    @staticmethod
    def _format_datetime(dt):
        if not dt:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")

    def handle_on_poll(self, param, action_result):
        # handles the on poll action. Gets sessions in a given time range and creates/updates containers and artifacts.

        self._connector.debug_print(f"param from on_poll input: {param}")
        session_id = param.get("source_id")
        self._connector.debug_print(f"session_id from on_poll input: {session_id}")
        config = self._connector.get_config()
        overlap_hours = config.get("overlap_hours", 10)
        severity_filter = config.get("severity_filter", "low,medium,high,critical")
        severity_filter_list = [severity.strip().lower() for severity in severity_filter.split(",")]
        risk_score_filter_list = [self._get_risk_score_from_sevirity(severity) for severity in severity_filter_list]
        if -1 in risk_score_filter_list:
            return action_result.set_status(phantom.APP_ERROR, "Invalid severity filter. Expected values are: low, medium, high, critical")
        container_count = param.get("container_count", DEFAULT_CONTAINER_COUNT)
        artifact_count = param.get("artifact_count", DEFAULT_ARTIFACT_COUNT)

        phantom_status = action_result.set_status(phantom.APP_SUCCESS)
        if session_id:
            self._connector.debug_print(f"In handle_on_poll with session_id: {session_id}")
            session_details = self._client.sessions.v1.get_session_details(session_id)
            container_id = self._create_or_update_container(session_details)
            if container_id is None:
                phantom_status = action_result.set_status(phantom.APP_ERROR, "Error creating or updating container(s)")
                return phantom_status
            self._add_new_artifacts_to_container(container_id, session_details.session_id, artifact_count)
        else:
            start_dt, end_dt, dt_error = self._get_date_parameters()
            if dt_error:
                return action_result.set_status(phantom.APP_ERROR, f"Invalid date parameter: {dt_error}")
            # Apply defaults if values are missing (caller decision)
            if start_dt is None:
                start_dt = datetime.now(timezone.utc) - timedelta(days=30)
            if end_dt is None:
                end_dt = datetime.now(timezone.utc)
            # starts from (start_dt - overlap_hours) since a session can be updated after it's ingestion.
            start_dt_overlap = start_dt - timedelta(hours=overlap_hours)
            self._connector.debug_print(f"start_dt_overlap: {start_dt_overlap}, end_dt: {end_dt}")

            sessions = []
            try:
                sessions_iter = self._client.sessions.v1.iter_all(
                    start_time=start_dt_overlap,
                    end_time=end_dt,
                    sort_key=SortKeys.END_TIME,
                    severities=risk_score_filter_list,
                )
            except Exception as e:
                self._connector.debug_print(f"error iterating sessions: {e}")
                return action_result.set_status(phantom.APP_ERROR, f"Error iterating sessions: {e}")

            # get all sessions and reverse the list to get the oldest sessions first.
            # sort_direction=SortDirection.ASC in iter_all is rejecting the request. So we are reversing the list.
            for session in sessions_iter:
                sessions.append(session)
            sessions.reverse()

            added_container_count = 0
            for session in sessions:
                last_updated_dt, last_updated_err = self._coerce_to_datetime(session.last_updated)
                if last_updated_err:
                    self._connector.debug_print(f"error coercing session.last_updated: {last_updated_err}, skipping session")
                # check if container already exists for the session.
                container_id = self._connector._get_existing_container_id_for_sdi(session.session_id)
                if container_id is not None:
                    self._connector.debug_print(f"container id: {container_id} found for session {session.session_id}")
                    # if true, and if container update time is after last updated time, update the container again with new session details.
                    container_metadata = self._connector._get_container(container_id)
                    container_update_dt, container_update_err = self._coerce_to_datetime(container_metadata.get("container_update_time", None))
                    if container_update_err:
                        container_update_dt = None
                    if container_update_dt and last_updated_dt > container_update_dt:
                        self._connector.debug_print(
                            f"container update time {container_update_dt} is before last updated time {last_updated_dt}, updating container {container_id}"
                        )
                        container_id = self._create_or_update_container(session)
                        if container_id is None:
                            phantom_status = action_result.set_status(phantom.APP_ERROR, "error creating or updating container(s)")
                            continue
                        self._add_new_artifacts_to_container(container_id, session.session_id, artifact_count)
                    else:
                        self._connector.debug_print(
                            f"container update time {container_update_dt} is after last updated time {last_updated_dt}, skipping container {container_id}"
                        )
                        continue
                else:
                    # if container does not exist, create a new container with session details.
                    self._connector.debug_print(f"container does not exist for session {session.session_id}, creating new container")
                    container_id = self._create_or_update_container(session)
                    if container_id is None:
                        phantom_status = action_result.set_status(phantom.APP_ERROR, "error creating or updating container(s)")
                        continue
                    added_container_count += 1
                    self._add_new_artifacts_to_container(container_id, session.session_id, artifact_count)
                    self._save_last_time(session.begin_time)

                    if added_container_count >= container_count:
                        self._connector.debug_print(
                            f"container count {added_container_count} is greater than or equal to container count {container_count}, breaking out of loop"
                        )
                        break

            return phantom_status
        return phantom_status

    def _get_session_events(self, session_id):
        """
        Gets the events for a given session.
        Args:
            session_id (str): The ID of the session to get the events for.
        Returns:
            list: The events for the session.
        """
        events = []
        page = self._client.sessions.v1.get_session_events(session_id)
        events.extend(page.file_events)
        next_pg_token = page.next_pg_token
        while next_pg_token:
            page = self._client.sessions.v1.get_session_events(session_id, pg_token=next_pg_token)
            events.extend(page.file_events)
            next_pg_token = page.next_pg_token
        return events

    def _get_container_label(self):
        return self._connector.get_config().get("ingest", {}).get("container_label")

    def _save_artifacts_from_file_event(self, container_id, file_events, artifact_count):
        """
        Saves the artifacts if an artifact does not already exist for the event.
        Args:
            container_id (str): The ID of the container to save the artifacts for.
            file_events (list): The events to save the artifacts for.
            artifact_count (int): The number of artifacts to save.
        Returns:
            list: The artifacts for the container.
        """
        artifacts = []
        total_artifacts_count = 0
        for event in file_events:
            if self._connector.artifact_exists(container_id, event.event.id):
                self._connector.debug_print(f"artifact already exists for event {event.event.id}")
                continue
            self._connector.debug_print(f"creating artifact for event {event.event.id}")
            artifact = self._create_artifact_payload(container_id, event)
            artifacts.append(artifact)
            total_artifacts_count += 1
            if total_artifacts_count >= artifact_count:
                break
        if len(artifacts) == 0:
            self._connector.debug_print("no artifacts to save")
            return
        self._connector.save_artifacts(artifacts)

    def _create_or_update_container(self, session_details):
        container_id = self._connector._get_existing_container_id_for_sdi(session_details.session_id)
        if container_id:
            severity_score = self._normalize_severity(self._get_session_severity_from_scores(session_details.scores))
            self._connector._update_container(container_id, session_details.dict(), severity_score)
            return container_id
        else:
            container_json = self._create_container_payload(session_details)
            saved_successfully, error, container_id = self._connector.save_container(container_json)
            if not saved_successfully:
                self._connector.debug_print(f"error creating container: {error}")
                return None
            self._connector.debug_print(f"container created with id: {container_id}")
            return container_id

    def _add_new_artifacts_to_container(self, container_id, session_id, artifact_count):
        file_events = self._get_session_events(session_id)
        self._save_artifacts_from_file_event(container_id, file_events, artifact_count)
        return container_id

    @staticmethod
    def _get_risk_score_from_sevirity(severity):
        risk_score_order = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
            "info": 0,
        }
        return risk_score_order.get(severity, -1)

    @staticmethod
    def _get_session_severity_from_scores(scores):
        severity_order = {
            4: "critical",
            3: "high",
            2: "medium",
            1: "low",
            0: "info",  # no risk indicated.
        }
        highest_severity = 0
        for score in scores:
            if score.severity > highest_severity:
                highest_severity = score.severity
        return severity_order[highest_severity]

    @staticmethod
    def _normalize_severity(severity):
        # maps session severity to sevirity of the container.
        session_container_sevirity_mapping = {
            "critical": "high",
            "high": "high",
            "medium": "medium",
            "low": "low",
            "info": "low",
        }
        return session_container_sevirity_mapping.get(severity.lower())

    def _create_container_payload(self, session_details):
        return {
            "name": session_details.activitySummary,
            "type": session_details.type,
            "data": json.loads(session_details.json()),
            "severity": self._normalize_severity(self._get_session_severity_from_scores(session_details.scores)),
            "description": session_details.context_summary,
            "source_data_identifier": session_details.session_id,
            "label": self._get_container_label(),
        }

    def _create_artifact_payload(self, container_id, file_event):
        cef = _map_event_to_cef(file_event)
        artifact_dict = {
            "name": "Code42 File Event Artifact",
            "container_id": container_id,
            "severity": self._normalize_severity(file_event.risk.severity) if file_event.risk.severity else "low",
            "label": file_event.event.detector_display_name,
            "cef": cef,
            "data": json.loads(file_event.json()),
            "start_time": file_event.event.ingested.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "source_data_identifier": file_event.event.id,
        }
        return artifact_dict


CEF_CUSTOM_FIELD_NAME_MAP = {
    "cn1Label": "Code42AEDRemovableMediaCapacity",
    "cs1Label": "Code42AEDRemovableMediaBusType",
    "cs2Label": "Code42AEDRemovableMediaVendor",
    "cs3Label": "Code42AEDRemovableMediaName",
    "cs4Label": "Code42AEDRemovableMediaSerialNumber",
}


def build_signature_id_map(prefix="C42", start=200):
    """
    Returns: dict like {"file-created": "C42200", ...}
    Enum order is stable; IDs are reproducible across runs.

    eg: {'removable-media-created': 'C42200', 'removable-media-modified': 'C42201', 'removable-media-deleted': 'C42202', 'sync-app-created': 'C42203',  ...}
    """
    return {action.value: f"{prefix}{start + i:03d}" for i, action in enumerate(EventAction)}


def _map_event_to_cef(file_event):
    cef_dict = {}
    init_cef_dict = _init_cef_dict(file_event)
    for key, value in init_cef_dict.items():
        custom_key_with_label = key + "Label"
        if custom_key_with_label in CEF_CUSTOM_FIELD_NAME_MAP:
            cef_dict[custom_key_with_label] = CEF_CUSTOM_FIELD_NAME_MAP[custom_key_with_label]
    sub_cef_dict_list = [_format_cef_kvp(key, value) for key, value in init_cef_dict.items()]
    for sub_dict in sub_cef_dict_list:
        cef_dict.update(sub_dict)

    event_action = getattr(getattr(file_event, "event", None), "action", None) or "UNKNOWN"
    FILE_EVENT_TO_SIGNATURE_ID_MAP = build_signature_id_map()
    cef_dict["signatureId"] = FILE_EVENT_TO_SIGNATURE_ID_MAP.get(event_action, "C42000")
    cef_dict["eventName"] = event_action
    return cef_dict


def _format_cef_kvp(cef_field_key, cef_field_value):
    if cef_field_key + "Label" in CEF_CUSTOM_FIELD_NAME_MAP:
        return _format_custom_cef_kvp(cef_field_key, cef_field_value)

    cef_field_value = _handle_nested_json_fields(cef_field_key, cef_field_value)
    if isinstance(cef_field_value, list):
        cef_field_value = _convert_list_to_csv(cef_field_value)

    return {cef_field_key: cef_field_value}


def _format_custom_cef_kvp(custom_cef_field_key, custom_cef_field_value):
    custom_cef_label_key = f"{custom_cef_field_key}Label"
    custom_cef_label_value = CEF_CUSTOM_FIELD_NAME_MAP[custom_cef_label_key]
    return {
        custom_cef_field_key: custom_cef_field_value,
        custom_cef_label_key: custom_cef_label_value,
    }


def _handle_nested_json_fields(cef_field_key, cef_field_value):
    result = []
    if cef_field_key == "duser":
        result = [item["cloudUsername"] for item in cef_field_value if type(item) is dict]

    return result or cef_field_value


def _convert_list_to_csv(_list):
    value = ",".join([val for val in _list if val])
    return value


def _init_cef_dict(file_event):
    cef_dict = {}
    event = getattr(file_event, "event", None)
    file_metadata = getattr(file_event, "file", None)
    source = getattr(file_event, "source", None)
    destination = getattr(file_event, "destination", None)
    process = getattr(file_event, "process", None)
    risk = getattr(file_event, "risk", None)
    user = getattr(file_event, "user", None)

    def _set_if_value(key, value):
        if value is None:
            return
        if isinstance(value, list):
            filtered = [item for item in value if item]
            if not filtered:
                return
            cef_dict[key] = filtered
            return
        cef_dict[key] = value

    def _to_cef_timestamp(value):
        if not value:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            else:
                value = value.astimezone(timezone.utc)
            return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        return value

    def _first_tab_attr(location, attr):
        tabs = getattr(location, "tabs", None)
        if not tabs:
            return None
        for tab in tabs:
            tab_value = getattr(tab, attr, None)
            if tab_value:
                return tab_value
        return None

    def _unique(values):
        seen = set()
        result = []
        for val in values:
            if not val or val in seen:
                continue
            seen.add(val)
            result.append(val)
        return result

    if event:
        _set_if_value("externalId", getattr(event, "id", None))
        inserted = getattr(event, "inserted", None)
        ingested = getattr(event, "ingested", None)
        _set_if_value("rt", _to_cef_timestamp(inserted or ingested))
        _set_if_value("eventName", getattr(event, "action", None))
        _set_if_value("shareType", getattr(event, "shareType", None))
        _set_if_value("vector", getattr(event, "vector", None))
        if not getattr(file_event, "timestamp", None):
            _set_if_value("end", _to_cef_timestamp(ingested))

    event_timestamp = getattr(file_event, "timestamp", None)
    _set_if_value("end", _to_cef_timestamp(event_timestamp))

    if user:
        _set_if_value("deviceExternalId", getattr(user, "device_uid", None))
        _set_if_value("suid", getattr(user, "id", None))

    if file_metadata:
        _set_if_value("fileType", getattr(file_metadata, "category", None))
        _set_if_value("aid", getattr(file_metadata, "cloud_drive_id", None))
        _set_if_value("fname", getattr(file_metadata, "name", None))
        _set_if_value("fsize", getattr(file_metadata, "size_in_bytes", None))
        _set_if_value("fileCreateTime", _to_cef_timestamp(getattr(file_metadata, "created", None)))
        _set_if_value("fileModificationTime", _to_cef_timestamp(getattr(file_metadata, "modified", None)))
        if file_hash := getattr(file_metadata, "hash", None):
            _set_if_value("fileHashMd5", getattr(file_hash, "md5", None))
            _set_if_value("fileHashSha256", getattr(file_hash, "sha256", None))
        directory = getattr(file_metadata, "directory", None)
        name = getattr(file_metadata, "name", None)
        file_url = getattr(file_metadata, "url", None)
        file_path = None
        if directory and name:
            file_path = f"{directory}{name}"
        elif directory:
            file_path = directory
        elif file_url:
            file_path = file_url
        _set_if_value("filePath", file_path)

    suser_candidates = []
    if source and getattr(source, "email", None):
        suser_candidates.extend([getattr(source.email, "sender", None), getattr(source.email, "from_", None)])
    if user:
        suser_candidates.append(getattr(user, "email", None))
    if suser_candidates:
        _set_if_value("suser", next((candidate for candidate in suser_candidates if candidate), None))

    if source:
        _set_if_value("dvchost", getattr(source, "domain", None))
        _set_if_value("shost", getattr(source, "name", None))
        source_ip = getattr(source, "ip", None)
        _set_if_value("src", source_ip or getattr(destination, "ip", None))
        source_service_name = getattr(source, "account_name", None) or getattr(source, "name", None) or getattr(source, "category", None)
        if not source_service_name and event:
            source_service_name = getattr(event, "observer", None)
        _set_if_value("sourceServiceName", source_service_name)

    if destination:
        destination_service_name = (
            getattr(destination, "account_name", None) or getattr(destination, "name", None) or getattr(destination, "category", None)
        )
        _set_if_value("destinationServiceName", destination_service_name)

    recipient_values = []
    if destination:
        if getattr(destination, "email", None):
            recipient_values.extend(getattr(destination.email, "recipients", []) or [])
        dest_user = getattr(destination, "user", None)
        if dest_user:
            recipient_values.extend(getattr(dest_user, "email", []) or [])
    if source and getattr(source, "user", None):
        recipient_values.extend(getattr(source.user, "email", []) or [])
    _set_if_value("duser", _unique(recipient_values))

    tab_url = _first_tab_attr(source, "url") or _first_tab_attr(destination, "url")
    tab_title = _first_tab_attr(source, "title") or _first_tab_attr(destination, "title")
    _set_if_value("request", tab_url)
    _set_if_value("requestClientApplication", tab_title)

    if process:
        _set_if_value("sproc", getattr(process, "executable", None))
        _set_if_value("spriv", getattr(process, "owner", None))

    removable_media = None
    if source and getattr(source, "removable_media", None):
        removable_media = source.removable_media
    elif destination and getattr(destination, "removable_media", None):
        removable_media = destination.removable_media
    if removable_media:
        _set_if_value("cn1", getattr(removable_media, "capacity", None))
        _set_if_value("cs1", getattr(removable_media, "bus_type", None))
        media_name = getattr(removable_media, "media_name", None) or getattr(removable_media, "name", None)
        _set_if_value("cs2", getattr(removable_media, "vendor", None))
        _set_if_value("cs3", media_name)
        _set_if_value("cs4", getattr(removable_media, "serial_number", None))

    if risk:
        message_bits = []
        severity = getattr(risk, "severity", None)
        if severity:
            message_bits.append(f"severity={severity}")
        score = getattr(risk, "score", None)
        if score is not None:
            message_bits.append(f"score={score}")
        indicators = getattr(risk, "indicators", None) or []
        message_bits.extend(indicator.name for indicator in indicators if getattr(indicator, "name", None))
        trust_reason = getattr(risk, "trust_reason", None)
        if trust_reason:
            message_bits.append(f"trustReason={trust_reason}")
        message_value = ", ".join(message_bits)
        _set_if_value("message", message_value or None)

    return cef_dict
