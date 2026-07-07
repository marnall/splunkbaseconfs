#
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import traceback

import jira_cloud_utils as utils
import requests
import splunk.admin as admin
from requests.auth import HTTPBasicAuth
from splunktaucclib.rest_handler.error import RestError
import jira_cloud_consts as jcc


class Connect:
    def __init__(self, *, logger, proxy) -> None:
        self.logger = logger
        self.proxy = proxy

    @staticmethod
    def build_hostname(*, domain):
        return f"{domain}.atlassian.net"

    @staticmethod
    def build_url(*, domain, endpoint="", params={}):
        p = ""
        for i, k in enumerate(params):
            prefix = "?" if i == 0 else "&"
            p += f"{prefix}{k}={params[k]}"
        return f"https://{Connect.build_hostname(domain=domain)}{endpoint}{p}"

    def _get(self, *, url, username, token, proxy):
        if username and token:
            auth = HTTPBasicAuth(username, token)
            headers = {"Accept": "application/json"}
            return requests.request(
                "GET", url, headers=headers, auth=auth, proxies=proxy
            )
        return requests.request("GET", url, proxies=proxy)

    def get(
        self,
        *,
        domain,
        endpoint="",
        params={},
        username=None,
        token=None,
        what_action=None,
    ):
        url = Connect.build_url(domain=domain, endpoint=endpoint, params=params)

        if not what_action:
            what_action = f"process GET HTTP request to {url}"
        try:
            r = self._get(url=url, username=username, token=token, proxy=self.proxy)
            if r.status_code in (400, 429):
                self.logger.error(
                    "Response received with status code {} = {}".format(
                        r.status_code, r.text
                    )
                )
            if r:
                self.logger.debug(f"Successfully {what_action}")
                return r
            else:
                msg = f"Failed to {what_action}"
                self.logger.warning(msg + traceback.format_exc())
                raise RestError(r.status_code, msg)
        except Exception as e:
            msg = f"Failed to connect to {what_action}"
            utils.add_ucc_error_logger(
                logger=self.logger,
                logger_type=jcc.CONNECTION_ERROR,
                exception=e,
                msg_before=msg + traceback.format_exc(),
            )
            raise RestError(400, msg)
