#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import os
import os.path
import sys
import uuid

try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
except ImportError:
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

import remedy_consts as c
from solnlib import log
from splunk.clilib import cli_common as cli

sys.path.append(make_splunkhome_path(["etc", "apps", c.APP_NAME, "bin"]))


def get_remedy_settings_path(conf_type):
    """
    Returns the path to the Remedy configuration file based on the type.
    @conf_type: 'local' or 'default'
    """
    return make_splunkhome_path(
        ["etc", "apps", c.APP_NAME, conf_type, c.REMEDY_CONF + ".conf"]
    )


def get_logger(log_name, set_invocation_id=False):
    """
    @log_name: which logger
    @set_invocation_id: Whether to include an invocation ID in the log format
    """
    log_file = "splunk_ta_remedy_" + log_name
    if set_invocation_id:
        invocation_id = uuid.uuid4().hex
        invocation_str = f"| [invocation_id={invocation_id}] %(message)s"
        new_log_format = log.Logs()._default_log_format.replace(
            "| %(message)s", invocation_str
        )
        log.Logs()._default_log_format = new_log_format

    logger = log.Logs().get_logger(log_file)

    logger.setLevel(c.DEFAULT_LOG_LEVEL)

    # Try to load the local settings, fall back to default if not found
    remedy_conf_path = get_remedy_settings_path("local")
    if os.path.exists(remedy_conf_path):
        remedy_conf = cli.readConfFile(remedy_conf_path)
        if remedy_conf.get("logging", {}).get("loglevel"):
            logger.setLevel(remedy_conf["logging"]["loglevel"])
        else:
            remedy_conf_path = get_remedy_settings_path("default")
            if os.path.exists(remedy_conf_path):
                remedy_conf = cli.readConfFile(remedy_conf_path)
                if remedy_conf.get("logging", {}).get("loglevel"):
                    logger.setLevel(remedy_conf["logging"]["loglevel"])

    return logger
