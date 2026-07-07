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
import logging

# Networking and URL handling imports
from urllib.parse import urlencode
import urllib3

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))
from trackme_libs_logging import get_effective_logger

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


"""
Define the function convert_epoch_to_datetime
"""


def convert_epoch_to_datetime(epoch):
    # convert epoch to float
    try:
        epoch = float(epoch)
        # convert epoch to datetime
        datetime = time.strftime("%d %b %Y %H:%M", time.localtime(epoch))
        return datetime
    except:
        epoch = 0
        return epoch


def get_all_ack_records_from_kvcollection(
    collection_name, collection_object, object_category
):
    """
    Retrieves all records from a collection and returns a tuple containing the records and a dictionary of records.

    :param collection: The collection object to query.
    :return: Tuple containing collection records and a dictionary of records.
    """

    # get all records
    get_collection_start = time.time()
    collection_records_list = []
    collection_records_keys = set()
    collection_records_objects = set()
    collection_records_objects_dict = {}
    collection_records_keys_dict = {}

    end = False
    skip_tracker = 0

    try:
        while end == False:
            process_collection_records = collection_object.data.query(skip=skip_tracker)
            if len(process_collection_records) != 0:
                for item in process_collection_records:
                    if (
                        item.get("_key") not in collection_records_keys
                        and item.get("object_category") == object_category
                    ):
                        collection_records_list.append(item)
                        collection_records_keys.add(item.get("_key"))
                        collection_records_keys_dict[item.get("_key")] = item
                        collection_records_objects.add(item.get("object"))
                        collection_records_objects_dict[item.get("object")] = item
                skip_tracker += len(process_collection_records)
            else:
                end = True

        get_effective_logger().debug(
            f'context="perf", get collection records, no_records="{len(collection_records_list)}", run_time="{round((time.time() - get_collection_start), 3)}", collection="{collection_name}"'
        )

        # return collection_records_list, collection_records_keys, collection_records_objects, collection_records_objects_dict, collection_records_keys_dict
        return (
            collection_records_list,
            collection_records_keys,
            collection_records_objects,
            collection_records_objects_dict,
            collection_records_keys_dict,
        )

    except Exception as e:
        get_effective_logger().error(
            f'context="perf", get collection records, exception="{str(e)}", collection="{collection_name}"'
        )
        raise Exception(
            f'context="perf", get collection records, exception="{str(e)}", collection="{collection_name}"'
        )
