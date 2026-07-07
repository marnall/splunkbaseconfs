##
## SPDX-FileCopyrightText: 2025 Splunk LLC.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import json
import os
import sys
import requests
import traceback
from requests.auth import HTTPBasicAuth
import jira_cloud_consts as jcc
import jira_cloud_utils as utils

APP_NAME = __file__.split(os.path.sep)[-3]


class JiraCloudIssueHelper:
    def __init__(self, payload, events=None):
        self.session_key = payload["session_key"]
        self.token = payload["configuration"]["api_token"]
        self.project_key = payload["configuration"]["project_key"].strip()
        self.issue_type = payload["configuration"]["issue_type"].strip()
        self.summary = payload["configuration"]["summary"].strip()
        self.priority = payload["configuration"]["priority"].strip()
        self.parent = payload["configuration"].get("parent", "").strip()
        self.description = payload["configuration"]["description"].strip()
        self.labels = payload["configuration"]["label"].strip()
        self.components = payload["configuration"]["component"].strip()
        self.custom_fields = payload["configuration"]["custom_fields"].strip()
        self.jira_key = payload["configuration"]["jira_key"].strip()
        self.jira_status = payload["configuration"]["status"].strip().lower()
        self.correlation_id = payload["configuration"].get("correlation_id", "")
        self.include_events_in_description = payload["configuration"].get(
            "include_events_in_description", "0"
        )
        self.available_transitions = list()

        if self.correlation_id:
            self.correlation_id = self.correlation_id + ": "

        self.labels = self.labels.split(",") if self.labels else self.labels
        self.components = (
            self.components.split(",") if self.components else self.components
        )
        self.custom_fields = (
            self.custom_fields.split("||") if self.custom_fields else self.custom_fields
        )
        self.events = events
        self.splunk_search_url = payload.get("results_link", None)

        if not payload.get("logger"):
            self.logger = utils.set_logger(
                self.session_key,
                jcc.JIRA_CLOUD_ALERT_ACTION_LOGFILE_PREFIX + payload["search_name"],
            )
        else:
            self.logger = payload["logger"]

        self.return_response = payload.get("return_response", False)
        self.proxy = utils.get_proxy_settings(self.session_key, self.logger)

    def make_api_request(self, method, url, params={}, payload=None):
        """This method makes the api request to the provided url and return the response

        Args:
            method (str): request method (GET, POST, PUT)
            url (str) : url to make the api request
            params (dict) : Query parameters
            payload (dict) : payload to create/update jira issue

        Returns:
            response (Object): response object
        """
        try:
            auth = HTTPBasicAuth(
                self.api_token_details["username"], self.api_token_details["token"]
            )
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            self.logger.debug("Making API request to {}".format(url))
            if payload:
                return requests.request(
                    method,
                    url,
                    headers=headers,
                    auth=auth,
                    data=json.dumps(payload),
                    proxies=self.proxy,
                )
            else:
                return requests.request(
                    method,
                    url,
                    headers=headers,
                    auth=auth,
                    params=params,
                    proxies=self.proxy,
                )
        except Exception as e:
            msg = "{}Error while making API request {}. Reason: {}".format(
                self.correlation_id, url, traceback.format_exc()
            )
            utils.add_ucc_error_logger(
                logger=self.logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=e,
                exc_label=jcc.UCC_EXCEPTION_EXE_LABEL.format("jira_cloud_issue_helper"),
                msg_before=msg,
            )
            sys.exit(1)

    def is_payload_within_limit(
        self, temp_payload, max_length=jcc.MAX_DESCRIPTION_LENGTH
    ):
        """
        Validates if the JSON stringified payload is within the allowed length.

        Args:
            temp_payload (dict or list): The payload to be checked.
            max_length (int): The maximum allowed length of the serialized payload.

        Returns:
            bool: True if within limit, False otherwise.
        """
        return len(json.dumps(temp_payload)) <= max_length

    def create_payload(self):
        """This method creates the payload for creating or updating the jira issue and returns the payload"""

        if self.priority:
            self.get_priority_list()
        if self.custom_fields:
            self.fetch_custom_field_ids()
        else:
            self.custom_field_ids = []

        payload = {}
        if not self.jira_key:
            payload["issuetype"] = {"name": self.issue_type}
            payload["project"] = {"key": self.project_key}
        if self.summary:
            payload["summary"] = self.summary
        if self.description:
            # Step 1: Only description
            content = [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": self.description}],
                }
            ]

            # Step 2: Check length with only description
            temp_payload = {"version": 1, "type": "doc", "content": content}

            if not self.is_payload_within_limit(temp_payload):
                # Log error and exit
                self.logger.error(
                    "Description exceeds Jira field character limit. Not ingesting any content."
                )
                sys.exit(1)

            # Step 3: Add the link as a second paragraph
            link_paragraph = {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "View Splunk Search Results",
                        "marks": [
                            {
                                "type": "link",
                                "attrs": {
                                    "href": self.splunk_search_url,
                                    "title": "Splunk Search",
                                },
                            }
                        ],
                    }
                ],
            }
            content_with_link = content + [link_paragraph]

            # Step 4: Check length with link added
            temp_payload_link = {
                "version": 1,
                "type": "doc",
                "content": content_with_link,
            }

            # Check and add the link only if this is triggered by an alert action.
            if self.splunk_search_url:
                if not self.is_payload_within_limit(temp_payload_link):
                    # Log warning; proceed with description only
                    self.logger.warning(
                        "Link not added: description plus link exceeds Jira field character limit. Ingesting description only."
                    )
                else:
                    # Link fits, use content_with_link for further processing
                    content = content_with_link

            # Now, try to add events one by one
            if self.include_events_in_description == "1" and self.events:
                events = self.events if isinstance(self.events, list) else [self.events]
                for event in events:
                    code_block = {
                        "type": "codeBlock",
                        "attrs": {"language": "json"},
                        "content": [{"type": "text", "text": str(event)}],
                    }
                    # Predict the length if this event is added
                    temp_content = content + [code_block]
                    temp_payload = {
                        "version": 1,
                        "type": "doc",
                        "content": temp_content,
                    }
                    if self.is_payload_within_limit(temp_payload):
                        # Safe to add
                        content.append(code_block)
                    else:
                        self.logger.warning(
                            "Payload size limit reached. Stopping addition of events to description."
                        )
                        break  # Stop as soon as adding the next event exceeds the limit

            payload["description"] = {
                "version": 1,
                "type": "doc",
                "content": content,
            }
        if self.priority:
            payload["priority"] = {"id": self.priority_id}
        if self.labels:
            payload["labels"] = [label.strip() for label in self.labels]

        components = []
        if self.components:
            for component in self.components:
                jira_component = {"name": component}
                components.append(jira_component)
            payload["components"] = components

        if self.custom_field_ids:
            for custom_field in self.custom_field_ids:
                payload[
                    self.custom_field_ids[custom_field]
                ] = self.custom_fields_values[custom_field]

        if self.parent:
            payload["parent"] = {"key": self.parent}

        payload = {"fields": payload}
        self.logger.debug("payload = {}".format(payload))
        return payload

    def validate_project(self):
        """This method validates if the jira project exists or not"""
        self.logger.info("Validatng the Jira Project")
        project_url = jcc.JIRA_ISSUE_PROJECT_ENDPOINT.format(
            self.domain, self.project_key
        )
        params = {"expand": "issueTypes"}

        response = self.make_api_request("GET", project_url, params=params)
        project_response = response.json()

        if response.status_code == 200:
            issue_types = []
            for issue_type in project_response["issueTypes"]:
                issue_types.append(issue_type["name"])

            self.logger.debug(
                "List of issueTypes present under ({}) = {}".format(
                    self.project_key, issue_types
                )
            )

            if not self.issue_type in issue_types:
                self.logger.error(
                    "{}IssueType ({}) is not present under the project key ({})".format(
                        self.correlation_id, self.issue_type, self.project_key
                    )
                )
                sys.exit(1)

        else:
            self.logger.error(
                "{}Project key ({}) is not valid. Error Message = {}".format(
                    self.correlation_id, self.project_key, response.text
                )
            )
            sys.exit(1)

    def validate_status(self):
        """This method validates if the jira status exists or not"""
        self.logger.info("Validating the Jira issue status")
        transition_url = jcc.JIRA_ISSUE_TRANSITION_ENDPOINT.format(
            self.domain, self.jira_key
        )

        response = self.make_api_request("GET", transition_url)
        transition_response = response.json()

        if response.status_code == 200:
            for status in transition_response["transitions"]:
                transitions = [status["name"].lower(), status["to"]["name"].lower()]

                if self.jira_status in transitions:
                    return {
                        "transition": {
                            "id": status.get("id"),
                            "name": self.jira_status,
                        }
                    }

                self.available_transitions.extend(transitions)

            self.logger.debug(
                "List of transitions available under ({}) = {}".format(
                    self.jira_key, self.available_transitions
                )
            )

            self.logger.error(
                "{}Transition to ({}) is unavailable for Jira Key ({}) or you do not have permission 'Transition Issues'.".format(
                    self.correlation_id, self.jira_status, self.jira_key
                )
            )
            sys.exit(1)
        else:
            self.logger.error(
                "Failed to update the Jira Issue. Error Message = {}".format(
                    response.text
                )
            )
            sys.exit(1)

    def get_priority_list(self):
        """This method gets the priority lists to verify if the user provided priority is present or not"""
        self.logger.info("Validating the Jira priority")
        priority_url = jcc.JIRA_ISSUE_PRIORITY_ENDPOINT.format(self.domain)
        response = self.make_api_request("GET", priority_url)

        priority_response = response.json()

        if response.status_code == 200:
            priorities = {}
            for priority in priority_response["values"]:
                priorities[priority["name"]] = priority["id"]

            self.logger.debug("List of priorities = {}".format(priorities))

            if not self.priority in priorities:
                self.logger.error(
                    "{}Priority ({}) is not present under the domain ({})".format(
                        self.correlation_id, self.priority, self.domain
                    )
                )
                sys.exit(1)
            else:
                self.priority_id = priorities[self.priority]
        else:
            self.logger.error(
                "{}Failed to get the list of priorities. Error Message = {}".format(
                    self.correlation_id, response.text
                )
            )
            sys.exit(1)

    def is_valid_number(self, s: str) -> bool:
        try:
            float(s)  # Try to convert the string to a float
            return True
        except ValueError:
            self.logger.error(
                "{} '{}' is not a valid Number".format(self.correlation_id, s)
            )
            return False

    def fetch_custom_field_ids(self):
        """This method fetches the custom field's ids"""
        self.logger.info("Fetching ids of the custom fields")
        issue_field_url = jcc.JIRA_ISSUE_FIELDS_ENDPOINT.format(self.domain)

        response = self.make_api_request("GET", issue_field_url)
        issue_fields_response = response.json()

        if response.status_code == 200:
            self.custom_fields_values = {}
            for custom_field in self.custom_fields:
                custom_field_value = custom_field.split("=")
                self.custom_fields_values[
                    custom_field_value[0].strip()
                ] = custom_field_value[1].strip()

            self.custom_field_ids = {}
            # Process each custom field and find corresponding field ID
            for custom_field, custom_field_value in self.custom_fields_values.items():
                matched_field = next(
                    (
                        field
                        for field in issue_fields_response
                        if field["name"] == custom_field
                    ),
                    None,
                )

                if matched_field:
                    self.custom_field_ids[custom_field] = matched_field["id"]
                    field_schema = matched_field["schema"]
                    custom_field_type = (
                        field_schema["custom"].split(":")[1]
                        if "custom" in field_schema
                        else None
                    )

                    if custom_field_type in ["select", "radiobuttons"]:
                        self.custom_fields_values[custom_field] = {
                            "value": custom_field_value
                        }

                    elif custom_field_type in ["multicheckboxes", "multiselect"]:
                        self.custom_fields_values[custom_field] = [
                            {"value": item.strip()}
                            for item in custom_field_value.split(",")
                        ]

                    elif custom_field_type == "labels":
                        self.custom_fields_values[
                            custom_field
                        ] = custom_field_value.split(",")

                    elif custom_field_type == "float" and self.is_valid_number(
                        custom_field_value
                    ):
                        self.custom_fields_values[custom_field] = float(
                            custom_field_value
                        )
            self.logger.debug("Ids of custom fields = {}".format(self.custom_field_ids))
        else:
            self.logger.error(
                "{}Failed to fetch the ids of the custom fields. Error Message = {}".format(
                    self.correlation_id, response.text
                )
            )
            sys.exit(1)

    def create_jira_issue(self):
        """This method creates the jira issue"""

        self.logger.info("Started Alert Action for Jira Issue Create")
        if not (self.project_key and self.issue_type and self.summary):
            self.logger.error(
                "{}Please provide the value for the fields: Project key, Issue type, Summary.".format(
                    self.correlation_id
                )
            )
            sys.exit(1)

        self.validate_project()

        payload = self.create_payload()
        jira_issue_url = jcc.JIRA_ISSUE_CREATE_ENDPOINT.format(self.domain)

        response = self.make_api_request("POST", jira_issue_url, payload=payload)

        if response.status_code == 201:
            jira_issue_res = response.json()
            self.logger.info(
                "{}Successfully created Jira Issue: {}".format(
                    self.correlation_id,
                    jcc.JIRA_ISSUE_ENDPOINT.format(self.domain, jira_issue_res["key"]),
                )
            )
            if self.return_response:
                return {
                    "jira_issue_link": jcc.JIRA_ISSUE_ENDPOINT.format(
                        self.domain, jira_issue_res["key"]
                    ),
                    "jira_issue_key": jira_issue_res["key"],
                    "correlation_id": self.correlation_id[:-2],
                }
        else:
            self.logger.error(
                "{}Failed to create the Jira Issue. Error Message = {}".format(
                    self.correlation_id, response.text
                )
            )
            sys.exit(1)

        self.logger.info("Completed Alert Action for Jira Issue Create")

    def update_jira_issue(self):
        """This method updates the jira issue"""

        self.logger.info("Started Alert Action for Jira Issue Update")

        if self.jira_status:
            transition_payload = self.validate_status()
            self.logger.debug("transition_payload = {}".format(transition_payload))

        payload = self.create_payload()

        jira_issue_url = jcc.JIRA_ISSUE_UPDATE_ENDPOINT.format(
            self.domain, self.jira_key
        )
        response = self.make_api_request("PUT", jira_issue_url, payload=payload)

        if response.status_code == 204:
            self.logger.info(
                "{}Successfully updated the Jira Issue: {}".format(
                    self.correlation_id,
                    jcc.JIRA_ISSUE_ENDPOINT.format(self.domain, self.jira_key),
                )
            )

            if self.jira_status:
                self.logger.info(
                    "Proceeding to transition the jira ({}) to ({}) status.".format(
                        self.jira_key,
                        self.jira_status,
                    )
                )
                transition_url = jcc.JIRA_ISSUE_TRANSITION_ENDPOINT.format(
                    self.domain, self.jira_key
                )
                transition_response = self.make_api_request(
                    "POST", transition_url, payload=transition_payload
                )

                if transition_response.status_code == 204:
                    self.logger.info(
                        "{}Successfully updated the status of Jira Issue: {}".format(
                            self.correlation_id,
                            jcc.JIRA_ISSUE_ENDPOINT.format(self.domain, self.jira_key),
                        )
                    )
                else:
                    self.logger.error(
                        "{}Failed to update the status of Jira Issue. Error Message = {}".format(
                            self.correlation_id, transition_response.text
                        )
                    )
                    sys.exit(1)

            if self.return_response:
                return {
                    "jira_issue_link": jcc.JIRA_ISSUE_ENDPOINT.format(
                        self.domain, self.jira_key
                    ),
                    "jira_issue_key": self.jira_key,
                    "correlation_id": self.correlation_id[:-2],
                }
        else:
            self.logger.error(
                "{}Failed to update the Jira Issue. Error Message = {}".format(
                    self.correlation_id, response.text
                )
            )
            sys.exit(1)

        self.logger.info("Completed Alert Action for Jira Issue Update")

    def jira_cloud_alert_action(self):
        """This method creates or updates the jira issue"""

        if not self.token:
            self.logger.error(
                "{}API token is not selected. Please select the API token.".format(
                    self.correlation_id
                )
            )
            sys.exit(1)
        self.api_token_details = utils.get_api_token_details(
            self.session_key, self.logger, self.token
        )
        self.domain = self.api_token_details["domain"]
        if self.jira_key:
            response = self.update_jira_issue()
        else:
            response = self.create_jira_issue()

        if self.return_response:
            return response
