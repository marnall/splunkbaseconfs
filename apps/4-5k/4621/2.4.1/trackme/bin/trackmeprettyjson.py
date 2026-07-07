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

# Standard library
import os
import sys
import json
import time

# Logging
import logging
from logging.handlers import RotatingFileHandler

# Networking
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_pretty_json.log" % splunkhome,
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

# import Splunk
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
class TrackMePrettyJson(StreamingCommand):
    fields = Option(
        doc="""
        **Syntax:** **fields=****
        **Description:** Comma-separated list of fields to pretty print.""",
        require=False,
        default="None",
        validate=validators.Match("fields", r"^.*$"),
    )

    remove_nonpositive_num = Option(
        doc="""
        **Syntax:** **remove_nonpositive_num=****
        **Description:** When sorting a JSON field, remove numerical values that are not greater than 0.""",
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    remove_null = Option(
        doc="""
        **Syntax:** **remove_null=****
        **Description:** When sorting a JSON field, remove null values.""",
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    merge = Option(
        doc="""
        **Syntax:** **merge=****
        **Description:** If True and multiple fields are provided in input, will produce a merged array of JSON objects.""",
        require=False,
        default="False",
        validate=validators.Match("add_root_label", r"^(True|False)$"),
    )

    merge_field_target = Option(
        doc="""
        **Syntax:** **merge_field_target=****
        **Description:** If merge is True, this defines the field name for the target.""",
        require=False,
        default="metrics",
        validate=validators.Match("merge_field_target", r"^.*$"),
    )

    def to_number(self, value):
        if value == "":
            return None

        try:
            return int(value)
        except ValueError:
            return float(value)

    def process_json(self, json_object):
        # For each key, value in the JSON object
        for k, v in list(json_object.items()):
            if isinstance(v, dict):
                # If the value is a dictionary, recursively process it
                json_object[k] = self.process_json(v)
            else:
                if v == "" or v is None:
                    if self.remove_null:
                        del json_object[k]
                elif isinstance(v, str) and v.lstrip("-").replace(".", "", 1).isdigit():
                    # If the value is a string representation of a number
                    number = self.to_number(v)

                    # Remove non-positive values if requested
                    if self.remove_nonpositive_num and number <= 0:
                        del json_object[k]

                    # Remove null values if requested
                    elif self.remove_null and number is None:
                        del json_object[k]

        return json_object

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

        # Process records
        for record in records:
            result_record = {}

            # If merge is true, metrics_record will be a list
            # Otherwise, it will be a dictionary
            if self.merge.lower() == "true":
                metrics_record = []
            else:
                metrics_record = {}

            # Add fields to the corresponding dictionaries
            for key in record:
                if key in fields_set:
                    try:
                        # Load JSON, sort keys alphabetically, and pretty print
                        json_object = json.loads(record[key])

                        # Process JSON
                        json_object = self.process_json(json_object)

                        # If merge is true, append JSON object to list
                        if self.merge.lower() == "true":
                            metrics_record.append(json_object)
                        else:
                            # If merge is false, add JSON object to dictionary
                            result_record[key] = json.dumps(
                                json_object, indent=4, sort_keys=True
                            )

                    except Exception as e:
                        logging.error(
                            f'Failed to load and render the json object in field="{key}", exception="{e}"'
                        )
                        result_record[key] = record[key]
                else:
                    result_record[key] = record[key]

            # If merge is true, dump metrics_record into a pretty printed string
            if self.merge.lower() == "true":
                result_record[self.merge_field_target] = json.dumps(
                    metrics_record, indent=4, sort_keys=True
                )

            yield result_record

        # performance counter
        logging.info(
            f'trackmeprettyjson has terminated, run_time="{round(time.time() - start, 3)}"'
        )


dispatch(TrackMePrettyJson, sys.argv, sys.stdin, sys.stdout, __name__)
