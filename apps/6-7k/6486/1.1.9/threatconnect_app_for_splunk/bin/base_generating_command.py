#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Generating Module"""

# standard library
import logging
import logging.handlers
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib_1_1_9"))

# third-party
import splunk
from splunklib.searchcommands import GeneratingCommand, Option
from threatconnect_splunk import TCS


class BaseGeneratingCommand(GeneratingCommand):
    """Base Generating Class."""

    # args
    _log_level = Option(default="info", doc="The logging level.", require=False)

    # properties
    _tcs = None
    _tc_logger = None
    execution_summary = {}
    filename = os.path.basename(__file__)
    log: logging.Logger
    results = []
    splunk_home = Path(os.environ["SPLUNK_HOME"])
    started_flag = False  # flag to indicate if the command has started

    # log data default
    _command = ""
    _job_id = str(time.time()).replace(".", "")
    _start_time = time.time()
    log_data_default = {}

    def _setup_logger(self):
        """Splunk logger
        https://dev.splunk.com/enterprise/docs/developapps/addsupport/logging/loggingsplunkextensions/
        """
        logging_default_config_file = self.splunk_home / "etc" / "log.cfg"
        logging_local_config_file = self.splunk_home / "etc" / "log-local.cfg"
        logging_file_name = "threatconnect_app_for_splunk.log"
        # logging_format = '%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s'
        logging_format = (
            "%(asctime)s - %(name)s - %(levelname)8s - %(message)s "
            # '(%(filename)s:%(funcName)s:%(lineno)d)'
        )
        logging_path = self.splunk_home / "var" / "log" / "splunk" / logging_file_name

        # define the splunk logging handler
        splunk_log_handler = logging.handlers.RotatingFileHandler(
            logging_path, mode="a"
        )
        splunk_log_handler.setFormatter(logging.Formatter(logging_format))

        self.log = logging.getLogger("threatconnect_app_for_splunk")
        self.log.addHandler(splunk_log_handler)
        self.log.level = logging.getLevelName(self._log_level.upper())
        # wrapping paths in str because Path may not be supported in setupSplunkLogger
        splunk.setupSplunkLogger(
            self.log,
            str(logging_default_config_file),
            str(logging_local_config_file),
            "python",
        )

    def finish(self):
        """Implement finish method."""
        if self.metadata.action.lower() == "execute":
            self.execution_summary["execution_seconds"] = round(
                time.time() - self._start_time, 4
            )
            self.log_data("INFO", "execution-summary", self.execution_summary)
        super().finish()

    def prepare(self):
        """Implement prepare method."""
        super().prepare()

        # setup logger
        self._setup_logger()

        # splunk dispatch seems to call the command multiple times before service is available
        if self.metadata.action.lower() != "execute":
            return False

        search = self.metadata.searchinfo.search.strip("\n") or ""
        if len(search) > 256:
            search = f"{search[:253]}..."
        self.log_data(
            "INFO",
            "started",
            {"search": search, "search_action": self.metadata.action.lower()},
        )
        return True

    @property
    def tc_logger(self):
        class TCLogger:
            def __init__(self, logger):
                self.logger = logger
                self.app_name = "ThreatConnect App for Splunk"

            def log(self, level, message, event=None, **kwargs):
                """Log the provided message under the provided level with a common prefix."""
                params = locals()
                if "level" in params:
                    del params["level"]
                if "self" in params:
                    del params["self"]
                log_msg = [f'app="{self.app_name}"']
                for key, value in params.items():
                    if key == "kwargs":
                        continue
                    if value:
                        log_msg.append(f'{key}="{value}')
                for key, value in kwargs.items():
                    if value:
                        log_msg.append(f'{key}="{value}')

                log_msg = ", ".join(log_msg)
                self.logger.__getattribute__(level.lower())(log_msg)

            def debug(self, msg, event=None, **kwargs):
                self.log("DEBUG", msg, event, **kwargs)

            def info(self, msg, event=None, **kwargs):
                self.log("INFO", msg, event, **kwargs)

            def warning(self, msg, event=None, **kwargs):
                self.log("WARNING", msg, event, **kwargs)

            def error(self, msg, event=None, **kwargs):
                self.log("ERROR", msg, event, **kwargs)

        if not self._tc_logger:
            self._tc_logger = TCLogger(self.logger)

        return self._tc_logger

    @property
    def tcs(self):
        """Instance of ThreatConnect Splunk Module."""
        if self._tcs is None:
            self._tcs = TCS(logger=self.logger, service=self.service)
        return self._tcs

    def log_data(self, level: str, event: str, details: dict):
        """Log the provided message under the provided level with a common prefix."""
        log_msg = {
            "app": '"threatconnect_app_for_splunk"',
            "command": f'"{self._command}"',
            "job_id": f'"{self._job_id}"',
            "event": f'"{event}"',
        }
        log_msg.update(self.log_data_default)
        for key, value in details.items():
            key = self.log_transform_key(key)
            value = str(value)
            if "." in str(value):
                try:
                    value = float(value)
                    value = f"{value:,}"
                except ValueError:
                    pass
            elif "epoch" not in key.lower() and str(value).isdigit():
                try:
                    value = int(value)
                    value = f"{value:,}"
                except ValueError:
                    pass
            value = str(value).replace('"', "''")
            log_msg[key] = f'"{value}"'

        log_msg = ", ".join([f"{k}={v}" for k, v in log_msg.items()])
        self.log.log(logging.getLevelName(level.upper()), log_msg)

    def log_execution_time(
        self, action: str, start_time: float, details: Optional[dict] = None
    ):
        """Log the execution time."""
        details = details or {}
        execution_time = time.time() - start_time
        details.update({"execution-seconds": round(execution_time, 2)})
        self.log_data("DEBUG", action, details)

    def log_transform_key(self, key):
        """Normalizes the key provided for logging purposes.

        Examples:
        - "Result Count" -> "result_count"
        - "ResultCount" -> "result_count"
        - "resultCount" -> "result_count"
        - "result_count" -> "result_count"
        - "result-count" -> "result_count"
        """
        try:
            # Replace uppercase letters with lowercase preceded by a hyphen
            slug = re.sub(r"([A-Z])", r"_\1", key).lower()
            # Replace spaces with hyphens
            slug = re.sub(r"\s+", "_", slug)
            # Remove leading hyphen if present
            slug = slug.lstrip("_")
            # replace hyphen with underscore
            slug = slug.replace("-", "_")
            # Remove double hyphens if present
            # These would be present for cases like "Result Count" -> "result--count"
            slug = slug.replace("__", "_")
            if not slug.startswith("tc"):
                slug = f"tc_{slug}"
        except Exception as e:
            self.log.error(f'transform-log-key, error="{e}"')
            slug = key
        return slug
