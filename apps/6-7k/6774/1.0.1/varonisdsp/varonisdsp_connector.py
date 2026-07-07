# File: varonisdsp_connector.py
#
# Copyright (c) Varonis, 2023
#
# This unpublished material is proprietary to Varonis DSP. All
# rights reserved. The methods and techniques described herein are
# considered trade secrets and/or confidential. Reproduction or
# distribution, in whole or in part, is forbidden except by express
# written permission of Varonis DSP.
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

# Python 3 Compatibility imports
from __future__ import print_function, unicode_literals

import json
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from requests.models import Response
from requests_ntlm import HttpNtlmAuth

import varonisdsp_tools as tools
from varonisdsp_consts import *

VDSP_NON_EXISTENT_SID = -1000
VDSP_ALERT_STATUSES = {'open': 1, 'under investigation': 2, 'closed': 3}
VDSP_ALERT_SEVERITIES = ['high', 'medium', 'low']
VDSP_CLOSE_REASONS = {
    'none': 0,
    'resolved': 1,
    'misconfiguration': 2,
    'threat model disabled or deleted': 3,
    'account misclassification': 4,
    'legitimate activity': 5,
    'other': 6
}


class RetVal(tuple):

    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class VaronisDSPConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(VaronisDSPConnector, self).__init__()

        self._state: Dict[str, Any] = None
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
            action_result.set_status(
                phantom.APP_ERROR,
                "Empty response and no information in the header"),
            None)

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split('\n')
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = '\n'.join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = "Status Code: {0}. Data from server:\n{1}\n".format(
            status_code, error_text)

        message = message.replace(u'{', '{{').replace(u'}', '}}')
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    "Unable to parse JSON response. Error: {0}".format(str(e))),
                None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(
            r.status_code,
            r.text.replace(u'{', '{{').replace(u'}', '}}'))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, 'add_debug_data'):
            action_result.add_debug_data({'r_status_code': r.status_code})
            action_result.add_debug_data({'r_text': r.text})
            action_result.add_debug_data({'r_headers': r.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if 'json' in r.headers.get('Content-Type', ''):
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if 'html' in r.headers.get('Content-Type', ''):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text or 'text' in r.headers.get('Content-Type', ''):
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
            r.status_code,
            r.text.replace('{', '{{').replace('}', '}}'))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _http_request(self,
                      url_suffix='',
                      method='GET',
                      full_url=None,
                      headers=None,
                      auth=None,
                      params=None,
                      data=None,
                      timeout=VDSP_REQUEST_TIMEOUT,
                      **kwargs) -> Response:

        address = full_url if full_url else tools.urljoin(self._base_url, url_suffix)
        headers = headers if headers else self._headers

        resp = self._session.request(method,
                                     address,
                                     verify=self._verify,
                                     params=params,
                                     data=data,
                                     headers=headers,
                                     auth=auth,
                                     timeout=timeout,
                                     **kwargs)
        return resp

    def _make_rest_call(self,
                        action_result,
                        url_suffix='',
                        method='GET',
                        full_url=None,
                        headers=None,
                        auth=None,
                        params=None,
                        data=None,
                        json=None,
                        timeout=VDSP_REQUEST_TIMEOUT,
                        **kwargs):
        try:
            resp = self._http_request(url_suffix=url_suffix,
                                      method=method,
                                      full_url=full_url,
                                      headers=headers,
                                      auth=auth,
                                      params=params,
                                      data=data,
                                      json=json,
                                      timeout=timeout,
                                      **kwargs)
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    "Error Connecting to server. Details: {0}".format(str(e))),
                None)

        return self._process_response(resp, action_result)

    def _authorize(self, username: str, password: str, url: str) -> Dict[str, Any]:
        response = self._http_request(url)
        response = response.json()
        auth_endpoint = response['authEndpoint']

        ntlm = HttpNtlmAuth(username, password)
        response = self._http_request(method='POST',
                                      full_url=auth_endpoint,
                                      auth=ntlm,
                                      data=VDSP_AUTH_DATA)
        response = response.json()

        self._state[VDSP_ACCESS_TOKEN_KEY] = response[VDSP_ACCESS_TOKEN_KEY]
        self._state[VDSP_TOKEN_TYPE_KEY] = response[VDSP_TOKEN_TYPE_KEY]
        self._state[VDSP_EXPIRES_IN_KEY] = int(
            time.time()) + response[VDSP_EXPIRES_IN_KEY] - VDSP_REQUEST_TIMEOUT

        self.debug_print("Expiration time", self._state[VDSP_EXPIRES_IN_KEY])
        return response

    def _get_users(self, search_string: str) -> List[Any]:
        """Search users by search string

        :type search_string: ``str``
        :param search_string: search string

        :return: The list of users
        :rtype: ``Dict[str, Any]``
        """
        request_params: Dict[str, Any] = {}
        request_params['columns'] = "['SamAccountName','Email','DomainName','ObjName']"
        request_params['searchString'] = search_string
        request_params['limit'] = 1000

        response = self._http_request('api/userdata/users', params=request_params)
        response = response.json()

        return response['ResultSet']

    def _get_sids(self, values: List[str], user_domain_name: Optional[str], key: str) -> List[int]:
        """Return list of user ids

        :type values: ``List[str]``
        :param values: A list of user names

        :type user_domain_name: ``str``
        :param user_domain_name: User domain name

        :type key: ``str``
        :param key: Display name

        :return: List of user ids
        :rtype: ``List[int]``
        """
        sidIds: List[int] = []

        if not values:
            return sidIds

        for value in values:
            users = self._get_users(value)

            for user in users:
                if tools.strEqual(user[key], value):
                    if (not user_domain_name or tools.strEqual(user['DomainName'], user_domain_name)):
                        sidIds.append(user['Id'])

        if len(sidIds) == 0:
            sidIds.append(VDSP_NON_EXISTENT_SID)

        return sidIds

    def _get_sids_by_user_name(self, user_names: List[str],
                               user_domain_name: str) -> List[int]:
        """Return list of user ids

        :type user_names: ``List[str]``
        :param user_names: A list of user names

        :type user_domain_name: ``str``
        :param user_domain_name: User domain name

        :return: List of user ids
        :rtype: ``List[int]``
        """
        return self._get_sids(user_names, user_domain_name, VDSP_DISPLAY_NAME_KEY)

    def _get_sids_by_sam(self, sam_account_names: List[str]) -> List[int]:
        """Return list of user ids

        :type sam_account_names: ``List[str]``
        :param sam_account_names: A list of sam account names

        :return: List of user ids
        :rtype: ``List[int]``
        """
        return self._get_sids(sam_account_names, None, VDSP_SAM_ACCOUNT_NAME_KEY)

    def _get_sids_by_email(self, emails: List[str]) -> List[int]:
        """Return list of user ids

        :type emails: ``List[str]``
        :param emails: A list of emails

        :return: List of user ids
        :rtype: ``List[int]``
        """
        return self._get_sids(emails, None, VDSP_EMAIL_KEY)

    def _get_alerts_params(self, threat_models: Optional[List[str]] = None,
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           device_names: Optional[List[str]] = None,
                           last_days: Optional[int] = None,
                           sid_ids: Optional[List[int]] = None,
                           from_alert_id: Optional[int] = None,
                           alert_statuses: Optional[List[str]] = None,
                           alert_severities: Optional[List[str]] = None,
                           aggregate: bool = False,
                           count: int = VDSP_MAX_ALERTS,
                           page: int = 1,
                           descending_order: bool = True) -> Dict[str, Any]:
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

        :type sid_ids: ``Optional[List[int]]``
        :param sid_ids: List of user ids

        :type from_alert_id: ``Optional[int]``
        :param from_alert_id: Alert id to fetch from

        :type alert_statuses: ``Optional[List[str]]``
        :param alert_statuses: List of alert statuses to filter by

        :type alert_severities: ``Optional[List[str]]``
        :param alert_severities: List of alert severities to filter by

        :type aggregate: ``bool``
        :param aggregate: Indicated whether agregate alert by alert id

        :type count: ``int``
        :param count: Alerts count

        :type page: ``int``
        :param page: Page number

        :type descendingOrder: ``bool``
        :param descendingOrder: Indicates whether alerts should be ordered in newest to oldest order

        :return: Parameters to be used in get alerts handler
        :rtype: ``Dict[str, Any]``
        """
        request_params: Dict[str, Any] = {}

        if threat_models and len(threat_models) > 0:
            request_params['ruleName'] = threat_models

        if start_time:
            request_params['startTime'] = start_time.isoformat()

        if end_time:
            request_params['endTime'] = end_time.isoformat()

        if device_names and len(device_names) > 0:
            request_params['deviceName'] = device_names

        if last_days:
            request_params['lastDays'] = last_days

        if sid_ids and len(sid_ids) > 0:
            request_params['sidId'] = sid_ids

        if from_alert_id is not None:
            request_params['fromAlertSeqId'] = from_alert_id

        if alert_statuses and len(alert_statuses) > 0:
            request_params['status'] = alert_statuses

        if alert_severities and len(alert_severities) > 0:
            request_params['severity'] = alert_severities

        request_params['descendingOrder'] = descending_order

        request_params['aggregate'] = aggregate
        request_params['offset'] = (page - 1) * count
        request_params['maxResult'] = count

        return request_params

    def _update_alert_status(self, action_result, query: Dict[str,
                                                              Any]) -> bool:
        """Update alert status

        :type query: ``Dict[str, Any]``
        :param query: Update request body

        :return: Result of execution
        :rtype: ``bool``

        """
        return self._make_rest_call(action_result,
                                    VDSP_UPDATE_ALET_STATUS_ENDPOINT,
                                    method='POST',
                                    json=query)

    def _get_alerted_events_params(self, alert_id: str, page: int, count: int, descending_order=True):
        request_params: Dict[str, Any] = {}
        request_params['alertId'] = tools.try_convert(alert_id, lambda x: tools.argToList(x))
        request_params['maxResults'] = count
        request_params['offset'] = (page - 1) * count
        request_params['descendingOrder'] = descending_order
        return request_params

    def _create_container(self, data: Dict[str, Any]):
        container = dict()
        container['name'] = data['Name']
        container['source_data_identifier'] = data['ID']
        container['status'] = data['Status']
        container['severity'] = data['Severity']
        container['start_time'] = f"{data['EventUTC']}Z"
        container['data'] = data
        return container

    def _create_artifact(self, data: Dict[str, Any]):
        artifact = dict()
        utc_time = datetime.strptime(data['UTCTime'], '%Y-%m-%dT%H:%M:%S%z') \
                    .replace(tzinfo=timezone.utc) \
                    .strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        artifact['name'] = data['Description']
        artifact['label'] = 'event'
        artifact['source_data_identifier'] = data['ID']
        artifact['start_time'] = utc_time
        artifact['type'] = data['Type']
        artifact['data'] = data
        return artifact

    # HANDLERS
    def _handle_test_connectivity(self, param):

        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Connecting to endpoint")

        # make rest call
        ret_val, _ = self._make_rest_call(action_result,
                                          '/api/entitymodel/enum/5821')

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_alerts(self, param):
        self.save_progress("In action handler for: {0}".format(
            self.get_action_identifier()))

        action_result = self.add_action_result(ActionResult(dict(param)))

        threat_model_names = param.get('threat_model_name', None)
        page = param.get('page', 1)
        max_results = param.get('max_results', VDSP_MAX_ALERTS)
        start_time = param.get('start_time', None)
        end_time = param.get('end_time', None)
        alert_statuses = param.get('alert_status', None)
        alert_severities = param.get('alert_severity', None)
        device_names = param.get('device_name', None)
        user_domain_name = param.get('user_domain_name', None)
        user_names = param.get('user_name', None)
        sam_account_names = param.get('sam_account_name', None)
        emails = param.get('email', None)
        last_days = param.get('last_days', None)
        descending_order = param.get('descending_order', True)

        try:
            user_names = tools.try_convert(user_names, lambda x: tools.argToList(x))
            sam_account_names = tools.try_convert(sam_account_names,
                                            lambda x: tools.argToList(x))
            emails = tools.try_convert(emails, lambda x: tools.argToList(x))

            if last_days:
                last_days = tools.try_convert(
                    last_days, lambda x: int(x),
                    ValueError(
                        f'last_days should be integer, but it is {last_days}.')
                )

                if last_days <= 0:
                    raise ValueError('last_days cannot be less then 1')

            if user_domain_name and (not user_names or len(user_names) == 0):
                raise ValueError(
                    'user_domain_name cannot be provided without user_name')

            if user_names and len(user_names) > VDSP_MAX_USERS_TO_SEARCH:
                raise ValueError(
                    f'cannot provide more then {VDSP_MAX_USERS_TO_SEARCH} users'
                )

            if sam_account_names and len(sam_account_names) > VDSP_MAX_USERS_TO_SEARCH:
                raise ValueError(
                    f'cannot provide more then {VDSP_MAX_USERS_TO_SEARCH} sam account names'
                )

            if emails and len(emails) > VDSP_MAX_USERS_TO_SEARCH:
                raise ValueError(
                    f'cannot provide more then {VDSP_MAX_USERS_TO_SEARCH} emails'
                )

            alert_severities = tools.try_convert(alert_severities,
                                           lambda x: tools.argToList(x))
            device_names = tools.try_convert(device_names, lambda x: tools.argToList(x))
            threat_model_names = tools.try_convert(threat_model_names,
                                             lambda x: tools.argToList(x))
            max_results = tools.try_convert(
                max_results, lambda x: int(x),
                ValueError(f'max_results should be integer, but it is {max_results}.')
            )
            start_time = tools.try_convert(
                start_time, lambda x: datetime.fromisoformat(x),
                ValueError(
                    f'start_time should be in iso format, but it is {start_time}.'
                ))
            end_time = tools.try_convert(
                end_time, lambda x: datetime.fromisoformat(x),
                ValueError(
                    f'end_time should be in iso format, but it is {start_time}.'
                ))

            alert_statuses = tools.try_convert(alert_statuses, lambda x: tools.argToList(x))
            page = tools.try_convert(
                page, lambda x: int(x),
                ValueError(f'page should be integer, but it is {page}.'))

            sid_ids = self._get_sids_by_email(emails) + self._get_sids_by_sam(sam_account_names) + \
                self._get_sids_by_user_name(user_names, user_domain_name)

            if alert_severities:
                for severity in alert_severities:
                    if severity.lower() not in VDSP_ALERT_SEVERITIES:
                        raise ValueError(f'There is no severity {severity}. Posible severities: {VDSP_ALERT_SEVERITIES}')

            if alert_statuses:
                for status in alert_statuses:
                    if status.lower() not in VDSP_ALERT_STATUSES.keys():
                        raise ValueError(f'There is no status {severity}.')

            alert_params = self._get_alerts_params(
                threat_model_names, start_time, end_time, device_names,
                last_days, sid_ids, None, alert_statuses, alert_severities,
                False, max_results, page, descending_order)

            self.debug_print('Params completed', alert_params)

            ret_val, results = self._make_rest_call(
                action_result,
                VDSP_GET_ALERTS_ENDPOINT,
                params=alert_params)

            self.debug_print('Request completed', ret_val)

            if phantom.is_fail(ret_val):
                self.error_print("Get alerts failed.")
                return action_result.get_status()

            for res in results:
                action_result.add_data(res)

            action_result.update_summary({'alerts_count': len(results)})
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, str(e))

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_alert_status(self, param):
        self.save_progress("In action handler for: {0}".format(
            self.get_action_identifier()))

        action_result = self.add_action_result(ActionResult(dict(param)))
        try:
            status = param['status']
            alert_id = param['alert_id']

            statuses = list(
                filter(lambda name: name != 'closed', VDSP_ALERT_STATUSES.keys()))
            if status.lower() not in statuses:
                raise ValueError(f'status must be one of {statuses}.')

            status_id = VDSP_ALERT_STATUSES[status.lower()]

            query: Dict[str, Any] = {
                'AlertGuids': tools.try_convert(alert_id, lambda x: tools.argToList(x)),
                'closeReasonId': VDSP_CLOSE_REASONS['none'],
                'statusId': status_id
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
        self.save_progress("In action handler for: {0}".format(
            self.get_action_identifier()))

        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            alert_id = param['alert_id']
            close_reason = param['close_reason']

            close_reasons = list(
                filter(lambda name: not tools.strEqual(name, 'none'),
                    VDSP_CLOSE_REASONS.keys()))
            if close_reason.lower() not in close_reasons:
                raise ValueError(f'close reason must be one of {close_reasons}')

            alert_ids = tools.try_convert(alert_id, lambda x: tools.argToList(x))
            close_reason_id = VDSP_CLOSE_REASONS[close_reason.lower()]

            if len(alert_ids) == 0:
                raise ValueError('alert id(s) not specified')

            query: Dict[str, Any] = {
                'AlertGuids': alert_ids,
                'closeReasonId': close_reason_id,
                'statusId': VDSP_ALERT_STATUSES['closed']
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
        self.save_progress("In action handler for: {0}".format(
            self.get_action_identifier()))

        action_result = self.add_action_result(ActionResult(dict(param)))
        try:
            alert_id = param['alert_id']
            page = param.get('page', 1)
            count = param.get('max_results', VDSP_MAX_ALERTED_EVENTS)
            descending_order = param.get('descending_order', True)

            count = tools.try_convert(
                count, lambda x: int(x),
                ValueError(f'max_results should be integer, but it is {count}.'))

            page = tools.try_convert(
                page, lambda x: int(x),
                ValueError(f'page should be integer, but it is {page}.'))

            request_params = self._get_alerted_events_params(alert_id, page, count, descending_order)

            ret_val, results = self._make_rest_call(
                action_result,
                VDSP_GET_ALERTED_EVENTS_ENDPOINT,
                params=request_params)

            if phantom.is_fail(ret_val):
                self.error_print("Get alerted events failed.")
                return action_result.get_status()

            for res in results:
                action_result.add_data(res)

            action_result.update_summary({'events_count': len(results)})
        except Exception as ex:
            action_result.set_status(phantom.APP_ERROR, str(ex))

        return action_result.set_status(phantom.APP_SUCCESS)

    def _on_poll(self, param):

        action_result = self.add_action_result(ActionResult(dict(param)))

        config = self.get_config()
        last_fetched_id = self._state.get(VDSP_LAST_FETCH_ID_KEY, 0)
        ingest_period = config.get(VDSP_INGEST_PERIOD_KEY, VDSP_DEFAULT_INGEST_PERIOD)
        is_ingest_artifacts = config.get(VDSP_INGEST_ARTIFACTS_KEY, False)

        try:
            container_count = param.get(phantom.APP_JSON_CONTAINER_COUNT, float('inf'))
            start_time = tools.arg_to_datetime(ingest_period)
            artifact_count = param.get(phantom.APP_JSON_ARTIFACT_COUNT, VDSP_MAX_ALERTED_EVENTS)
            alert_status = param.get('alert_status', None)
            threat_model = param.get('threat_model', None)
            severity = param.get('severity', None)

            self.save_progress(f'Start ingesting data for interval from {start_time}, amount {container_count}')

            while container_count > 0:
                max_alerts = VDSP_MAX_ALERTS if container_count > VDSP_MAX_ALERTS else container_count
                container_count -= max_alerts

                alert_params = self._get_alerts_params(
                    start_time=start_time,
                    from_alert_id=last_fetched_id,
                    count=max_alerts,
                    threat_models=threat_model,
                    alert_severities=severity,
                    alert_statuses=alert_status
                )

                self.debug_print('Params completed', alert_params)
                self.save_progress(f'Start ingesting data from {last_fetched_id}')
                ret_val, alert_results = self._make_rest_call(
                    action_result,
                    VDSP_GET_ALERTS_ENDPOINT,
                    params=alert_params
                )

                if not alert_results:
                    break

                self.debug_print('Request completed', ret_val)

                if phantom.is_fail(ret_val):
                    self.save_progress('On poll Failed.')
                    return action_result.get_status()

                containers = list()

                for alert_res in alert_results:
                    action_result.add_data(alert_res)

                    id = alert_res['AlertSeqId']
                    if not last_fetched_id or id > last_fetched_id:
                        last_fetched_id = id

                    container = self._create_container(alert_res)

                    if is_ingest_artifacts:
                        alert_id = alert_res['ID']
                        request_params = self._get_alerted_events_params(alert_id, 1, artifact_count)

                        ret_val, event_results = self._make_rest_call(
                            action_result,
                            VDSP_GET_ALERTED_EVENTS_ENDPOINT,
                            params=request_params
                        )

                        if phantom.is_fail(ret_val):
                            self.save_progress('On poll Failed while getting alerted events.')
                            return action_result.get_status()

                        action_result.add_data(event_results)

                        artifacts = list(map(self._create_artifact, event_results))
                        container['artifacts'] = artifacts

                    containers.append(container)

                self.save_progress(f'Prepare {len(containers)} to save.')
                ret_val, message, container_responses = self.save_containers(containers)

                for cr in container_responses:
                    self.save_progress('Save container returns, ret_val: {0}, message: {1}, id: {2}'
                        .format(cr['success'], cr['message'], cr['id']))

                if phantom.is_fail(ret_val):
                    self.save_progress(f'On poll Failed while saving containers. Message: {message}')
                    return action_result.get_status()

            self._state[VDSP_LAST_FETCH_ID_KEY] = last_fetched_id
            action_result.update_summary({'alerts_count': len(alert_results)})

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, str(e))

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)

        elif action_id == 'get_alerts':
            ret_val = self._handle_get_alerts(param)

        elif action_id == 'update_alert_status':
            ret_val = self._handle_update_alert_status(param)

        elif action_id == 'close_alert':
            ret_val = self._handle_close_alert(param)

        elif action_id == 'get_alerted_events':
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
        self._verify = config.get('verify_server_cert', False)
        self._session = requests.Session()

        password = config[phantom.APP_JSON_PASSWORD]
        username = config[phantom.APP_JSON_USERNAME]
        username = username.replace('/', '\\')
        try:
            state = self._state.get(VDSP_EXPIRES_IN_KEY, -1)
            if state < int(time.time()):
                self._authorize(username, password, '/auth/configuration')

            self._headers = {
                'Authorization':
                f'{self._state[VDSP_TOKEN_TYPE_KEY]} {self._state[VDSP_ACCESS_TOKEN_KEY]}'
            }
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

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)
    argparser.add_argument('-v', '--verify', action='store_true', help='verify', required=False, default=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password
    verify = args.verify

    if username is not None and password is None:

        # User specified a username but not a password, so ask
        import getpass
        password = getpass.getpass('Password: ')

    if username and password:
        try:
            login_url = VaronisDSPConnector._get_phantom_base_url() + '/login'

            print('Accessing the Login page')
            r = requests.get(login_url, verify=verify, timeout=DEFAULT_TIMEOUT)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken=' + csrftoken
            headers['Referer'] = login_url

            print('Logging into Platform to get the session id')
            r2 = requests.post(login_url,
                               verify=verify,
                               data=data,
                               headers=headers,
                               timeout=DEFAULT_TIMEOUT)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print(
                f'Unable to get session id from the platform. Error: {str(e)}')
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = VaronisDSPConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json['user_session_token'] = session_id
            connector._set_csrf_info(csrftoken, headers['Referer'])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == '__main__':
    main()
