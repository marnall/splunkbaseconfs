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

import os
import sys
import time
import json
import logging
from logging.handlers import RotatingFileHandler
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_trackmefieldsqualityextract.log" % splunkhome,
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

# import trackme libs
from trackme_libs import (
    trackme_reqinfo,
)

# import trackme licensing libs
from trackme_libs_licensing import trackme_check_license


@Configuration(distributed=False)
class TrackMeFieldsQualityExtract(StreamingCommand):

    input_field = Option(
        doc="""
        **Syntax:** **input_field=****
        **Description:** The field containing the JSON data to extract. Default is '_raw'.
        """,
        require=False,
        default="_raw",
        validate=validators.Match("input_field", r"^.*$"),
    )

    metadata_fieldname = Option(
        doc="""
        **Syntax:** **metadata_fieldname=****
        **Description:** The name of the metadata field in the JSON. Default is 'metadata'.
        """,
        require=False,
        default="metadata",
        validate=validators.Match("metadata_fieldname", r"^.*$"),
    )

    def stream(self, records):

        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # check license state
        try:
            check_license = trackme_check_license(
                reqinfo["server_rest_uri"], self._metadata.searchinfo.session_key
            )
            license_is_valid = check_license.get("license_is_valid")
            logging.debug(
                f'function check_license called, response="{json.dumps(check_license, indent=2)}"'
            )

        except Exception as e:
            license_is_valid = 0
            logging.error(f'function check_license exception="{str(e)}"')

        # check restricted components
        if license_is_valid != 1:
            logging.error(
                f'The requested component is restricted to the Full and Trial edition mode, its execution cannot be accepted, check_license="{json.dumps(check_license, indent=2)}"'
            )
            raise Exception(
                f"The requested component is restricted to the Full and Trial edition mode, its execution cannot be accepted, please contact your Splunk administrator."
            )

        # Loop in the results
        records_count = 0
        for record in records:
            records_count += 1

            # Get the JSON data from the input field
            json_data = record.get(self.input_field)

            if not json_data:
                log.warning(f"No data found in field '{self.input_field}'")
                continue

            try:
                # Parse the JSON data
                if isinstance(json_data, str):
                    data = json.loads(json_data)
                else:
                    data = json_data

                # Extract metadata
                metadata = data.get(self.metadata_fieldname, {})

                # Process each field in the data
                for field_name, field_data in data.items():
                    # Skip metadata, summary, and time fields
                    if field_name in [
                        self.metadata_fieldname,
                        "summary",
                        "time",
                        "event_id",
                    ]:
                        continue

                    # Skip if field_data is not a dictionary (should be field quality data)
                    if not isinstance(field_data, dict):
                        continue

                    # Create a new record for this field
                    yield_record = {}

                    # Add time information
                    if "time" in data:
                        yield_record["_time"] = data["time"]
                    else:
                        yield_record["_time"] = time.time()

                    # Add all metadata fields with prefix
                    for meta_key, meta_value in metadata.items():
                        # if is a list, only consider the first element
                        if isinstance(meta_value, list):
                            meta_value = meta_value[0]
                        yield_record[f"metadata.{meta_key}"] = meta_value

                    # Add field name
                    yield_record["fieldname"] = field_name

                    # Add all field quality data
                    for field_key, field_value in field_data.items():
                        yield_record[field_key] = field_value

                    # Add event_id if available
                    if "event_id" in data:
                        yield_record["event_id"] = data["event_id"]

                    # create _raw field
                    yield_record["_raw"] = json.dumps(yield_record)

                    yield yield_record

            except json.JSONDecodeError as e:
                log.error(
                    f"Failed to parse JSON from field '{self.input_field}': {str(e)}"
                )
                continue
            except Exception as e:
                log.error(f"Error processing record: {str(e)}")
                continue

        # Log the run time
        logging.info(
            f'context="perf", trackmefieldsqualityextract has terminated, records_count="{records_count}", run_time="{round((time.time() - start), 3)}"'
        )


dispatch(TrackMeFieldsQualityExtract, sys.argv, sys.stdin, sys.stdout, __name__)
