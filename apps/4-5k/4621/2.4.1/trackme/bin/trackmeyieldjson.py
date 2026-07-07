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
import base64

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
    "%s/var/log/splunk/trackme_yield_json.log" % splunkhome,
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
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo


@Configuration(distributed=False)
class TrackMeYieldJson(GeneratingCommand):

    json_value = Option(
        doc="""
        **Syntax:** **json_value=****
        **Description:** The JSON value to yield.""",
        require=False,
        default=None,
        validate=validators.Match("json_value", r"^.*$"),
    )

    json_value_b64 = Option(
        doc="""
        **Syntax:** **json_value_b64=****
        **Description:** The base64 encoded JSON value to yield.""",
        require=False,
        default=None,
        validate=validators.Match("json_value_b64", r"^.*$"),
    )

    def generate(self, **kwargs):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Check if we have either json_value or json_value_b64
        if not self.json_value and not self.json_value_b64:
            logging.error("Either json_value or json_value_b64 must be provided")
            return

        # Initialize json_value
        json_value = None

        # Handle base64 encoded JSON
        if self.json_value_b64:
            try:
                json_str = base64.b64decode(self.json_value_b64).decode("utf-8")
                json_value = json.loads(json_str)
            except Exception as e:
                logging.error(
                    f"Error parsing base64 JSON value: {e}, json_value_b64={self.json_value_b64}"
                )
                return

        # Handle direct JSON value
        elif self.json_value:
            try:
                json_value = json.loads(self.json_value)
            except Exception as e:
                logging.error(
                    f"Error parsing JSON value: {e}, json_value={self.json_value}"
                )
                return

        # yield the json value
        yield_record = {
            "_time": time.time(),
            "_raw": json_value,
        }

        # for key value in json_value, add to yield_record
        for key, value in json_value.items():
            yield_record[key] = value

        # yield the yield_record
        yield yield_record

        # performance counter
        run_time = round(time.time() - start, 3)
        logging.info(f'trackmeyieldjson has terminated, run_time="{run_time}"')


dispatch(TrackMeYieldJson, sys.argv, sys.stdin, sys.stdout, __name__)
