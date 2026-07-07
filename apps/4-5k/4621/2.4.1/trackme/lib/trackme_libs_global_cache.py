#!/usr/bin/env python
# coding=utf-8

"""
trackme_libs_global_cache.py

Provides a global cache backed by the kv_trackme_global_cache KV Store collection.
This cache is shared across all tenants to avoid redundant expensive operations
(e.g., license checks) being repeated independently by each tenant's health tracker.

Usage:
    from trackme_libs_global_cache import global_cache_get, global_cache_set, global_cache_invalidate

    # Read from cache (returns None if expired or missing)
    cached = global_cache_get(service, "license_cache", ttl=86400)
    if cached is not None:
        license_data = cached
    else:
        license_data = do_expensive_check()
        global_cache_set(service, "license_cache", license_data, tenant_id="my_tenant")

    # Invalidate cache (e.g., after a license mutation)
    global_cache_invalidate(service, "license_cache")
"""

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import json
import time
import logging
from trackme_libs_logging import get_effective_logger

# Collection name
GLOBAL_CACHE_COLLECTION = "kv_trackme_global_cache"


def global_cache_get(service, cache_name, ttl=86400):
    """
    Read a cached value from the global cache.

    Args:
        service: Splunk service connection
        cache_name: The cache key name (e.g., "license_cache")
        ttl: Time-to-live in seconds (default: 86400 = 24 hours)

    Returns:
        The cached data as a dict if the cache is valid, or None if expired/missing.
    """
    try:
        collection = service.kvstore[GLOBAL_CACHE_COLLECTION]
        records = collection.data.query(
            query=json.dumps({"_key": cache_name})
        )
        if records:
            record = records[0]
            cache_time = float(record.get("cache_time", 0))
            if (time.time() - cache_time) < ttl:
                cache_data = json.loads(record.get("cache_data", "{}"))
                if cache_data:
                    get_effective_logger().debug(
                        f'global_cache_get: cache_name="{cache_name}", status="hit", '
                        f'age={round(time.time() - cache_time, 1)}s, ttl={ttl}s'
                    )
                    return cache_data
            else:
                get_effective_logger().debug(
                    f'global_cache_get: cache_name="{cache_name}", status="expired", '
                    f'age={round(time.time() - cache_time, 1)}s, ttl={ttl}s'
                )
    except Exception as e:
        get_effective_logger().debug(
            f'global_cache_get: cache_name="{cache_name}", status="error", '
            f'exception="{str(e)}"'
        )
    return None


def global_cache_set(service, cache_name, cache_data, tenant_id=None):
    """
    Write a value to the global cache.

    Args:
        service: Splunk service connection
        cache_name: The cache key name (e.g., "license_cache")
        cache_data: The data to cache (must be JSON-serializable dict)
        tenant_id: Optional tenant ID that performed the refresh (for audit/debug)
    """
    try:
        collection = service.kvstore[GLOBAL_CACHE_COLLECTION]
        record = {
            "_key": cache_name,
            "cache_name": cache_name,
            "cache_data": json.dumps(cache_data),
            "cache_time": time.time(),
            "updated_by_tenant_id": tenant_id or "unknown",
            "mtime": time.time(),
        }
        try:
            collection.data.update(cache_name, json.dumps(record))
        except Exception:
            collection.data.insert(json.dumps(record))
        get_effective_logger().debug(
            f'global_cache_set: cache_name="{cache_name}", '
            f'updated_by_tenant_id="{tenant_id}"'
        )
    except Exception as e:
        get_effective_logger().warning(
            f'global_cache_set: cache_name="{cache_name}", status="error", '
            f'failed to write cache, exception="{str(e)}"'
        )


def global_cache_invalidate(service, cache_name):
    """
    Invalidate (delete) a cache entry, forcing the next reader to refresh it.

    Args:
        service: Splunk service connection
        cache_name: The cache key name to invalidate (e.g., "license_cache")

    Returns:
        True if the cache was invalidated, False if it didn't exist or on error.
    """
    try:
        collection = service.kvstore[GLOBAL_CACHE_COLLECTION]
        collection.data.delete(json.dumps({"_key": cache_name}))
        get_effective_logger().info(
            f'global_cache_invalidate: cache_name="{cache_name}", status="invalidated"'
        )
        return True
    except Exception as e:
        get_effective_logger().warning(
            f'global_cache_invalidate: cache_name="{cache_name}", status="not_found_or_error", '
            f'exception="{str(e)}"'
        )
        return False
