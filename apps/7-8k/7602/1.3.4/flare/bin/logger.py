import logging
import os
import tempfile

from constants import APP_NAME
from logging.handlers import TimedRotatingFileHandler
from typing import Any


class Logger:
    def __init__(self, *, class_name: str) -> None:
        splunk_home = os.environ.get("SPLUNK_HOME")
        log_filepath = ""
        if splunk_home:
            log_filepath = os.path.join(
                splunk_home, "var", "log", "splunk", f"{APP_NAME}.log"
            )
        else:
            log_filepath = os.path.join(tempfile.gettempdir(), f"{APP_NAME}.log")

        self.tag_name = os.path.splitext(os.path.basename(class_name))[0]
        self._logger = logging.getLogger(f"flare-{self.tag_name}")

        if os.environ.get("FLARE_ENV") == "dev":
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s %(levelname)-5s %(message)s")
        handler = TimedRotatingFileHandler(
            log_filepath, when="d", interval=1, backupCount=5
        )
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)

    def debug(self, msg: Any) -> None:
        self._logger.debug(msg=f"{self.tag_name}: {msg}")

    def info(self, msg: Any) -> None:
        self._logger.info(msg=f"{self.tag_name}: {msg}")

    def warning(self, msg: Any) -> None:
        self._logger.warning(msg=f"{self.tag_name}: {msg}")

    def error(self, msg: Any) -> None:
        self._logger.error(msg=f"{self.tag_name}: {msg}")

    def exception(self, msg: Any) -> None:
        self._logger.exception(msg=f"{self.tag_name}: {msg}")

    def critical(self, msg: Any) -> None:
        self._logger.critical(msg=f"{self.tag_name}: {msg}")
