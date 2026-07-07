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
import json
import logging
import os
import sys
import time
import hashlib
from logging.handlers import RotatingFileHandler

# Third-party imports
import urllib3

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_collect.log" % splunkhome,
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
    StreamingCommand,
    Configuration,
    Option,
    validators,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo, trackme_gen_state


@Configuration(distributed=False)
class TrackMeCollect(StreamingCommand):
    index = Option(
        doc="""
        **Syntax:** **index=****
        **Description:** Specify the index destination, if unspecified will be set based on the app global configuration.""",
        require=False,
        default="None",
        validate=validators.Match("index", r"^.*$"),
    )

    sourcetype = Option(
        doc="""
        **Syntax:** **sourcetype=****
        **Description:** Specify the sourcetype event value, if unspecified will be set to "trackme:state", this value is set as the sourcetype Metadata of the events.""",
        require=False,
        default="trackme:state",
        validate=validators.Match("sourcetype", r"^.*$"),
    )

    source = Option(
        doc="""
        **Syntax:** **source=****
        **Description:** Specify the source event value, if unspecified will be set to "trackme:state", this value is set as the source Metadata of the events.""",
        require=False,
        default="trackme:state",
        validate=validators.Match("source", r"^.*$"),
    )

    # status will be statically defined as imported

    def stream(self, records):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # get the state_events_minimal
        state_events_minimal = int(
            reqinfo["trackme_conf"]["trackme_general"]["state_events_minimal"]
        )

        # allow list and block list
        allowlist_fields = reqinfo["trackme_conf"]["trackme_general"][
            "state_events_allowlist"
        ]
        blocklist_fields = reqinfo["trackme_conf"]["trackme_general"][
            "state_events_blocklist"
        ]

        # Get configuration and define metadata
        trackme_summary_idx = reqinfo["trackme_conf"]["index_settings"][
            "trackme_summary_idx"
        ]
        splunk_index = trackme_summary_idx if self.index == "None" else self.index
        splunk_sourcetype = self.sourcetype
        splunk_source = self.source

        # Allowed and Prohibited fields
        allowlist_set = set(allowlist_fields.split(","))
        blocklist_set = set(blocklist_fields.split(","))

        # Process records
        for record in records:
            if state_events_minimal == 1:
                summary_record = {
                    k: v
                    for k, v in record.items()
                    if k in allowlist_set and v not in ("N/A", None, "", [], {})
                }

            elif state_events_minimal == 0:
                summary_record = {
                    k: v
                    for k, v in record.items()
                    if k not in blocklist_set and v not in ("N/A", None, "", [], {})
                }

            event_id = hashlib.sha256(json.dumps(summary_record).encode()).hexdigest()
            summary_record["event_id"] = event_id

            # Index the audit record
            try:
                trackme_gen_state(
                    index=splunk_index,
                    sourcetype=splunk_sourcetype,
                    source=splunk_source,
                    event=summary_record,
                )
            except Exception as e:
                logging.error(
                    f'TrackMe summary event creation failure, record="{json.dumps(summary_record, indent=1)}", exception="{str(e)}"'
                )

            yield record

        # Log the run time
        logging.info(
            f"trackmesplkgetflipping has terminated, run_time={round(time.time() - start, 3)}"
        )


dispatch(TrackMeCollect, sys.argv, sys.stdin, sys.stdout, __name__)
