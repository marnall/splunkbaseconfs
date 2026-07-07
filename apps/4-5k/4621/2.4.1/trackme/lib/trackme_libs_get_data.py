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
from concurrent.futures import ThreadPoolExecutor, as_completed

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))
from trackme_libs_logging import get_effective_logger

# import trackme libs
from trackme_libs import (
    run_splunk_search,
)

# import splunklib binding exceptions for proper auth error handling
try:
    import splunklib.binding as binding
except ImportError:
    binding = None

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves



def search_kv_collection_restmode(
    logger,
    headers,
    splunkd_uri,
    collection_name,
    page=1,
    page_count=0,
    key_filter=None,
    object_filter=None,
    orderby="keyid",
):
    """
    Get records from a KVstore collection using REST API.

    :param headers: The headers to use for the request.
    :param splunkd_uri: The Splunkd URI.
    :param collection_name: The name of the collection to query.
    :param page: The page number to retrieve.
    :param page_count: The number of records to retrieve per page.
    :param key_filter: The key filter to apply to the query.
    :param object_filter: The object filter to apply to the query.
    :param orderby: The order by field to use for the query.

    :return: A tuple containing the records, keys, a dictionary of the records, and last_page.
    """

    # check orderby argument
    if orderby not in ["keyid", "object"]:
        raise ValueError(f'invalid orderby argument="{orderby}"')

    start_time = time.time()
    collection_dict = {}

    try:
        # Create a session for connection pooling
        with requests.Session() as session:
            session.headers.update(headers)
            session.verify = False

            # Build base URL
            url = f"{splunkd_uri}/servicesNS/nobody/trackme/storage/collections/data/{collection_name}"

            # Add filter if specified
            if key_filter:
                url = f"{url}/{key_filter}"
            elif object_filter:
                query_dict = {"object": {"$eq": object_filter}}
                query = f"?{urlencode({'query': json.dumps(query_dict)})}"
                url = f"{url}{query}"

            # If pagination is needed, use it directly in the request
            if page_count > 0:
                skip = (page - 1) * page_count
                params = {
                    "output_mode": "json",
                    "skip": skip,
                    "limit": page_count,
                }

                # Make the request
                response = session.get(
                    url,
                    params=params,
                    timeout=600,
                )
                response.raise_for_status()
                response_json = response.json()

                # Process results efficiently
                for item in response_json:
                    if orderby == "keyid":
                        key = item.get("_key")
                        if key:  # Only process items with valid keys
                            collection_dict[key] = item
                    elif orderby == "object":
                        object = item.get("object")
                        if object:  # Only process items with valid objects
                            collection_dict[object] = item

            else:
                # For non-paginated requests, fetch all records in chunks
                chunk_size = 10000  # KVstore's default limit
                skip = 0
                while True:
                    params = {
                        "output_mode": "json",
                        "skip": skip,
                        "limit": chunk_size,
                    }

                    # Make the request
                    response = session.get(
                        url,
                        params=params,
                        timeout=600,
                    )
                    response.raise_for_status()
                    response_json = response.json()

                    # If no more records, break the loop
                    if not response_json:
                        break

                    # Process results efficiently
                    for item in response_json:
                        if orderby == "keyid":
                            key = item.get("_key")
                            if key:  # Only process items with valid keys
                                collection_dict[key] = item
                        elif orderby == "object":
                            object = item.get("object")
                            if object:  # Only process items with valid objects
                                collection_dict[object] = item

                    # Advance by the ACTUAL number of records returned, and stop
                    # only on an empty page. KVstore caps a page by result-size
                    # (bytes), so on large-record collections a page can come back
                    # SHORT (fewer than chunk_size) while more records remain.
                    # Advancing by chunk_size / breaking on a short page here would
                    # skip the gap and silently drop those records.
                    skip += len(response_json)

            # Convert to required formats only once
            collection_records = list(collection_dict.values())
            collection_records_keys = set(collection_dict.keys())

            # Handle pagination
            if page_count == 0:
                last_page = 1
            else:
                # Get total count for pagination
                count_url = f"{splunkd_uri}/servicesNS/nobody/trackme/storage/collections/data/{collection_name}/count"
                if object_filter:
                    count_url += f"?{urlencode({'query': json.dumps({'object': {'$eq': object_filter}})})}"

                count_response = session.get(
                    count_url,
                    params={"output_mode": "json"},
                    timeout=600,
                )
                count_response.raise_for_status()
                total_count = count_response.json().get("count", 0)
                last_page = (total_count + page_count - 1) // page_count

    except Exception as e:
        msg = f'REST query failed with exception="{str(e)}"'
        get_effective_logger().error(msg)
        raise Exception(msg)

    get_effective_logger().debug(
        f'context="perf", search_kv_collection_rest, KVstore select terminated, no_records="{len(collection_records)}", run_time="{round((time.time() - start_time), 3)}", collection="{collection_name}"'
    )

    return collection_records, collection_records_keys, collection_dict, last_page


def search_kv_collection_searchmode(
    logger,
    service,
    collection_name,
    page=1,
    page_count=0,
    key_filter=None,
    object_filter=None,
    orderby="keyid",
):
    """
    Get records from a KVstore collection using a Splunk search.

    :param service: The Splunk service object.
    :param collection_name: The name of the collection to query.
    :param page: The page number to retrieve.
    :param page_count: The number of records to retrieve per page.
    :param key_filter: The key filter to apply to the query.
    :param object_filter: The object filter to apply to the query.
    :param orderby: The order by field to use for the query.

    :return: A tuple containing the records, keys, a dictionary of the records, and last_page.
    """

    # check orderby argument
    if orderby not in ["keyid", "object"]:
        raise ValueError(f'invalid orderby argument="{orderby}"')

    start_time = time.time()
    collection_dict = {}

    try:
        # Build the search command efficiently
        search_parts = [f'| inputlookup {collection_name.replace("kv_", "")}']

        # Add filter if specified
        if key_filter:
            search_parts.append(f'where keyid="{key_filter}"')
        elif object_filter:
            search_parts.append(f'where object="{object_filter}"')

        # Add pagination if needed
        if page_count > 0:
            search_parts.append(f"| head {page_count} | tail {page_count}")

        # Complete the search
        search_parts.append("| eval keyid=_key")
        search = " ".join(search_parts)

        # Optimize search parameters
        kwargs_search = {
            "earliest_time": "-5m",
            "latest_time": "now",
            "preview": "false",
            "output_mode": "json",
            "count": 0,
        }

        # Execute search and process results
        reader = run_splunk_search(
            service,
            search,
            kwargs_search,
            24,  # max_retries
            5,  # retry_delay
        )

        # Process results efficiently
        for item in reader:
            if isinstance(item, dict):
                # orderby=keyid
                if orderby == "keyid":
                    key = item.get("keyid")
                    if key:  # Only process items with valid keys
                        collection_dict[key] = item
                elif orderby == "object":
                    object = item.get("object")
                    if object:  # Only process items with valid objects
                        collection_dict[object] = item

        # Convert to required formats only once
        collection_records = list(collection_dict.values())
        collection_records_keys = set(collection_dict.keys())

        # Handle pagination
        if page_count == 0:
            last_page = 1
        else:
            # Get total count for pagination
            count_search = f'| inputlookup {collection_name.replace("kv_", "")}'
            if key_filter:
                count_search += f' where keyid="{key_filter}"'
            elif object_filter:
                count_search += f' where object="{object_filter}"'
            count_search += " | stats count"

            count_reader = run_splunk_search(
                service,
                count_search,
                kwargs_search,
                24,
                5,
            )

            total_count = 0
            for item in count_reader:
                if isinstance(item, dict) and "count" in item:
                    total_count = int(item["count"])
                    break

            last_page = (total_count + page_count - 1) // page_count

    except Exception as e:
        msg = f'main search failed with exception="{str(e)}"'
        get_effective_logger().error(msg)
        raise Exception(msg)

    get_effective_logger().debug(
        f'context="perf", search_kv_collection, KVstore select terminated, no_records="{len(collection_records)}", run_time="{round((time.time() - start_time), 3)}", collection="{collection_name}"'
    )

    return collection_records, collection_records_keys, collection_dict, last_page


def search_kv_collection_sdkmode(
    logger,
    service,
    collection_name,
    page=1,
    page_count=0,
    key_filter=None,
    object_filter=None,
    orderby="keyid",
):
    """
    Get records from a KVstore collection using a Splunk search.

    :param service: The Splunk service object.
    :param collection_name: The name of the collection to query.
    :param page: The page number to retrieve.
    :param page_count: The number of records to retrieve per page.
    :param key_filter: The key filter to apply to the query.
    :param object_filter: The object filter to apply to the query.
    :param orderby: The order by field to use for the query.

    :return: A tuple containing the records, keys, a dictionary of the records, and last_page.
    """

    # check orderby argument
    if orderby not in ["keyid", "object"]:
        raise ValueError(f'invalid orderby argument="{orderby}"')

    start_time = time.time()
    collection_dict = {}

    # connect to the collection
    collection = service.kvstore[collection_name]

    # add filter, if any
    # Note: KVstore uses _key, not keyid. keyid is only added in search_mode via | eval keyid=_key
    if key_filter:
        query_string = {"_key": key_filter}
    elif object_filter:
        query_string = {"object": object_filter}
    else:
        query_string = {}

    try:
        if query_string:
            # For filtered queries, we can fetch all matching records at once
            process_collection_records = collection.data.query(
                query=json.dumps(query_string)
            )
            for item in process_collection_records:
                # Add keyid field to match search_mode format (keyid = _key)
                keyid_value = item.get("_key")
                item["keyid"] = keyid_value
                if orderby == "keyid":
                    # Use keyid as dict key to match search_mode format exactly
                    collection_dict[keyid_value] = item
                elif orderby == "object":
                    collection_dict[item.get("object")] = item
        else:
            # For unfiltered queries, we need to use chunked fetching
            chunk_size = 10000  # KVstore's default limit
            skip_tracker = 0
            while True:
                process_collection_records = collection.data.query(
                    limit=chunk_size, skip=skip_tracker
                )
                if not process_collection_records:
                    break

                for item in process_collection_records:
                    # Add keyid field to match search_mode format (keyid = _key)
                    keyid_value = item.get("_key")
                    item["keyid"] = keyid_value
                    if orderby == "keyid":
                        # Use keyid as dict key to match search_mode format exactly
                        collection_dict[keyid_value] = item
                    elif orderby == "object":
                        collection_dict[item.get("object")] = item
                # Advance by the ACTUAL number of records returned, not the
                # requested chunk_size. KVstore caps a page by result-size (bytes),
                # so on large-record collections a page can come back SHORT while
                # more records remain; advancing by chunk_size would skip the gap
                # and silently drop those records. Loop terminates on an empty page.
                skip_tracker += len(process_collection_records)

        # Convert to list and set only once at the end
        collection_records = list(collection_dict.values())
        # collection_records_keys should contain keyid values to match search_mode format
        # Since collection_dict keys are now keyid values (which equal _key), we can use dict keys directly
        collection_records_keys = set(collection_dict.keys())

        # Handle pagination
        if page_count == 0:
            last_page = 1
        else:
            total_record_count = len(collection_records)
            last_page = (total_record_count + page_count - 1) // page_count
            # Apply pagination to the records
            start_index = (page - 1) * page_count
            end_index = page * page_count
            collection_records = collection_records[start_index:end_index]

    except Exception as e:
        # Distinguish authentication/session errors from other failures.
        # Stale or expired Splunk sessions produce AuthenticationError or HTTP 401;
        # these are transient and expected (e.g. user left a browser tab open),
        # so we log at WARNING level and raise a specific exception so the REST
        # handler can return HTTP 401 instead of a misleading 500.
        if _is_auth_expired_error(e):
            msg = f'KVstore query failed due to expired or invalid session, collection="{collection_name}", exception="{str(e)}"'
            get_effective_logger().warning(msg)
            raise AuthenticationExpiredError(msg) from e

        msg = f'main search failed with exception="{str(e)}"'
        get_effective_logger().error(msg)
        raise Exception(msg)

    get_effective_logger().debug(
        f'context="perf", search_kv_collection, KVstore select terminated, no_records="{len(collection_records)}", run_time="{round((time.time() - start_time), 3)}", collection="{collection_name}"'
    )

    return collection_records, collection_records_keys, collection_dict, last_page


class AuthenticationExpiredError(Exception):
    """Raised when a KVstore SDK query fails due to an expired or invalid Splunk session."""
    pass


def _is_auth_expired_error(e):
    """
    Determine whether an exception represents an expired or invalid Splunk session.

    Checks for splunklib AuthenticationError, HTTPError with 401/Unauthorized,
    and common session-expiry text patterns in exception messages.

    :param e: The exception to inspect.
    :return: True if the exception indicates an authentication/session failure.
    """
    error_str = str(e)
    if binding is not None and isinstance(
        e, (binding.AuthenticationError, binding.HTTPError)
    ):
        if isinstance(e, binding.AuthenticationError):
            return True
        if isinstance(e, binding.HTTPError) and (
            "401" in error_str or "Unauthorized" in error_str
        ):
            return True
    # Fallback: detect auth errors from exception text (e.g. search mode failures)
    if (
        "not logged in" in error_str.lower()
        or "not properly authenticated" in error_str.lower()
    ):
        return True
    return False


def search_kv_collection(
    service, collection_name, page=1, page_count=0, key_filter=None, object_filter=None, kvcollection_mode="search_mode", provenance=None, logger=None, instance_id=None
):
    """
    Get records from a KVstore collection using a Splunk search.
    
    This function acts as a wrapper that calls either _search_kv_collection_searchmode_impl (search_mode)
    or search_kv_collection_sdkmode (python_mode) based on the kvcollection_mode parameter.

    :param service: The Splunk service object.
    :param collection_name: The name of the collection to query.
    :param page: The page number to retrieve.
    :param page_count: The number of records to retrieve per page.
    :param key_filter: The key filter to apply to the query.
    :param object_filter: The object filter to apply to the query.
    :param kvcollection_mode: The mode to use ("search_mode" or "python_mode"). Defaults to "search_mode".
                             Should be obtained from trackme_conf["trackme_general"]["central_kvcollection_mode"]
                             via trackme_reqinfo() to ensure proper privilege elevation.
    :param provenance: Optional string describing the backend/caller (e.g., "trackme_rest_handler_component_user:dsm:tenant_123").
                       Used for debugging and logging purposes.
    :param logger: Optional logger object. If not provided, falls back to the logging module.
    :param instance_id: Optional instance identifier for request tracking. Used for debugging concurrent calls.

    :return: A tuple containing the records, keys, a dictionary of the records, and last_page.

    """
    # Use provided logger or fall back to logging module
    if logger is None:
        logger = logging
    
    # Validate and normalize mode
    if kvcollection_mode not in ("search_mode", "python_mode"):
        logger.warning(
            f'invalid kvcollection_mode value="{kvcollection_mode}", defaulting to "search_mode"'
        )
        kvcollection_mode = "search_mode"
    
    # Build provenance string for logging
    provenance_str = f', provenance="{provenance}"' if provenance else ""
    instance_id_str = f', instance_id="{instance_id}"' if instance_id else ""
    
    # Log the call
    logger.debug(
        f'search_kv_collection called, collection="{collection_name}", page="{page}", page_count="{page_count}", key_filter="{key_filter}", object_filter="{object_filter}", mode="{kvcollection_mode}"{provenance_str}{instance_id_str}'
    )
    
    try:
        # Execute the actual query based on mode
        if kvcollection_mode == "python_mode":
            # Use SDK mode
            logger.debug(
                f'using python_mode (SDK) for collection="{collection_name}"{provenance_str}'
            )
            result = search_kv_collection_sdkmode(
                logger=logger,
                service=service,
                collection_name=collection_name,
                page=page,
                page_count=page_count,
                key_filter=key_filter,
                object_filter=object_filter,
                orderby="keyid",
            )
        else:
            # Use search mode (default)
            logger.debug(
                f'using search_mode (Splunk search) for collection="{collection_name}"{provenance_str}'
            )
            result = _search_kv_collection_searchmode_impl(
                service=service,
                collection_name=collection_name,
                page=page,
                page_count=page_count,
                key_filter=key_filter,
                object_filter=object_filter,
            )
        
        return result
    
    except AuthenticationExpiredError:
        # Already logged at WARNING by the inner function; re-raise without
        # adding another ERROR-level entry for this transient condition.
        raise
    except Exception as e:
        logger.error(
            f'search_kv_collection failed, collection="{collection_name}", error="{str(e)}"{provenance_str}{instance_id_str}'
        )
        raise


def _search_kv_collection_searchmode_impl(
    service, collection_name, page=1, page_count=0, key_filter=None, object_filter=None
):
    """
    Internal implementation of search_kv_collection using Splunk search.
    This is the original search_kv_collection implementation, now renamed.

    :param service: The Splunk service object.
    :param collection_name: The name of the collection to query.
    :param page: The page number to retrieve.
    :param page_count: The number of records to retrieve per page.

    :return: A tuple containing the records, keys, a dictionary of the records, and last_page.

    """

    # run the main report, every result is a Splunk search to be executed on its own thread
    search = f'| inputlookup {collection_name.replace("kv_", "")}'

    # add filter, if any
    if key_filter:
        search += f' where keyid="{key_filter}"'
    elif object_filter:
        search += f' where object="{object_filter}"'

    # complete the search
    search = f"{search} | eval keyid=_key"

    # kwargs
    kwargs_search = {
        "earliest_time": "-5m",
        "latest_time": "now",
        "preview": "false",
        "output_mode": "json",
        "count": 0,
    }

    collection_records = []
    collection_records_keys = set()
    collection_dict = {}

    start_time = time.time()

    try:
        reader = run_splunk_search(
            service,
            search,
            kwargs_search,
            24,
            5,
        )

        for item in reader:
            if isinstance(item, dict):
                collection_records.append(item)
                collection_records_keys.add(item.get("keyid"))
                collection_dict[item.get("keyid")] = item

    except Exception as e:
        if _is_auth_expired_error(e):
            msg = f'KVstore query failed due to expired or invalid session, collection="{collection_name}", exception="{str(e)}"'
            get_effective_logger().warning(msg)
            raise AuthenticationExpiredError(msg) from e

        msg = f'main search failed with exception="{str(e)}"'
        get_effective_logger().error(msg)
        raise Exception(msg)

    get_effective_logger().debug(
        f'context="perf", search_kv_collection, KVstore select terminated, no_records="{len(collection_records)}", run_time="{round((time.time() - start_time), 3)}", collection="{collection_name}"'
    )

    # if size is 0, we consider all records as one page, simply return everything
    if page_count == 0:
        last_page = 1
        return collection_records, collection_records_keys, collection_dict, last_page

    # if size is not 0, we need to paginate
    else:
        # calculate the total number of pages
        total_record_count = len(collection_records)
        last_page = (total_record_count + page_count - 1) // page_count

        # calculate the start and end index
        start_index = (page - 1) * page_count
        end_index = page * page_count

        # return the records, keys, dict and last_page
        return (
            collection_records[start_index:end_index],
            collection_records_keys,
            collection_dict,
            last_page,
        )


def get_full_kv_collection(
    collection,
    collection_name,
    limit=1000,
    total_record_count=0,
    multi_threading=False,
    max_workers=50,
):
    """
    Get all records from a KVstore collection.

    :param collection: The KVstore collection object.
    :param collection_name: The name of the collection to query.
    :param limit: The number of records to fetch in each request.
    :param total_record_count: The total number of records in the collection (if known).

    :return: A tuple containing the records, keys, and a dictionary of the records.
    """
    collection_records = []
    collection_records_keys = set()
    collection_dict = {}

    start_time = time.time()

    def fetch_page(skip):
        """Fetch the [skip, skip+limit) window for one worker.

        Loops over byte-capped short pages so a result-size-capped page never
        leaves a gap between the parallel, precomputed windows.
        """
        try:
            out = []
            cur = skip
            window_end = skip + limit
            while cur < window_end:
                batch = collection.data.query(limit=window_end - cur, skip=cur)
                if not batch:
                    break
                out.extend(batch)
                cur += len(batch)
            return out
        except Exception as e:
            get_effective_logger().error(f"Exception fetching records with skip {skip}: {e}")
            return []

    try:

        if total_record_count == 0 or not multi_threading:

            get_effective_logger().debug(
                f'calling get_full_kv_collection with no multi-threading, collection="{collection_name}", limit="{limit}", total_record_count="{total_record_count}", multi_threading="{multi_threading}"'
            )

            end = False
            skip_tracker = 0
            while end == False:
                process_collection_records = collection.data.query(skip=skip_tracker)
                if len(process_collection_records) != 0:
                    for item in process_collection_records:
                        if item.get("_key") not in collection_records_keys:
                            collection_records.append(item)
                            collection_records_keys.add(item.get("_key"))
                            collection_dict[item.get("_key")] = item
                    skip_tracker += len(process_collection_records)
                else:
                    end = True

            return collection_records, collection_records_keys, collection_dict

        else:  # proceed with multi-threading

            get_effective_logger().debug(
                f'calling get_full_kv_collection with multi-threading, collection="{collection_name}", max_workers="{max_workers}"'
            )

            # Prepare to fetch all pages concurrently
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(fetch_page, skip): skip
                    for skip in range(0, total_record_count, limit)
                }

                for future in as_completed(futures):
                    skip = futures[future]
                    try:
                        process_collection_records = future.result()
                        if process_collection_records:
                            for item in process_collection_records:
                                if item.get("_key") not in collection_records_keys:
                                    collection_records.append(item)
                                    collection_records_keys.add(item.get("_key"))
                                    collection_dict[item.get("_key")] = item
                            get_effective_logger().debug(
                                f"Retrieved records with skip {skip}, total={len(process_collection_records)} records"
                            )
                    except Exception as e:
                        get_effective_logger().error(
                            f"Exception processing records with skip {skip}: {e}"
                        )

            get_effective_logger().info(
                f'context="perf", get_full_kv_collection, KVstore select terminated, no_records="{len(collection_records)}", run_time="{round((time.time() - start_time), 3)}", collection="{collection_name}"'
            )

            return collection_records, collection_records_keys, collection_dict

    except Exception as e:
        get_effective_logger().error(
            f"Failed to call get_kv_collection, args={collection_name}, exception={str(e)}"
        )
        raise Exception(str(e))


def get_kv_collection(
    collection, collection_name, total_record_count, page=1, page_count=100
):
    """
    Get records from a KVstore collection with support for pagination.

    :param collection: The KVstore collection object.
    :param collection_name: The name of the collection to query.
    :param total_record_count: Total number of records in the collection.
    :param page: The page number to retrieve.
    :param page_count: The number of records to retrieve per page.

    :return: A tuple containing the records, keys, a dictionary of the records, and last_page.

    """

    start_time = time.time()
    collection_records = []
    collection_records_keys = set()
    collection_dict = {}

    # Initialize last_page with a default value
    last_page = 1

    try:
        if page_count == 0:

            # Retrieve all records without pagination
            end = False
            skip_tracker = 0
            while not end:
                process_collection_records = collection.data.query(skip=skip_tracker)
                if len(process_collection_records) == 0:
                    end = True
                else:
                    for item in process_collection_records:
                        if item.get("_key") not in collection_records_keys:
                            collection_records.append(item)
                            collection_records_keys.add(item.get("_key"))
                    skip_tracker += len(process_collection_records)

            # If page_count is 0, we consider all records as one page
            last_page = 1

        else:
            # Pagination logic
            skip_tracker = (page - 1) * page_count
            limit = page_count

            fetched_records = 0
            while fetched_records < limit:
                process_collection_records = collection.data.query(
                    limit=limit, skip=skip_tracker
                )
                if process_collection_records:
                    for item in process_collection_records:
                        if item.get("_key") not in collection_records_keys:
                            collection_records.append(item)
                            collection_records_keys.add(item.get("_key"))
                            fetched_records += 1
                            if fetched_records == limit:
                                break  # Stop if we have fetched enough records for the page
                    skip_tracker += len(process_collection_records)
                else:
                    break  # End if no more records to fetch

            # Calculate the total number of pages
            if total_record_count > 0 and page_count > 0:
                last_page = (total_record_count + page_count - 1) // page_count

        get_effective_logger().info(
            f'context="perf", KVstore select terminated, no_records="{len(collection_records)}", run_time="{round((time.time() - start_time), 3)}", collection="{collection_name}", last_page="{last_page}"'
        )

        # Include last_page in the return value
        return collection_records, collection_records_keys, collection_dict, last_page

    except Exception as e:
        get_effective_logger().error(
            f"failed to call get_kv_collection, args={collection_name}, exception={str(e)}"
        )
        raise Exception(str(e))


def get_target_from_kv_collection(
    filter_field, filter_value, collection, collection_name
):
    """
    Get a specific record from a KVstore collection.

    :param filter_field: The field to filter the record by.
    :param filter_value: The value to filter the record by. Can be a single value or a list of values.
    :param collection: The KVstore collection object.
    :param collection_name: The name of the collection to query.

    :return: A tuple containing the records, keys, and a dictionary of the records.

    """
    collection_records = []
    collection_records_keys = set()
    collection_dict = {}

    # Handle list of values
    if isinstance(filter_value, list):
        query_string = {filter_field: {"$in": filter_value}}
    else:
        query_string = {filter_field: filter_value}

    try:
        process_collection_records = collection.data.query(
            query=json.dumps(query_string)
        )
        if len(process_collection_records) != 0:
            for item in process_collection_records:
                if item.get("_key") not in collection_records_keys:
                    collection_records.append(item)
                    collection_records_keys.add(item.get("_key"))
                    collection_dict[item.get("_key")] = item

        return collection_records, collection_records_keys, collection_dict

    except Exception as e:
        get_effective_logger().error(
            f"failed to call get_kv_collection, args={collection_name}, exception={str(e)}"
        )
        raise Exception(str(e))


def get_full_kv_collection_by_object(collection, collection_name):
    """
    Get all records from a KVstore collection.

    :param collection: The KVstore collection object.
    :param collection_name: The name of the collection to query.

    :return: A tuple containing the records, keys, and a dictionary of the records.

    """
    collection_records = []
    collection_records_keys = set()
    collection_dict = {}

    try:
        end = False
        skip_tracker = 0
        while end == False:
            process_collection_records = collection.data.query(skip=skip_tracker)
            if len(process_collection_records) != 0:
                for item in process_collection_records:
                    # Dedup on "object": the set and dict are both keyed by
                    # "object" and every consumer of this helper reads them by
                    # "object" (membership / lookup). The guard MUST test the
                    # same identifier or it never fires (see issue #1800).
                    item_object = item.get("object")
                    if item_object and item_object not in collection_records_keys:
                        collection_records.append(item)
                        collection_records_keys.add(item_object)
                        collection_dict[item_object] = item
                skip_tracker += len(process_collection_records)
            else:
                end = True

        return collection_records, collection_records_keys, collection_dict

    except Exception as e:
        get_effective_logger().error(
            f"failed to call get_kv_collection, args={collection_name}, exception={str(e)}"
        )
        raise Exception(str(e))


def get_sampling_kv_collection(collection, collection_name):
    """
    Get records from the DSM sampling collection

    :param collection: The KVstore collection object.
    :param collection_name: The name of the collection to query.

    :return: A tuple containing the records, keys, and a dictionary of the records.

    """
    collection_records = []
    collection_records_keys = set()
    collection_dict = {}

    try:
        end = False
        skip_tracker = 0
        while end == False:
            process_collection_records = collection.data.query(skip=skip_tracker)
            if len(process_collection_records) != 0:
                for item in process_collection_records:
                    # Dedup on "object": the set and dict are both keyed by
                    # "object" and dsm_sampling_lookup() reads them by "object".
                    # The guard MUST test the same identifier or it never fires
                    # (see issue #1800).
                    item_object = item.get("object")
                    if item_object and item_object not in collection_records_keys:
                        collection_records.append(item)
                        collection_records_keys.add(item_object)
                        # add to the dict except for raw_sample
                        collection_dict[item_object] = {
                            k: v for k, v in item.items() if k != "raw_sample"
                        }
                skip_tracker += len(process_collection_records)
            else:
                end = True

        return collection_records, collection_records_keys, collection_dict

    except Exception as e:
        get_effective_logger().error(
            f"failed to call get_kv_collection, args={collection_name}, exception={str(e)}"
        )
        raise Exception(str(e))


def get_collection_documents_count(server_rest_uri, session_key, collection_name):

    header = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/json",
    }
    url = f"{server_rest_uri}/services/server/introspection/kvstore/collectionstats?output_mode=json&count=0"

    try:
        response = requests.get(
            url,
            headers=header,
            verify=False,
            timeout=600,
        )
        if response.status_code not in (
            200,
            201,
            204,
        ):
            error_msg = f'failure to retrieve the KVstore collection document count, response.status_code="{response.status_code}", response.text="{response.text}"'
            raise Exception(error_msg)

        else:
            response_json = response.json()
            collection_count = 0
            entry = response_json["entry"]
            for item in entry:
                content = item.get("content")
                data = content.get("data")
                for subdata in data:
                    subdata = json.loads(subdata)
                    ns = subdata.get("ns")
                    count = subdata.get("count")
                    if ns == f"trackme.{collection_name}":
                        collection_count = count
                        break

            return collection_count

    except Exception as e:
        get_effective_logger().error(
            f'failure to retrieve the KVstore collection document count, exception="{str(e)}"'
        )
        raise Exception(str(e))


def get_wlk_apps_enablement_kv_collection(collection, collection_name):
    """
    Get records from the Wlk apps enablement collection

    :param collection: The KVstore collection object.
    :param collection_name: The name of the collection to query.

    :return: A tuple containing the records, keys, and a dictionary of the records.

    """
    collection_records = []
    collection_records_keys = set()
    collection_dict = {}

    try:
        end = False
        skip_tracker = 0
        while end == False:
            process_collection_records = collection.data.query(skip=skip_tracker)
            if len(process_collection_records) != 0:
                for item in process_collection_records:
                    # Dedup on "app": the set and dict are both keyed by "app"
                    # and wlk_disabled_apps_lookup() reads them by "app". The
                    # guard MUST test the same identifier or it never fires
                    # (see issue #1800).
                    item_app = item.get("app")
                    if item_app and item_app not in collection_records_keys:
                        collection_records.append(item)
                        collection_records_keys.add(item_app)
                        collection_dict[item_app] = item
                skip_tracker += len(process_collection_records)
            else:
                end = True

        return collection_records, collection_records_keys, collection_dict

    except Exception as e:
        get_effective_logger().error(
            f"failed to call get_kv_collection, args={collection_name}, exception={str(e)}"
        )
        raise Exception(str(e))


def get_feeds_datagen_kv_collection(collection, collection_name, component):
    """
    Get all records from a KVstore collection.

    :param collection: The KVstore collection object.
    :param collection_name: The name of the collection to query.

    :return: A tuple containing the records, keys, and a dictionary of the records.

    """
    datagen_collection_records = []
    datagen_collection_records_keys = set()
    datagen_collection_dict = {}

    datagen_collection_blocklist_not_regex_dict = {}
    datagen_collection_blocklist_regex_dict = {}

    try:
        end = False
        skip_tracker = 0
        while end == False:
            process_collection_records = collection.data.query(skip=skip_tracker)
            if len(process_collection_records) != 0:
                for item in process_collection_records:
                    if item.get("_key") not in datagen_collection_records_keys:
                        datagen_collection_records.append(item)
                        datagen_collection_records_keys.add(item.get("_key"))
                        datagen_collection_dict[item.get("_key")] = item

                        # blocklist
                        if item.get("action") == "block":

                            if item.get("is_rex") == "false":
                                datagen_collection_blocklist_not_regex_dict[
                                    item.get("_key")
                                ] = {
                                    "object": item.get("object"),
                                    "object_category": item.get("object_category"),
                                }

                            elif item.get("is_rex") == "true":
                                datagen_collection_blocklist_regex_dict[
                                    item.get("_key")
                                ] = {
                                    "object": item.get("object"),
                                    "object_category": item.get("object_category"),
                                }

                skip_tracker += len(process_collection_records)
            else:
                end = True

        return (
            datagen_collection_records,
            datagen_collection_records_keys,
            datagen_collection_dict,
            datagen_collection_blocklist_not_regex_dict,
            datagen_collection_blocklist_regex_dict,
        )

    except Exception as e:
        get_effective_logger().error(
            f"failed to call get_kv_collection, args={collection_name}, exception={str(e)}"
        )
        raise Exception(str(e))


def execute_batch_find_in_chunks(collection, dbqueries, chunk_size=500):
    """
    Executes batch find operations in chunks to adhere to the query limit.

    :param collection: The collection to query.
    :param dbqueries: A list of query dictionaries.
    :param chunk_size: Maximum number of queries per batch operation.
    :return: A list of kvrecords.
    """
    kvrecords_nested = []

    # Process dbqueries in chunks
    for i in range(0, len(dbqueries), chunk_size):
        chunk = dbqueries[i : i + chunk_size]
        try:
            # Execute batch_find for the current chunk
            chunk_results = collection.data.batch_find(*chunk)
            kvrecords_nested.extend(chunk_results)
        except Exception as e:
            error_msg = f"Batch find failed for a chunk, exception={str(e)}"
            get_effective_logger().error(error_msg)
            raise Exception(error_msg)

    return kvrecords_nested


def batch_find_records_by_object(collection, object_list):
    dbqueries = [{"query": {"object": object_value}} for object_value in object_list]

    try:
        # Execute batch_find to retrieve records in chunks
        kvrecords_nested = execute_batch_find_in_chunks(collection, dbqueries)

        # Flatten the list of lists to get a single list of kvrecords
        kvrecords = list(itertools.chain.from_iterable(kvrecords_nested))

        # Create a dictionary from kvrecords, keying by '_key'
        kvrecords_dict = {kvrecord["_key"]: kvrecord for kvrecord in kvrecords}

        # Return the dictionary and the flat list of kvrecords
        return kvrecords_dict, kvrecords

    except Exception as e:
        get_effective_logger().error(
            f"Failed to call batch_find_records_by_object, args={object_list}, exception={str(e)}"
        )
        raise Exception(str(e))


def batch_find_records_by_key(collection, keys_list):
    dbqueries = [{"query": {"_key": key}} for key in keys_list]

    try:
        # Execute batch_find to retrieve records in chunks
        kvrecords_nested = execute_batch_find_in_chunks(collection, dbqueries)

        # Flatten the list of lists to get a single list of kvrecords
        kvrecords = list(itertools.chain.from_iterable(kvrecords_nested))

        # Create a dictionary from kvrecords, keying by '_key'
        kvrecords_dict = {kvrecord["_key"]: kvrecord for kvrecord in kvrecords}

        # Return the dictionary and the flat list of kvrecords
        return kvrecords_dict, kvrecords

    except Exception as e:
        get_effective_logger().error(
            f"Failed to call batch_find_records_by_key, args={keys_list}, exception={str(e)}"
        )
        raise Exception(str(e))
