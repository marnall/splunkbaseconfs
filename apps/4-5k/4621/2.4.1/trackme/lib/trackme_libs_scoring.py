#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2023-2025, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import os
import sys
import json
import hashlib
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
from trackme_libs_logging import get_effective_logger

# import TrackMe libs
from trackme_libs import JSONFormatter

# Import trackMe utils libs
from trackme_libs_utils import decode_unicode

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


def trackme_impact_score_gen_metrics(tenant_id, metrics_idx, records):
    # proceed
    try:
        # Validate inputs
        if records is None:
            get_effective_logger().warning(
                f'context="impact_score_gen_metrics", tenant_id="{tenant_id}", records parameter is None, skipping metrics generation'
            )
            return False

        if not isinstance(records, (list, tuple)):
            get_effective_logger().warning(
                f'context="impact_score_gen_metrics", tenant_id="{tenant_id}", records parameter is not iterable (type: {type(records)}), skipping metrics generation'
            )
            return False

        if len(records) == 0:
            get_effective_logger().debug(
                f'context="impact_score_gen_metrics", tenant_id="{tenant_id}", records is empty, skipping metrics generation'
            )
            return True

        if metrics_idx is None:
            get_effective_logger().warning(
                f'context="impact_score_gen_metrics", tenant_id="{tenant_id}", metrics_idx is None, skipping metrics generation'
            )
            return False

        # Create a dedicated logger for impact score metrics
        impact_logger = logging.getLogger("trackme.impact_score.metrics")
        impact_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not impact_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_impact_score_metrics.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            formatter = JSONFormatter()
            logging.Formatter.converter = time.gmtime
            filehandler.setFormatter(formatter)
            impact_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            impact_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in impact_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break

            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_impact_score_metrics.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                formatter = JSONFormatter()
                logging.Formatter.converter = time.gmtime
                filehandler.setFormatter(formatter)
                impact_logger.addHandler(filehandler)

        for record in records:
            impact_logger.info(
                "Metrics - group=impact_score_metrics",
                extra={
                    "target_index": metrics_idx,
                    "tenant_id": tenant_id,
                    "object": decode_unicode(record.get("object")),
                    "object_id": record.get("object_id"),
                    "component": record.get("component"),
                    "metrics_event": json.dumps(record.get("metrics_event")),
                },
            )

        return True

    except Exception as e:
        raise Exception(str(e))


def trackme_scoring_gen_metrics(tenant_id, metrics_idx, records):
    # proceed
    try:
        # Validate inputs
        if records is None:
            get_effective_logger().warning(
                f'context="scoring_gen_metrics", tenant_id="{tenant_id}", records parameter is None, skipping metrics generation'
            )
            return False
        
        if not isinstance(records, (list, tuple)):
            get_effective_logger().warning(
                f'context="scoring_gen_metrics", tenant_id="{tenant_id}", records parameter is not iterable (type: {type(records)}), skipping metrics generation'
            )
            return False
        
        if len(records) == 0:
            get_effective_logger().debug(
                f'context="scoring_gen_metrics", tenant_id="{tenant_id}", records is empty, skipping metrics generation'
            )
            return True
        
        if metrics_idx is None:
            get_effective_logger().warning(
                f'context="scoring_gen_metrics", tenant_id="{tenant_id}", metrics_idx is None, skipping metrics generation'
            )
            return False

        # Create a dedicated logger for SLA metrics
        scoring_logger = logging.getLogger("trackme.scoring.metrics")
        scoring_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not scoring_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_scoring_metrics.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            formatter = JSONFormatter()
            logging.Formatter.converter = time.gmtime
            filehandler.setFormatter(formatter)
            scoring_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            scoring_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in scoring_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break
            
            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_scoring_metrics.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                formatter = JSONFormatter()
                logging.Formatter.converter = time.gmtime
                filehandler.setFormatter(formatter)
                scoring_logger.addHandler(filehandler)

        for record in records:
            scoring_logger.info(
                "Metrics - group=scoring_metrics",
                extra={
                    "target_index": metrics_idx,
                    "tenant_id": tenant_id,
                    "object": decode_unicode(record.get("object")),
                    "object_id": record.get("object_id"),
                    "object_category": record.get("object_category"),
                    "score_source": record.get("score_source"),
                    "metrics_event": json.dumps(record.get("metrics_event")),
                },
            )

        return True

    except Exception as e:
        raise Exception(str(e))


def generate_score_id(tenant_id, object_id, object_category, score_source, score, ctime):
    """
    Generate a deterministic SHA256 hash for score event deduplication and traceability.

    :param tenant_id: The tenant ID.
    :param object_id: The entity object ID.
    :param object_category: The component category (dsm, dhm, mhm, flx, fqm, wlk).
    :param score_source: The score source (e.g., false_positive, manual_score).
    :param score: The numeric score value.
    :param ctime: The creation time (epoch).
    :return: A SHA256 hex digest string.
    """
    raw = f"{tenant_id}|{object_id}|{object_category}|{score_source}|{score}|{ctime}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def write_score_cache(service, tenant_id, object_id, object_value, object_category, score_source, score, score_id=None, ctime=None):
    """
    Write a score record to the KV store cache for immediate visibility in the decision maker.

    For false_positive score source, uses a deterministic _key based on (object_id, score_source)
    so repeated calls upsert rather than accumulate — preventing over-correction when
    set_false_positive is called multiple times before mstats indexes.

    For manual_score, uses the unique score_id as _key so multiple manual score changes
    accumulate correctly in the cache.

    :param service: The Splunk service object.
    :param tenant_id: The tenant ID.
    :param object_id: The entity object ID.
    :param object_value: The entity name.
    :param object_category: The component category.
    :param score_source: The score source (false_positive or manual_score).
    :param score: The numeric score value.
    :param score_id: Optional pre-generated score_id for traceability with the metrics event.
    :param ctime: Optional pre-generated creation time for consistency with the metrics event.
    :return: A tuple of (score_id, ctime).
    """
    if ctime is None:
        ctime = time.time()
    if score_id is None:
        score_id = generate_score_id(tenant_id, object_id, object_category, score_source, score, ctime)

    # For false_positive sources, use deterministic _key so repeated calls upsert (latest value wins)
    # rather than accumulating multiple negative scores.
    # For manual_score, use unique score_id so multiple adjustments accumulate correctly.
    if score_source in ("false_positive", "false_positive_outlier"):
        record_key = f"{object_id}_{score_source}"
    else:
        record_key = score_id

    collection_name = f"kv_trackme_common_score_cache_tenant_{tenant_id}"
    record = {
        "_key": record_key,
        "score_id": score_id,
        "tenant_id": tenant_id,
        "object_id": object_id,
        "object": object_value,
        "object_category": object_category,
        "score_source": score_source,
        "score": score,
        "ctime": ctime,
    }

    collection = service.kvstore[collection_name]

    # Use batch_save for upsert semantics — insert() would fail on duplicate _key
    # for false_positive entries which use a deterministic key to prevent accumulation.
    collection.data.batch_save(record)

    return score_id, ctime


def read_score_cache(service, tenant_id, component):
    """
    Read all valid (within 24h) score cache records for a tenant and component.

    :param service: The Splunk service object.
    :param tenant_id: The tenant ID.
    :param component: The component category (dsm, dhm, mhm, flx, fqm, wlk).
    :return: A list of cache record dicts, or empty list on error.
    """
    collection_name = f"kv_trackme_common_score_cache_tenant_{tenant_id}"
    cutoff = time.time() - 86400  # 24 hours ago

    try:
        query = json.dumps({
            "$and": [
                {"object_category": component},
                {"ctime": {"$gt": cutoff}},
            ]
        })
        records = service.kvstore[collection_name].data.query(query=query)
        return records
    except Exception as e:
        get_effective_logger().warning(
            f'function read_score_cache, tenant_id="{tenant_id}", component="{component}", '
            f'failed to read score cache, exception="{str(e)}"'
        )
        return []
