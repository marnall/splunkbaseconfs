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
    "%s/var/log/splunk/trackme_trackmesplkoutliersexpand.log" % splunkhome,
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
class TrackMeSplkOutliersExpand(StreamingCommand):
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
            result_record = {}

            list_keys = []
            for key in record.keys():
                list_keys.append(key)

            # loads the field models_summary as a dictionary
            models_summary = json.loads(record["models_summary"])

            # get object name and object_category
            object_name = record["object"]
            object_category = record["object_category"]

            # loop through the models summary, for each model, yield the object and any key/value pairs from the dictionary
            for model in models_summary:
                result_record["object_category"] = object_category
                result_record["object"] = object_name
                result_record["model"] = model
                for key, value in models_summary[model].items():
                    # if key is the field summary_search_results, attempts to pretty print the json
                    if key == "summary_search_results":
                        try:
                            if isinstance(value, dict):
                                result_record[key] = json.dumps(
                                    value, indent=4, sort_keys=True
                                )
                                raw_value = value["_raw"]
                                for k, v in raw_value.items():
                                    if not k in ("_raw", "_time"):
                                        result_record[k] = v
                            else:
                                result_record[key] = value

                        except Exception as e:
                            pass

                    else:
                        result_record[key] = value

                # add to the list of reecords to be yielded
                result_records.append(result_record)

            # finally, add any key values pairs originally in the record and stored in the list list_keys
            for key in list_keys:
                result_record[key] = record[key]

            # yield
            for yield_record in self.generate_fields(result_records):
                yield yield_record

        # performance counter
        run_time = str(time.time() - start)
        logging.info(f'trackmesplkoutliersexpand has terminated, run_time="{run_time}"')


dispatch(TrackMeSplkOutliersExpand, sys.argv, sys.stdin, sys.stdout, __name__)
