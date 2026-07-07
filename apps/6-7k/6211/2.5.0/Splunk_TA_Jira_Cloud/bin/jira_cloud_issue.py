##
## SPDX-FileCopyrightText: 2025 Splunk LLC.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test  # isort: skip # noqa: F401

import os
import sys
import json
import jira_cloud_issue_helper
import traceback
from splunktaucclib.alert_actions_base import ModularAlertBase


class AlertActionWorkerJira_Cloud_Issue_alert(ModularAlertBase):
    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerJira_Cloud_Issue_alert, self).__init__(
            ta_name, alert_name
        )

    def process_event(helper, *args, **kwargs):
        try:
            events = [list(event.items()) for event in helper.get_events()]
            jira_cloud_issue_helper.JiraCloudIssueHelper(
                helper.settings,
                events,
            ).jira_cloud_alert_action()
        except Exception:
            return traceback.format_exc()


if __name__ == "__main__":
    exitcode = AlertActionWorkerJira_Cloud_Issue_alert(
        "Splunk_TA_Jira_Cloud", "jira_cloud_issue"
    ).run(sys.argv)
    sys.exit(exitcode)
