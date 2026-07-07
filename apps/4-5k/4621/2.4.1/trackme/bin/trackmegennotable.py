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
    "%s/var/log/splunk/trackme_gen_notable.log" % splunkhome,
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
from trackme_libs import trackme_reqinfo


@Configuration(distributed=False)
class TrackMeGenNotable(StreamingCommand):
    notable_title = Option(
        doc="""
        **Syntax:** **notable_title=****
        **Description:** Specify the Notable event title, if unspecified will be set to "trackme:notable", this value is set as the source Metadata of the Notable event.""",
        require=False,
        default="trackme:notable",
        validate=validators.Match("notable_title", r"^.*$"),
    )

    # status will be statically defined as imported

    def stream(self, records):
        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Get conf
        trackme_notable_idx = reqinfo["trackme_conf"]["index_settings"][
            "trackme_notable_idx"
        ]

        # Define Meta
        splunk_index = str(trackme_notable_idx)
        splunk_sourcetype = "trackme:notable"
        splunk_source = self.notable_title
        splunk_host = reqinfo["server_servername"]

        # Loop in the results
        records_count = 0
        for splrecord in records:
            # increment
            records_count += 1

            # Generate a controlled properties value
            properties = {}
            for k in splrecord:
                logging.debug(f'field="{k}", value="{splrecord[k]}"')
                if splrecord[k] != "null":
                    properties[k] = splrecord[k]

            notable_record = {
                "_time": time.time(),
                "tenant_id": splrecord["tenant_id"],
                "object": splrecord["object"],
                "object_category": splrecord["object_category"],
                "keyid": splrecord["keyid"],
                "priority": splrecord["priority"],
                "state": splrecord["state"],
                "anomaly_reason": splrecord["anomaly_reason"],
                "status_message": splrecord["status_message"],
                "properties": json.dumps(properties, indent=1),
            }

            # index the audit record
            try:
                target = self.service.indexes[splunk_index]
                target.submit(
                    event=json.dumps(notable_record),
                    source=str(splunk_source),
                    sourcetype=str(splunk_sourcetype),
                    host=str(splunk_host),
                )
                logging.info(
                    f'TrackMe summary event created successfully, tenant_id="{notable_record["tenant_id"]}", object_category="{notable_record["object_category"]}", object="{notable_record["object"]}"'
                )
                logging.debug(f'record="{json.dumps(notable_record, indent=1)}"')
            except Exception as e:
                logging.error(
                    f'TrackMe notable event creation failure with exception="{str(e)}"'
                )

            # yield
            yield {
                "_time": time.time(),
                "tenant_id": splrecord["tenant_id"],
                "object": splrecord["object"],
                "object_category": splrecord["object_category"],
                "keyid": splrecord["keyid"],
                "priority": splrecord["priority"],
                "state": splrecord["state"],
                "anomaly_reason": splrecord["anomaly_reason"],
                "status_message": splrecord["status_message"],
                "properties": json.dumps(properties, indent=1),
            }


dispatch(TrackMeGenNotable, sys.argv, sys.stdin, sys.stdout, __name__)
