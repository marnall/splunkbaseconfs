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
    "%s/var/log/splunk/trackme_splk_outliers_get_rules.log" % splunkhome,
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
class SplkOutliersGetRules(GeneratingCommand):
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

        # Outliers rules storage collection
        collection_rules_name = (
            f"kv_trackme_{self.component}_outliers_entity_rules_tenant_{self.tenant_id}"
        )
        collection_rule = self.service.kvstore[collection_rules_name]

        # Get app level config
        splk_outliers_detection = reqinfo["trackme_conf"]["splk_outliers_detection"]

        # available algorithms
        splk_outliers_mltk_algorithms_list = splk_outliers_detection.get(
            "splk_outliers_mltk_algorithms_list", ["DensityFunction"]
        )

        # default algorithm
        splk_outliers_mltk_algorithms_default = splk_outliers_detection.get(
            "splk_outliers_mltk_algorithms_default", "DensityFunction"
        )

        # available boundaries extraction macros
        splk_outliers_boundaries_extraction_macros_list = splk_outliers_detection.get(
            "splk_outliers_boundaries_extraction_macros_list",
            ["splk_outliers_extract_boundaries"],
        )

        # default bundaries extraction macro
        splk_outliers_boundaries_extraction_macro_default = splk_outliers_detection.get(
            "splk_outliers_boundaries_extraction_macro_default",
            "splk_outliers_extract_boundaries",
        )

        # default period_calculation_latest
        splk_outliers_detection_period_latest_default = splk_outliers_detection.get(
            "splk_outliers_detection_period_latest_default", "now"
        )

        #
        # Get the Outliers rules
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
            record_outliers_rules = collection_rule.data.query(
                query=json.dumps(query_string)
            )

        except Exception as e:
            record_outliers_rules = None

        # log debug
        logging.debug(f'record_outliers_rules="{record_outliers_rules}"')

        # Loop through entities
        for entity_rules in record_outliers_rules:
            #
            # ML confidence
            #

            ml_confidence = entity_rules.get("confidence", "low")
            ml_confidence_reason = entity_rules.get("confidence_reason", "unknown")

            # Get the JSON outliers rules object
            entities_outliers = entity_rules.get("entities_outliers")

            # Load as a dict
            try:
                entities_outliers = json.loads(entity_rules.get("entities_outliers"))
            except Exception as e:
                msg = f'Failed to load entities_outliers with exception="{str(e)}"'

            # log debug
            logging.debug(f'entities_outliers="{entities_outliers}"')

            # Get object
            entity_object = entity_rules.get("object")

            # Get object_id
            entity_object_id = entity_rules.get("_key")

            # Get object_category
            entity_object_category = entity_rules.get("object_category")

            #
            # Start
            #

            # Loop through outliers entities
            for entity_outlier in entities_outliers:
                # Set as a dict
                entity_outliers_dict = entities_outliers[entity_outlier]

                # ensures retro-compatibility < version 2.0.15 with the auto_correct option, set default True if not defined
                try:
                    auto_correct = entity_outliers_dict["auto_correct"]
                except Exception as e:
                    entity_outliers_dict["auto_correct"] = 1

                # ensure retro-compatibility < version 2.0.84 with the min_value_for_lowerbound_breached/min_value_for_upperbound_breached, set default value to 0 if not defined
                try:
                    min_value_for_lowerbound_breached = entity_outliers_dict[
                        "min_value_for_lowerbound_breached"
                    ]
                except Exception as e:
                    entity_outliers_dict["min_value_for_lowerbound_breached"] = 0

                try:
                    min_value_for_upperbound_breached = entity_outliers_dict[
                        "min_value_for_upperbound_breached"
                    ]
                except Exception as e:
                    entity_outliers_dict["min_value_for_upperbound_breached"] = 0

                # ensure retro-compatibility with < version 2.0.89, set algorithm with default value if not defined
                try:
                    algorithm = entity_outliers_dict["algorithm"]
                except Exception as e:
                    entity_outliers_dict["algorithm"] = (
                        splk_outliers_mltk_algorithms_default
                    )

                # add algorithms_list
                entity_outliers_dict["algorithms_list"] = (
                    splk_outliers_mltk_algorithms_list
                )

                # ensure retro-compatibility with < version 2.0.89, set bundaries extraction macro with default value if not defined
                try:
                    boundaries_extraction_macro = entity_outliers_dict[
                        "boundaries_extraction_macro"
                    ]
                except Exception as e:
                    entity_outliers_dict["boundaries_extraction_macro"] = (
                        splk_outliers_boundaries_extraction_macro_default
                    )

                # ensure retro-compatibility with < version 2.0.96, set period_calculation_latest with default value if not defined
                try:
                    period_calculation_latest = entity_outliers_dict[
                        "period_calculation_latest"
                    ]
                except Exception as e:
                    entity_outliers_dict["period_calculation_latest"] = (
                        splk_outliers_detection_period_latest_default
                    )

                # add boundaries_extraction_macros_list
                entity_outliers_dict["boundaries_extraction_macros_list"] = (
                    splk_outliers_boundaries_extraction_macros_list
                )

                # Add a pseudo time
                entity_outliers_dict["_time"] = str(time.time())

                # Add the object reference
                entity_outliers_dict["object"] = entity_object

                # Add the object_id reference
                entity_outliers_dict["object_id"] = entity_object_id

                # Add the object_category reference
                entity_outliers_dict["object_category"] = entity_object_category

                # Add the model_id reference
                entity_outliers_dict["model_id"] = entity_outlier

                # Add ml_confidence and ml_confidence_reason
                entity_outliers_dict["confidence"] = ml_confidence
                entity_outliers_dict["confidence_reason"] = ml_confidence_reason

                # Add _raw
                entity_outliers_dict["_raw"] = json.dumps(entity_outliers_dict)

                # yield
                yield entity_outliers_dict


dispatch(SplkOutliersGetRules, sys.argv, sys.stdin, sys.stdout, __name__)
