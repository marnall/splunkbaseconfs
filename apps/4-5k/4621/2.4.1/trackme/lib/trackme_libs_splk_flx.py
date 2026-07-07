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
import json
from collections import OrderedDict
import time
import logging
from logging.handlers import RotatingFileHandler
from urllib.parse import urlencode
import urllib.parse
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))
from trackme_libs_logging import get_effective_logger

# import TrackMe libs
from trackme_libs import JSONFormatter

# import trackme libs utils
from trackme_libs_utils import (
    escape_backslash,
    replace_encoded_doublebackslashes,
    remove_leading_spaces,
)

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


def trackme_flx_gen_metrics(
    timestamp, tenant_id, object_value, object_id, metric_index, metrics_event
):
    try:
        if not isinstance(metrics_event, dict):
            metrics_event = json.loads(metrics_event)

        # Create a dedicated logger for FLX metrics
        flx_logger = logging.getLogger("trackme.flx.metrics")
        flx_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not flx_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_flx_metrics.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            formatter = JSONFormatter(timestamp=timestamp)
            filehandler.setFormatter(formatter)
            flx_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            flx_logger.propagate = False

        flx_logger.info(
            "Metrics - group=flx_metrics",
            extra={
                "target_index": metric_index,
                "tenant_id": tenant_id,
                "object": object_value,
                "object_id": object_id,
                "object_category": "splk-flx",
                "metrics_event": json.dumps(metrics_event),
            },
        )

    except Exception as e:
        raise Exception(str(e))


def trackme_flx_gen_metrics_from_list(
    tenant_id, object_value, object_id, metric_index, metrics_list
):
    try:
        if not isinstance(metrics_list, list):
            metrics_list = json.loads(metrics_list)

        # Create a dedicated logger for FLX metrics
        flx_logger = logging.getLogger("trackme.flx.metrics_from_list")
        flx_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not flx_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_flx_metrics.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            flx_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            flx_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in flx_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break
            
            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_flx_metrics.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                flx_logger.addHandler(filehandler)

        for metrics_item in metrics_list:
            timestamp = float(metrics_item.get("time"))
            metrics_item.pop("time")  # Remove time field

            # Update formatter with new timestamp
            formatter = JSONFormatter(timestamp=timestamp)
            filehandler.setFormatter(formatter)

            flx_logger.info(
                "Metrics - group=flx_metrics",
                extra={
                    "target_index": metric_index,
                    "tenant_id": tenant_id,
                    "object": object_value,
                    "object_id": object_id,
                    "object_category": "splk-flx",
                    "metrics_event": json.dumps(metrics_item),
                },
            )

    except Exception as e:
        raise Exception(str(e))


# return main searches logics for that entity
def splk_flx_return_searches(tenant_id, entity_info, tenant_trackme_metric_idx="trackme_metrics"):
    # log debug
    get_effective_logger().debug(
        f'Starting function=splk_flx_return_searches with entity_info="{json.dumps(entity_info, indent=2)}"'
    )

    # define required searches dynamically based on the upstream entity information
    splk_flx_mctalog_search = None
    splk_flx_metrics_report = None
    splk_flx_mpreview = None
    splk_flx_metrics_populate_search = None

    try:
        ########
        # mstats
        ########

        # mcatalog
        splk_flx_mctalog_search = remove_leading_spaces(
            f"""\
                | mcatalog values(metric_name) as metrics, values(_dims) as dims where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-flx" object_id="{entity_info["_key"]}" metric_name=* by index                        
            """
        )

        # metrics report
        splk_flx_metrics_report = remove_leading_spaces(
            f"""\
                | mstats latest(_value) as latest_value, avg(_value) as avg_value, max(_value) as max_value, perc95(_value) as perc95_value, stdev(_value) as stdev_value where index="{tenant_trackme_metric_idx}" metric_name=* tenant_id="{tenant_id}" object_category="splk-flx" object_id="{entity_info["_key"]}" by index, object, metric_name
                | foreach *_value [ eval <<FIELD>> = if(match(metric_name, "\\.status"), round('<<FIELD>>', 0), round('<<FIELD>>', 3)) ]
            """
        )

        # mpreview
        splk_flx_mpreview = remove_leading_spaces(
            f"""\
                | mpreview index="{tenant_trackme_metric_idx}" filter="tenant_id={tenant_id} object_category="splk-flx" object_id={entity_info["_key"]}"
            """
        )

        # metrics popuating search
        splk_flx_metrics_populate_search = remove_leading_spaces(
            f"""\
                | mcatalog values(metric_name) as metrics where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-flx" object_id="{entity_info["_key"]}" metric_name=*
                | mvexpand metrics
                | rename metrics as metric_name
                | rex field=metric_name "^trackme\\.splk\\.flx\\.(?<label>.*)"
                | eval order=if(metric_name=="trackme.splk.flx.status", 0, 1)
                | sort 0 order
                | fields - order
            """
        )

        response = {
            "splk_flx_mctalog_search": f"search?q={urllib.parse.quote(splk_flx_mctalog_search)}",
            "splk_flx_mctalog_search_litsearch": splk_flx_mctalog_search,
            "splk_flx_metrics_report": f"search?q={urllib.parse.quote(splk_flx_metrics_report)}",
            "splk_flx_metrics_report_litsearch": splk_flx_metrics_report,
            "splk_flx_mpreview": f"search?q={urllib.parse.quote(splk_flx_mpreview)}",
            "splk_flx_mpreview_litsearch": splk_flx_mpreview,
            "splk_flx_metrics_populate_search": splk_flx_metrics_populate_search,
        }

        # return
        return response

    except Exception as e:
        get_effective_logger().error(
            f'function splk_flx_return_searches, an exception was encountered, exception="{str(e)}"'
        )
        raise Exception(e)


def normalize_flx_tracker_name(tenant_id, tracker_name):
    """
    Normalize FLX tracker name by removing the trackme_flx_hybrid_ prefix and tenant suffix.
    
    Args:
        tenant_id (str): The tenant ID
        tracker_name (str): The tracker name to normalize
        
    Returns:
        str: The normalized tracker name
    """
    # handle tracker_name:
    # - if starts by "trackme_flx_hybrid_", remove it
    # - extract the name as: <tracker_name>_tracker_tenant_<tenant_id>
    normalized_name = tracker_name.replace("trackme_flx_hybrid_", "")
    normalized_name = normalized_name.replace(f"_tracker_tenant_{tenant_id}", "")
    
    return normalized_name
