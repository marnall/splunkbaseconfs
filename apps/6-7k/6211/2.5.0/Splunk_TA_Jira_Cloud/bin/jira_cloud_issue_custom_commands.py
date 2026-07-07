##
## SPDX-FileCopyrightText: 2025 Splunk LLC.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test
import sys

from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option
from jira_cloud_issue_helper import JiraCloudIssueHelper

import jira_cloud_utils as utils
import jira_cloud_consts as jcc


@Configuration()
class JiraCloudIssue(EventingCommand):
    api_token = Option(name="api_token", default="", require=True)
    project_key = Option(name="project_key", default="", require=False)
    issue_type = Option(name="issue_type", default="", require=False)
    summary = Option(name="summary", default="", require=False)
    priority = Option(name="priority", default="", require=False)
    parent = Option(name="parent", default="", require=False)
    description = Option(name="description", default="", require=False)
    label = Option(name="label", default="", require=False)
    component = Option(name="component", default="", require=False)
    custom_fields = Option(name="custom_fields", default="", require=False)
    jira_key = Option(name="jira_key", default="", require=False)
    correlation_id = Option(name="correlation_id", default="", require=False)
    status = Option(name="status", default="", require=False)
    include_events_in_description = Option(
        name="include_events_in_description", default="0", require=False
    )

    def transform(self, records):
        session_key = self._metadata.searchinfo.session_key

        logger = utils.set_logger(
            session_key,
            jcc.JIRA_CLOUD_CUSTOM_COMMAND,
        )

        payload = {}
        configuration = {}

        configuration["api_token"] = self.api_token
        configuration["project_key"] = self.project_key
        configuration["issue_type"] = self.issue_type
        configuration["summary"] = self.summary
        configuration["priority"] = self.priority
        configuration["parent"] = self.parent
        configuration["description"] = self.description
        configuration["label"] = self.label
        configuration["component"] = self.component
        configuration["custom_fields"] = self.custom_fields
        configuration["jira_key"] = self.jira_key
        configuration["status"] = self.status
        configuration["correlation_id"] = self.correlation_id
        configuration[
            "include_events_in_description"
        ] = self.include_events_in_description

        payload["configuration"] = configuration
        payload["logger"] = logger
        payload["return_response"] = True

        logger.info(f"Jira Issue Payload: {payload}")

        payload["session_key"] = session_key

        results = JiraCloudIssueHelper(payload).jira_cloud_alert_action()

        yield results


dispatch(JiraCloudIssue, sys.argv, sys.stdin, sys.stdout, __name__)
