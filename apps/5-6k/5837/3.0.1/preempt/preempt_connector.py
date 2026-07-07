# File: preempt_connector.py
#
# Copyright (c) 2019-2025 Splunk Inc.
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
import copy
import json
import sys
import time
from datetime import datetime

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from preempt_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class PreemptConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self.platform_address = None
        self.api_token = None

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove the script, style, footer and navigation part from the HTML message
            for element in soup(["script", "style", "footer", "nav"]):
                element.extract()
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines).encode("ascii", "ignore").strip()
        except:
            error_text = "Cannot parse error details"

        if error_text:
            self.debug_print(f"Status Code: {status_code}. Data from server: {error_text}")
            message = "Error while connecting to the server."

        message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {e!s}"), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        msg = []
        if resp_json.get("errors"):
            for error in resp_json.get("errors"):
                msg.append(error.get("message").strip("."))

        if msg:
            message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, ".".join(msg))
        else:
            # You should process the error returned in the json
            message = "Error from server. Status Code: {} Data from server: {}".format(
                r.status_code, r.text.replace("{", "{{").replace("}", "}}")
            )

        if "Method Not Allowed" in message:
            message = "Method not allowed"

        if "Conflict" in message:
            message = "Incident not found"

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
        if not r.text:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, action_result, method="post", data=None, **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = self.platform_address + "/api/public/graphql"

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_token}"}

        try:
            r = request_func(url, headers=headers, json={"query": data}, verify=config.get("verify_server_cert", False), **kwargs)
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {e!s}"), resp_json)

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Retrieving Administrator Role entity")

        data = """{
            entities(
            roles: [BuiltinAdministratorRole],first: 1){
                nodes {
                primaryDisplayName
                secondaryDisplayName
                }
            }
        }"""

        # make rest call
        ret_val, response = self._make_rest_call(action_result, data=data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_user_attributes(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        username = param["attribute_value"]
        attribute = param["attribute_type"]
        domain = param["domain"]

        attribute_type = ATTRIBUTE_TYPES.get(attribute)

        data = f'''{{
            entities({attribute_type}: "{username}"
                    domains: "{domain}"
                    archived: false
                    first: 1)
            {{
                nodes {{
                    entityId
                    type

                    primaryDisplayName
                    secondaryDisplayName

                    isHuman: hasRole(type: HumanUserAccountRole)
                    isAdmin: hasRole(type: AdminAccountRole)

                    riskScore
                    riskFactors
                    {{
                        type
                    }}

                    ... on UserEntity
                    {{
                        emailAddresses
                        phoneNumbers
                        watched
                    }}

                    ownedEndpoints: associations(bindingTypes: OWNERSHIP)
                    {{
                        ... on EntityAssociation
                        {{
                        entity
                        {{
                            primaryDisplayName
                            secondaryDisplayName
                        }}
                        }}
                    }}
                }}
            }}
        }}'''

        # make rest call
        ret_val, response = self._make_rest_call(action_result, data=data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        result = response.get("data", {}).get("entities", {}).get("nodes", [])

        summary = action_result.update_summary({})

        if len(result) > 0:
            action_result.add_data(result[0])
            summary["risk_score"] = float(result[0].get("riskScore")) * 10
            summary["primary_display_name"] = result[0].get("primaryDisplayName")
        else:
            action_result.add_data({"riskScore": "Unavailable"})
            action_result.add_data({"primaryDisplayName": "Unavailable"})
            summary["result"] = "Attribute type, attribute value, and domain combination not found"
            return action_result.set_status(phantom.APP_ERROR)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_user_activity(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        types = param.get("types")
        invalid_types = list()
        if types is None:
            types = f"types: {TIMELINE_EVENT_TYPES}"
        else:
            types = [i.strip().upper() for i in types.split(",")]
            types_list = copy.deepcopy(types)
            for item in types_list:
                if item not in TIMELINE_EVENT_TYPES_LIST:
                    invalid_types.append(item)
                    types.remove(item)
                    # Remove the invalid types, but still query on the rest of the valid ones
            if len(types) == 0:
                return action_result.set_status(
                    phantom.APP_ERROR, "All types provided are invalid. Refer to Preempt TimelineEventType API documentation for valid types"
                )
            types = f"types: {types}".replace("'", "")

        while True:
            username = param["username"]
            start_time = param["start_time"]

            limit = param.get("limit", None)
            if limit is None:
                result_limit = 1000  # Minimize the number of REST calls made by using max limit
            elif bool(limit) is True and int(limit) <= 0:
                return action_result.set_status(phantom.APP_ERROR, "Limit must be greater than 0")
            elif bool(limit) is True and int(limit) > 1000:
                return action_result.set_status(phantom.APP_ERROR, "Limit cannot be greater than 1000")
            else:
                result_limit = int(limit)

            after = param.get("after", None)
            if after is None:
                after = ""

            data = f'''{{
                timeline(sourceEntityQuery: {{ samAccountNames: "{username}" }}
                        startTime: "{start_time}"
                        {after}
                        sortOrder: DESCENDING
                        {types}
                        first: {result_limit})
                {{
                    nodes
                    {{
                    timestamp
                    eventType
                    eventLabel
                    eventSeverity
                    ... on TimelineAuthenticationEvent
                    {{
                        authenticationType
                        userEntity
                        {{
                        primaryDisplayName
                        secondaryDisplayName
                        }}
                        endpointEntity
                        {{
                        primaryDisplayName
                        secondaryDisplayName
                        }}
                        ipAddress
                        hostName
                    }}
                    }}
                    pageInfo {{
                        endCursor
                        hasNextPage
                    }}
                }}
            }}'''

            # make rest call
            ret_val, response = self._make_rest_call(action_result, data=data)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            result = response.get("data", {}).get("timeline", {})
            nodes = result.get("nodes", [])

            if limit is not None and len(action_result.get_data()) + len(nodes) > int(result_limit):
                for item in nodes:
                    if int(result_limit) > len(action_result.get_data()):
                        action_result.add_data(item)
                    else:
                        break
            else:
                action_result.update_data(nodes)

            has_next_page = result.get("pageInfo", {}).get("hasNextPage", False)
            if has_next_page is True and len(action_result.get_data()) < result_limit:
                param.update({"after": 'after: "{}"'.format(result["pageInfo"]["endCursor"])})
            else:
                break

        num_results = len(action_result.get_data())
        if num_results == 0:
            return action_result.set_status(phantom.APP_ERROR, "No activity found for user")

        summary = action_result.update_summary({})
        summary["num_results"] = num_results

        if len(invalid_types) == 1:
            summary["type_parameter_error"] = f"{invalid_types[0]} is invalid and was not used in the query"
        elif len(invalid_types) > 1:
            types_formatted = "".join(
                [f"and {item}" if idx + 1 == len(invalid_types) else f"{item}, " for idx, item in enumerate(invalid_types)]
            )
            summary["type_parameter_error"] = f"{types_formatted} are invalid and were not used in the query"

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_user_risk(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        username = param["username"]
        domain = param["domain"]
        attribute = param.get("attribute_type", "samAccountName")
        attribute_type = ATTRIBUTE_TYPES.get(attribute)

        data = f'''{{
            entities({attribute_type}: "{username}"
                    domains: "{domain}"
                    archived: false
                    first: 1)
            {{
                nodes {{
                    riskScore
                    riskFactors
                    {{
                        type
                    }}
                }}
            }}
        }}'''

        # make rest call
        ret_val, response = self._make_rest_call(action_result, data=data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        result = response.get("data", {}).get("entities", {}).get("nodes", [])

        summary = action_result.update_summary({})

        if len(result) > 0:
            action_result.add_data(result[0])
            summary["risk_score"] = float(result[0].get("riskScore")) * 10
        else:
            action_result.add_data({"riskScore": "Unavailable"})
            summary["result"] = "Username and domain combination not found"
            return action_result.set_status(phantom.APP_ERROR)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_watch_user(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        username = param["username"]
        domain = param["domain"]
        attribute = param.get("attribute_type", "samAccountName")
        attribute_type = ATTRIBUTE_TYPES.get(attribute)

        data = f'''mutation {{
            addEntitiesToWatchList(input: {{ entityQuery: {{ {attribute_type}: "{username}", domains: "{domain}" }} }})
            {{
                updatedEntities
                {{
                primaryDisplayName
                secondaryDisplayName
                }}
            }}
        }}'''

        # make rest call
        ret_val, response = self._make_rest_call(action_result, data=data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        result = response.get("data", {}).get("addEntitiesToWatchList", {})
        action_result.add_data(result)

        summary = action_result.update_summary({})
        if len(result.get("updatedEntities", [])) == 0:
            summary["result"] = "No entities updated"
            return action_result.set_status(phantom.APP_ERROR)
        else:
            summary["result"] = "{} was added to the watch list".format(result["updatedEntities"][0]["primaryDisplayName"])

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_unwatch_user(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        username = param["username"]
        domain = param["domain"]
        attribute = param.get("attribute_type", "samAccountName")
        attribute_type = ATTRIBUTE_TYPES.get(attribute)

        data = f'''mutation {{
            removeEntitiesFromWatchList(input: {{ entityQuery: {{ {attribute_type}: "{username}", domains: "{domain}" }} }})
            {{
                updatedEntities
                {{
                primaryDisplayName
                secondaryDisplayName
                }}
            }}
        }}'''

        # make rest call
        ret_val, response = self._make_rest_call(action_result, data=data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        result = response.get("data", {}).get("removeEntitiesFromWatchList", {})
        action_result.add_data(result)

        summary = action_result.update_summary({})
        if len(result.get("updatedEntities", [])) == 0:
            summary["result"] = "No entities updated"
            return action_result.set_status(phantom.APP_ERROR)
        else:
            summary["result"] = "{} was removed from the watch list".format(result["updatedEntities"][0]["primaryDisplayName"])

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_incident(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        incident_number = param["incident_number"]

        data = f"""{{
            incident(incidentId: "INC-{incident_number}")
            {{
                ... on Incident {{
                alertEvents {{
                    alertId
                    alertType
                    endTime
                    endpointEntity {{
                    impactScore
                    hostName
                    riskScore
                    riskFactors {{
                        severity
                        type
                    }}
                    watched
                    }}

                }}
                comments {{
                    author {{
                        displayName
                        type
                    }}
                    text
                    timestamp
                }}

                compromisedEntities {{
                    accounts {{
                        archived
                        dataSource
                        enabled
                    }}
                }}

                endTime
                incidentId
                lifeCycleStage
                markedAsRead
                severity
                startTime
                type
                }}
            }}
            }}"""

        # make rest call
        ret_val, response = self._make_rest_call(action_result, data=data)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        result = response.get("data", {}).get("incident", {})

        if result is None:
            return action_result.set_status(phantom.APP_ERROR, "Incident not found")

        action_result.add_data(result)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary["severity"] = result.get("severity", "Could not retrieve severity")

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_incident(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        incident_number = param["incident_number"]
        stage = param.get("stage")
        reason = param.get("reason")
        comment = param.get("comment")

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        if stage and reason:
            data_stage = f'''mutation {{
                setIncidentState(input: {{ incidentId: "INC-{incident_number}", lifeCycleStage: {stage}, reason: "{reason}" }})
                {{
                    incident
                    {{
                    lifeCycleStage
                    }}
                }}
            }}'''

            # make rest call
            ret_val, response = self._make_rest_call(action_result, data=data_stage)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            result = response.get("data", {})
            action_result.add_data(result)

            summary["life_cycle_state"] = f"Incident state is {stage}"

        if comment:
            data_comment = f'''mutation {{
                addCommentToIncident(input: {{ comment: "{comment}", incidentId: "INC-{incident_number}"}}){{
                    incident {{
                        comments {{
                            author {{
                                displayName
                            }}
                            text
                        }}
                    }}
                }}
            }}'''

            # make rest call
            ret_val, response = self._make_rest_call(action_result, data=data_comment)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            result = response.get("data", {})
            action_result.add_data(result)

            summary["num_comments"] = len(result.get("addCommentToIncident", {}).get("incident", {}).get("comments", []))
            summary["comment_status"] = "Comment successfully added to incident"

        if not stage or not reason:
            summary["life_cycle_state"] = "Life cycle stage not updated. Both stage and reason parameters must be included in action request"
            if not comment:
                return action_result.set_status(phantom.APP_ERROR, PREEMPT_INVALID_UPDATE_INCIDENT_PARAMS)

        if not stage and not reason and not comment:
            return action_result.set_status(phantom.APP_ERROR, PREEMPT_INVALID_UPDATE_INCIDENT_PARAMS)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_artifact_id(self, sdi, container_id):
        config = self.get_config()
        verify_server_cert = config.get(PREEMPT_JSON_VERIFY_SERVER_CERT, False)
        url = f'{self.get_phantom_base_url()}rest/artifact?_filter_source_data_identifier="{sdi}"&_filter_container_id={container_id}'

        try:
            r = requests.get(url, verify=verify_server_cert, timeout=DEFAULT_REQUEST_TIMEOUT)
            resp_json = r.json()
        except Exception as e:
            self.debug_print("Unable to query Preempt artifact", e)
            return None

        if resp_json.get("count", 0) <= 0:
            self.debug_print("No artifact matched")
            return None

        try:
            artifact_id = resp_json.get("data", [])[0]["id"]
        except Exception as e:
            self.debug_print("Artifact results, not proper", e)
            return None

        return artifact_id

    def _update_container(self, incident, container_id, last_time):
        config = self.get_config()
        verify_server_cert = config.get(PREEMPT_JSON_VERIFY_SERVER_CERT, False)
        updated = dict()
        updated["data"] = incident
        updated["description"] = "{}: {}".format(incident["incidentId"], incident["type"])

        url = f"{self.get_phantom_base_url()}rest/container/{container_id}"

        try:
            r = requests.post(url, data=json.dumps(updated), verify=verify_server_cert, timeout=DEFAULT_REQUEST_TIMEOUT)
            resp_json = r.json()
        except Exception as e:
            self.debug_print("Exception occurred while updating container", e)
            return phantom.APP_ERROR

        if r.status_code != 200 or resp_json.get("failed"):
            self.debug_print("There was an issue updating a container", resp_json.get("failed"))
            return phantom.APP_ERROR

        artifact_list = list()
        # Artifact ID is in format "INC-<incident_number>-<type>-<timestamp>". Example: "INC-1-comment-2017-11-15T17:50:28.000Z"

        # Check for and add comments as artifacts
        try:
            for comment in incident["comments"]:
                if not self._get_artifact_id("{}-{}-{}".format(container_id, "comment", comment["timestamp"]), container_id):
                    self._handle_comment(comment, container_id, "Comment", artifact_list)
        except:
            pass

        # Check for and add compromised entities as artifacts
        try:
            for entity in incident["compromisedEntities"]:
                if not self._get_artifact_id("{}-{}-{}".format(container_id, "compromisedEntity", entity["creationTime"]), container_id):
                    self._handle_compromised_entity(entity, container_id, "Compromised Entity", artifact_list)
        except:
            pass

        # Check for and add alert events as artifacts
        try:
            for event in incident["alertEvents"]:
                if not self._get_artifact_id("{}-{}-{}".format(container_id, "alertEvent", event["timestamp"]), container_id):
                    self._handle_alert_event(event, container_id, "Alert Event", artifact_list)
        except:
            pass

        if len(artifact_list) > 0:
            ret_val, message, resp = self.save_artifacts(artifact_list)

            if not ret_val:
                self.debug_print("Error saving artifact: ", message)

    def _get_container_id(self, incident_id):
        config = self.get_config()
        verify_server_cert = config.get(PREEMPT_JSON_VERIFY_SERVER_CERT, False)
        url = f'{self.get_phantom_base_url()}rest/container?_filter_source_data_identifier="{incident_id}"&_filter_asset={self.get_asset_id()}'
        # url = '{0}rest/container?_filter_source_data_identifier="{1}"&_filter_asset={2}'.format(
        # "https://172.16.182.130/", incident_id, self.get_asset_id())

        try:
            r = requests.get(url, verify=verify_server_cert, timeout=DEFAULT_REQUEST_TIMEOUT)
            resp_json = r.json()
        except Exception as e:
            self.debug_print("Unable to query Preempt incident container", e)
            return None

        if resp_json.get("count", 0) <= 0:
            self.debug_print("No container matched")
            return None

        try:
            container_id = resp_json.get("data", [])[0]["id"]
        except Exception as e:
            self.debug_print("Container results, not proper", e)
            return None

        return container_id

    def _handle_comment(self, comment, container_id, base_name, artifact_list):
        artifact = dict()

        artifact["name"] = "{} by {}".format(base_name, comment["author"]["displayName"])
        artifact["label"] = "comment"
        artifact["container_id"] = container_id
        # Comments do not have IDs, so using timestamp instead
        artifact["source_data_identifier"] = "{}-{}-{}".format(container_id, "comment", comment["timestamp"])

        artifact_cef = dict()

        artifact_cef["body"] = comment["text"]
        artifact_cef["created"] = comment["timestamp"]
        artifact_cef["author_display_name"] = comment["author"]["displayName"]

        artifact["cef"] = artifact_cef

        artifact_list.append(artifact)

        return phantom.APP_SUCCESS

    def _handle_compromised_entity(self, entity, container_id, base_name, artifact_list):
        artifact = dict()

        artifact["name"] = '{}: {} "{}"'.format(base_name, entity["type"], entity["primaryDisplayName"])
        artifact["label"] = "compromised_entity"
        artifact["container_id"] = container_id
        artifact["source_data_identifier"] = "{}-{}-{}".format(container_id, "compromisedEntity", entity["creationTime"])

        artifact_cef = dict()

        artifact_cef["type"] = entity["type"]
        artifact_cef["primary_display_name"] = entity["primaryDisplayName"]
        artifact_cef["secondary_display_name"] = entity["secondaryDisplayName"]

        artifact["cef"] = artifact_cef

        artifact_list.append(artifact)

        return phantom.APP_SUCCESS

    def _handle_alert_event(self, event, container_id, base_name, artifact_list):
        for ent in event["entities"]:
            artifact = dict()

            artifact["name"] = "{}: {}".format(base_name, event["eventLabel"])
            artifact["label"] = "alert_event"
            artifact["container_id"] = container_id
            artifact["source_data_identifier"] = "{}-{}-{}".format(container_id, "alertEvent", event["timestamp"])

            artifact_cef = dict()

            artifact_cef["type"] = ent["type"]
            artifact_cef["primary_display_name"] = ent["primaryDisplayName"]
            artifact_cef["secondary_display_name"] = ent["secondaryDisplayName"]

            artifact["cef"] = artifact_cef

            artifact_list.append(artifact)

        return phantom.APP_SUCCESS

    def _save_incident(self, incident, last_time):
        # Check if there is already a container for the incident id (Example: INC-1)
        container_id = self._get_container_id(incident["incidentId"])

        if container_id:
            # Ticket has already been ingested. Need to update its container.
            self._update_container(incident, container_id, last_time)
            return phantom.APP_SUCCESS

        # Build the new container
        container = dict()
        container["name"] = "Preempt {}: {}".format(incident["incidentId"], incident["type"])
        container["data"] = incident
        container["description"] = "{}: {}".format(incident["incidentId"], incident["type"])
        container["source_data_identifier"] = incident["incidentId"]
        container["label"] = self.get_config().get("ingest", {}).get("container_label")

        # Save the container
        ret_val, message, container_id = self.save_container(container)

        if not ret_val:
            return phantom.APP_ERROR

        artifact_list = list()

        # Check for and add comments as artifacts
        try:
            for comment in incident["comments"]:
                self._handle_comment(comment, container_id, "Comment", artifact_list)
        except:
            pass

        # Check for and add compromised entities as artifacts
        try:
            for entity in incident["compromisedEntities"]:
                self._handle_compromised_entity(entity, container_id, "Compromised Entity", artifact_list)
        except:
            pass

        # Check for and add alert events as artifacts
        try:
            for event in incident["alertEvents"]:
                self._handle_alert_event(event, container_id, "Alert Event", artifact_list)
        except:
            pass

        ret_val, message, resp = self.save_artifacts(artifact_list)
        if not ret_val:
            self.debug_print("Error saving container: ", message)
            return phantom.APP_ERROR

        return phantom.APP_SUCCESS

    def _build_artifact(self, incident, container_id):
        artifact = dict()
        artifact["container_id"] = container_id
        artifact["source_data_identifier"] = incident["incidentId"]

    def _on_poll(self, param):
        self.save_progress(f"Using URL: {self.platform_address}")
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self.platform_address)

        # Get config and state
        state = self.load_state()
        config = self.get_config()

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Get time from last poll, save now as time for this poll
        last_time = state.get("last_time", 0.0)
        state["last_time"] = time.time()
        last_converted_time = datetime.fromtimestamp(last_time)

        data = """{{
            incidents({after}
                        {updated_after}
                        sortOrder: ASCENDING
                        sortKey: END_TIME
                        first: {max_incidents}) {{
                nodes {{
                    incidentId
                    type
                    startTime
                    endTime
                    comments {{
                        text
                        timestamp
                        author {{
                            displayName
                        }}
                    }}
                    compromisedEntities {{
                        creationTime
                        type
                        primaryDisplayName
                        secondaryDisplayName
                    }}
                    alertEvents {{
                        timestamp
                        eventLabel
                        entities {{
                            type
                            primaryDisplayName
                            secondaryDisplayName
                        }}
                    }}
                }}
                pageInfo {{
                    endCursor
                    hasNextPage
                }}
            }}
        }}"""

        # If it's a poll now don't filter based on update time
        if self.is_poll_now():
            after = ""
            updated_after = ""
            max_incidents = param.get(phantom.APP_JSON_CONTAINER_COUNT)

        # If it's the first poll, don't filter based on update time
        elif state.get("first_run", True):
            state["first_run"] = False
            after = ""
            updated_after = f'updatedAfter: "{last_converted_time}"'
            max_incidents = int(config.get("first_run_max_incidents", 1000))

        # If it's scheduled polling add a filter for update time being greater than the last poll time
        else:
            after = ""
            updated_time = datetime.fromtimestamp(last_time + 0.01)
            updated_after = f'updatedAfter: "{updated_time}"'
            max_incidents = int(config.get("max_incidents", 1000))

        incidents = list()
        new_last_time = ""
        # Make rest call using query
        while True:
            query = data.format(after=after, updated_after=updated_after, max_incidents=max_incidents)

            ret_val, response = self._make_rest_call(action_result, data=query)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            # Parse the response to get list of incidents
            tmp_incidents = response.get("data", {}).get("incidents", {}).get("nodes", [])

            if not tmp_incidents:
                return action_result.set_status(phantom.APP_SUCCESS)

            if len(incidents) + len(tmp_incidents) >= max_incidents:
                for item in tmp_incidents:
                    if max_incidents > len(incidents):
                        incidents.append(item)
                        if not self.is_poll_now():
                            new_last_time = item["endTime"]  # This will be converted to epoch below
                    else:
                        break
                else:
                    continue
                break
            else:
                incidents += tmp_incidents
                new_last_time = tmp_incidents[-1]["endTime"]

            has_next_page = response.get("data", {}).get("incidents", {}).get("pageInfo", {}).get("hasNextPage", False)
            if has_next_page is True:
                after = 'after: "{}"'.format(response["data"]["incidents"]["pageInfo"]["endCursor"])
                updated_after = ""
            else:
                break

        # Make sure duplicate tickets are not included

        # Ingest the incidents
        failed = 0
        for incident in incidents:
            if not self._save_incident(incident, last_time):
                failed += 1

        # Convert last_time to epoch
        if not self.is_poll_now() and incidents:
            try:
                utc_time = datetime.strptime(str(new_last_time), "%Y-%m-%dT%H:%M:%S.%fZ")
                epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
                state["last_time"] = epoch_time
            except:
                state["last_time"] = str(new_last_time)

            # Set self._state to state. It will be saved in finalize()
            self._state = state

            if failed:
                return action_result.set_status(phantom.APP_ERROR, PREEMPT_ERR_FAILURES)

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "get_user_attributes":
            ret_val = self._handle_get_user_attributes(param)

        elif action_id == "get_user_activity":
            ret_val = self._handle_get_user_activity(param)

        elif action_id == "get_user_risk":
            ret_val = self._handle_get_user_risk(param)

        elif action_id == "watch_user":
            ret_val = self._handle_watch_user(param)

        elif action_id == "unwatch_user":
            ret_val = self._handle_unwatch_user(param)

        elif action_id == "get_incident":
            ret_val = self._handle_get_incident(param)

        elif action_id == "update_incident":
            ret_val = self._handle_update_incident(param)

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

        self.platform_address = config["platform_address"].rstrip("/")
        self.api_token = config["api_token"]

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == "__main__":
    import argparse

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument("-v", "--verify", action="store_true", help="verify", required=False, default=False)

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
            login_url = BaseConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=DEFAULT_REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = PreemptConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
