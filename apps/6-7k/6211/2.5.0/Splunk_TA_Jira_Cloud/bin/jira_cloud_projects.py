#
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import requests
import json
import import_declare_test  # noqa
import splunk.admin as admin
import jira_cloud_utils as utils
import jira_cloud_consts as jcc
from requests.auth import HTTPBasicAuth

APP_NAME = import_declare_test.ta_name


class JiraProjects(admin.MConfigHandler):
    param = "api_token"

    def setup(self):
        self.supportedArgs.addOptArg(self.param)

    def handleList(self, conf_info):
        session_key = self.getSessionKey()
        logger = utils.set_logger(session_key, jcc.JIRA_CLOUD_RH_INPUT_VALIDATION)

        logger.debug("Getting proxy settings")
        proxy = utils.get_proxy_settings(session_key, logger)
        if not self.callerArgs or not self.callerArgs.get("api_token"):
            logger.error("Missing Jira credentials")
            raise Exception("Missing Jira credentials")

        projects = []

        api_token_details = utils.get_api_token_details(
            session_key, logger, self.callerArgs.get("api_token")[0]
        )
        logger.info("Start listing jira projects")

        url = jcc.JIRA_PROJECT_SEARCH_ENDPOINT.format(
            api_token_details["domain"], jcc.API_VERSION
        )

        auth = HTTPBasicAuth(api_token_details["username"], api_token_details["token"])

        headers = {"Accept": "application/json"}

        while url:
            response = requests.request(
                "GET", url, headers=headers, auth=auth, proxies=proxy
            )

            res_json = json.loads(response.text)

            for project in res_json["values"]:
                projects.append(project["key"])

            url = res_json.get("nextPage")

        logger.info(
            'Total Projects under "{}" domain  = {}'.format(
                api_token_details["domain"], len(projects)
            )
        )
        if projects:
            logger.debug(
                'Projects List under "{}" domain = {}'.format(
                    api_token_details["domain"], projects
                )
            )
            for project in projects:
                conf_info[project].append("projects", project)

        logger.info("End of listing jira projects")


def main():
    admin.init(JiraProjects, admin.CONTEXT_NONE)
