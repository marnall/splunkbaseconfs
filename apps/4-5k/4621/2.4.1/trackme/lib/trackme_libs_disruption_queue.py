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
import time
import json
from collections import OrderedDict
import logging
from logging.handlers import RotatingFileHandler
from urllib.parse import urlencode
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))


def disruption_queue_lookup(
    key_value,
    disruption_queue_collection_keys,
    disruption_queue_collection_dict,
    default_disruption_min_time_sec,
):
    """
    retrieve and return the disruption record for the given key_value, if any.

    returns:
        - disruption_record: disruption record if found, {} otherwise

    """

    if key_value in disruption_queue_collection_keys:
        try:
            return disruption_queue_collection_dict[key_value]
        except Exception as e:
            return {}

    else:

        # if default_disruption_min_time_sec is > 0, return a disruption record with the default value
        if default_disruption_min_time_sec > 0:
            return {
                "_key": key_value,
                "is_system_default": 1,
                "disruption_min_time_sec": default_disruption_min_time_sec,
                "disruption_start_epoch": 0,
                "object_state": "green",
                "mtime": time.time(),
            }

        else:
            return {}


def disruption_queue_update(collection_object, disruption_record):
    """
    update the disruption record
    """

    disruption_record_key = disruption_record.get("_key")
    if not disruption_record_key:
        raise Exception(
            f"disruption_record_key is required and is missing from disruption_record={json.dumps(disruption_record)}"
        )
    # if is_system_default is 1, the record does exist yet and needs to be created
    try:
        is_system_default = disruption_record.get("is_system_default", 0)
    except Exception as e:
        is_system_default = 0

    if is_system_default == 1:

        # set is_system_default to 0 since we are creating the record now
        disruption_record["is_system_default"] = 0

        try:
            collection_object.data.insert(json.dumps(disruption_record))
            return True
        except Exception as e:
            raise Exception(
                f"error creating disruption_record_key={disruption_record_key} with disruption_record={json.dumps(disruption_record)}: {e}"
            )

    # if is_system_default is not 1, the record does exist and needs to be updated
    else:

        try:
            # Create a copy of the disruption record to avoid modifying the original
            disruption_record_copy = disruption_record.copy()
            # remove the _key field from the copy
            disruption_record_copy.pop("_key", None)
            collection_object.data.update(
                disruption_record_key, json.dumps(disruption_record_copy)
            )
            return True
        except Exception as e:
            raise Exception(
                f"error updating disruption_record_key={disruption_record_key} with disruption_record={json.dumps(disruption_record)}: {e}"
            )


def disruption_queue_get_duration(disruption_record):
    """
    get the disruption duration for the entity record based on the disruption record
    """

    if disruption_record:

        # get the disruption_min_time_sec from the disruption record
        disruption_min_time_sec = int(
            disruption_record.get("disruption_min_time_sec", 0)
        )

        # if disruption_min_time_sec is not > 0, skip
        if not disruption_min_time_sec > 0:
            return

        # get the current time
        current_time = time.time()

        # get the disruption_start_epoch from the disruption record
        disruption_start_epoch = float(
            disruption_record.get("disruption_start_epoch", 0)
        )
        if not disruption_start_epoch > 0:
            return 0

        # calculate the current disruption duration
        current_disruption_duration = round(current_time - disruption_start_epoch)

        return current_disruption_duration

    else:
        return 0
