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
import fnmatch

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
    "%s/var/log/splunk/trackme_genjson_metrics.log" % splunkhome,
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
class TrackMeGenJsonMetrics(StreamingCommand):
    fields = Option(
        doc="""
        **Syntax:** **fields=****
        **Description:** Comma-separated list of fields containing the list of metrics, wildcards are supported anywhere in the field names.""",
        require=False,
        default="None",
        validate=validators.Match("fields", r"^.*$"),
    )

    add_root_label = Option(
        doc="""
        **Syntax:** **add_root_label=****
        **Description:** Adds the provided label as the root of the JSON object.""",
        require=False,
        default="None",
        validate=validators.Match("add_root_label", r"^.*$"),
    )

    target = Option(
        doc="""
        **Syntax:** **target=****
        **Description:** The target field name.""",
        require=False,
        default="metrics",
        validate=validators.Match("target", r"^.*$"),
    )

    add_prefix = Option(
        doc="""
        **Syntax:** **add_prefix=****
        **Description:** Adds the provided prefix to field names.""",
        require=False,
        default="None",
        validate=validators.Match("add_prefix", r"^.*$"),
    )

    suppress_suffix = Option(
        doc="""
        **Syntax:** **suppress_suffix=****
        **Description:** Suppress the provided suffix from field names.""",
        require=False,
        default="None",
        validate=validators.Match("suppress_suffix", r"^.*$"),
    )

    def stream(self, records):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Convert fields into a list of patterns
        fields_patterns = [pattern.strip() for pattern in self.fields.split(",")]

        def match_field(field_name):
            """Check if a field name matches any of the given patterns"""
            return any(
                fnmatch.fnmatch(field_name, pattern) for pattern in fields_patterns
            )

        # Process records
        for record in records:
            result_record = {}

            if self.add_root_label != "None":
                metrics_record = {
                    "label": self.add_root_label,
                    "metrics": {},
                }
            else:
                metrics_record = {}

            # Add fields to the corresponding dictionaries
            for key, value in record.items():
                if match_field(key):  # Use wildcard matching
                    # Suppress suffix if the option is provided and the field name ends with it
                    if self.suppress_suffix != "None" and len(self.suppress_suffix) > 0 and key.endswith(
                        self.suppress_suffix
                    ):
                        newkey = key[: -len(self.suppress_suffix)].rstrip("_")
                    else:
                        newkey = key

                    # Add prefix if the option is provided
                    if self.add_prefix != "None":
                        newkey = f"{self.add_prefix}{newkey}"

                    # Convert numeric values where possible
                    try:
                        value = int(value)
                    except ValueError:
                        try:
                            value = float(value)
                        except ValueError:
                            pass

                    if self.add_root_label != "None":
                        try:
                            metrics_record["metrics"][newkey] = value
                        except Exception as e:
                            logging.error(
                                f'Failed to add requested metric in field="{newkey}", exception="{str(e)}"'
                            )
                            result_record[newkey] = value
                    else:
                        try:
                            metrics_record[newkey] = value
                        except Exception as e:
                            logging.error(
                                f'Failed to add requested metric in field="{newkey}", exception="{str(e)}"'
                            )
                            result_record[newkey] = value

                    # Keep the original field/value in the record
                    result_record[key] = value

                else:
                    result_record[key] = value

            # Add the generated metrics field
            result_record[self.target] = metrics_record

            yield result_record

        # Performance counter
        logging.info(
            f'trackmegenjsonmetrics has terminated, run_time="{round(time.time() - start, 3)}"'
        )


dispatch(TrackMeGenJsonMetrics, sys.argv, sys.stdin, sys.stdout, __name__)
