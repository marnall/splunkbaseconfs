#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import import_declare_test

import os
import sys
from palo_utils import logger_instance, get_proxy_settings, get_account_credentials
from firewall_client import FirewallClient
import splunk.Intersplunk as sI

bin_dir = os.path.basename(__file__)

logger = logger_instance("pancontentpack")


def main():
    _, _, settings = sI.getOrganizedResults()
    args, _ = sI.getKeywordsAndOptions()
    session_key = settings["sessionKey"]
    proxy_config = get_proxy_settings(logger, session_key)
    firewall_credentials = get_account_credentials(
        session_key, args[0], "firewall_account", logger
    )
    firewall_client = FirewallClient(
        host=args[0],
        username=firewall_credentials.get("username"),
        password=firewall_credentials.get("password"),
        logger=logger,
        proxy=proxy_config,
    )
    csv = firewall_client.get_predefined_threats_or_applications(args[1])
    sI.outputResults(csv)


if __name__ == "__main__":
    main()
