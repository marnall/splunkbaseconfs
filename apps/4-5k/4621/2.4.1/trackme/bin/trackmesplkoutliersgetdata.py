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
import os
import sys
import time
import json

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# Networking imports
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splk_outliers_get_data.log" % splunkhome,
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
class SplkOutliersGetData(GeneratingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The value for tenant_id.""",
        require=True,
        validate=validators.Match("tenant_id", r"^.*$"),
    )

    component = Option(
        doc="""
        **Syntax:** **component=****
        **Description:** The component category.""",
        require=True,
        default=None,
        validate=validators.Match("component", r"^(?:dsm|dhm|flx|fqm|wlk)$"),
    )

    object = Option(
        doc="""
        **Syntax:** **object=****
        **Description:** Optional, The value for object.""",
        require=False,
        default="*",
        validate=validators.Match("object", r"^.*$"),
    )

    object_id = Option(
        doc="""
        **Syntax:** **object_id=****
        **Description:** Optional, The value for object id.""",
        require=False,
        default="*",
        validate=validators.Match("object_id", r"^.*$"),
    )

    def generate(self, **kwargs):
        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Validate that at least one of object or object_id is provided
        if self.object == "*" and self.object_id == "*":
            msg = f'tenant_id="{self.tenant_id}", component="{self.component}", Either object or object_id must be provided.'
            logging.error(msg)
            raise Exception(msg)

        # Outliers data storage collection
        collection_data_name = (
            f"kv_trackme_{self.component}_outliers_entity_data_tenant_{self.tenant_id}"
        )
        collection_data = self.service.kvstore[collection_data_name]

        #
        # Get the Outliers data
        #

        # Define the KV query
        # object_id takes precedence over object when both are provided
        if self.object == "*" and self.object_id == "*":
            query_string = {
                "object_category": f"splk-{self.component}",
            }
        else:
            if self.object_id != "*":
                # Use object_id first (preferred method)
                query_string_filter = {
                    "object_category": f"splk-{self.component}",
                    "_key": self.object_id,
                }
            elif self.object != "*":
                # Fall back to object if object_id is not provided
                query_string_filter = {
                    "object_category": f"splk-{self.component}",
                    "object": self.object,
                }

            query_string = {"$and": [query_string_filter]}

        # get records
        try:
            record_outliers_data = collection_data.data.query(
                query=json.dumps(query_string)
            )

        except Exception as e:
            record_outliers_data = None

        # if no records
        if not record_outliers_data:
            object_ref = self.object if self.object != "*" else f"object_id={self.object_id}"
            msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {object_ref} outliers data record cannot be found or are not yet available for this selection.'
            logging.error(msg)
            raise Exception(msg)

        # log debug
        logging.debug(f'record_outliers_data="{record_outliers_data}"')

        # Loop through entities
        for entity_data in record_outliers_data:
            # Get object
            entity_object = entity_data.get("object")

            # Get object_id
            entity_object_id = entity_data.get("_key")

            # Get object_category
            entity_object_category = entity_data.get("object_category")

            # Get isOutlier
            entity_is_outliers = entity_data.get("isOutlier")

            # Get isOutlierReason
            entity_is_outliers_reason = entity_data.get("isOutlierReason")

            # Get models_in_anomaly
            entity_models_in_anomaly = entity_data.get("models_in_anomaly")

            # Get models_summary
            entity_models_summary = json.loads(entity_data.get("models_summary"))

            # Get mtime
            entity_mtime = float(entity_data.get("mtime"))

            #
            # Start
            #

            entity_outliers_results = {}

            # Add each field retrieved
            entity_outliers_results["object"] = entity_object
            entity_outliers_results["object_id"] = entity_object_id
            entity_outliers_results["object_category"] = entity_object_category
            entity_outliers_results["IsOutlier"] = entity_is_outliers
            entity_outliers_results["isOutlierReason"] = entity_is_outliers_reason
            entity_outliers_results["models_in_anomaly"] = entity_models_in_anomaly
            entity_outliers_results["models_summary"] = entity_models_summary
            # generate an mtime_human which is strftime %c of the epoch time
            entity_outliers_results["mtime"] = entity_mtime
            entity_outliers_results["mtime_human"] = time.strftime(
                "%c", time.localtime(entity_mtime)
            )

            # Add _raw
            entity_outliers_results["_raw"] = json.dumps(entity_outliers_results)

            # yield
            yield entity_outliers_results


dispatch(SplkOutliersGetData, sys.argv, sys.stdin, sys.stdout, __name__)
