# File: varonissaas_connector.py
#
# Copyright (c) Varonis, 2024-2025
#
# This unpublished material is proprietary to Varonis SaaS. All
# rights reserved. The methods and techniques described herein are
# considered trade secrets and/or confidential. Reproduction or
# distribution, in whole or in part, is forbidden except by express
# written permission of Varonis SaaS.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

# Python 3 Compatibility imports

import json
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Optional

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from requests.adapters import HTTPAdapter
from requests.models import Response
from urllib3 import Retry

import varonissaas_tools as tools
from varonissaas_consts import *
from varonissaas_search import *


REQUEST_RETRIES = 30
HTTP_STATUS_WHITE_LIST = [304, 206]


class RetVal(tuple):
    def __new__(cls, val1: bool, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class VaronisSaasConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state: dict[str, Any] = None
        self._session = None
        self._verify = None
        self._headers = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None

    # HELPERS
    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"),
            None,
        )

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Unable to parse JSON response. Error: {e!s}",
                ),
                None,
            )

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text or "text" in r.headers.get("Content-Type", ""):
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _http_request(
        self,
        url_suffix="",
        method="GET",
        full_url=None,
        headers=None,
        auth=None,
        params=None,
        data=None,
        timeout=VDSP_REQUEST_TIMEOUT,
        **kwargs,
    ) -> Response:
        address = full_url if full_url else tools.urljoin(self._base_url, url_suffix)
        headers = headers if headers else self._headers
        headers["varonis-integration"] = "Splunk SOAR"

        resp = self._session.request(
            method,
            address,
            verify=self._verify,
            params=params,
            data=data,
            headers=headers,
            auth=auth,
            timeout=timeout,
            **kwargs,
        )
        return resp

    def _make_rest_call(
        self,
        action_result,
        url_suffix="",
        method="GET",
        full_url=None,
        headers=None,
        auth=None,
        params=None,
        data=None,
        json=None,
        timeout=VDSP_REQUEST_TIMEOUT,
        **kwargs,
    ):
        try:
            resp = self._http_request(
                url_suffix=url_suffix,
                method=method,
                full_url=full_url,
                headers=headers,
                auth=auth,
                params=params,
                data=data,
                json=json,
                timeout=timeout,
                **kwargs,
            )
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Error Connecting to server. Details: {e!s}",
                ),
                None,
            )

        return self._process_response(resp, action_result)

    def _make_search_call(self, action_result, query: SearchRequest, count: int, page: int = 1) -> RetVal:
        ret_val, results = self._make_rest_call(
            action_result=action_result,
            url_suffix=VDSP_SEARCH_ENDPOINT,
            method="POST",
            json=query.to_dict(),
        )

        if phantom.is_fail(ret_val):
            self.save_progress("Faild to make search query call.")
            return action_result.get_status()

        search_result_location = next(filter(lambda x: (x["dataType"] == "rows"), results))["location"]

        ret_val, results = self._make_rest_call(
            action_result=action_result,
            url_suffix=f"{VDSP_SEARCH_RESULT_ENDPOINT}/{search_result_location}",
            method="GET",
            params=get_query_range(count, page),
        )

        if phantom.is_fail(ret_val):
            self.save_progress("Faild to get results of search query call.")
            return action_result.get_status()

        return ret_val, results

    def _authorize(self, api_key: str) -> dict[str, Any]:
        action_result = self.add_action_result(ActionResult({}))
        headers = {"x-api-key": api_key}
        ret_val, response = self._make_rest_call(
            action_result=action_result,
            method="POST",
            url_suffix=VDSP_AUTH_ENDPOINT,
            data="grant_type=varonis_custom",
            headers=headers,
        )

        if phantom.is_fail(ret_val):
            self.save_progress(f"Faild to authorize on {VDSP_AUTH_ENDPOINT} endpoint.")
            return action_result.get_status()

        self._state[VDSP_ACCESS_TOKEN_KEY] = response[VDSP_ACCESS_TOKEN_KEY]
        self._state[VDSP_TOKEN_TYPE_KEY] = response[VDSP_TOKEN_TYPE_KEY]
        self._state[VDSP_EXPIRES_IN_KEY] = int(time.time()) + response[VDSP_EXPIRES_IN_KEY] - VDSP_REQUEST_TIMEOUT

        self.debug_print("Expiration time", self._state[VDSP_EXPIRES_IN_KEY])

        return response

    def _get_alerts_payload(
        self,
        threat_models: Optional[list[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        device_names: Optional[list[str]] = None,
        last_days: Optional[int] = None,
        user_names: Optional[list[str]] = None,
        from_ingest_time: Optional[datetime] = None,
        alert_statuses: Optional[list[str]] = None,
        alert_severities: Optional[list[str]] = None,
        descending_order: bool = True,
    ) -> SearchRequest:
        """Get alerts parameters

        :type threat_models: ``Optional[List[str]]``
        :param threat_models: List of threat models to filter by

        :type start_time: ``Optional[datetime]``
        :param start_time: Start time of the range of alerts

        :type end_time: ``Optional[datetime]``
        :param end_time: End time of the range of alerts

        :type device_names: ``Optional[List[str]]``
        :param device_names: List of device names to filter by

        :type last_days: ``Optional[List[int]]``
        :param last_days: Number of days you want the search to go back to

        :type user_names: ``Optional[List[int]]``
        :param user_names: List of user names

        :type from_alert_id: ``Optional[int]``
        :param from_alert_id: Alert id to fetch from

        :type alert_statuses: ``Optional[List[str]]``
        :param alert_statuses: List of alert statuses to filter by

        :type alert_severities: ``Optional[List[str]]``
        :param alert_severities: List of alert severities to filter by

        :type descendingOrder: ``bool``
        :param descendingOrder: Indicates whether alerts should be ordered in newest to oldest order

        :return: Parameters to be used in get alerts handler
        :rtype: ``Dict[str, Any]``
        """
        ingest_time_end = None
        if from_ingest_time:
            ingest_time_end = datetime.now()

        payload = create_alert_request(
            ingest_time_start=from_ingest_time,
            ingest_time_end=ingest_time_end,
            threat_models=threat_models,
            start_time=start_time,
            end_time=end_time,
            last_days=last_days,
            device_names=device_names,
            users=user_names,
            alert_statuses=alert_statuses,
            alert_severities=alert_severities,
            descending_order=descending_order,
        )

        return payload

    def _get_alerted_events_payload(self, alert_ids: list[str], descending_order: bool = True) -> SearchRequest:
        """Get alerted events parameters

        :type alert_ids: ``List[str]``
        :param alert_ids: List of related alerts

        :return: Parameters to be used in get alerted events handler
        :rtype: ``Dict[str, Any]`
        """
        payload = create_alerted_events_request(alert_ids, descending_order)
        return payload

    def _update_alert_status(self, action_result, query: dict[str, Any]) -> bool:
        """Update alert status

        :type query: ``Dict[str, Any]``
        :param query: Update request body

        :return: Result of execution
        :rtype: ``bool``

        """
        return self._make_rest_call(action_result, VDSP_UPDATE_ALET_STATUS_ENDPOINT, method="POST", json=query)

    def _create_container(self, data: AlertItem):
        container = dict()
        container["name"] = data.Name
        container["source_data_identifier"] = data.ID
        container["status"] = data.Status
        container["severity"] = data.Severity
        container["start_time"] = data.EventUTC.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        container["custom_fields"] = {
            "category": data.Category,
            "sam_account_name": data.SamAccountName,
            "privileged_account_type": data.PrivilegedAccountType,
            "asset": data.Asset,
            "platform": data.Platform,
            "file_server_or_domain": data.FileServerOrDomain,
            "contains_flagged_data": data.AssetContainsFlaggedData,
            "contains_sensitive_data": data.AssetContainsSensitiveData,
            "country": data.Country,
            "state": data.State,
            "device_name": data.DeviceName,
            "ip_threat_types": data.IPThreatTypes,
            "contain_malicious_external_ip": data.ContainMaliciousExternalIP,
            "blacklist_location": data.BlacklistLocation,
            "close_reason": data.CloseReason,
            "user_name": data.UserName,
            "abnormal_location": data.AbnormalLocation,
        }
        container["data"] = data.to_dict()
        return container

    def _create_artifact(self, data: EventItem):
        artifact = dict()
        utc_time = data.TimeUTC.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        artifact["name"] = data.Description
        artifact["label"] = "event"
        artifact["source_data_identifier"] = data.ID
        artifact["start_time"] = utc_time
        artifact["type"] = data.Type
        artifact["data"] = data.to_dict()
        return artifact

    # HANDLERS
    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Connecting to endpoint")

        # make rest call
        ret_val, _ = self._make_rest_call(action_result, VDSP_TEST_CONNECTION_ENDPOINT)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_alerts(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        threat_model_names = param.get("threat_model_name", None)
        page = param.get("page", 1)
        max_results = param.get("max_results", VDSP_MAX_ALERTS)
        start_time = param.get("start_time", None)
        end_time = param.get("end_time", None)
        alert_statuses = param.get("alert_status", None)
        alert_severities = param.get("alert_severity", None)
        device_names = param.get("device_name", None)
        user_names = param.get("user_name", None)
        last_days = param.get("last_days", None)
        descending_order = param.get("descending_order", True)

        try:
            user_names = tools.try_convert(user_names, lambda x: tools.multi_value_to_string_list(x))

            if last_days:
                last_days = tools.try_convert(
                    last_days,
                    lambda x: int(x),
                    ValueError(f"last_days should be integer, but it is {last_days}."),
                )

                if last_days <= 0:
                    raise ValueError("last_days cannot be less then 1")

            if user_names and len(user_names) > VDSP_MAX_USERS_TO_SEARCH:
                raise ValueError(f"cannot provide more then {VDSP_MAX_USERS_TO_SEARCH} users")

            alert_severities = tools.try_convert(alert_severities, lambda x: tools.multi_value_to_string_list(x))
            device_names = tools.try_convert(device_names, lambda x: tools.multi_value_to_string_list(x))
            threat_model_names = tools.try_convert(threat_model_names, lambda x: tools.multi_value_to_string_list(x))
            max_results = tools.try_convert(
                max_results,
                lambda x: int(x),
                ValueError(f"max_results should be integer, but it is {max_results}."),
            )
            start_time = tools.try_convert(
                start_time,
                lambda x: datetime.fromisoformat(x),
                ValueError(f"start_time should be in iso format, but it is {start_time}."),
            )
            end_time = tools.try_convert(
                end_time,
                lambda x: datetime.fromisoformat(x),
                ValueError(f"end_time should be in iso format, but it is {start_time}."),
            )

            alert_statuses = tools.try_convert(alert_statuses, lambda x: tools.multi_value_to_string_list(x))
            page = tools.try_convert(
                page,
                lambda x: int(x),
                ValueError(f"page should be integer, but it is {page}."),
            )

            if alert_severities:
                for severity in alert_severities:
                    if severity.lower() not in ALERT_SEVERITIES:
                        raise ValueError(f"There is no severity {severity}. Posible severities: {ALERT_SEVERITIES}")

            if alert_statuses:
                for status in alert_statuses:
                    if status.lower() not in ALERT_STATUSES.keys():
                        raise ValueError(f"There is no status {status}.")

            payload = self._get_alerts_payload(
                threat_models=threat_model_names,
                start_time=start_time,
                end_time=end_time,
                device_names=device_names,
                last_days=last_days,
                user_names=user_names,
                alert_statuses=alert_statuses,
                alert_severities=alert_severities,
                descending_order=descending_order,
            )

            self.debug_print("Alert search request payload:", json.dumps(payload.to_dict()))

            ret_val, results = self._make_search_call(action_result, query=payload, page=page, count=max_results)

            self.debug_print("Request completed", ret_val)

            if phantom.is_fail(ret_val):
                self.error_print("Get alerts failed.")
                return action_result.get_status()

            results = SearchAlertObjectMapper().map(results)

            for res in results:
                action_result.add_data(res.to_dict())

            action_result.update_summary({"alerts_count": len(results)})
        except Exception as e:
            self.error_print("Exception occurred while getting alerts.", e)
            return action_result.set_status(phantom.APP_ERROR, str(e))

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_alert_status(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        try:
            status = param["status"]
            alert_id = param["alert_id"]

            statuses = list(filter(lambda name: name != "closed", ALERT_STATUSES.keys()))
            if status.lower() not in statuses:
                raise ValueError(f"status must be one of {statuses}.")

            status_id = ALERT_STATUSES[status.lower()]

            query: dict[str, Any] = {
                "AlertGuids": tools.try_convert(alert_id, lambda x: tools.multi_value_to_string_list(x)),
                "closeReasonId": CLOSE_REASONS["none"],
                "statusId": status_id,
            }

            ret_val, response = self._update_alert_status(action_result, query)

            if phantom.is_fail(ret_val):
                self.error_print("Update alert status failed.")
                return action_result.get_status()

            action_result.add_data(response)
        except Exception as ex:
            action_result.set_status(phantom.APP_ERROR, str(ex))

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_close_alert(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            alert_id = param["alert_id"]
            close_reason = param["close_reason"]

            close_reasons = list(filter(lambda name: not tools.strEqual(name, "none"), CLOSE_REASONS.keys()))
            if close_reason.lower() not in close_reasons:
                raise ValueError(f"close reason must be one of {close_reasons}")

            alert_ids = tools.try_convert(alert_id, lambda x: tools.multi_value_to_string_list(x))
            close_reason_id = CLOSE_REASONS[close_reason.lower()]

            if len(alert_ids) == 0:
                raise ValueError("alert id(s) not specified")

            query: dict[str, Any] = {
                "AlertGuids": alert_ids,
                "closeReasonId": close_reason_id,
                "statusId": ALERT_STATUSES["closed"],
            }

            ret_val, response = self._update_alert_status(action_result, query)

            if phantom.is_fail(ret_val):
                self.error_print("Close alert failed.")
                return action_result.get_status()

            action_result.add_data(response)
        except Exception as ex:
            action_result.set_status(phantom.APP_ERROR, str(ex))

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_alerted_events(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        try:
            alert_ids = tools.multi_value_to_string_list(param["alert_id"])
            page = param.get("page", 1)
            count = param.get("max_results", VDSP_MAX_ALERTED_EVENTS)
            descending_order = param.get("descending_order", True)

            count = tools.try_convert(
                count,
                lambda x: int(x),
                ValueError(f"max_results should be integer, but it is {count}."),
            )

            page = tools.try_convert(
                page,
                lambda x: int(x),
                ValueError(f"page should be integer, but it is {page}."),
            )

            payload = self._get_alerted_events_payload(alert_ids, descending_order)

            ret_val, results = self._make_search_call(action_result, query=payload, page=page, count=count)

            if phantom.is_fail(ret_val):
                self.error_print("Get alerted events failed.")
                return action_result.get_status()

            results = SearchEventObjectMapper().map(results)

            for res in results:
                action_result.add_data(res.to_dict())

            action_result.update_summary({"events_count": len(results)})
        except Exception as ex:
            action_result.set_status(phantom.APP_ERROR, str(ex))

        return action_result.set_status(phantom.APP_SUCCESS)

    def _on_poll(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        config = self.get_config()
        last_fetched_time = self._state.get(VDSP_LAST_FETCH_TIME, None)
        last_fetched_time = tools.try_convert(last_fetched_time, lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%S.%f%z"))
        ingest_period = config.get(VDSP_INGEST_PERIOD_KEY, VDSP_DEFAULT_INGEST_PERIOD)
        is_ingest_artifacts = config.get(VDSP_INGEST_ARTIFACTS_FLAG, True)
        alert_status = config.get(VDSP_ALERT_STATUS_KEY, None)
        alert_status = tools.multi_value_to_string_list(alert_status)
        threat_model = config.get(VDSP_THREAT_MODEL_KEY, None)
        threat_model = tools.multi_value_to_string_list(threat_model)
        severity = config.get(VDSP_ALERT_SEVERITY_KEY, None)
        severity = tools.convert_level(severity, list(ALERT_SEVERITIES.keys()))

        try:
            container_count = param.get(phantom.APP_JSON_CONTAINER_COUNT, float("inf"))
            start_time = tools.numeric_to_date(ingest_period)
            artifact_count = param.get(phantom.APP_JSON_ARTIFACT_COUNT, VDSP_MAX_ALERTED_EVENTS)

            self.save_progress(f"Start ingesting data for interval from {start_time}, amount {container_count}")

            while container_count > 0:
                max_alerts = VDSP_MAX_ALERTS if container_count > VDSP_MAX_ALERTS else container_count
                container_count -= max_alerts

                alert_payload = self._get_alerts_payload(
                    start_time=start_time,
                    from_ingest_time=last_fetched_time,
                    threat_models=threat_model,
                    alert_severities=severity,
                    alert_statuses=alert_status,
                    descending_order=False,
                )

                self.save_progress(f"Start ingesting data from {last_fetched_time}")
                ret_val, alert_results = self._make_search_call(action_result, query=alert_payload, count=max_alerts)

                if phantom.is_fail(ret_val):
                    self.save_progress("On poll Failed.")
                    return action_result.get_status()

                self.debug_print("Alert has results:", alert_results["hasResults"])

                if not alert_results["hasResults"]:
                    break

                self.debug_print("Request completed", ret_val)

                containers = list()
                alert_results = SearchAlertObjectMapper().map(alert_results)
                dict_events = None
                event_items = []

                if is_ingest_artifacts:
                    alert_ids = list(map(lambda x: x.ID, alert_results))
                    batch_size = VDSP_MAX_ALERTS

                    for batch_alert_ids in tools.batched(alert_ids, batch_size):
                        event_payload = self._get_alerted_events_payload(batch_alert_ids, descending_order=False)

                        ret_val, event_result = self._make_search_call(
                            action_result,
                            query=event_payload,
                            count=artifact_count * batch_size,
                        )

                        if phantom.is_fail(ret_val):
                            self.save_progress("On poll Failed while getting alerted events.")
                            return action_result.get_status()

                        event_items.extend(SearchEventObjectMapper().map(event_result))

                    dict_events = tools.group_by(event_items, key_func=lambda x: x.AlertId)

                for alert_res in alert_results:
                    ingest_time = alert_res.IngestTime
                    if not last_fetched_time or ingest_time > last_fetched_time:
                        last_fetched_time = ingest_time + timedelta(seconds=1)

                    container = self._create_container(alert_res)

                    if dict_events:
                        artifacts = list(map(self._create_artifact, dict_events[alert_res.ID]))
                        container["artifacts"] = artifacts

                    containers.append(container)

                self.save_progress(f"Prepare {len(containers)} to save.")
                ret_val, message, container_responses = self.save_containers(containers)

                for cr in container_responses:
                    self.save_progress("Save container returns, ret_val: {}, message: {}, id: {}".format(cr["success"], cr["message"], cr["id"]))

                if phantom.is_fail(ret_val):
                    self.save_progress(f"On poll Failed while saving containers. Message: {message}")
                    return action_result.get_status()

            self._state[VDSP_LAST_FETCH_TIME] = last_fetched_time.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
            action_result.update_summary({"alerts_count": len(alert_results)})

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, str(e))

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "get_alerts":
            ret_val = self._handle_get_alerts(param)

        elif action_id == "update_alert_status":
            ret_val = self._handle_update_alert_status(param)

        elif action_id == "close_alert":
            ret_val = self._handle_close_alert(param)

        elif action_id == "get_alerted_events":
            ret_val = self._handle_get_alerted_events(param)

        elif action_id == phantom.ACTION_ID_INGEST_ON_POLL:
            ret_val = self._on_poll(param)

        return ret_val

    def initialize(self):
        self._state = self.load_state()

        config = self.get_config()
        """
        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """

        self._base_url = config.get(VDSP_JSON_BASE_URL_KEY)
        self._verify = config.get("verify_server_cert", False)
        self._session = requests.Session()

        try:
            method_whitelist = "allowed_methods" if hasattr(Retry.DEFAULT, "allowed_methods") else "method_whitelist"
            whitelist_kawargs = {method_whitelist: frozenset(["GET", "POST", "PUT"])}
            retry = Retry(
                total=REQUEST_RETRIES,
                read=REQUEST_RETRIES,
                connect=REQUEST_RETRIES,
                status=REQUEST_RETRIES,
                status_forcelist=HTTP_STATUS_WHITE_LIST,
                raise_on_status=False,
                raise_on_redirect=False,
                **whitelist_kawargs,  # type: ignore[arg-type]
            )
            http_adapter = HTTPAdapter(max_retries=retry)

            self._session.mount("https://", http_adapter)

        except NameError:
            pass

        api_key = config.get(VDSP_SCRT)

        try:
            state = self._state.get(VDSP_EXPIRES_IN_KEY, -1)
            if state < int(time.time()):
                self._authorize(api_key)

            self._headers = {"Authorization": f"{self._state[VDSP_TOKEN_TYPE_KEY]} {self._state[VDSP_ACCESS_TOKEN_KEY]}"}
        except Exception as e:
            self.error_print("Authorization", e)
            return phantom.APP_ERROR

        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS


# MAIN FUNCTION
def main():
    import argparse

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument(
        "-v",
        "--verify",
        action="store_true",
        help="verify",
        required=False,
        default=False,
    )

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password
    verify = args.verify

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = VaronisSaasConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=VDSP_DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(
                login_url,
                verify=verify,
                data=data,
                headers=headers,
                timeout=VDSP_DEFAULT_TIMEOUT,
            )
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print(f"Unable to get session id from the platform. Error: {e!s}")
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = VaronisSaasConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
