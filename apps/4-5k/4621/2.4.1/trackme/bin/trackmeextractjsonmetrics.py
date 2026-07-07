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

# Third-party library imports
import urllib3

# Disable InsecureRequestWarning for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_extract_json_metrics.log" % splunkhome,
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

# impport TrackMe libs
from trackme_libs import trackme_reqinfo


@Configuration(distributed=False)
class TrackMeExtractJsonMetrics(StreamingCommand):
    fields = Option(
        doc="""
        **Syntax:** **fields=****
        **Description:** Comma-separated list of fields containing JSON metrics objects.""",
        require=False,
        default="metrics",
        validate=validators.Match("fields", r"^.*$"),
    )

    def stream(self, records):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Convert fields into a set for faster lookup
        fields_set = set(self.fields.split(","))

        # Create a set to store unique metric field names
        metrics_extracted = set()

        # Process records
        result_records = []
        for record in records:
            result_record = {}

            # Add fields to the corresponding dictionaries
            for key, value in record.items():
                if key in fields_set:
                    try:
                        # Here we load the JSON object
                        metrics_json = json.loads(value)

                        # Now we check its type
                        if isinstance(metrics_json, dict):
                            # If it's a dictionary, handle as before
                            for subkey, subvalue in metrics_json.items():
                                result_record[subkey] = subvalue
                                metrics_extracted.add(subkey)
                        elif isinstance(metrics_json, list):
                            # If it's a list, handle each element as a dictionary
                            for elem in metrics_json:
                                for subkey, subvalue in elem["metrics"].items():
                                    result_record[subkey] = subvalue
                                    metrics_extracted.add(subkey)

                        # Add the original in pretty print format
                        result_record[key] = json.dumps(metrics_json, indent=2)

                    except Exception as e:
                        logging.error(
                            f'Failed to extract metrics in field="{key}", value="{value}", exception="{str(e)}"'
                        )
                        # Add the original untouched
                        result_record[key] = value
                else:
                    result_record[key] = value

            # Add to the final records
            result_records.append(result_record)

        # Ensure we have a value for each extracted field, otherwise set to 0
        for result_record in result_records:
            for field in metrics_extracted:
                result_record.setdefault(field, 0)

            # Yield the result_record
            yield result_record

        # Log the run time
        logging.info(
            f"trackmeextractjsonmetrics has terminated, run_time={round(time.time() - start, 3)}"
        )


dispatch(TrackMeExtractJsonMetrics, sys.argv, sys.stdin, sys.stdout, __name__)
