import time
from nexthink import Nexthink

from account_info import AccountInfo

import logging
from logging.config import dictConfig
import os
from pathlib import Path

SPLUNK_HOME = os.environ.get("SPLUNK_HOME", "/opt/splunk")
LOG_FILE = Path(SPLUNK_HOME) / "var" / "log" / "splunk" / "list_remote_actions.log"

DEFAULT_LOG_CONFIG = {
    "version": 1,
    "formatters": {
        "default": {"format": "%(asctime)s - %(levelname)s - %(name)s: %(message)s"},
        "cmd": {
            "format": "%(asctime)s - %(levelname)s - %(name)s - %(sid)s: %(message)s"
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_FILE),
            "maxBytes": 102400,
            "backupCount": 3,
        },
        "cmd": {
            "formatter": "cmd",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_FILE),
            "maxBytes": 102400,
            "backupCount": 3,
        },
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": "NOTSET",
            "propagate": False,
        },  # Root logger
        "Nexthink": {
            "handlers": ["default"],
            "level": "NOTSET",
            "propagate": False,
        },
    },
}


def generate(self):
    new_log_config = DEFAULT_LOG_CONFIG.copy()
    valid_levels = ["DEBUG", "INFO", "ERROR"]
    log_level = self.log_level.upper()
    if log_level not in valid_levels:
        self.write_error(
            f"Invalid log_level: '{self.log_level}'. Valid values: {valid_levels}"
        )
        return

    new_log_config["loggers"].update(
        {
            "ListremoteactionsCommand": {
                "handlers": ["cmd"],
                "level": log_level,
                "propagate": False,
            },
            "Nexthink": {
                "handlers": ["default"],
                "level": log_level,
                "propagate": False,
            },
            "AccountInfo": {
                "handlers": ["default"],
                "level": log_level,
                "propagate": False,
            },
        },
    )
    dictConfig(new_log_config)
    self._logger = logging.getLogger(self.__class__.__name__)

    def debug(msg):
        self._logger.debug(msg, extra={"sid": self.metadata.searchinfo.sid})

    def info(msg):
        self._logger.info(msg, extra={"sid": self.metadata.searchinfo.sid})

    def error(msg):
        self._logger.error(msg, extra={"sid": self.metadata.searchinfo.sid})

    try:
        if self.service is None:
            raise ValueError("Service not created.")

        debug("Start")
        accounts = [x.strip() for x in self.account.split(",")]

        if self.account.upper() == "ALL":
            debug("Getting all accounts.")
            accounts = [x.name for x in self.service.confs[AccountInfo.get_conf_name()]]

        debug(f"accounts: {accounts}")
        for account_name in accounts:
            debug(f"Getting remote action for account: {account_name}")
            account = AccountInfo(self.service, account_name)
            nexthink = Nexthink(account.nexthink_host)
            nexthink.authorize(account.client_id, account.client_secret)
            cur = time.time()

            for remote_action in nexthink.get_remote_actions():
                targeting = remote_action.get("targeting")
                if targeting is None or not targeting.get("apiEnabled", False):
                    continue
                _raw = {
                    "_time": cur,
                    "_raw": remote_action,
                    "id": remote_action.get("id"),
                    "name": remote_action.get("name"),
                    "account": account_name,
                }
                yield _raw
        debug("End")

    except Exception as e:
        error(f"Error: {str(e)}")
        self.write_error(f"{str(e)}")
