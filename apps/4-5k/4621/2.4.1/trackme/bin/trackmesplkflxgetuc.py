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

# Standard library imports
import json
import logging
import os
import sys
import time
import glob

# Third-party library imports
import urllib3
from logging.handlers import RotatingFileHandler

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_flx_get_usecases.log" % splunkhome,
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
from trackme_libs import cd, trackme_reqinfo

# import splk_flx_allowed_uc_ref
from collections_data import splk_flx_allowed_uc_ref


@Configuration(distributed=False)
class TrackMeApiAutoDocs(GeneratingCommand):
    def generate(self, **kwargs):
        # performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        #
        # start
        #

        with cd(
            os.path.join(splunkhome, "etc", "apps", "trackme", "lib", "flx_library")
        ):
            logging.info("cd done")

            uc_json_files = glob.glob(os.path.join("*.json"))
            for uc_json in uc_json_files:
                try:
                    with open(uc_json, "r") as f:
                        uc_json_def = json.load(f)

                        # get uc_ref and check if it is in the allowed list
                        uc_ref = uc_json_def.get("uc_ref")
                        if uc_ref in splk_flx_allowed_uc_ref:

                            yield {
                                "_time": time.time(),
                                "_raw": {
                                    "uc_ref": uc_json_def.get("uc_ref"),
                                    "uc_vendor": uc_json_def.get("uc_vendor"),
                                    "uc_category": uc_json_def.get("uc_category"),
                                    "uc_description": uc_json_def.get("uc_description"),
                                    "uc_earliest": uc_json_def.get("uc_earliest"),
                                    "uc_latest": uc_json_def.get("uc_latest"),
                                    "uc_replacements": uc_json_def.get(
                                        "uc_replacements"
                                    ),
                                    "uc_implementation_comments": uc_json_def.get(
                                        "uc_implementation_comments"
                                    ),
                                    "uc_metrics": uc_json_def.get("uc_metrics"),
                                    "uc_search": uc_json_def.get("uc_search"),
                                },
                                "uc_ref": uc_json_def.get("uc_ref"),
                                "uc_vendor": uc_json_def.get("uc_vendor"),
                                "uc_category": uc_json_def.get("uc_category"),
                                "uc_description": uc_json_def.get("uc_description"),
                                "uc_earliest": uc_json_def.get("uc_earliest"),
                                "uc_latest": uc_json_def.get("uc_latest"),
                                "uc_replacements": uc_json_def.get("uc_replacements"),
                                "uc_implementation_comments": uc_json_def.get(
                                    "uc_implementation_comments"
                                ),
                                "uc_metrics": uc_json_def.get("uc_metrics"),
                                "uc_search": uc_json_def.get("uc_search"),
                            }

                except Exception as e:
                    # render response
                    msg = f'An exception was encountered, uc_file={uc_json}, exception="{str(e)}"'
                    logging.error(msg)
                    raise Exception(msg)

        run_time = run_time = round(time.time() - start, 3)
        logging.info(
            f"trackmesplkflxgetuc has terminated successfully, run_time={run_time}"
        )


dispatch(TrackMeApiAutoDocs, sys.argv, sys.stdin, sys.stdout, __name__)
