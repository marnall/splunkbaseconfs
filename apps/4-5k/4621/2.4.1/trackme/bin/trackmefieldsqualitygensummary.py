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
from collections import defaultdict, Counter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_trackmefieldsqualitygensummary.log" % splunkhome,
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

# Helper to ensure hashable group keys

def make_hashable(value):
    if isinstance(value, list):
        # return the first element of the list
        return make_hashable(value[0])
    elif isinstance(value, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in value.items()))
    else:
        return value

# import trackme licensing libs
from trackme_libs_licensing import trackme_check_license


@Configuration(distributed=False)
class TrackMeFieldsQualityGenSummary(StreamingCommand):

    maxvals = Option(
        doc="""
        **Syntax:** **maxvals=****
        **Description:** Max number of distinct values to report in field_values.
        """,
        require=False,
        default=15,
        validate=validators.Match("maxvals", r"^.*$"),
    )

    fieldvalues_format = Option(
        doc="""
        **Syntax:** **fieldvalues_format, either list or csv=****
        **Description:** Format of field_values.
        """,
        require=False,
        default="csv",
        validate=validators.Match("fieldvalues_format", r"^(list|csv)$"),
    )

    groupby_metadata_fields = Option(
        doc="""
        **Syntax:** **groupby_metadata_fields=field1,field2,...**
        **Description:** Comma-separated list of metadata fields to group by in addition to fieldname.
        """,
        require=False,
        default="",
        validate=validators.Match("groupby_metadata_fields", r"^.*$"),
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

        # Parse groupby_metadata_fields argument
        groupby_metadata_fields = []
        if hasattr(self, "groupby_metadata_fields") and self.groupby_metadata_fields:
            groupby_metadata_fields = [
                f.strip() for f in self.groupby_metadata_fields.split(",") if f.strip()
            ]
        # if fieldname is in the list, remove it
        if "fieldname" in groupby_metadata_fields:
            groupby_metadata_fields.remove("fieldname")

        # Initialize data structures to aggregate by fieldname + metadata fields
        field_data = defaultdict(
            lambda: {
                "values": Counter(),
                "total_count": 0,
                "non_empty_count": 0,
                "metadata": {},
                "meta_key_values": {},
            }
        )

        # Loop through all records to collect data
        records_count = 0
        for record in records:
            records_count += 1

            # Extract required fields
            fieldname = record.get("fieldname")
            value = record.get("value")
            event_time = record.get("_time")
            regex_expression = record.get("regex_expression")

            if not fieldname:
                log.warning(f"Record {records_count} missing fieldname")
                continue

            # Build the group key: (fieldname, metadata values...)
            meta_key_values = tuple(make_hashable(record.get(f, None)) for f in groupby_metadata_fields)
            group_key = (fieldname,) + meta_key_values

            # Initialize field data if not exists
            if group_key not in field_data:
                field_data[group_key] = {
                    "values": Counter(),
                    "total_count": 0,
                    "non_empty_count": 0,
                    "metadata": {},
                    "meta_key_values": {
                        f: record.get(f, None) for f in groupby_metadata_fields
                    },
                    "regex_expression": regex_expression,
                }

            # Count total events
            field_data[group_key]["total_count"] += 1

            # Check if value is not null and not empty
            is_non_empty = value is not None and str(value).strip() != ""
            if is_non_empty:
                field_data[group_key]["non_empty_count"] += 1
                # Count the value (convert to string for consistency)
                field_data[group_key]["values"][str(value)] += 1

            # Store metadata from first record (assuming consistent metadata per field)
            if not field_data[group_key]["metadata"]:
                for key, val in record.items():
                    if key not in ["fieldname", "value", "_time", "_raw"]:
                        field_data[group_key]["metadata"][key] = val

        # Generate summary records for each field+metadata combination
        for group_key, data in field_data.items():
            try:
                # Calculate statistics
                total_events = data["total_count"]
                non_empty_count = data["non_empty_count"]
                distinct_value_count = len(data["values"])

                # Calculate percent coverage
                percent_coverage = (
                    (non_empty_count / total_events * 100) if total_events > 0 else 0
                )

                # Generate field_values string
                field_values_parts = []
                if data["values"]:
                    # Sort values by count (descending) and take top maxvals
                    sorted_values = data["values"].most_common(int(self.maxvals))

                    for value, count in sorted_values:
                        value_percentage = (
                            (count / non_empty_count * 100)
                            if non_empty_count > 0
                            else 0
                        )
                        field_values_parts.append(f"{value_percentage:.2f}% {value}")

                field_values = field_values_parts
                if self.fieldvalues_format == "csv":
                    field_values = ",".join(field_values_parts)

                # Create summary record
                yield_record = {
                    "fieldname": group_key[0],
                    "total_events": total_events,
                    "distinct_value_count": distinct_value_count,
                    "percent_coverage": round(percent_coverage, 2),
                    "field_values": field_values,
                    "summary": {
                        "fieldname": group_key[0],
                        "total_events": total_events,
                        "distinct_value_count": distinct_value_count,
                        "percent_coverage": round(percent_coverage, 2),
                        "field_values": field_values,
                    },
                }

                # Add regex_expression if it exists in the data
                if data.get("regex_expression") is not None:
                    yield_record["regex_expression"] = data["regex_expression"]

                # Add selected metadata fields to output (only if they exist in the group)
                for idx, meta_field in enumerate(groupby_metadata_fields):
                    meta_value = group_key[idx + 1]
                    if meta_value is not None:
                        yield_record[meta_field] = meta_value

                # Add time from first record if available
                if event_time:
                    yield_record["_time"] = event_time
                else:
                    yield_record["_time"] = time.time()

                # add _raw
                yield_record["_raw"] = json.dumps(yield_record)

                yield yield_record

            except Exception as e:
                log.error(f"Error processing field '{group_key}': {str(e)}")
                continue

        # Log the run time
        logging.info(
            f'context="perf", trackmefieldsqualitygensummary has terminated, records_count="{records_count}", fields_processed="{len(field_data)}", run_time="{round((time.time() - start), 3)}"'
        )


dispatch(TrackMeFieldsQualityGenSummary, sys.argv, sys.stdin, sys.stdout, __name__)
