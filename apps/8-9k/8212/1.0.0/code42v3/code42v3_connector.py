# File: code42v3_connector.py
#
# Copyright (c) 2025 Splunk Inc.
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
import os
from datetime import datetime

# Incydr imports
import incydr

# Phantom App imports
import phantom.app as phantom
import phantom.utils as utils
import requests
from incydr import EventQuery
from incydr.enums.cases import CaseStatus
from incydr.enums.file_events import RiskSeverity
from incydr.enums.sessions import SessionStates
from incydr.enums.watchlists import WatchlistType
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault
from phantom_common.install_info import get_verify_ssl_setting
from requests import HTTPError

from code42v3_consts import (
    CODE42V3_CASE_NUM_KEY,
    CODE42V3_MAX_RESULTS_KEY,
    CODE42V3_NON_NEG_INT_MSG,
    CODE42V3_NON_NEG_NON_ZERO_INT_MSG,
    CODE42V3_VALID_INT_MSG,
    MAX_RESULTS_DEFAULT,
)
from code42v3_on_poll import Code42v3OnPoll


class Code42UnsupportedHashError(Exception):
    def __init__(self):
        super().__init__("Unsupported hash format. Hash must sha256")


class Code42V3Connector(BaseConnector):
    def __init__(self):
        super().__init__()

        self._state = None
        self._base_url = None
        self._client = None
        self._client_id = None
        self._client_secret = None
        self._proxy = {}

    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
        """
        Validates an integer parameter.
        Args:
            action_result (ActionResult): Action result object.
            parameter (int): Parameter to validate.
            key (str): Key of the parameter.
            allow_zero (bool): Whether to allow zero.
        Returns:
            tuple: Tuple containing the status and the validated parameter.
        """
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, CODE42V3_VALID_INT_MSG.format(param=key)), None

                parameter = int(parameter)
            except:
                return action_result.set_status(phantom.APP_ERROR, CODE42V3_VALID_INT_MSG.format(param=key)), None

            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, CODE42V3_NON_NEG_INT_MSG.format(param=key)), None
            if not allow_zero and parameter == 0:
                return action_result.set_status(phantom.APP_ERROR, CODE42V3_NON_NEG_NON_ZERO_INT_MSG.format(param=key)), None

        return phantom.APP_SUCCESS, parameter

    def _is_valid_watchlist_name(self, watchlist_name):
        """
        Validates a watchlist name.
        Args:
            watchlist_name (str): Watchlist name to validate.
        Returns:
            bool: True if the watchlist name is valid, False otherwise.
        """
        valid_watchlist_names = [e.value for e in WatchlistType]
        return watchlist_name in valid_watchlist_names

    def _is_valid_date(self, date):
        """
        Validates a date.
        Args:
            date (str): Date to validate.
        Returns:
            bool: True if the date is valid, False otherwise.
        """
        try:
            datetime.fromisoformat(date.replace("Z", "+00:00"))
        except ValueError as e:
            return False, str(e)
        return True, None

    def _get_existing_container_id_for_sdi(self, sdi):
        """
        Gets the existing container ID for a given source data identifier.
        Args:
            sdi (str): Source data identifier to get the container ID for.
        Returns:
            int: The container ID.
        """
        url = f'{self.get_phantom_base_url()}rest/container?_filter_source_data_identifier="{sdi}"&_filter_asset={self.get_asset_id()}'
        # Make rest call
        try:
            response = requests.get(url, verify=get_verify_ssl_setting(), timeout=30)
        except Exception as e:
            raise RuntimeError("Encountered an error getting the existing container ID from Phantom.") from e

        container_data = response.json()
        if "data" not in container_data or len(container_data["data"]) == 0:
            return None
        return container_data["data"][0]["id"]

    def _update_container(self, container_id, data, severity):
        """
        Updates the metadata for a given container.
        Args:
            container_id (int): Container ID to update.
            data (dict): Data to update the container with.
            severity (str): Severity to update the container with.
        """
        # update old container
        container_metadata = {
            "data": data,
            "severity": severity,
        }
        try:
            requests.post(
                f"{self.get_phantom_base_url()}rest/container/{container_id}",
                data=json.dumps(container_metadata),
                verify=get_verify_ssl_setting(),
                timeout=30,
            )
        except Exception as e:
            raise RuntimeError("Encountered an error updating container metadata.") from e

    def artifact_exists(self, container_id: int, event_id: str):
        """
        Makes a rest call to see if the artifact exists or not.
        Args:
            container_id (int): Container ID to filter.
            alert_id (str): Alert ID.
        Returns:
            ID: Returns an ID or None if no ID exists.
        """

        # check if a given artifact exists for in a container
        url = f'{self.get_phantom_base_url()}rest/artifact?_filter_source_data_identifier="{event_id}"&_filter_container_id={container_id}'
        # Make rest call
        try:
            self.debug_print(f"Making request on url: {url}")
            response = requests.get(url, verify=get_verify_ssl_setting(), timeout=30)
        except Exception:
            return None
        # return id or None
        if response.json().get("data", None):
            return response.json().get("data", None)[0].get("id", None)
        return None

    def _extract_http_errors(self, e):
        error_detail = ""
        if e.response is not None:
            try:
                error_detail = json.dumps(e.response.json())
            except Exception:
                pass
            try:
                if e.response.text:
                    error_detail += f". Response text: {e.response.text}"
            except Exception:
                pass
        if error_detail == "":
            error_detail = str(e)
        return error_detail

    def _get_container(self, container_id):
        """
        Gets the metadata for a given container.
        Args:
            container_id (int): Container ID to get the metadata for.
        Returns:
            dict: The metadata for the container.
        """
        url = f"{self.get_phantom_base_url()}rest/container/{container_id}"
        try:
            response = requests.get(url, verify=get_verify_ssl_setting(), timeout=30)  # nosemgrep
        except Exception:
            return None
        return response.json()

    # test connectivity
    def _handle_test_connectivity(self, param, action_result):
        self.save_progress("Connecting to endpoint")
        _ = self._client.users.v1.get_page()
        return action_result.set_status(phantom.APP_SUCCESS, "")

    # on poll
    def _handle_on_poll(self, param, action_result):
        self.save_progress("Handling on poll")
        connector = Code42v3OnPoll(self, self._client, self._state)
        return connector.handle_on_poll(param, action_result)

    # get session details
    def _handle_get_session_details(self, param, action_result):
        """
        Gets the details for a given session.
        Args:
            session_id (str): The session ID to get the details for.
        Returns:
            ActionResult: The action result object which contains the session details.
        """
        self.save_progress("Getting session details")
        session_id = param.get("session_id")
        try:
            session_details = self._client.sessions.v1.get_session_details(session_id)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to get session details for {session_id}. Error: {e!s}")
        action_result.add_data(session_details.dict())
        action_result.update_summary(
            {
                "actor_id": session_details.actor_id,
                "type": session_details.type,
                "first_observed": session_details.first_observed,
                "last_updated": session_details.last_updated,
            }
        )
        return action_result.set_status(phantom.APP_SUCCESS, "Session details retrieved successfully")

    def _handle_search_sessions(self, param, action_result):
        """
        Searches for sessions in a given time range.
        Args:
            start_date (str): The start date to search for sessions.
            end_date (str): The end date to search for sessions.
            results_count (int): The number of results to return.
            session_state (str): The session state to search for.
            actor_id (str): The actor ID to search for.
        Returns:
            ActionResult: The action result object which contains the session details.
        """
        self.save_progress("Searching sessions")
        results_count = param.get("results_count")

        if start_date := param.get("start_date"):
            is_valid, error = self._is_valid_date(start_date)
            if not is_valid:
                return action_result.set_status(phantom.APP_ERROR, f"Invalid start date. Error: {error}")
        if end_date := param.get("end_date"):
            is_valid, error = self._is_valid_date(end_date)
            if not is_valid:
                return action_result.set_status(phantom.APP_ERROR, f"Invalid end date. Error: {error}")

        input_states = None
        if val := param.get("session_state", ""):
            input_states = val.split(",")
            input_states = [state.strip() for state in input_states]
            valid_states = [e.value for e in SessionStates]
            is_valid = all(state in valid_states for state in input_states)
            if not is_valid:
                return action_result.set_status(
                    phantom.APP_ERROR, "Invalid session state. Expected values are: {}".format(", ".join(valid_states))
                )
        if results_count:
            ret_val, results_count = self._validate_integer(action_result, results_count, "results_count")
            if phantom.is_fail(ret_val):
                return action_result.get_status()
        else:
            results_count = MAX_RESULTS_DEFAULT
        try:
            response_iter = self._client.sessions.v1.iter_all(
                start_time=param.get("start_date", None),
                end_time=param.get("end_date", None),
                actor_id=param.get("actor_id", None),
                states=input_states,
            )
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to search sessions. Error: {e!s}")

        session_ids = []
        session_count = 0
        for session in response_iter:
            action_result.add_data(session.dict())
            session_ids.append(session.session_id)
            session_count += 1
            if session_count >= results_count:
                break

        action_result.update_summary({"session_ids": session_ids})
        return action_result.set_status(phantom.APP_SUCCESS, "Sessions retrieved successfully")

    # run query
    def _handle_run_query(self, param, action_result):
        """
        Runs a query on the the file events.
        Args:
            accepts filters for file metadata, event attributes, risk indicators/severity/trust, and network/process identifiers.
        Returns:
            ActionResult: The action result object which contains the file events.
        """
        self.save_progress(f"In action handler for run query")

        start_date = param.get("start_date")
        end_date = param.get("end_date")
        query = EventQuery(start_date=start_date, end_date=end_date)

        # Convenience enum-backed filters
        if param.get("file_category"):
            query = query.equals("file.category", param.get("file_category"))
        if param.get("event_action"):
            query = query.equals("event.action", param.get("event_action"))
        if param.get("source_category"):
            vals = param.get("source_category")
            vals = vals if isinstance(vals, list) else [vals]
            query = query.is_any("source.category", vals)
        if param.get("destination_category"):
            vals = param.get("destination_category")
            vals = vals if isinstance(vals, list) else [vals]
            query = query.is_any("destination.category", vals)
        if param.get("event_share_type"):
            vals = param.get("event_share_type")
            vals = vals if isinstance(vals, list) else [vals]
            query = query.is_any("event.shareType", vals)
        if param.get("report_type"):
            vals = param.get("report_type")
            vals = vals if isinstance(vals, list) else [vals]
            query = query.is_any("report.type", vals)
        if param.get("risk_indicators"):
            vals = param.get("risk_indicators")
            vals = vals if isinstance(vals, list) else [vals]
            query = query.is_any("risk.indicators.name", vals)
        if param.get("risk_severity"):
            risk_severity = param.get("risk_severity").strip().upper()
            valid_severities = [e.value for e in RiskSeverity]
            if risk_severity not in valid_severities:
                return action_result.set_status(phantom.APP_ERROR, f"Invalid risk severity. Expected values are: {valid_severities}")
            query = query.equals("risk.severity", risk_severity)
        if param.get("risk_trust_reason"):
            vals = param.get("risk_trust_reason")
            vals = vals if isinstance(vals, list) else [vals]
            query = query.is_any("risk.trustReason", vals)

        # Additional convenience filters
        if param.get("file_name"):
            query = query.equals("file.name", param.get("file_name"))
        if param.get("file_path"):
            query = query.equals("file.path", param.get("file_path"))
        if param.get("md5"):
            query = query.equals("file.hash.md5", param.get("md5"))
        if param.get("sha256"):
            query = query.equals("file.hash.sha256", param.get("sha256"))
        if param.get("process_name"):
            query = query.equals("process.name", param.get("process_name"))
        if param.get("url"):
            query = query.equals("tab.url", param.get("url"))
        if param.get("window_title"):
            query = query.equals("window.title", param.get("window_title"))
        if param.get("private_ip"):
            query = query.equals("source.ip", param.get("private_ip"))
        if param.get("public_ip"):
            query = query.equals("destination.ip", param.get("public_ip"))
        if param.get("risk_score_gt") is not None:
            try:
                risk_score_val = float(param.get("risk_score_gt"))
                query = query.greater_than("risk.score", risk_score_val)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Code42: risk_score_gt must be numeric")
        if param.get("untrusted_only"):
            query = query.does_not_exist("risk.trustReason")

        # Pagination with max_results
        max_results = param.get("max_results", MAX_RESULTS_DEFAULT)
        ret_val, max_results = self._validate_integer(action_result, max_results, CODE42V3_MAX_RESULTS_KEY)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if not getattr(query, "groups", None):
            return action_result.set_status(phantom.APP_ERROR, "No filters provided")

        returned = 0
        while returned < max_results:
            response = self._client.file_events.v2.search(query)
            page_events = getattr(response, "file_events", [])
            for event in page_events:
                action_result.add_data(json.loads(event.json()))
                returned += 1
                if returned >= max_results:
                    break
            if response.next_pg_token is None:
                break
            query.page_token = response.next_pg_token

        action_result.update_summary(
            {
                "total_count": returned,
            }
        )
        return action_result.set_status(phantom.APP_SUCCESS)

    def _apply_incydr_filters(self, query, filters_dict):
        """Re-use the standard filter application for subquery blocks."""
        if not filters_dict:
            return query
        return self._apply_query_filters(query, filters_dict)

    def _apply_query_filters(self, query, filters_dict):
        """Apply arbitrary incydr EventQuery operations from a dict schema.

        Schema examples:
        {"equals": [{"term": "file.category", "values": "Document"}]}
        {"is_any": [{"term": "destination.category", "values": ["AI Tools", "Cloud Storage"]}]}
        {"greater_than": [{"term": "risk.score", "value": 10}]}
        {"date_range": [{"term": "event.inserted", "start_date": "P1D"}]}
        {"matches_any": true}
        {"subquery": [{"query": {...}}]
        """
        ops = ("equals", "not_equals", "exists", "does_not_exist", "greater_than", "less_than", "is_any", "is_none", "date_range")

        # matches_any flips group clause to OR
        if filters_dict.get("matches_any"):
            query = query.matches_any()

        for op in ops:
            if op not in filters_dict:
                continue
            items = filters_dict[op]
            if not isinstance(items, list):
                items = [items]
            for item in items:
                term = item.get("term")
                if not term and op != "date_range":
                    continue
                if op in {"equals", "not_equals", "is_any", "is_none"}:
                    values = item.get("values")
                    if values is None:
                        continue
                    query = getattr(query, op)(term, values)
                elif op in {"greater_than", "less_than"}:
                    value = item.get("value")
                    if value is None:
                        continue
                    query = getattr(query, op)(term, value)
                elif op in {"exists", "does_not_exist"}:
                    query = getattr(query, op)(term)
                elif op == "date_range":
                    term = item.get("term")
                    query = query.date_range(term=term, start_date=item.get("start_date"), end_date=item.get("end_date"))

        # Subquery support
        subgroups = filters_dict.get("subquery")
        if subgroups:
            if not isinstance(subgroups, list):
                subgroups = [subgroups]
            for sg in subgroups:
                sub_q_dict = sg.get("query")
                if not sub_q_dict:
                    continue
                sub_q = EventQuery()
                sub_q = self._apply_incydr_filters(sub_q, sub_q_dict)
                query = query.subquery(sub_q)

        return query

    def _handle_run_advanced_query(self, param, action_result):
        filters_json = param.get("filters_json")
        query = EventQuery()

        if filters_json:
            try:
                filters_dict = json.loads(filters_json)
            except Exception as ex:
                return action_result.set_status(phantom.APP_ERROR, f"Code42: Invalid filters_json: {ex}")

            try:
                query = self._apply_query_filters(query, filters_dict)
            except Exception as ex:
                return action_result.set_status(phantom.APP_ERROR, f"Code42: Failed to apply filters_json: {ex}")
        else:
            return action_result.set_status(phantom.APP_ERROR, "filters_json parameter is required")

        # Pagination with max_results
        max_results = param.get("max_results", MAX_RESULTS_DEFAULT)
        ret_val, max_results = self._validate_integer(action_result, max_results, CODE42V3_MAX_RESULTS_KEY)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if not bool(getattr(query, "groups", None)):
            return action_result.set_status(phantom.APP_ERROR, "No filters provided")

        returned = 0
        try:
            while returned < max_results:
                response = self._client.file_events.v2.search(query)
                page_events = getattr(response, "file_events", [])
                for event in page_events:
                    action_result.add_data(json.loads(event.json()))
                    returned += 1
                    if returned >= max_results:
                        break
                if response.next_pg_token is None:
                    break
                query.page_token = response.next_pg_token
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to run advanced query. Error: {e!s}")
        action_result.update_summary({"total_count": returned})
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_set_session_state(self, param, action_result):
        """
        Sets the state for a given session.
        Args:
            session_ids (list): The session IDs to set the state for.
            session_state (str): The state to set for the session.
        Returns:
            ActionResult: The action result object which contains the session state.
        """
        self.save_progress("Setting session state")
        session_ids = param.get("session_ids").split(",")
        session_ids = [session_id.strip() for session_id in session_ids if session_id.strip()]
        if len(session_ids) == 0:
            return action_result.set_status(phantom.APP_ERROR, "No session IDs provided")

        state = param.get("session_state").strip().upper()
        valid_states = {e.value for e in SessionStates}
        if state not in valid_states:
            return action_result.set_status(phantom.APP_ERROR, f"Invalid session state. Expected values are: {valid_states}")
        try:
            responses = self._client.sessions.v1.update_state_by_id(session_ids=session_ids, new_state=SessionStates(state))
        except HTTPError as e:
            error_detail = self._extract_http_errors(e)
            error_message = f"Failed to update session state. Error: {e!s}. Details: {error_detail}"
            return action_result.set_status(phantom.APP_ERROR, error_message)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to update session state. Error: {e!s}")
        failed_count = 0
        failure_messages = ""
        phantom_status = phantom.APP_SUCCESS
        for response in responses:
            if not response.ok:
                phantom_status = phantom.APP_ERROR
                failure_messages += f"{response.text}\n\n"
                failed_count += 1
        status_message = f"Successfully set session state to {state} for all {len(session_ids)} session(s)"
        if failed_count > 0:
            status_message = f"Session state set to {state} successfully for {len(session_ids) - failed_count} session(s), failed for {failed_count} session(s). Failure details: {failure_messages}"
        action_result.update_summary(
            {
                "total_count": len(session_ids),
                "total_count_successful": len(session_ids) - failed_count,
            }
        )
        return action_result.set_status(phantom_status, status_message)

    """ USER ACTIONS """

    def _handle_list_users(self, param, action_result):
        """
        Lists all users with optional filters for active, blocked, and username.
        Args:
            active (bool): Whether to list active users.
            blocked (bool): Whether to list  blocked users.
            username (str): The username to filter by.
        Returns:
            ActionResult: The action result object which contains the users.
        """
        active = param.get("active")
        blocked = param.get("blocked")
        username = param.get("username")

        try:
            users_iter = self._client.users.v1.iter_all(active=active, blocked=blocked, username=username)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to list users. Error: {e!s}")

        count = 0
        for user in users_iter:
            count += 1
            action_result.add_data(json.loads(user.json()))
        action_result.update_summary({"total_count": count})
        return action_result.set_status(phantom.APP_SUCCESS, "User list retrieved successfully")

    def _handle_get_user(self, param, action_result):
        """
        Gets a user by their ID.
        Args:
            user_id (str): The ID of the user to get.
        Returns:
            ActionResult: The action result object which contains the user.
        """

        user_id = param.get("user_id").strip()
        try:
            user = self._client.users.v1.get_user(user_id)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to get user {user_id}. Error: {e!s}")
        action_result.add_data(json.loads(user.json()))
        action_result.update_summary(
            {
                "user_id": user.user_id,
                "username": user.username,
                "active": user.active,
                "blocked": user.blocked,
            }
        )
        return action_result.set_status(phantom.APP_SUCCESS, f"User with id {user_id} retrieved successfully")

    def _handle_deactivate_user(self, param, action_result):
        """
        Deactivates a user by their ID.
        Args:
            user_id (str): The ID of the user to deactivate.
        Returns:
            ActionResult: The action result object which contains the user status.
        """
        user_id = param.get("user_id")
        try:
            response = self._client.users.v1.deactivate(user_id)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to deactivate user {user_id}. Error: {e!s}")

        if response.ok:
            action_result.update_summary({"user_id": user_id, "deactivated": True})
            return action_result.set_status(phantom.APP_SUCCESS, f"User with id {user_id} deactivated successfully")

        return action_result.set_status(
            phantom.APP_ERROR, f"Failed to deactivate user {user_id}. Status code: {response.status_code}. Response: {response.text}"
        )

    def _handle_reactivate_user(self, param, action_result):
        """
        Reactivates a user by their ID.
        Args:
            user_id (str): The ID of the user to reactivate.
        Returns:
            ActionResult: The action result object which contains the user status.
        """

        user_id = param.get("user_id").strip()
        try:
            response = self._client.users.v1.activate(user_id)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to reactivate user {user_id}. Error: {e!s}")

        if response.ok:
            action_result.update_summary({"user_id": user_id, "reactivated": True})
            return action_result.set_status(phantom.APP_SUCCESS, f"User with id {user_id} reactivated successfully")

        return action_result.set_status(
            phantom.APP_ERROR, f"Failed to reactivate user {user_id}. Status code: {response.status_code}. Response: {response.text}"
        )

    def _handle_get_actor_by_id(self, param, action_result):
        """
        Gets an actor by their ID.
        Args:
            actor_id (str): The ID of the actor to get.
            prefer_parent (bool): Whether to prefer the parent actor.
        Returns:
            ActionResult: The action result object which contains the actor.
        """

        actor_id = param.get("actor_id").strip()
        prefer_parent = param.get("prefer_parent")
        try:
            actor = self._client.actors.v1.get_actor_by_id(actor_id=actor_id, prefer_parent=prefer_parent)
            action_result.add_data(actor.dict())
            action_result.update_summary(
                {
                    "actor_id": actor.actor_id,
                    "name": actor.name,
                }
            )
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to get actor {actor_id}. Error: {e!s}")
        return action_result.set_status(phantom.APP_SUCCESS, f"Actor with id {actor_id} retrieved successfully")

    def _handle_get_actor_by_name(self, param, action_result):
        """
        Gets an actor by their name.
        Args:
            name (str): The name of the actor to get.
            prefer_parent (bool): Whether to prefer the parent actor.
        Returns:
            ActionResult: The action result object which contains the actor.
        """
        name = param.get("name")
        prefer_parent = param.get("prefer_parent")
        try:
            actor = self._client.actors.v1.get_actor_by_name(name=name, prefer_parent=prefer_parent)
            action_result.add_data(actor.dict())
            action_result.update_summary(
                {
                    "actor_id": actor.actor_id,
                    "name": actor.name,
                }
            )
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to get actor {name}. Error: {e!s}")
        return action_result.set_status(phantom.APP_SUCCESS, f"Actor with name {name} retrieved successfully")

    def _handle_update_actor(self, param, action_result):
        """
        Updates an actor by their ID.
        Args:
            actor_id (str): The ID of the actor to update.
            notes (str): The notes to update the actor with.
            start_date (str): The start date to update the actor with.
            end_date (str): The end date to update the actor with.
        Returns:
            ActionResult: The action result object which contains the actor status.
        """
        actor_id = param.get("actor_id")
        if notes := param.get("notes"):
            notes = notes.strip()
        if start_date := param.get("start_date"):
            start_date = start_date.strip()
        if end_date := param.get("end_date"):
            end_date = end_date.strip()

        if start_date:
            is_valid, error = self._is_valid_date(start_date)
            if not is_valid:
                return action_result.set_status(phantom.APP_ERROR, f"Invalid start date. Error: {error}")

        if end_date:
            is_valid, error = self._is_valid_date(end_date)
            if not is_valid:
                return action_result.set_status(phantom.APP_ERROR, f"Invalid end date. Error: {error}")

        try:
            response = self._client.actors.v1.update_actor(actor=actor_id, notes=notes, start_date=start_date, end_date=end_date)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to update actor `{actor_id}`. Error: {e}")
        return action_result.set_status(phantom.APP_SUCCESS, f"Actor with id {actor_id} updated successfully")

    """
       Case actions
    """

    def _handle_create_case(self, param, action_result):
        """
        Creates a new case.
        Args:
            name (str): The name of the case.
            description (str): The description of the case.
            subject (str): The subject of the case.
            assignee (str): The assignee of the case.
            findings (str): The findings of the case.
        Returns:
            ActionResult: The action result object which contains the case details.
        """
        self.save_progress("Creating case")
        name = param.get("name")
        description = param.get("description")
        subject = param.get("subject")
        assignee = param.get("assignee")
        findings = param.get("findings")
        try:
            case_detail = self._client.cases.v1.create(
                name=name,
                subject=subject,
                assignee=assignee,
                description=description,
                findings=findings,
            )

        except HTTPError as e:
            error_detail = self._extract_http_errors(e)
            error_message = f"Failed to create case. Error: {e!s}. Details: {error_detail}"
            return action_result.set_status(phantom.APP_ERROR, error_message)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to create case. Error: {e!s}")

        action_result.add_data(json.loads(case_detail.json()))
        action_result.update_summary({"case_number": case_detail.number, "case_name": case_detail.name, "status": case_detail.status})
        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully created case {case_detail.number}")

    def _handle_update_case(self, params, action_result):
        """
        Updates an existing case.
        Args:
            case_number (str): The number of the case to update.
            name (str): The name of the case.
            subject (str): The subject of the case.
            assignee (str): The assignee of the case.
            description (str): The description of the case.
            findings (str): The findings of the case.
            status (str): The status of the case.
        Returns:
            ActionResult: The action result object which contains the case details.
        """
        case_number = params.get("case_number")
        ret_val, case_number = self._validate_integer(action_result, case_number, CODE42V3_CASE_NUM_KEY)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        try:
            case = self._client.cases.v1.get_case(case_number)
        except HTTPError as e:
            error_detail = self._extract_http_errors(e)
            error_message = f"Failed to update case {case_number}. Error: {e!s}. Details: {error_detail}"
            return action_result.set_status(phantom.APP_ERROR, error_message)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to update case {case_number}. Error: {e!s}")

        if params.get("name"):
            case.name = params.get("name")
        if params.get("subject"):
            case.subject = params.get("subject")
        if params.get("assignee"):
            case.assignee = params.get("assignee")
        if params.get("description"):
            case.description = params.get("description")
        if params.get("findings"):
            case.findings = params.get("findings")
        if status := params.get("status"):
            valid_statuses = {e.value for e in CaseStatus}
            sanitized_status = status.strip().upper()
            if sanitized_status not in valid_statuses:
                return action_result.set_status(phantom.APP_ERROR, f"Invalid status. Expected values are: {', '.join(valid_statuses)}")
            case.status = CaseStatus(sanitized_status)
        try:
            updated_case = self._client.cases.v1.update(case)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to update case {case_number}. Error: {e!s}")

        action_result.add_data(json.loads(updated_case.json()))
        action_result.update_summary({"case_number": updated_case.number, "case_name": updated_case.name, "status": updated_case.status})
        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully updated case {case_number}")

    def _handle_close_case(self, params, action_result):
        """
        Closes an existing case.
        Args:
            case_number (str): The number of the case to close.
        Returns:
            ActionResult: The action result object which contains the case details.
        """
        case_number = params.get("case_number")
        ret_val, case_number = self._validate_integer(action_result, case_number, CODE42V3_CASE_NUM_KEY)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        try:
            case = self._client.cases.v1.get_case(case_number)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Unable to retrieve case {case_number}. Error: {e!s}")

        if CaseStatus(case.status) == CaseStatus.CLOSED:
            action_result.update_summary({"case_number": case_number, "status": case.status})
            return action_result.set_status(phantom.APP_SUCCESS, f"Case {case_number} is already closed")

        try:
            case.status = CaseStatus.CLOSED
            closed_case = self._client.cases.v1.update(case)
        except HTTPError as e:
            error_detail = self._extract_http_errors(e)
            error_message = f"Failed to close case {case_number}. Error: {e!s}. Details: {error_detail}"
            return action_result.set_status(phantom.APP_ERROR, error_message)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to close case {case_number}. Error: {e!s}")
        if CaseStatus(closed_case.status) == CaseStatus.CLOSED:
            action_result.update_summary({"case_number": closed_case.number, "status": closed_case.status})
            return action_result.set_status(phantom.APP_SUCCESS, f"Successfully closed case {case_number}")
        else:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to close case {case_number}. Error: {closed_case.status}")

    def _handle_list_cases(self, params, action_result):
        """
        Lists all cases with optional filters for assignee, is_assigned, name, and status.
        Args:
            assignee (str): The assignee of the case.
            is_assigned (bool): Whether the case is assigned.
            name (str): The name of the case.
            status (str): The status of the case.
        Returns:
            ActionResult: The action result object which contains the cases.
        """
        assignee = params.get("assignee")
        is_assigned = params.get("is_assigned")
        name = params.get("name")

        status = None
        if status_param := params.get("status"):
            valid_statuses = {e.value for e in CaseStatus}
            sanitized_status = status_param.strip().upper()
            if sanitized_status not in valid_statuses:
                return action_result.set_status(phantom.APP_ERROR, f"Invalid status. Expected values are: {', '.join(valid_statuses)}")
            status = CaseStatus(sanitized_status)
        try:
            cases_iter = self._client.cases.v1.iter_all(assignee=assignee, is_assigned=is_assigned, name=name, status=status)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to list cases. Error: {e!s}")

        case_count = 0
        for case in cases_iter:
            action_result.add_data(json.loads(case.json()))
            case_count += 1

        action_result.update_summary({"total_count": case_count})
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully listed cases")

    def _handle_add_case_event(self, param, action_result):
        """
        Adds events to a case.
        Args:
            case_number (str): The number of the case to add the events to.
            event_ids (list): The IDs of the events to add to the case.
        Returns:
            ActionResult: The action result object which contains the case details.
        """
        case_number = param.get("case_number")

        ret_val, case_number = self._validate_integer(action_result, case_number, CODE42V3_CASE_NUM_KEY)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        event_ids_param = param.get("event_ids")

        event_ids = event_ids_param.split(",")
        event_ids = [event_id.strip() for event_id in event_ids if event_id.strip()]
        try:
            response = self._client.cases.v1.add_file_events_to_case(case_number=case_number, event_ids=event_ids)
        except HTTPError as e:
            error_detail = self._extract_http_errors(e)
            error_message = f"Failed to add events to case {case_number}. Error: {e!s}. Details: {error_detail}"
            return action_result.set_status(phantom.APP_ERROR, error_message)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to add events to case {case_number}. Error: {e!s}")
        if not response.ok:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to add events to case {case_number}. Error: {response.text}")
        action_result.update_summary({"added_event_count": len(event_ids)})
        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully added events to case {case_number}")

    def _handle_add_legalhold_custodian(self, param, action_result):
        """
        Adds a custodian to a legal hold matter.
        Args:
            matter_id (str): The ID of the matter to add the custodian to.
            user_id (str): The ID of the user to add as a custodian.
        Returns:
            ActionResult: The action result object which contains the custodian details.
        """
        matter_id = param.get("matter_id")
        user_id = param.get("user_id")
        try:
            response = self._client.legal_hold.v1.add_custodian(matter_id=matter_id, user_id=user_id)
        except HTTPError as e:
            error_detail = self._extract_http_errors(e)
            error_message = f"Failed to add custodian to matter {matter_id}. Error: {e!s}. Details: {error_detail}"
            return action_result.set_status(phantom.APP_ERROR, error_message)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to add custodian to matter {matter_id}. Error: {e!s}")
        action_result.add_data(json.loads(response.json()))
        action_result.update_summary(
            {
                "membership_active": response.membership_active,
                "matter_id": response.matter.matter_id if response.matter else matter_id,
                "user_id": response.custodian.user_id if response.custodian else user_id,
            }
        )
        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully added custodian {user_id} to matter {matter_id}")

    def _handle_remove_legalhold_custodian(self, param, action_result):
        """
        Removes a custodian from a legal hold matter.
        Args:
            matter_id (str): The ID of the matter to remove the custodian from.
            user_id (str): The ID of the user to remove as a custodian.
        Returns:
            ActionResult: The action result object which contains the custodian details.
        """
        matter_id = param.get("matter_id")
        user_id = param.get("user_id")
        try:
            response = self._client.legal_hold.v1.remove_custodian(matter_id=matter_id, user_id=user_id)
        except HTTPError as e:
            error_detail = self._extract_http_errors(e)
            error_message = f"Failed to remove custodian {user_id} from matter {matter_id}. Error: {e!s}. Details: {error_detail}"
            return action_result.set_status(phantom.APP_ERROR, error_message)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to remove custodian {user_id} from matter {matter_id}. Error: {e!s}")
        if not response.ok:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Failed to remove custodian {user_id} from matter {matter_id}. Status code: {response.status_code}. Error: {response.text}",
            )
        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully removed custodian {user_id} from matter {matter_id}")

    def _handle_list_available_watchlists(self, param, action_result):
        """
        Lists all available watchlists.
        Args:
            actor_id (str): Optional. The ID of the actor to list the watchlists for.
        Returns:
            ActionResult: The action result object which contains the watchlists.
        """
        actor_id = param.get("actor_id")
        watchlists = {}
        try:
            watchlists_iter = self._client.watchlists.v2.iter_all(actor_id=actor_id)
        except HTTPError as e:
            error_detail = self._extract_http_errors(e)
            error_message = f"Failed to list available watchlists. Error: {e!s}. Details: {error_detail}"
            return action_result.set_status(phantom.APP_ERROR, error_message)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to list available watchlists. Error: {e!s}")
        for watchlist in watchlists_iter:
            action_result.add_data(watchlist.dict())
            watchlists[watchlist.list_type] = watchlist.watchlist_id
        action_result.update_summary(watchlists)
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully listed available watchlists")

    def _handle_get_watchlist_id_by_name(self, param, action_result):
        """
        Gets the ID of a watchlist by its name.
        Args:
            watchlist_name (str): The name of the watchlist to get the ID of.
        Returns:
            ActionResult: The action result object which contains the watchlist ID.
        """
        watchlist_name = param.get("watchlist_name").strip()
        try:
            watchlist_id = self._client.watchlists.v2.get_id_by_name(watchlist_name)
        except HTTPError as e:
            error_detail = self._extract_http_errors(e)
            error_message = f"Failed to get watchlist id by name {watchlist_name}. Error: {e!s}. Details: {error_detail}"
            return action_result.set_status(phantom.APP_ERROR, error_message)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to get watchlist id by name {watchlist_name}. Error: {e!s}")
        if watchlist_id is None:
            return action_result.set_status(phantom.APP_ERROR, f"Watchlist {watchlist_name} not found")
        action_result.add_data({"watchlistId": watchlist_id})
        action_result.update_summary({"watchlistId": watchlist_id})
        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully got watchlist id by name {watchlist_name}")

    def _handle_create_watchlist(self, param, action_result):
        """
        Creates a new watchlist.
        Args:
            watchlist_name (str): The name of the watchlist to create.
            title (str): The title of the watchlist to create.
            description (str): The description of the watchlist to create.
        Returns:
            ActionResult: The action result object which contains the watchlist details.
        """
        watchlist_name = param.get("watchlist_name")
        title = param.get("title")
        description = param.get("description")
        # validate if watchlist name is valid.
        if not self._is_valid_watchlist_name(watchlist_name):
            return action_result.set_status(phantom.APP_ERROR, f"Invalid watchlist name `{watchlist_name}`")
        try:
            response = self._client.watchlists.v2.create(watchlist_type=WatchlistType(watchlist_name), title=title, description=description)
        except HTTPError as e:
            error_detail = self._extract_http_errors(e)
            error_message = f"Failed to create watchlist {watchlist_name}. Error: {e!s}. Details: {error_detail}"
            return action_result.set_status(phantom.APP_ERROR, error_message)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to create watchlist {watchlist_name}. Error: {e!s}")
        action_result.add_data(response.dict())
        action_result.update_summary({"watchlist_id": response.watchlist_id, "watchlist_name": watchlist_name})
        return action_result.set_status(
            phantom.APP_SUCCESS, f"Successfully created watchlist {watchlist_name} with watchlist id: {response.watchlist_id}"
        )

    def _handle_delete_watchlist(self, param, action_result):
        """
        Deletes a watchlist.
        Args:
            watchlist_id (str): The ID of the watchlist to delete.
        Returns:
            ActionResult: The action result object which contains the watchlist details.
        """
        watchlist_id = param.get("watchlist_id")
        try:
            response = self._client.watchlists.v2.delete(watchlist_id)
        except HTTPError as e:
            error_detail = self._extract_http_errors(e)
            error_message = f"Failed to delete watchlist {watchlist_id}. Error: {e!s}. Details: {error_detail}"
            return action_result.set_status(phantom.APP_ERROR, error_message)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to delete watchlist {watchlist_id}. Error: {e!s}")
        if not response.ok:
            return action_result.set_status(
                phantom.APP_ERROR, f"Failed to delete watchlist {watchlist_id}. Status code: {response.status_code}. Error: {response.text}"
            )

        action_result.update_summary({"watchlist_id": watchlist_id, "status_code": response.status_code})

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully deleted watchlist {watchlist_id}")

    def _handle_add_actors_to_watchlist(self, param, action_result):
        """
        Adds actors to a watchlist.
        Args:
            actor_ids (list): The IDs of the actors to add to the watchlist.
            watchlist_id (str): The ID of the watchlist to add the actors to.
        Returns:
            ActionResult: The action result object which contains the watchlist details.
        """
        actor_ids = param.get("actor_ids")
        actor_ids = [actor_id.strip() for actor_id in actor_ids.split(",") if actor_id.strip()]
        watchlist_id = param.get("watchlist_id")

        try:
            response = self._client.watchlists.v2.add_included_actors(watchlist_id, actor_ids)
        except HTTPError as e:
            error_detail = self._extract_http_errors(e)
            error_message = f"Failed to add actors {actor_ids} to watchlist {watchlist_id}. Error: {e!s}. Details: {error_detail}"
            return action_result.set_status(phantom.APP_ERROR, error_message)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Failed to add actors {actor_ids} to watchlist {watchlist_id}. Error: {e!s}")
        if not response.ok:
            return action_result.set_status(
                phantom.APP_ERROR, f"Failed to add actors {actor_ids} to watchlist {watchlist_id}. Error: {response.text}"
            )
        action_result.update_summary({"added": True, "added_actor_count": len(actor_ids)})
        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully added actors {actor_ids} to watchlist {watchlist_id}")

    def _handle_remove_actors_from_watchlist(self, param, action_result):
        """
        Removes actors from a watchlist.
        Args:
            actor_ids (list): The IDs of the actors to remove from the watchlist.
            watchlist_id (str): The ID of the watchlist to remove the actors from.
        Returns:
            ActionResult: The action result object which contains the watchlist details.
        """
        actor_ids = param.get("actor_ids")
        actor_ids = [actor_id.strip() for actor_id in actor_ids.split(",") if actor_id.strip()]
        watchlist_id = param.get("watchlist_id")
        try:
            response = self._client.watchlists.v2.remove_included_actors(watchlist_id, actor_ids)
        except HTTPError as e:
            error_detail = self._extract_http_errors(e)
            error_message = f"Failed to remove actors {actor_ids} from watchlist {watchlist_id}. Error: {e!s}. Details: {error_detail}"
            return action_result.set_status(phantom.APP_ERROR, error_message)
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, f"Failed to remove actors {actor_ids} from watchlist {watchlist_id}. Error: {e!s}"
            )
        if not response.ok:
            return action_result.set_status(
                phantom.APP_ERROR, f"Failed to remove actors {actor_ids} from watchlist {watchlist_id}. Error: {response.text}"
            )
        action_result.update_summary({"removed": True, "removed_actor_count": len(actor_ids)})
        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully removed actors {actor_ids} from watchlist {watchlist_id}")

    def _handle_list_actors_in_watchlist(self, param, action_result):
        """
        Lists all employees in a watchlist.
        Args:
            watchlist_id (str): The ID of the watchlist to list the employees in.
        Returns:
            ActionResult: The action result object which contains the employees.
        """
        watchlist_id = param.get("watchlist_id")
        actor_count = 0
        if not watchlist_id:
            return action_result.set_status(phantom.APP_ERROR, "`watchlist_id` action parameter is required.")
        try:
            actors_iter = self._client.watchlists.v2.iter_all_included_actors(watchlist_id)
            for actor in actors_iter:
                action_result.add_data(json.loads(actor.json()))
                actor_count += 1
        except HTTPError as e:
            error_detail = self._extract_http_errors(e)
            error_message = f"Failed to list employees in watchlist {watchlist_id}. Error: {e!s}. Details: {error_detail}"
            return action_result.set_status(phantom.APP_ERROR, error_message)
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Failed to list employees in watchlist `{watchlist_id}`. Error: {e}",
            )

        action_result.update_summary({"watchlist_id": watchlist_id, "total_count": actor_count})
        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully listed {actor_count} actors in watchlist {watchlist_id}")

    def _get_file_content(self, file_hash):
        if not utils.is_sha256(file_hash):
            raise Code42UnsupportedHashError()

        response = self._client.files.v1.stream_file_by_sha256(sha256=file_hash)

        if response.ok:
            try:
                return b"".join(chunk for chunk in response.iter_content(chunk_size=128) if chunk)
            finally:
                response.close()
        else:
            raise Exception(f"failed to get file content for {file_hash}. Error: {response.text}")

    def _handle_hunt_file(self, param, action_result):
        self.save_progress("Hunting file")
        file_hash = param.get("file_hash")
        file_name = param.get("file_name")
        if not file_name:
            file_name = file_hash
        self.save_progress("getting file content")
        try:
            file_content = self._get_file_content(file_hash)
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return action_result.set_status(
                    phantom.APP_ERROR,
                    f"File content for {file_hash} is unavailable. The file may not exist or the content is no longer retained. {e.response.text}",
                )
            error_message = f"Failed to get file content for {file_hash}. Error: {e!s}"
            return action_result.set_status(phantom.APP_ERROR, error_message)
        except Exception as e:
            error_msg = str(e)
            return action_result.set_status(phantom.APP_ERROR, f"failed to get file content for {file_hash}. Error: {error_msg}")
        container_id = self.get_container_id()
        if not container_id:
            return action_result.set_status(phantom.APP_ERROR, "failed to get container id")
        try:
            status = Vault.create_attachment(file_content, container_id, file_name=file_name)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"failed to create attachment for {file_name}. Error: {e!s}")
        if not status.get("succeeded", False):
            return action_result.set_status(
                phantom.APP_ERROR, f"failed to create attachment for {file_name}. Error message: {status.get('message', 'Unknown error')}"
            )
        status_message = f"{file_name} was successfully downloaded and attached to container {container_id}"
        action_result.update_summary({"file_name": file_name, "container_id": container_id, "vault_id": status.get("vault_id")})
        return action_result.set_status(phantom.APP_SUCCESS, status_message)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        action_id = self.get_action_identifier()
        self.debug_print("action_id", action_id)

        action_result = self.add_action_result(ActionResult(dict(param)))

        if self._client is None:
            self._client = incydr.Client(url=self._base_url, api_client_id=self._client_id, api_client_secret=self._client_secret)

        handlers = {
            "test_connectivity": self._handle_test_connectivity,
            "on_poll": self._handle_on_poll,
            "get_session_details": self._handle_get_session_details,
            "set_session_state": self._handle_set_session_state,
            "search_sessions": self._handle_search_sessions,
            "run_query": self._handle_run_query,
            "run_advanced_query": self._handle_run_advanced_query,
            "list_users": self._handle_list_users,
            "deactivate_user": self._handle_deactivate_user,
            "reactivate_user": self._handle_reactivate_user,
            "get_user": self._handle_get_user,
            "create_case": self._handle_create_case,
            "update_case": self._handle_update_case,
            "close_case": self._handle_close_case,
            "list_cases": self._handle_list_cases,
            "add_case_event": self._handle_add_case_event,
            "add_legalhold_custodian": self._handle_add_legalhold_custodian,
            "remove_legalhold_custodian": self._handle_remove_legalhold_custodian,
            "list_available_watchlists": self._handle_list_available_watchlists,
            "get_watchlist_id_by_name": self._handle_get_watchlist_id_by_name,
            "create_watchlist": self._handle_create_watchlist,
            "delete_watchlist": self._handle_delete_watchlist,
            "add_actors_to_watchlist": self._handle_add_actors_to_watchlist,
            "remove_actors_from_watchlist": self._handle_remove_actors_from_watchlist,
            "list_actors_in_watchlist": self._handle_list_actors_in_watchlist,
            "update_actor": self._handle_update_actor,
            "get_actor_by_id": self._handle_get_actor_by_id,
            "get_actor_by_name": self._handle_get_actor_by_name,
            "hunt_file": self._handle_hunt_file,
        }

        if action_id in handlers:
            ret_val = handlers[action_id](param, action_result)
        else:
            ret_val = action_result.set_status(phantom.APP_ERROR, "Action not yet implemented")

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()

        self._base_url = config.get("cloud_instance")
        if not self._base_url:
            return self.set_status(phantom.APP_ERROR, "Base URL is required.")

        if not self._base_url.lower().startswith(("http://", "https://")):
            self._base_url = f"https://{self._base_url}"

        self._client_id = config.get("client_id")
        self._client_secret = config["client_secret"]

        env_vars = config.get("_reserved_environment_variables", {})
        if "HTTP_PROXY" in env_vars:
            self._proxy["http"] = env_vars["HTTP_PROXY"]["value"]
        elif "HTTP_PROXY" in os.environ:
            self._proxy["http"] = os.environ.get("HTTP_PROXY")

        if "HTTPS_PROXY" in env_vars:
            self._proxy["https"] = env_vars["HTTPS_PROXY"]["value"]
        elif "HTTPS_PROXY" in os.environ:
            self._proxy["https"] = os.environ.get("HTTPS_PROXY")

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = Code42V3Connector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=False)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=False, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = Code42V3Connector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json))
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)


if __name__ == "__main__":
    main()
