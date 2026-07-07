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
    "%s/var/log/splunk/trackme_trackmesplkflxexpandextra.log" % splunkhome,
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
class TrackMeSplkFlxExpandExtra(StreamingCommand):
    target = Option(
        doc="""
        **Syntax:** **target=****
        **Description:** The target key name in the extra_attributes object.""",
        require=False,
        default="objects",
        validate=validators.Match("target", r"^.*$"),
    )

    def generate_fields(self, records):
        # this function ensures that records have the same list of fields to allow Splunk to automatically extract these fields
        # if a given result does not have a given field, it will be added to the record as an empty value
        all_keys = set()
        for record in records:
            all_keys.update(record.keys())

        for record in records:
            for key in all_keys:
                if key not in record:
                    record[key] = ""
            yield record

    def stream(self, records):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Process records
        result_records = []

        for record in records:
            list_keys = []
            for key in record.keys():
                if key != "extra_attributes":
                    list_keys.append(key)

            # loads the field extra_attributes as a dictionary
            try:
                extra_attributes = json.loads(record["extra_attributes"])
            except Exception as e:
                extra_attributes = None

            # get target list
            if extra_attributes:
                target_list = extra_attributes.get(self.target, None)

            if extra_attributes and target_list:
                # loop through the list of objects
                for extra_attribute in target_list:
                    result_record = {}
                    result_record["extra_attribute"] = extra_attribute

                    # add to the list of reecords to be yielded
                    result_records.append(result_record)

                    # finally, add any key values pairs originally in the record and stored in the list list_keys
                    for key in list_keys:
                        result_record[key] = record[key]

            else:
                # render the original record
                result_records.append(record)

            # yield
            for yield_record in self.generate_fields(result_records):
                yield yield_record

        # performance counter
        run_time = str(time.time() - start)
        logging.info(f'trackmesplkflxexpandextra has terminated, run_time="{run_time}"')


dispatch(TrackMeSplkFlxExpandExtra, sys.argv, sys.stdin, sys.stdout, __name__)
