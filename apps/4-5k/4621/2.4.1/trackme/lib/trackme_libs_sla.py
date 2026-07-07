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
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))

# import TrackMe libs
from trackme_libs import JSONFormatter

# Import trackMe utils libs
from trackme_libs_utils import decode_unicode

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


def trackme_sla_gen_metrics(tenant_id, metrics_idx, records):
    # proceed
    try:
        # Create a dedicated logger for SLA metrics
        sla_logger = logging.getLogger("trackme.sla.metrics")
        sla_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not sla_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_sla_metrics.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            formatter = JSONFormatter()
            logging.Formatter.converter = time.gmtime
            filehandler.setFormatter(formatter)
            sla_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            sla_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in sla_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break
            
            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_sla_metrics.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                formatter = JSONFormatter()
                logging.Formatter.converter = time.gmtime
                filehandler.setFormatter(formatter)
                sla_logger.addHandler(filehandler)

        for record in records:
            sla_logger.info(
                "Metrics - group=sla_metrics",
                extra={
                    "target_index": metrics_idx,
                    "tenant_id": tenant_id,
                    "object": decode_unicode(record.get("object")),
                    "object_id": record.get("object_id"),
                    "alias": decode_unicode(record.get("alias")),
                    "object_category": record.get("object_category"),
                    "monitored_state": record.get("monitored_state"),
                    "priority": record.get("priority"),
                    "metrics_event": json.dumps(record.get("metrics_event")),
                },
            )

        return True

    except Exception as e:
        raise Exception(str(e))
