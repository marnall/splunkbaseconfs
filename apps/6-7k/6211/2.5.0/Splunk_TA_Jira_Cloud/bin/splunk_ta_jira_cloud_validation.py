#
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import jira_cloud_utils as utils
import jira_cloud_consts as jcc
from jira_cloud_connect import Connect
from splunktaucclib.rest_handler.error import RestError


class Validator:
    def __init__(self, *, session_key) -> None:
        self.logger = utils.set_logger(session_key, jcc.JIRA_CLOUD_VALIDATION)
        self.proxy_settings = utils.get_proxy_settings(session_key, self.logger)
        self.connect = Connect(logger=self.logger, proxy=self.proxy_settings)

    def validate_domain(self, *, domain):
        if domain.endswith(".atlassian.net"):
            msg = "Only the domain name (e.g. your-domain, not your-domain.atlassian.net) is required."
            self.logger.error(msg)
            raise RestError(400, msg)
        self.connect.get(
            domain=domain,
            what_action=f"validate domain '{domain}' (checked url: '{Connect.build_url(domain=domain)}')",
        )

    def validate_token(self, *, domain, username, token):
        self.validate_domain(domain=domain)
        self.connect.get(
            domain=domain,
            endpoint=jcc.JIRA_ISSUES_GET_TIMEZONE,
            username=username,
            token=token,
            what_action=f"validate all api token data for domain '{domain}' and username '{username}'",
        )
