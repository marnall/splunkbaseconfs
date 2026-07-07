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
    "%s/var/log/splunk/trackme_trackmeexpandtokens.log" % splunkhome,
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
class TrackMeExpandTokens(StreamingCommand):

    def stream(self, records):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        def expand_tokens(value, record):
            # Only process if value is a string
            if not isinstance(value, str):
                return value
            result = ""
            i = 0
            while i < len(value):
                if value[i] == "$":
                    # Look for closing $
                    end = value.find("$", i + 1)
                    if end != -1:
                        token = value[i + 1 : end]
                        # Handle $result.<token_name>$
                        if token.startswith("result."):
                            token_name = token[7:]
                        else:
                            token_name = token
                        # Replace if token_name exists in record
                        if token_name in record:
                            replacement = str(record[token_name])
                            result += replacement
                        else:
                            # No replacement, keep as is
                            result += "$" + token + "$"
                        i = end + 1
                    else:
                        # No closing $, just add the rest
                        result += value[i:]
                        break
                else:
                    result += value[i]
                    i += 1
            return result

        # Process records
        for record in records:
            result_record = {}
            for key in record:
                value = record[key]
                # Expand tokens if value is a string
                expanded_value = expand_tokens(value, record)
                result_record[key] = expanded_value
            yield result_record

        # performance counter
        logging.info(
            f'trackmeexpendtokens has terminated, run_time="{round(time.time() - start, 3)}"'
        )


dispatch(TrackMeExpandTokens, sys.argv, sys.stdin, sys.stdout, __name__)
