##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test
import os

from solnlib import conf_manager, log

DEFAULT_LOG_LEVEL = "INFO"
APP_NAME = import_declare_test.ta_name
SETTINGS_CONFIG_FILE = import_declare_test.SETTINGS_CONF


def setup_logging(session_key, filename):
    """
    This function sets up a logger with configured log level.
    :param filename: Name of the log file
    :return logger: logger object
    """
    logger = log.Logs().get_logger(filename)
    log_level = conf_manager.get_log_level(
        logger=logger,
        session_key=session_key,
        app_name=APP_NAME,
        conf_name=SETTINGS_CONFIG_FILE,
        default_log_level=DEFAULT_LOG_LEVEL,
    )
    logger.setLevel(log_level)
    return logger
