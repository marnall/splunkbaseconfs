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
import time
import json

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
    "%s/var/log/splunk/trackme_trackmeyamlpath.log" % splunkhome,
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

# import yaml from lib
import yaml
from datetime import date, datetime


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles date, datetime, and other non-serializable objects."""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return str(obj)
        return super().default(obj)


@Configuration(distributed=False)
class parseyamlCommand(StreamingCommand):

    yaml_fieldname = Option(
        doc="""
        **Syntax:** **yaml_fieldname=****
        **Description:** The name of the field containing the YAML data to be parsed. Default is '_raw'.""",
        require=False,
        default="_raw",
        validate=validators.Match("yaml_fieldname", r"^.*$"),
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

    def flatten_yaml(self, data, parent_key="", sep="."):
        """Recursively flattens a nested dictionary or list into a flat dictionary, extracting all nested fields."""
        items = {}
        if isinstance(data, dict):
            for k, v in data.items():
                new_key = (
                    f"{parent_key}{sep}{k.replace(' ', '_')}"
                    if parent_key
                    else k.replace(" ", "_")
                )
                items.update(self.flatten_yaml(v, new_key, sep=sep))
        elif isinstance(data, list):
            # Process each item in the list individually
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    # For complex items, flatten them with or without index
                    if len(data) == 1:
                        # If only one item, don't include index
                        list_key = parent_key if parent_key else ""
                    else:
                        # If multiple items, include index
                        list_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
                    items.update(self.flatten_yaml(item, list_key, sep=sep))
                else:
                    # For simple items, store them with or without index
                    if len(data) == 1:
                        # If only one item, don't include index
                        list_key = parent_key if parent_key else ""
                    else:
                        # If multiple items, include index
                        list_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
                    if isinstance(item, (date, datetime)):
                        items[list_key] = item.isoformat()
                    elif hasattr(item, '__dict__') and not isinstance(item, (str, int, float, bool, type(None))):
                        items[list_key] = str(item)
                    else:
                        items[list_key] = item
        else:
            # Convert non-serializable objects to strings
            if isinstance(data, (date, datetime)):
                items[parent_key] = data.isoformat()
            elif hasattr(data, '__dict__') and not isinstance(data, (str, int, float, bool, type(None))):
                items[parent_key] = str(data)
            else:
                items[parent_key] = data
        return items

    def stream(self, records):

        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Loop in the results
        yield_records = []
        for record in records:

            # Start with a copy of the original record to preserve all original fields
            yield_record = dict(record)

            # Attempt to parse the specified field as YAML
            try:
                if self.yaml_fieldname not in record:
                    log.warning(f"Field {self.yaml_fieldname} not found in record, skipping YAML parsing")
                    yield_record[self.yaml_fieldname] = ""
                else:
                    yaml_content = yaml.safe_load(record[self.yaml_fieldname])
                    if yaml_content is not None:
                        flat_yaml = self.flatten_yaml(yaml_content)
                        yield_record.update(flat_yaml)
                    else:
                        log.warning(f"YAML content is None for field {self.yaml_fieldname}")
                        yield_record[self.yaml_fieldname] = record[self.yaml_fieldname]

            except Exception as e:
                log.error(
                    f"Failed to parse YAML from {self.yaml_fieldname}, exception={str(e)}, record={record}"
                )
                yield_record[self.yaml_fieldname] = record[self.yaml_fieldname]

            # Ensure _time is set (in case it wasn't in the original record)
            if "_time" not in yield_record:
                yield_record["_time"] = time.time()

            # add yield_record
            yield_records.append(yield_record)

        # final yield processing
        for yield_record in self.generate_fields(yield_records):
            yield yield_record

        # performance counter
        run_time = round(time.time() - start, 3)
        logging.info(f'trackmeyamlpath has terminated, run_time="{run_time}"')


dispatch(parseyamlCommand, sys.argv, sys.stdin, sys.stdout, __name__)
