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

# Logging
import logging
from logging.handlers import RotatingFileHandler

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_get_conf.log" % splunkhome,
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

# Import Splunk libs
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
class TrackMeGetConf(GeneratingCommand):
    target = Option(
        doc="""
        **Syntax:** **target=****
        **Description:** The config stanza target, optional, use * to match all configuration stanzas.""",
        require=False,
        default="*",
        validate=validators.Match(
            "mode",
            r"^(\*|logging|index_settings|trackme_general|splk_data_sampling|splk_outliers_detection|splk_general)$",
        ),
    )

    def generate(self, **kwargs):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Proceed
        current_time = time.time()
        raw_data = (
            {self.target: reqinfo["trackme_conf"][self.target]}
            if self.target != "*"
            else reqinfo["trackme_conf"]
        )
        yield {"_time": current_time, "_raw": raw_data}

        # performance counter
        logging.debug(f'trackmeget has terminated, run_time="{time.time() - start}"')


dispatch(TrackMeGetConf, sys.argv, sys.stdin, sys.stdout, __name__)
