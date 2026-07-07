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
import json
import itertools

# Networking and URL handling imports
import requests
from urllib.parse import urlencode
import urllib3

# multithreading
import concurrent.futures

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


def batch_update_worker(
    collection_name,
    collection_object,
    inputs_dict_or_list,
    parent_instance_id,
    task_instance_id,
    task_name="batch_update",
    max_multi_thread_workers=16,
):
    """
    Function to handle batch updates in parallel using ThreadPoolExecutor
    """
    batch_update_collection_start = time.time()
    max_retries = 3
    
    # Handle both dictionary and list inputs
    final_records = []
    if isinstance(inputs_dict_or_list, dict):
        # loop through the collection_object dict and add to the list
        for key, value in inputs_dict_or_list.items():
            value["_key"] = key
            final_records.append(value)
    elif isinstance(inputs_dict_or_list, list):
        # If it's a list, use the records directly
        final_records = inputs_dict_or_list
    
    # process by chunk
    chunks = [final_records[i : i + 500] for i in range(0, len(final_records), 500)]
    
    total_records = sum(len(chunk) for chunk in chunks)
    successful_updates = 0
    failed_updates = 0

    def process_chunk(chunk_data):
        chunk_idx, chunk = chunk_data
        chunk_success = 0
        chunk_failed = 0
        retry_count = 0

        while retry_count < max_retries:
            try:
                collection_object.data.batch_save(*chunk)
                chunk_success = len(chunk)
                break
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    chunk_failed = len(chunk)
                    get_effective_logger().error(
                        f'parent_instance_id={parent_instance_id}, task="{task_name}", task_instance_id={task_instance_id}, KVstore batch failed after {max_retries} retries with exception="{str(e)}", chunk={chunk_idx}/{len(chunks)}, collection="{collection_name}"'
                    )
                else:
                    get_effective_logger().warning(
                        f'parent_instance_id={parent_instance_id}, task="{task_name}", task_instance_id={task_instance_id}, KVstore batch failed, retrying ({retry_count}/{max_retries}) with exception="{str(e)}", chunk={chunk_idx}/{len(chunks)}, collection="{collection_name}"'
                    )
                    time.sleep(1)  # Add small delay between retries

        return chunk_success, chunk_failed

    # Use ThreadPoolExecutor for parallel processing
    # max_multi_thread_workers is the absolute maximum allowed by configuration
    # We might use fewer workers if we have fewer chunks to process
    max_workers = max(
        1, min(max_multi_thread_workers, len(chunks))
    )  # Never exceed configured max, but might use fewer if we have less work, and never less than 1

    get_effective_logger().info(
        f'parent_instance_id={parent_instance_id}, task="{task_name}", task_instance_id={task_instance_id}, context="perf", parallel processing configuration, configured_max_workers="{max_multi_thread_workers}", actual_workers="{max_workers}", total_chunks="{len(chunks)}", collection="{collection_name}"'
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all chunks for processing
        future_to_chunk = {
            executor.submit(process_chunk, (idx, chunk)): (idx, chunk)
            for idx, chunk in enumerate(chunks, 1)
        }

        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_chunk):
            chunk_success, chunk_failed = future.result()
            successful_updates += chunk_success
            failed_updates += chunk_failed

    # perf counter for the batch operation
    run_time = round((time.time() - batch_update_collection_start), 3)
    success_rate = (
        round((successful_updates / total_records) * 100, 2)
        if total_records > 0
        else 0
    )
    get_effective_logger().info(
        f'parent_instance_id={parent_instance_id}, task="{task_name}", task_instance_id={task_instance_id}, context="perf", batch KVstore update terminated, total_records="{total_records}", successful="{successful_updates}", failed="{failed_updates}", success_rate="{success_rate}%", run_time="{run_time}", collection="{collection_name}"'
    )

    # Return per-call counters so REST handlers and callers can surface them
    # to clients / audit. Existing callers that ignore the return value remain
    # unaffected.
    return {
        "total_records": total_records,
        "successful_updates": successful_updates,
        "failed_updates": failed_updates,
        "success_rate": success_rate,
        "run_time": run_time,
    }
