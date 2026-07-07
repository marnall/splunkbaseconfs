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

# Built-in modules
import json
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

# Third-party modules
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(InsecureRequestWarning)

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_get_logicalgroups.log" % splunkhome,
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

# Splunk libs
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo

# import trackme libs logical groups
from trackme_libs_logicalgroup import (
    get_logical_groups_collection_records,
)


@Configuration(distributed=False)
class TrackMeGetLogicalGroups(GeneratingCommand):

    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
        validate=validators.Match("tenant_id", r".*"),
    )

    def generate(self, **kwargs):
        # Start performance counter
        start = time.time()

        # Log the run time
        logging.info(f"trackmegetcomponent is starting")

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        #
        # Logical groups collection records
        #

        logical_group_coll = self.service.kvstore[
            f"kv_trackme_common_logical_group_tenant_{self.tenant_id}"
        ]

        (
            logical_groups_coll_records,
            logical_groups_by_group_key_dict,
            logical_groups_by_group_name_list,
            logical_groups_by_member_dict,
            logical_groups_by_member_list,
        ) = get_logical_groups_collection_records(logical_group_coll)

        response = {
            "logical_groups_coll_records": logical_groups_coll_records,
            "logical_groups_by_group_key_dict": logical_groups_by_group_key_dict,
            "logical_groups_by_group_name_list": logical_groups_by_group_name_list,
            "logical_groups_by_member_dict": logical_groups_by_member_dict,
            "logical_groups_by_member_list": logical_groups_by_member_list,
        }

        yield {
            "_time": time.time(),
            "response": response,
            "_raw": json.dumps(response),
        }

        # Log the run time
        logging.info(
            f'context="perf", trackmegetlogicalgroups has terminated, run_time="{round((time.time() - start), 3)}", tenant_id="{self.tenant_id}"'
        )


dispatch(TrackMeGetLogicalGroups, sys.argv, sys.stdin, sys.stdout, __name__)
