#!/usr/bin/env python

KV_COLLECTION_NAME = "bhe-kv-last-stream"

def get_last_data_stream(service):
    # Get last data stream timestamp from kv store (RFC-3339 format)
    last_data_stream = None

    if KV_COLLECTION_NAME in service.kvstore:
        kv_collection = service.kvstore[KV_COLLECTION_NAME]

        if kv_collection.data.query():
            data = kv_collection.data.query_by_id("last_data_stream")
            if data['timestamp']:
                last_data_stream = data['timestamp']

    return last_data_stream

def insert_last_data_stream(service, new_timestamp):
    # Insert last data stream timestamp in kv store (RFC-3339 format)
    # Use insert when value does not exist
    if not KV_COLLECTION_NAME in service.kvstore:
        service.kvstore.create(KV_COLLECTION_NAME)

    kv_collection = service.kvstore[KV_COLLECTION_NAME]
    kv_collection.data.insert({"_key": "last_data_stream", "timestamp": new_timestamp})

def update_last_data_stream(service, new_timestamp):
    # Update last data stream timestamp in kv store (RFC-3339 format)
    # Use update when value already exist
    kv_collection = service.kvstore[KV_COLLECTION_NAME]
    kv_collection.data.update("last_data_stream", {"timestamp": new_timestamp})
