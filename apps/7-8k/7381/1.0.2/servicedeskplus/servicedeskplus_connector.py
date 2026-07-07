# File: servicedeskplus_connector.py
#
# Copyright (c) Splunk Inc., 2024-2026
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
#
# Python 3 Compatibility imports

import ast
import json
from datetime import datetime, timedelta

import dateutil.parser

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
import servicedeskplus_consts as consts


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class ServicedeskplusConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None
        self._account_url = None
        self._onprem = False

    def _get_headers(self, token):
        return {"Authtoken": token}

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.

        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_message = consts.ERR_MSG_UNAVAILABLE

        self.error_print("Error occurred:", e)

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except Exception:
            pass

        if not error_code:
            error_text = f"Error Message: {error_message}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_message}"

        return error_text

    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
        """This method is to check if the provided input parameter value
        is a non-zero positive integer and returns the integer value of the parameter itself.
        :param action_result: Action result or BaseConnector object
        :param parameter: input parameter
        :param key: input parameter message key
        :allow_zero: whether zero should be considered as valid value or not
        :return: integer value of the parameter or None in case of failure
        """

        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, consts.SDP_VALID_INT_MSG.format(param=key)), None

                parameter = int(parameter)
            except:
                return action_result.set_status(phantom.APP_ERROR, consts.SDP_VALID_INT_MSG.format(param=key)), None

            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, consts.SDP_NON_NEG_INT_MSG.format(param=key)), None
            if not allow_zero and parameter == 0:
                return action_result.set_status(phantom.APP_ERROR, consts.SDP_NON_NEG_NON_ZERO_INT_MSG.format(param=key)), None

        return phantom.APP_SUCCESS, parameter

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, consts.SDP_ERR_EMPTY_RESPONSE.format(code=response.status_code)), None)

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            error_text = consts.SDP_ERR_UNABLE_TO_PARSE_HTML_RESPONSE.format(error=error_message)

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        status_code = r.status_code
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, consts.SDP_ERR_UNABLE_TO_PARSE_JSON_RESPONSE.format(error=error_message)), None
            )

        # Please specify the status codes here
        if 200 <= status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {} Data from server: {}".format(status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), resp_json)

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
        if not r.text:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        config = self.get_config()
        headers = self._get_headers(config.get("technician_key"))

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = self._base_url + endpoint

        try:
            r = request_func(
                url,
                # auth=(username, password),  # basic authentication
                verify=config.get("verify_server_cert", False),
                headers=headers,
                **kwargs,
            )
        except Exception as e:
            error_text = consts.SDP_EXCEPTION_ERR_MSG.format(
                msg=consts.SDP_ERR_CONNECTIVITY_FAILURE, error=self._get_error_message_from_exception(e)
            )
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_text), resp_json)

        return self._process_response(r, action_result)

    def format_params(self, name: str, value: str):
        if not value:
            return {}
        try:
            if value[0] == "{" and value[-1] == "}":  # check if the user entered a dict as the value
                return ast.literal_eval(value)

            fields = value.split(",")
            rval_dict = {}
            for field in fields:
                if field:
                    field_key_value = field.split(":")
                    if field_key_value[0] and field_key_value[1]:
                        rval_dict[field_key_value[0]] = field_key_value[1]
                    else:
                        raise Exception("Invalid input")
            return rval_dict
        except Exception:
            raise Exception(consts.SDP_ERR_ILLEGAL_FORMAT.format(name=name))

    def get_query_params(self, param):
        request_fields = {}
        for field in consts.REQUEST_FIELDS:
            value = param.get(field, None)
            if value:
                if field in ["udf_fields", "template"]:
                    request_fields[field] = f"{self.format_params(field, value)}"
                elif field not in consts.FIELDS_WITH_NAME or (value[0] == "{" and value[-1] == "}"):
                    request_fields[field] = value
                else:
                    request_fields[field] = {"name": value}
        return {"request": request_fields}

    def create_requests_list_info(self, start_index, row_count, search_fields, filter_by):
        list_info = {}
        if start_index is not None:
            list_info["start_index"] = start_index
        if row_count is not None:
            list_info["row_count"] = row_count
        if search_fields:
            list_info["search_fields"] = search_fields
        if filter_by:
            list_info["filter_by"] = filter_by
        list_info["sort_field"] = "created_time"
        list_info["sort_order"] = "asc"
        list_info["get_total_count"] = True
        return {"list_info": list_info}

    def _search_ticket_container(self, ticket):
        "Find the SOAR container corresponding to the servicedeskplus ticket"

        ticket_id = ticket[consts.SDP_TICKET_JSON_ID]

        url = f'{self.get_phantom_base_url()}rest/container?_filter_source_data_identifier="{ticket_id}"&_filter_asset={self.get_asset_id()}'
        try:
            r = requests.get(url, verify=False)
            resp_json = r.json()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.debug_print(consts.SDP_ERR_CONTAINERS_UNABLE.format(error={error_message}))
            return

        if resp_json.get("count", 0) <= 0:
            self.debug_print(consts.SDP_ERR_NO_CONTAINERS)
            return
        else:
            try:
                container_id = resp_json.get("data", [])[0]["id"]
                self.debug_print(consts.SDP_CONTAINER_FOUND_MSG.format(cid=container_id))
            except Exception as e:
                error_message = self._get_error_message_from_exception(e)
                self.debug_print(consts.SDP_ERR_CONTAINER_WRONG.format(error=error_message))
                return

            return container_id

    def _update_ticket_container(self, container_id, ticket):
        """Update an existing SOAR container with new ticket information"""

        updated_container = self._create_ticket_container_json(ticket)
        url = f"{self.get_phantom_base_url()}rest/container/{container_id}"

        try:
            requests.post(url, data=(json.dumps(updated_container)), verify=False)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.debug_print(consts.SDP_ERR_CONTAINER_UPDATE.format(err=error_message))

    def _create_ticket_artifacts(self, ticket, container_id):
        """Creates artifacts for a given container based on ticket information"""
        artifacts = []

        # if ticket["last_updated_time"] is None:
        #     ticket_updated_on = None
        # else:
        #     ticket_updated_on = ticket["last_updated_time"]["value"]

        ticket_artifact = {
            "container_id": container_id,
            "name": "ticket Artifact",
            "label": consts.SDP_TICKET_ARTIFACT_LABEL,
            "source_data_identifier": ticket[consts.SDP_TICKET_JSON_ID],
        }

        cef = ticket
        # NOTE Eventually refactor ticket JSON structure to have it cleaner
        for field in list(ticket):
            if isinstance(ticket[field], dict):
                if field in consts.FIELDS_WITH_NAME:
                    # self.save_progress(f"{ticket[field]}")
                    if ticket[field] is not None:
                        cef[field] = ticket[field]["name"]

        ticket_artifact["cef"] = cef

        artifacts.append(ticket_artifact)

        return artifacts

    def _gen_ticket_container_title(self, ticket):
        """Generate title for the new SOAR container based on ticket information"""

        primary = ticket[consts.SDP_TICKET_JSON_ID]
        secondary = ticket.get("subject")
        return f"{primary} - {secondary}"

    def _create_ticket_container_json(self, ticket):
        """Creates a new SOAR container based on ticket information"""
        ticket_container = {
            "name": self._gen_ticket_container_title(ticket),
            "label": self.get_config().get("ingest", {}).get("container_label"),
            "source_data_identifier": ticket[consts.SDP_TICKET_JSON_ID],
            "description": ticket["short_description"] if "short_description" in ticket else ticket["description"],
            "data": json.dumps(ticket),
        }
        return ticket_container

    def _save_ticket_container(self, action_result, ticket):
        """
        Save a ticket retrieved from ManageEngine to a corresponding SOAR container.
        If a container already exists, it is updated.
        """

        container_id = self._search_ticket_container(ticket)

        if container_id:
            self.debug_print(consts.SDP_CONTAINER_UPDATE_MSG)
            ret_val = self._update_ticket_container(container_id, ticket)
            ticket_artifacts = self._create_ticket_artifacts(ticket, container_id)
            self.save_artifacts(ticket_artifacts)

        ticket_container = self._create_ticket_container_json(ticket)
        ret_val, message, container_id = self.save_container(ticket_container)

        if not ret_val:
            self.debug_print(consts.SDP_ERR_CONTAINER_FAILURE)
            return RetVal(phantom.APP_ERROR)
        else:
            ticket_artifacts = self._create_ticket_artifacts(ticket, container_id)
            self.debug_print(len(ticket_artifacts))
            self.save_artifacts(ticket_artifacts)
            return RetVal(phantom.APP_SUCCESS)

    def _get_ticket_last_updated_time(self, action_result, ticket_id):
        """Retrieves the last updated time of a single ticket"""
        search_criteria = [{"field": "id", "value": f"{ticket_id}", "condition": "eq"}]

        list_info = {"list_info": {"search_criteria": search_criteria, "fields_required": ["last_updated_time"]}}

        params = {"input_data": f"{list_info}"}

        self.debug_print(f"Parameters {params}")

        # make rest call
        ret_val, response = self._make_rest_call(consts.API_GET_REQUESTS, action_result, params=params)

        if phantom.is_fail(ret_val) or "requests" not in response:
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            action_result_message = action_result.get_message()
            if action_result_message:
                message = f"{consts.SDP_ERR_RETRIEVE_TICKETS}. {action_result_message}"
            else:
                message = consts.SDP_ERR_RETRIEVE_TICKETS
            return RetVal(action_result.set_status(phantom.APP_ERROR, message), response)

        return ret_val, response["requests"]

    def _make_paginated_call(self, endpoint, action_result, list_info, limit=-1):
        results_list = []
        next_index = 1

        while True:
            if next_index > 1:
                list_info[consts.SDP_JSON_LIST_INFO]["start_index"] = next_index

            params = {"input_data": f"{list_info}"}

            self.debug_print(f"Parameters {params}")

            ret_val, res_json = self._make_rest_call(endpoint, action_result, params=params)

            if phantom.is_fail(ret_val):
                return action_result.get_status(), res_json

            if consts.SDP_JSON_LIST_INFO not in res_json:
                raise Exception(consts.SDP_ERR_NO_VALUE.format(value=consts.SDP_JSON_LIST_INFO))

            for entry in res_json["requests"]:
                results_list.append(entry)

            if int(limit) > 0:
                if int(limit) < len(results_list):
                    results_list = results_list[:limit]
                break

            if not res_json[consts.SDP_JSON_LIST_INFO].get("has_more_rows"):
                # No more rows left
                break

            next_index += res_json[consts.SDP_JSON_LIST_INFO]["row_count"]

        return phantom.APP_SUCCESS, results_list

    def _retrieve_tickets(self, action_result, since, limit):
        """Retrieves tickets from ServiceDeskPlus that recently have been updated"""
        time_from = since.strftime("%s")

        search_criteria = [
            {"field": "last_updated_time", "value": f"{time_from}", "condition": "gte"},
            {"field": "created_time", "condition": "gte", "value": f"{time_from}", "logical_operator": "OR"},
        ]

        list_info = {
            "list_info": {
                "search_criteria": search_criteria,
                "sort_field": "created_time",
                "sort_order": "asc",
            }
        }

        # make rest call
        ret_val, requests = self._make_paginated_call(consts.API_GET_REQUESTS, action_result, list_info, limit)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            action_result_message = action_result.get_message()
            if action_result_message:
                message = f"{consts.SDP_ERR_RETRIEVE_TICKETS}. {action_result_message}"
            else:
                message = consts.SDP_ERR_RETRIEVE_TICKETS
            return RetVal(action_result.set_status(phantom.APP_ERROR, message), requests)

        self.save_progress(consts.SDP_SUCCESS_MSG)

        return ret_val, requests

    def _handle_list_tickets(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        start_index = param.get("start_index", None)
        row_count = param.get("row_count", None)
        search_fields = param.get("search_fields", None)
        filter_by = param.get("filter_by", None)
        list_info = self.create_requests_list_info(start_index, row_count, search_fields, filter_by)

        try:
            # make rest call
            ret_val, requests = self._make_paginated_call(consts.API_GET_REQUESTS, action_result, list_info)
            if phantom.is_fail(ret_val):
                # the call to the 3rd party device or service failed, action result should contain all the error details
                # for now the return is commented out, but after implementation, return from here
                self.save_progress(f"Error {action_result.get_message()}")
                return action_result.get_status()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.debug_print(consts.SDP_ERR_FETCHING_TICKETS.format(error=error_message))
            return action_result.set_status(phantom.APP_ERROR, consts.SDP_ERR_FETCHING_TICKETS.format(error=error_message))

        self.save_progress(consts.SDP_SUCCESS_MSG)

        for request in requests:
            action_result.add_data(request)

        summary = action_result.set_summary({})
        summary["num_tickets"] = len(requests)

        # Return success
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_ticket(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        request_id = param.get("request_id")

        query = self.get_query_params(json.loads(param["fields"]))
        data = {"input_data": f"{query}"}

        # make rest call
        ret_val, response = self._make_rest_call(f"{consts.API_GET_REQUESTS}/{request_id}", action_result, data=data, method="put")

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress(f"Error {action_result.get_message()}")
            return action_result.get_status()

        self.save_progress(consts.SDP_SUCCESS_MSG)

        # Add the response into the data section
        action_result.add_data(response["request"])
        action_result.set_summary({})

        return action_result.set_status(phantom.APP_SUCCESS, consts.SDP_SUCCESS_UPDATE_MSG)

    def _handle_create_ticket(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        request_fields = json.loads(param["fields"])

        query = self.get_query_params(request_fields)
        data = {"input_data": f"{query}"}

        # make rest call
        ret_val, response = self._make_rest_call(consts.API_GET_REQUESTS, action_result, data=data, method="post")

        # Add the response into the data section
        action_result.add_data(response)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress(f"Error {action_result.get_message()}")
            return action_result.get_status()

        self.save_progress(consts.SDP_SUCCESS_MSG)

        request_id = response["request"]["id"]
        self.save_progress(f"Created request with id {request_id}")

        summary = action_result.set_summary({})
        summary["new_request_id"] = request_id

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully created ticket {request_id}")

    def _handle_delete_ticket(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        request_id = param.get("request_id")

        # NOTE URL changes for Cloud data centres
        delete_endpoint = consts.API_DELETE_ENDPOINT["onprem"] if self._onprem else consts.API_DELETE_ENDPOINT["cloud"]
        url = f"{consts.API_GET_REQUESTS}/{request_id}{delete_endpoint}"

        # make rest call
        ret_val, response = self._make_rest_call(url, action_result, method="delete")

        # Add the response into the data section
        action_result.add_data(response)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress(f"Error {action_result.get_message()}")
            return action_result.get_status()

        self.save_progress(consts.SDP_SUCCESS_MSG)

        action_result.set_summary({})

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully deleted ticket")

    def _handle_assign_ticket(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        request_id = param.get("request_id")
        request_fields = json.loads(param["fields"])

        # NOTE URL changes for Cloud data centres
        assign_endpoint = consts.API_ASSIGN_ENDPOINT["onprem"] if self._onprem else consts.API_ASSIGN_ENDPOINT["cloud"]
        url = f"{consts.API_GET_REQUESTS}/{request_id}/{assign_endpoint}"

        query = self.get_query_params(request_fields)
        data = {"input_data": f"{query}"}

        # make rest call
        ret_val, response = self._make_rest_call(url, action_result, method="put", data=data)

        response_status = response["response_status"]
        # Add the response into the data section
        action_result.add_data(response_status)
        action_result.set_summary({})

        if phantom.is_fail(ret_val):
            message = response_status["messages"][0]
            msg = f"'{message['field']}' value does not exist or not in use or user cannot set the value" if "field" in message else ""
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress(f"{action_result.get_message()}")
            self.save_progress(f"Error details: {msg}")
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully assigned ticket")

    def _handle_close_ticket(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        request_id = param.get("request_id")
        input_data = {
            "request": {
                "closure_info": {
                    "requester_ack_resolution": param.get("requester_ack_resolution", False),
                    "requester_ack_comments": param.get("requester_ack_comments", ""),
                    "closure_comments": param.get("closure_comments", ""),
                }
            }
        }

        if param.get("closure_code"):
            input_data["request"]["closure_info"]["closure_code"] = {"name": param.get("code")}

        # NOTE URL changes for Cloud data centres
        close_endpoint = consts.API_CLOSE_ENDPOINT["onprem"] if self._onprem else consts.API_CLOSE_ENDPOINT["cloud"]
        url = f"{consts.API_GET_REQUESTS}/{request_id}/{close_endpoint}"

        data = {"input_data": f"{input_data}"}

        self.save_progress(f"{data}")

        # make rest call
        ret_val, response = self._make_rest_call(url, action_result, method="put", data=data)

        response_status = response["response_status"]
        # Add the response into the data section
        action_result.add_data(response_status)
        action_result.set_summary({})

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress(f"Error {action_result.get_message()}")
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully closed ticket")

    def _handle_list_linked_tickets(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        request_id = param.get("request_id")

        # make rest call
        ret_val, response = self._make_rest_call(f"{consts.API_GET_REQUESTS}/{request_id}/link_requests", action_result)

        # Add the response into the data section
        action_result.add_data(response)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress(f"Error {action_result.get_message()}")
            return action_result.get_status()

        self.save_progress(consts.SDP_SUCCESS_MSG)

        summary = action_result.set_summary({})
        summary["num_linked_tickets"] = len(response["link_requests"])

        return action_result.set_status(
            phantom.APP_SUCCESS, f"Successfully fetched [{summary['num_linked_tickets']}] tickets linked to ticket [{request_id}]"
        )

    def _handle_get_ticket_resolution(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        request_id = param.get("request_id")

        # make rest call
        ret_val, response = self._make_rest_call(f"{consts.API_GET_REQUESTS}/{request_id}/resolutions", action_result)

        # Add the response into the data section
        action_result.add_data(response)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress(f"Error {action_result.get_message()}")
            return action_result.get_status()

        self.save_progress(consts.SDP_SUCCESS_MSG)

        action_result.set_summary({})

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully fetched resolution for ticket [{request_id}]")

    def _handle_set_ticket_resolution(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        request_id = param.get("request_id")
        query = {"resolution": {"content": param.get("content"), "add_to_linked_requests": param.get("add_to_linked_requests", False)}}
        data = {"input_data": f"{query}"}

        # make rest call
        ret_val, response = self._make_rest_call(f"{consts.API_GET_REQUESTS}/{request_id}/resolutions", action_result, method="post", data=data)

        # Add the response into the data section
        action_result.add_data(response)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress(f"Error {action_result.get_message()}")
            return action_result.get_status()

        self.save_progress(consts.SDP_SUCCESS_MSG)

        action_result.set_summary({})

        return action_result.set_status(phantom.APP_SUCCESS, f"Successfully added a resolution for ticket [{request_id}]")

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # NOTE: test connectivity does _NOT_ take any parameters
        # i.e. the param dictionary passed to this handler will be empty.
        # Also typically it does not add any data into an action_result either.
        # The status and progress messages are more important.

        self.save_progress("Connecting to endpoint")
        # make rest call
        ret_val, response = self._make_rest_call(consts.API_GET_REQUESTS, action_result, params=None)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _on_poll(self, param):
        """
        Keep phantom containers up-to-date with data from servicedeskplus
        """

        # Add action result
        action_result = self.add_action_result(phantom.ActionResult(dict(param)))

        last_run = self._state.get("last_run")
        max_tickets = 100
        backfill = datetime.now() - timedelta(consts.SDP_BACKFILL_DAYS)

        if self.is_poll_now():
            self.debug_print("Run Mode: Poll Now")
            self.save_progress("Run Mode: Poll Now")

            # Integer validation for 'maximum containers' configuration parameter
            max_tickets = param[phantom.APP_JSON_CONTAINER_COUNT]
            ret_val, max_tickets = self._validate_integer(action_result, max_tickets, consts.SDP_CONTAINER_COUNT_KEY)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            last_run = backfill
        else:
            if not last_run:
                self.debug_print("Run Mode: First Scheduled Poll")
                last_run = backfill
            else:
                self.debug_print("Run Mode: Scheduled Poll")
                last_run = dateutil.parser.isoparse(last_run)

        self.debug_print(f"Last Run: {last_run}")
        self.save_progress(f"Last Run: {last_run}")

        tickets = []
        try:
            ret_val, tickets = self._retrieve_tickets(action_result, last_run, max_tickets)
            if phantom.is_fail(ret_val):
                self.debug_print(consts.SDP_ERR_FETCHING_TICKETS.format(error=action_result.get_message()))
                return action_result.get_status()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.debug_print(consts.SDP_ERR_FETCHING_TICKETS.format(error=error_message))
            return action_result.set_status(phantom.APP_ERROR, consts.SDP_ERR_FETCHING_TICKETS.format(error=error_message))

        self.debug_print(f"Total tickets fetched: {len(tickets)}")
        self.save_progress(f"Total tickets fetched: {len(tickets)}")
        for ticket in tickets:
            # Adding info about ticket last updated time.
            # This info is surprisingly not automatically returned by the API
            try:
                ret_val, last_updated_on = self._get_ticket_last_updated_time(action_result, ticket["id"])
                if phantom.is_fail(ret_val):
                    return action_result.get_status()
            except Exception as e:
                error_message = self._get_error_message_from_exception(e)
                return action_result.set_status(
                    phantom.APP_ERROR, consts.SDP_ERR_FETCHING_TICKET.format(error=error_message, ticket_id=ticket["id"])
                )
            ticket["last_updated_time"] = last_updated_on[0]["last_updated_time"]
            self._save_ticket_container(action_result, ticket)

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)
        elif action_id == "update_ticket":
            ret_val = self._handle_update_ticket(param)
        elif action_id == "create_ticket":
            ret_val = self._handle_create_ticket(param)
        elif action_id == "delete_ticket":
            ret_val = self._handle_delete_ticket(param)
        elif action_id == "list_tickets":
            ret_val = self._handle_list_tickets(param)
        elif action_id == "list_linked_tickets":
            ret_val = self._handle_list_linked_tickets(param)
        elif action_id == "assign_ticket":
            ret_val = self._handle_assign_ticket(param)
        elif action_id == "close_ticket":
            ret_val = self._handle_close_ticket(param)
        elif action_id == "get_ticket_resolution":
            ret_val = self._handle_get_ticket_resolution(param)
        elif action_id == "set_ticket_resolution":
            ret_val = self._handle_set_ticket_resolution(param)
        elif action_id == "on_poll":
            ret_val = self._on_poll(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()
        """
        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """

        self._base_url = config.get("base_url")

        data_centre = config.get("data_centre")
        if data_centre == "On-Premises":
            self._onprem = True

            if not self._base_url:
                return self.set_status(phantom.APP_ERROR, consts.SDP_ERR_INVALID_CONFIGURATION)

            if self._base_url.endswith("/"):
                self._base_url = self._base_url[:-1]

        else:
            return self.set_status(phantom.APP_ERROR, consts.SDP_ERR_NOT_IMPLEMENTED)
            # self._base_url = consts.SDP_DATA_CENTERS[data_centre]['base_url']
            # self._account_url = consts.SDP_DATA_CENTERS[data_centre]['oauth']

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        new_state = {"last_run": datetime.now().isoformat()}
        self.save_state(new_state)
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
            login_url = ServicedeskplusConnector._get_phantom_base_url() + "/login"

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

        connector = ServicedeskplusConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)


if __name__ == "__main__":
    main()
