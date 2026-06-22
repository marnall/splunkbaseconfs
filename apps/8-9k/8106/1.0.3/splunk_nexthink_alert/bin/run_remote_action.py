from shlex import shlex
from nexthink import Nexthink
from account_info import AccountInfo
import logging
from logging.config import dictConfig
import os
from pathlib import Path

SPLUNK_HOME = os.environ.get("SPLUNK_HOME", "/opt/splunk")
LOG_FILE = Path(SPLUNK_HOME) / "var" / "log" / "splunk" / "run_remote_action.log"

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
            "level": "DEBUG",
            "propagate": False,
        },  # Root logger
        "Nexthink": {
            "handlers": ["default"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}


def parse_params(value, item_sep=";", value_sep="="):
    if value is None or not value.strip():
        return {}

    lexer = shlex(value, posix=True)
    lexer.whitespace = item_sep
    lexer.wordchars += value_sep

    return dict(word.split(value_sep, maxsplit=1) for word in lexer)


def transform(self, events):
    valid_levels = ["DEBUG", "INFO", "ERROR"]
    log_level = self.log_level.upper()
    if log_level not in valid_levels:
        self.write_error(
            f"Invalid log_level: '{self.log_level}'. Valid values: {valid_levels}"
        )
        return
    new_log_config = DEFAULT_LOG_CONFIG.copy()
    new_log_config["loggers"].update(
        {
            "RunremoteactionCommand": {
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
        }
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

        account = AccountInfo(self.service, self.account)
        nexthink = Nexthink(account.nexthink_host)
        nexthink.authorize(account.client_id, account.client_secret)

        device_uids = []
        debug(f"device_uid: {self.device_uid}")
        for event in events:
            self.logger.debug(event, extra={"sid": self.metadata.searchinfo.sid})
            device_uids.append(event.get(self.device_uid))
        self.logger.debug(f"device_uids: {device_uids}")
        yield nexthink.execute_remote_action(
            self.remote_action_id,
            device_uids,
            parse_params(self.params),
            self.reason,
            self.external_reference,
            self.expires_in_minutes,
            self.external_source,
        )
    except Exception as e:
        yield {"error": str(e)}
        error(f"Error: {str(e)}")
