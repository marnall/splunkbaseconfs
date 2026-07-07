#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import os
import sys
import time
import json
import requests

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# Networking imports
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_oneshot_executor.log" % splunkhome,
    mode="a",
    maxBytes=10000000,
    backupCount=1,
)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(filename)s %(funcName)s %(lineno)d %(message)s"
)
logging.Formatter.converter = time.gmtime
filehandler.setFormatter(formatter)
log = logging.getLogger()  # root logger - Good to get it only once.
for hdlr in log.handlers[:]:  # remove the existing file handlers
    if isinstance(hdlr, logging.FileHandler):
        log.removeHandler(hdlr)
log.addHandler(filehandler)  # set the new handler
# set the log level to INFO, DEBUG as the default is ERROR
log.setLevel(logging.INFO)

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# import trackme libs
from trackme_libs import trackme_reqinfo


@Configuration(distributed=False)
class TrackMeTrackerExecutor(GeneratingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
    )

    report = Option(
        doc="""
        **Syntax:** **report=****
        **Description:** The report to be executed.""",
        require=True,
        default=None,
        validate=validators.Match("report", r"^.*$"),
    )

    earliest = Option(
        doc="""
        **Syntax:** **earliest=****
        **Description:** The earliest time for the search.""",
        require=False,
        default=None,
    )

    latest = Option(
        doc="""
        **Syntax:** **latest=****
        **Description:** The latest time for the search.""",
        require=False,
        default=None,
    )

    use_savedsearch_time = Option(
        doc="""
        **Syntax:** **use_savedsearch_earliest_latest=****
        **Description:** If the savedsearch has earliest and latest times, use them instead of the searchinfo earliest and latest times.""",
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    def generate(self, **kwargs):
        # performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Get the session key
        session_key = self._metadata.searchinfo.session_key

        # Header for requests
        header = {
            "Authorization": f"Splunk {session_key}",
            "Content-Type": "application/json",
        }

        # set earliest and latest
        if not self.earliest:
            earliest = self._metadata.searchinfo.earliest_time
        else:
            earliest = self.earliest

        if not self.latest:
            latest = self._metadata.searchinfo.latest_time
        else:
            latest = self.latest

        # Call our API endpoint to allow privilege escalation and run as system, if the user has access to admin endpoints
        try:
            json_data = {
                "tenant_id": self.tenant_id,
                "report": self.report,
            }
            if not self.use_savedsearch_time:
                json_data["earliest"] = earliest
                json_data["latest"] = latest
            else:
                json_data["use_savedsearch_time"] = True

            target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/vtenants/write/run_tenant_tracker"

            logging.info(f'tenant_id="{self.tenant_id}" calling {target_url} with data="{json.dumps(json_data, indent=0)}", requester="{self._metadata.searchinfo.username}"')

            response = requests.post(
                target_url,
                headers=header,
                verify=False,
                data=json.dumps(json_data),
                timeout=600,
            )

            # run_time
            run_time = round(time.time() - start, 3)

            try:
                response_json = response.json()

                # yield
                data = {
                    "_time": time.time(),
                    "_raw": {
                        "response": response_json,
                        "report": self.report,
                        "earliest": earliest,
                        "latest": latest,
                        "run_time": run_time,
                    },
                    "response": response_json,
                    "run_time": run_time,
                }
                yield data

                # End
                logging.info(
                    f'tenant_id="{self.tenant_id}" trackmeoneshotexecutor executed, status=success, run_time="{run_time}", requester="{self._metadata.searchinfo.username}", context="{json.dumps(json_data, indent=0)}", response="{json.dumps(response_json, indent=0)}"'
                )

            # the response may not generate an exception but still be not valid
            except Exception as e:
                error_msg = f"An exception was encountered, exception={response.text}"
                logging.error(
                    f"tenant_id={self.tenant_id}, {error_msg}, context={json.dumps(json_data, indent=2)}"
                )
                raise Exception(error_msg)

        except Exception as e:
            error_msg = f"An exception was encountered, exception={str(e)}"
            logging.error(
                f"tenant_id={self.tenant_id}, {error_msg}, context={json.dumps(json_data, indent=2)}"
            )
            raise Exception(error_msg)


dispatch(TrackMeTrackerExecutor, sys.argv, sys.stdin, sys.stdout, __name__)
