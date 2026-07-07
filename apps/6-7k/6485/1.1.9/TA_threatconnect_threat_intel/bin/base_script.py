"""ThreatConnect Generating Module"""

# standard library
import io
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib_1_1_9"))

# third-party
import re

from checkpoint_manager import CheckpointManager
from password_manager import PasswordManager
from splunklib import results
from splunklib.modularinput import EventWriter, Script
from threatconnect_splunk.collections.settings import Settings
from threatconnect_splunk.request.tc_request import TcRequest
from threatconnect_splunk.session.tc_session import TcSession
from threatconnect_splunk.utils import Utils


class BaseScript(Script):
    """Base Generating Class."""

    # properties
    _session = None
    _request = None
    _settings = None
    password_manager = PasswordManager()
    checkpoint_manager = CheckpointManager()
    job_uuid = None
    tracker = None
    utils = Utils()
    filename = os.path.basename(__file__)
    event_writer: EventWriter = None
    # logger.root  # pylint: disable=pointless-statement
    # logger.root.setLevel(logger.DEBUG)
    # formatter = logger.Formatter('%(levelname)s %(message)s')
    # handler = logger.StreamHandler(stream=sys.stderr)
    # handler.setFormatter(formatter)
    # logger.root.addHandler(handler)

    def get_scheme(self):
        """Must be overridden"""
        raise NotImplementedError("get_scheme is not implemented.")

    def stream_events(self, inputs, ew):
        """Must be overridden"""
        raise NotImplementedError("stream_events is not implemented.")

    @property
    def request(self):
        """Return an instance of the Request Class.

        A wrapper on the Python Request Module specifically for interacting with the
        ThreatConnect API.  However, this can also be used for connecting to other
        API endpoints.

        Returns:
            (object): An instance of Request Class
        """
        if self._request is None:
            self._request = TcRequest(self.session, self.log)
        return self._request

    @property
    def session(self):
        """Return an instance of Requests Session configured for the ThreatConnect API."""
        if self._session is None:
            self._session = TcSession(self.service, self.log)
        return self._session

    @property
    def settings(self):
        """Return an instance of Requests Session configured for the ThreatConnect API."""
        if self._settings is None:
            self._settings = Settings(self.service, self.log).get()
        return self._settings

    def search(self, search, **kwargs):
        """Execute a Splunk Search."""
        self.service.parse(search, parse_only=True)
        job = self.service.jobs.create(search, **kwargs)
        while True:
            while not job.is_ready():
                pass

            stats = {
                "is-done": job["isDone"],
                "done-progress": float(job["doneProgress"]) * 100,
                "scan-count": job["scanCount"],
                "event-count": job["eventCount"],
                "result-count": job["resultCount"],
            }
            time.sleep(10)
            if job["isDone"] == "1":
                self.log("debug", "running-search:metrics", stats)
                break

        return job

    def iterate(self, job):
        count = 50_000
        offset = 0
        result_count = int(job["resultCount"])
        self.log("info", "running-search:total", {"result-count": result_count})
        while offset < result_count:
            self.log(
                "info",
                "running-search:paginate",
                {"result-offset": offset, "result-count": result_count},
            )
            kwargs_paginate = {"count": count, "offset": offset}
            for result in results.JSONResultsReader(
                io.BufferedReader(job.results(**kwargs_paginate, output_mode="json"))
            ):
                if isinstance(result, results.Message):
                    # handle error
                    self.log("error", "job-error", f"{result}")
                    continue
                yield result
            offset += count

    def transform_log_key(self, key):
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
            self.log("error", "transform-log-key", f'error="{e}"')
            slug = key
        return slug

    def log(self, level, event, details):
        """Log the provided message under the provided level with a common prefix."""

        log_msg = {"app": "TA_threatconnect_threat_intel", "event": f'"{event}"'}
        if isinstance(details, dict):
            for key, value in details.items():
                key = self.transform_log_key(key)
                value = str(value)
                if "." in str(value):
                    try:
                        value = float(value)
                        value = f"{value:,}"
                    except ValueError:
                        pass
                else:
                    try:
                        value = int(value)
                        value = f"{value:,}"
                    except ValueError:
                        pass
                value = str(value).replace('"', "''")
                log_msg[key] = f'"{value}"'
        else:
            log_msg.update({"message": f'"{details}"'})

        if self.tracker:
            if self.tracker.job_name:
                log_msg.update({"tc_collection_name": f'"{self.tracker.job_name}"'})
            if self.tracker.start_time:
                log_msg.update(
                    {"tc_job_id": f'"{self.tracker.start_time.timestamp()}"'}
                )

        log_msg = ", ".join([f"{k}={v}" for k, v in log_msg.items()])
        self.event_writer.log(level.upper(), log_msg)
