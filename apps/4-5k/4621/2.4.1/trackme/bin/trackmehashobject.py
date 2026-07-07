#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = ["Guilhem Marchand"]
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library
import os
import sys
import time
import hashlib
import json

# External libraries
import urllib3

# Disable urllib3 warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
import logging
from logging.handlers import RotatingFileHandler

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_trackmehashobject.log" % splunkhome,
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

# import Splunk libs (after lib appended)
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)

from trackme_libs_utils import decode_unicode

# import trackme libs (after lib appended)
from trackme_libs import trackme_reqinfo


@Configuration(distributed=False)
class TrackMeGetKeyidFromObject(StreamingCommand):

    input_field = Option(
        doc="""
        **Syntax:** **input_field=****
        **Description:** The name of the field in input, used to define the keyid sha256 hash.""",
        require=False,
        default="object",
        validate=validators.Match(
            "input_field",
            r"^.*$",
        ),
    )

    output_field = Option(
        doc="""
        **Syntax:** **output_field=****
        **Description:** The name of the field in output, which will contain the sha256 hash.""",
        require=False,
        default="keyid",
        validate=validators.Match(
            "output_field",
            r"^.*$",
        ),
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

    # main
    def stream(self, records):
        if self:
            # start perf duration counter
            start = time.time()

            # Get request info and set logging level
            reqinfo = trackme_reqinfo(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
            )
            log.setLevel(reqinfo["logging_level"])

            #
            # loop through upstream records
            #

            yield_records = []

            # Loop in the results
            for record in records:

                try:
                    record_object_value = decode_unicode(record[self.input_field])
                    record_object_id = hashlib.sha256(
                        record_object_value.encode("utf-8")
                    ).hexdigest()
                    record[self.output_field] = record_object_id
                except Exception as e:
                    logging.error(
                        f'error processing record, exception={str(e)}, record="{json.dumps(record, indent=2)}'
                    )

                # Process the saved search and yield the result
                yield_records.append(record)

            for yield_record in self.generate_fields(yield_records):
                yield yield_record

            logging.info(
                f'trackmehashobject has terminated, no_records="{len(yield_records)}", run_time="{round(time.time() - start, 3)}"'
            )


dispatch(TrackMeGetKeyidFromObject, sys.argv, sys.stdin, sys.stdout, __name__)
