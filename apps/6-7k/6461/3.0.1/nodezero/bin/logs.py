"""Logging configuration via solnlib."""

import logging

from solnlib import conf_manager, log

APP_NAME = "nodezero"
CONF_NAME = "nodezero_settings"


def set_up_logging(session_key):
    logger = log.Logs().get_logger(APP_NAME)
    loglevel_name = conf_manager.get_log_level(
        logger=logger,
        session_key=session_key,
        app_name=APP_NAME,
        conf_name=CONF_NAME,
    )
    loglevel = logging.getLevelName(loglevel_name)
    log.Logs().set_level(loglevel, APP_NAME)
    return logger
