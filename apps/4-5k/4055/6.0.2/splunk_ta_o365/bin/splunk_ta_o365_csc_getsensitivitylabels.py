#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
import time

import splunk_ta_o365_bootstrap

from splunk_ta_o365.common.portal import O365PortalRegistry
from splunk_ta_o365.common.tenant import O365Tenant
from splunk_ta_o365.common.settings import Proxy, APP_NAME
from splunklib.binding import HTTPError
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)
from splunksdc import logging
from splunksdc.config import ConfigManager

logging.setup_root_logger(app_name=APP_NAME, stanza_name="getsensitivitylabel")
logger = logging.get_module_logger()


@Configuration()
class GetSensitivityLabelsCommand(GeneratingCommand):
    """
    The getsensitivitylabels command collects O365 sensitivity labels

    Example:

    ``| getsensitivitylabels tenant_name="my_tenant"``

    Collect O365 organization sensitivity labels
    """

    tenant_name = Option(
        require=True, validate=validators.Match("tenant", r"(?!^$)([^\s])")
    )

    logger.set_level(logging.INFO)

    def generate(self):
        config = ConfigManager(self.service)

        try:
            tenant = O365Tenant.create(config, self.tenant_name)
        except HTTPError as ex:
            msg = f"Could not find object id={self.tenant_name}"
            if msg in ex.body.decode("utf-8"):
                raise ValueError(msg)
            logger.error(f"{ex.status} {ex.reason} - {ex.body}", exception=ex)
            raise ValueError(ex.body)

        registry = O365PortalRegistry.load(config)
        try:
            graph = tenant.create_graph_portal(registry)
        except ValueError as ex:
            logger.warning(
                f"This API is available only under 'Worldwide' cloud deployment. Message: {ex}"
            )
            logger.error(
                "Please check the provided tenant has endpoint=Worldwide and try again",
                exception=ex,
            )
            sys.exit(1)

        policy = tenant.create_v2_token_policy(registry)
        token = graph.create_graph_token_provider(policy)

        proxy = Proxy.load(config)
        session = proxy.create_requests_session()
        session.headers.update({"user-agent": "splunk_ta_o365"})
        session = token.auth(session)

        path = "/beta/security/informationProtection/sensitivityLabels"
        portal = graph.get_graph_portal_communications()
        labels = portal.o365_graph_api({}, None, path)
        # Assuming there is no next_link / No pagination expected here. TBC
        items, next_link = labels.throttled_get(session)
        for item in items:
            # Assuming all keys (incl. parents) will be returned anyway
            # -> Ignore keys beginning with parent
            result = {k: v for k, v in item.items() if not k.startswith("parent")}
            result["_raw"] = f"{result}"
            result["_time"] = time.time()

            yield result


dispatch(GetSensitivityLabelsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
