# File: xmatters_connector.py
# Copyright (c) 2017-2025 Splunk Inc.
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
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

# Phantom Imports
import phantom.app as phantom

# Generic Imports
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Const Imports
from xmatters_consts import *


APP_PARAM_TO_API_PARAM_MAP = {
    "property_name": "propertyName",
    "property_value": "propertyValue",
}

DECODE_JSON_PARAMETERS = ["properties", "responses", "callbacks", "conferences"]

DT_STR_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class UnauthorizedOAuthTokenException(Exception):
    pass


class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class XMattersConnector(BaseConnector):
    ACTION_ID_LIST_EVENTS = "list_events"
    ACTION_ID_GET_EVENT = "get_event"
    ACTION_ID_UPDATE_EVENT = "update_event"
    ACTION_ID_LIST_PEOPLE = "list_people"
    ACTION_ID_GET_PERSON = "get_person"
    ACTION_ID_INITIATE_EVENT = "initiate_event"
    ACTION_ID_LIST_GROUPS = "list_groups"
    ACTION_ID_GET_ONCALL_USER = "get_oncall_user"

    def __init__(self):
        super().__init__()
        self._base_url = None
        self._username = None
        self._password = None
        self._client_id = None
        self._try_oauth = False
        self._use_token = False
        self._state = {}
        self._oauth_obj = None
        return

    def initialize(self):
        config = self.get_config()
        self._base_url = config[XM_CONFIG_BASE_URL].rstrip("/")
        self._username = config[XM_CONFIG_USERNAME].encode("utf-8")
        self._password = config[XM_CONFIG_PASSWORD]
        self._client_id = config.get(XM_CONFIG_CLIENT_ID, None)
        if self._client_id:
            self._use_token = True

        self._state = self.load_state()
        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _get_error_message_from_exception(self, e):
        """This method is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        error_code = PHANTOM_ERR_CODE_UNAVAILABLE
        err_message = PHANTOM_ERR_MSG_UNAVAILABLE
        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    err_message = e.args[1]
                elif len(e.args) == 1:
                    err_message = e.args[0]
        except:
            pass

        return f"Error Code: {error_code}. Error Message: {err_message}"

    def _process_empty_reponse(self, response, action_result):
        if 200 <= response.status_code < 205:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    def _process_html_response(self, response, action_result):
        # An html response, is bound to be an error
        status_code = response.status_code

        try:
            clean_text = response.text.encode("utf8").decode("ascii", "ignore")
            soup = BeautifulSoup(clean_text, "html.parser")
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
            self.save_progress("Cannot parse JSON")
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Unable to parse response as JSON", e), None)

        if 200 <= r.status_code < 205:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # Unauthorized Request
        if r.status_code == 401:
            if resp_json.get("error") == "invalid_token":
                raise UnauthorizedOAuthTokenException

        action_result.add_data(resp_json)
        message = r.text.replace("{", "{{").replace("}", "}}")
        return RetVal(
            action_result.set_status(phantom.APP_ERROR, f"Error from server, Status Code: {r.status_code} data returned: {message}"), resp_json
        )

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if an error occurs
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # There are just too many differences in the response to handle all of them in the same function
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # it's not an html or json, handle if it is a successfull empty reponse
        if (200 <= r.status_code < 205) and (not r.text):
            return self._process_empty_reponse(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, action_result, endpoint, data=None, params={}, headers={}, method="get", auth=None, **kwargs):
        """Returns 2 values, use RetVal"""

        url = self._base_url + endpoint

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            # Set the action_result status to error, the handler function will most probably return as is
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unsupported method: {method}"), None)
        except Exception as e:
            # Set the action_result status to error, the handler function will most probably return as is
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Handled exception: {e!s}"), None)

        try:
            response = request_func(
                url, data=data, params=params, headers=headers, auth=auth, timeout=XMATTERS_DEFAULT_REQUEST_TIMEOUT, **kwargs
            )
        except Exception as e:
            # Set the action_result status to error, the handler function will most probably return as is
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error connecting: {e!s}"), None)

        return self._process_response(response, action_result)

    def _create_headers(self, h={}, **kwargs):
        d = {"Content-Type": "application/json"}
        d.update(h)
        for k, v in kwargs.items():
            d[k] = v
        return d

    def _get_new_oauth_token(self, action_result):
        """Generate a new oauth token using the refresh token, if available"""
        params = {"client_id": self._client_id}
        try:
            params["refresh_token"] = self._state["oauth_token"]["refresh_token"]
            params["grant_type"] = "refresh_token"
        except KeyError:
            config = self.get_config()
            params["username"] = config[XM_CONFIG_USERNAME]
            params["password"] = config[XM_CONFIG_PASSWORD]
            params["grant_type"] = "password"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        ret_val, response_json = self._make_rest_call(action_result, "/api/xm/1/oauth2/token", data=params, headers=headers, method="post")

        if phantom.is_fail(ret_val) and params["grant_type"] == "refresh_token":
            self.debug_print("Unable to generate new key with refresh token")
            self._state = {}
            # Try again, using a password
            return self._get_new_oauth_token(action_result)

        if phantom.is_fail(ret_val):
            return RetVal(action_result.set_status(phantom.APP_ERROR, XM_ERR_TOKEN_REQUEST), None)

        self._state["oauth_token"] = response_json
        self._state["retrieval_time"] = datetime.now().strftime(DT_STR_FORMAT)
        try:
            return RetVal(phantom.APP_SUCCESS, response_json["access_token"])
        except Exception as e:
            self._state = {}
            return RetVal(action_result.set_status(phantom.APP_ERROR, XM_ERR_PARSE_ACCESS_TOKEN, e), None)

    def _get_oauth_token(self, action_result, force_new=False):
        if self._state.get("oauth_token") and not force_new:
            expires_in = self._state.get("oauth_token", {}).get("expires_in", 0)
            try:
                diff = (datetime.now() - datetime.strptime(self._state["retrieval_time"], DT_STR_FORMAT)).total_seconds()
                self.debug_print(diff)
                if diff < expires_in:
                    self.debug_print("Using old OAuth Token")
                    return RetVal(action_result.set_status(phantom.APP_SUCCESS), self._state["oauth_token"]["access_token"])
            except KeyError:
                self.debug_print("Key Error")
                pass

        self.debug_print("Generating new OAuth Token")
        return self._get_new_oauth_token(action_result)

    def _get_authorization_credentials(self, action_result, force_new=False):
        auth = None
        headers = {}
        auth = None
        if self._use_token:
            self.save_progress("Connecting with OAuth Token")
            ret_val, oauth_token = self._get_oauth_token(action_result, force_new)
            if phantom.is_fail(ret_val):
                return ret_val, None, None
            self.save_progress("OAuth Token Retrieved")
            headers = self._create_headers({"Authorization": f"Bearer {oauth_token}"})
            self._try_oauth = True
        else:
            ret_val = phantom.APP_SUCCESS
            self.save_progress("Connecting with HTTP Basic Auth")
            auth = requests.auth.HTTPBasicAuth(self._username, self._password)
            headers = self._create_headers()

        return ret_val, auth, headers

    def _make_rest_call_helper(self, action_result, endpoint, data=None, params={}, headers={}, method="get", auth=None, **kwargs):
        try:
            return self._make_rest_call(action_result, endpoint, data=data, params=params, headers=headers, method=method, auth=auth, **kwargs)
        except UnauthorizedOAuthTokenException:
            # We should only be here if we didn't generate a new token, and if the old token wasn't valid
            # (Hopefully) this should only happen rarely
            self.debug_print("UnauthorizedOAuthTokenException")
            if self._try_oauth:
                self._try_oauth = False
                ret_val, auth, headers = self._get_authorization_credentials(action_result, force_new=True)
                if phantom.is_fail(ret_val):
                    return RetVal(phantom.APP_ERROR, None)
                return self._make_rest_call_helper(action_result, endpoint, params=params, headers=headers, method=method, auth=auth, **kwargs)
            return RetVal(action_result.set_status(phantom.APP_ERROR, XM_ERR_AUTHORIZE_OAUTH_TOKEN), None)

    def _format_params_to_query(self, params):
        """If you just pass with the params argument into the request, commas will be encoded to %2C
        (Requests also uses the urlencode method on a dictionary)
        The API uses literal commas and %2C differently. %2C would be for when the actual field has a comma, and
        ',' is for creating a list in the query.
        For example: ?propertyName=isTure,floor&propertyValue=false,Balcony%2Cupper
        %1A is the code for substitute character, which seemed fitting and unused, though urlencode will
        encode this this into %251A.
        """
        for k, v in params.items():
            try:
                if "%1A" in v:
                    self.debug_print("Check the _format_params_to_query method")
                self.debug_print(v)
                v.replace("%2C", "%1A")
            except TypeError:
                # v is a boolean or something
                pass

        return urllib.parse.urlencode(params).replace("%2C", ",").replace("%252C", "%2C").replace("%20", " ").replace("%2B", "+")

    def _test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        ret_val, auth, headers = self._get_authorization_credentials(action_result)
        if phantom.is_fail(ret_val):
            return self.set_status_save_progress(phantom.APP_ERROR, XM_ERR_TEST_CONNECTIVITY_FAILURE)

        self.save_progress("Making Request")
        # While there is a 'ping' endpoint, it will always return 200; it doesn't check auth at all
        ret_val, response_json = self._make_rest_call_helper(action_result, XM_ENDPOINT_TEST_CONNECTIVITY, headers=headers, auth=auth)

        if phantom.is_fail(ret_val):
            if response_json:
                reason = response_json.get("reason")
                if reason:
                    self.save_progress(f"Error: {reason}")
            return self.set_status(phantom.APP_ERROR, XM_ERR_TEST_CONNECTIVITY_FAILURE)
        else:
            return self.set_status_save_progress(phantom.APP_SUCCESS, XM_SUCCESS_TEST_CONNECTIVITY)

    def _list_events(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        params = {}

        ret_val, auth, headers = self._get_authorization_credentials(action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        # Prefer the next page if provided
        try:
            endpoint = param["page_uri"]
        except KeyError:
            for k, v in param.items():
                if k == "context":
                    continue
                value_list = [x.strip() for x in str(v).split(",") if x]
                params[APP_PARAM_TO_API_PARAM_MAP.get(k, k)] = ",".join(value_list)  # Remove any whitespace after commas
            endpoint = XM_ENDPOINT_LIST_EVENTS
            endpoint += f"?{self._format_params_to_query(params)}"
            self.debug_print(endpoint)

        ret_val, response_json = self._make_rest_call_helper(action_result, endpoint, headers=headers, auth=auth)

        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response_json)

        summary = action_result.update_summary({})
        summary["events_returned"] = response_json.get("count")
        try:
            summary["next_page"] = response_json["links"]["next"]
        except KeyError:
            pass
        return action_result.set_status(phantom.APP_SUCCESS, XM_LIST_EVENTS_SUCCESS)

    def _initiate_event(self, param):
        """This API is going to be depreciated 'soon'. If this action suddenly and/or violently
        stops functioning, that is probably what happened
        """
        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = XM_ENDPOINT_TRIGGER_EVENT

        body = {}

        # Oauth doesn't work with this endpoint
        ret_val, auth, headers = self._get_authorization_credentials(action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        for k, v in param.items():
            if k == "context":
                continue
            elif k == "form_uuid":
                endpoint = endpoint.format(v)
            elif k == "recipients":
                tnames = v.split(",")
                recipients = [{"targetName": x.strip()} for x in tnames]
                body[k] = recipients
            elif k in DECODE_JSON_PARAMETERS:
                try:
                    body[k] = json.loads(v)
                except Exception as e:
                    self.debug_print(k)
                    self.debug_print(v)
                    err_message = self._get_error_message_from_exception(e)
                    return action_result.set_status(phantom.APP_ERROR, f"Unable to parse parameter '{k}' to json: {err_message}")
            else:
                body[k] = v

        self.debug_print(body)
        ret_val, response_json = self._make_rest_call_helper(action_result, endpoint, json=body, headers=headers, auth=auth, method="post")

        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response_json)
        summary = action_result.update_summary({})
        summary["event_id"] = response_json.get("id")
        return action_result.set_status(phantom.APP_SUCCESS, XM_CREATE_EVENT_SUCCESS)

    def _get_event(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        params = {}

        event_id = param["event_id"]
        endpoint = XM_ENDPOINT_GET_EVENT.format(event_id)

        ret_val, auth, headers = self._get_authorization_credentials(action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        embed = []
        if param.get("embed_recipients", False):
            embed.append("recipients")
            params["targeted"] = param.get("targeted", False)

        if param.get("embed_response_options", False):
            embed.append("responseOptions")

        if embed:
            params["embed"] = ",".join(embed)

        endpoint += f"?{self._format_params_to_query(params)}"
        ret_val, response_json = self._make_rest_call_helper(action_result, endpoint, headers=headers, auth=auth)

        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response_json)
        summary = action_result.update_summary({})
        summary["event_id"] = event_id
        return action_result.set_status(phantom.APP_SUCCESS, XM_GET_EVENT_SUCCESS)

    def _update_event(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        body = {}

        ret_val, auth, headers = self._get_authorization_credentials(action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        endpoint = XM_ENDPOINT_UPDATE_EVENT
        event_id = param["event_id"]
        body["id"] = event_id
        body["status"] = param["status"]

        ret_val, response_json = self._make_rest_call_helper(action_result, endpoint, headers=headers, json=body, auth=auth, method="post")

        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response_json)
        summary = action_result.update_summary({})
        summary["event_id"] = event_id

        return action_result.set_status(phantom.APP_SUCCESS, XM_UPDATE_EVENT_SUCCESS)

    def _list_people(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        params = {}

        ret_val, auth, headers = self._get_authorization_credentials(action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        try:
            endpoint = param["page_uri"]
        except KeyError:
            regex = re.compile(r",\s+")
            for k, v in param.items():
                if k == "context":
                    continue
                if k == "embed_roles":
                    params["embed"] = "roles"
                params[APP_PARAM_TO_API_PARAM_MAP.get(k, k)] = regex.sub(",", str(v))
            endpoint = XM_ENDPOINT_LIST_PEOPLE
            endpoint += f"?{self._format_params_to_query(params)}"

        ret_val, response_json = self._make_rest_call_helper(action_result, endpoint, headers=headers, auth=auth)

        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response_json)

        summary = action_result.update_summary({})
        summary["people_returned"] = response_json.get("count")
        try:
            summary["next_page"] = response_json["links"]["next"]
        except KeyError:
            pass

        return action_result.set_status(phantom.APP_SUCCESS, XM_LIST_PEOPLE_SUCCESS)

    def _get_person(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        params = {}

        person_id = param["identifier"]
        endpoint = XM_ENDPOINT_GET_PEOPLE.format(person_id)

        ret_val, auth, headers = self._get_authorization_credentials(action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        if param.get("embed_roles", False):
            params["embed"] = "roles"

        ret_val, response_json = self._make_rest_call_helper(action_result, endpoint, params=params, headers=headers, auth=auth)

        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response_json)
        summary = action_result.update_summary({})
        summary["person_id"] = person_id
        return action_result.set_status(phantom.APP_SUCCESS, XM_GET_PERSON_SUCCESS)

    def _list_groups(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        params = {}

        embed = []
        if param.get("embed_observers"):
            embed.append("observers")

        if param.get("embed_supervisors"):
            embed.append("supervisors")

        embed = ",".join(embed)
        params["embed"] = embed

        ret_val, auth, headers = self._get_authorization_credentials(action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        regex = re.compile(r",\s+")
        for k, v in param.items():
            if k == "context":
                continue
            if k == "search_group":
                params["search"] = param["search_group"]
            if k == "members":
                params["members"] = param["members"]
            if k == "status":
                params["status"] = param["status"]
            params[APP_PARAM_TO_API_PARAM_MAP.get(k, k)] = regex.sub(",", str(v))
        endpoint = XM_ENDPOINT_LIST_GROUPS
        endpoint += f"?{self._format_params_to_query(params)}"

        ret_val, response_json = self._make_rest_call_helper(action_result, endpoint, headers=headers, auth=auth)

        if phantom.is_fail(ret_val):
            return ret_val

        if response_json is None:
            return action_result.get_status()

        for res in response_json["data"]:
            action_result.add_data(res)

        summary = action_result.update_summary({})
        summary["groups_returned"] = response_json.get("count")

        return action_result.set_status(phantom.APP_SUCCESS, "Num of groups found: {}".format(response_json.get("count")))

    def _get_oncall_user(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        params = {}
        shift_count = 0

        embed = []
        if param.get("embed_shift"):
            embed.append("shift")

        if param.get("embed_owner"):
            embed.append("members.owner")

        embed = ",".join(embed)
        params["embed"] = embed

        timeframe = []
        if param.get("from"):
            timeframe.append("from")
        if param.get("to"):
            timeframe.append("shift")
        if len(timeframe) == 1:
            return action_result.set_status(phantom.APP_ERROR, XM_WHO_IS_ONCALL_TIME_FAILURE)

        if (param.get("members_per_shift") is not None) and ((param.get("members_per_shift") > 100) or (param.get("members_per_shift") <= 0)):
            return action_result.set_status(phantom.APP_ERROR, XM_WHO_IS_ONCALL_INVALID_MEM_FAILURE)

        ret_val, auth, headers = self._get_authorization_credentials(action_result)
        if phantom.is_fail(ret_val):
            return ret_val

        for k, v in param.items():
            if k == "context":
                continue
            if k == "groups":
                params["groups"] = param["groups"]
            if k == "members_per_shift":
                params["membersPerShift"] = str(v)
            if k == "from":
                params["from"] = param["from"]
            if k == "to":
                params["to"] = param["to"]
            value_list = [x.strip() for x in str(v).split(",") if x]
            params[APP_PARAM_TO_API_PARAM_MAP.get(k, k)] = ",".join(value_list)  # Remove any whitespace after commas
        endpoint = XM_ENDPOINT_GET_ONCALL
        endpoint += f"?{self._format_params_to_query(params)}"

        ret_val, response_json = self._make_rest_call_helper(action_result, endpoint, headers=headers, auth=auth)

        if phantom.is_fail(ret_val):
            return ret_val

        if response_json is None:
            return action_result.get_status()

        for res in response_json["data"]:
            action_result.add_data(res)

            if res.get("shift"):
                shift_count += 1

        summary = action_result.update_summary({})
        try:
            response_json["data"][0]["members"]["count"]
        except KeyError:
            return action_result.set_status(phantom.APP_ERROR, XM_WHO_IS_ONCALL_FAILURE)

        try:
            summary["next_page"] = response_json["data"][0]["members"]["links"]["next"]
        except KeyError:
            pass
        summary["num_of_shifts"] = shift_count
        return action_result.set_status(phantom.APP_SUCCESS, XM_WHO_IS_ONCALL_SUCCESS)

    def handle_action(self, param):
        result = None
        action = self.get_action_identifier()

        if action == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            result = self._test_connectivity(param)
        if action == self.ACTION_ID_LIST_EVENTS:
            result = self._list_events(param)
        if action == self.ACTION_ID_GET_EVENT:
            result = self._get_event(param)
        if action == self.ACTION_ID_UPDATE_EVENT:
            result = self._update_event(param)
        if action == self.ACTION_ID_LIST_PEOPLE:
            result = self._list_people(param)
        if action == self.ACTION_ID_GET_PERSON:
            result = self._get_person(param)
        if action == self.ACTION_ID_INITIATE_EVENT:
            result = self._initiate_event(param)
        if action == self.ACTION_ID_LIST_GROUPS:
            result = self._list_groups(param)
        if action == self.ACTION_ID_GET_ONCALL_USER:
            result = self._get_oncall_user(param)

        return result


if __name__ == "__main__":
    import sys

    import pudb

    pudb.set_trace()

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = XMattersConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
