# encoding = utf-8

import json
import sys
import os
import time
import requests
from collections import OrderedDict
from datetime import datetime, timezone
from timestamp_utils import get_timestamp_format, format_timestamp_ms, epoch_ms_to_seconds

# Add the current directory to sys.path for custom libraries
sys.path.append(os.path.dirname(__file__))

from taxii2client.v21 import Server, as_pages
from taxii2client.exceptions import TAXIIServiceException


class TaxiiFeed:

    def __init__(self, helper):
        self.helper = helper
        self.taxii_server_url = helper.get_arg("taxii_server_url")
        self.api_key = helper.get_arg("api_key")
        self.username = helper.get_arg("username")
        
        self.invalid_key_checkpoint_key = "invalid_api_key"
        self.retry_interval_seconds = 3600
        saved_invalid_key = self.helper.get_check_point(self.invalid_key_checkpoint_key)

        if saved_invalid_key == self.api_key:
            self.helper.log_info("API key previously marked invalid. Skipping execution.")
            self.should_run = False
            return

        proxy_config = helper.get_proxy()
        proxies = {}
        if proxy_config.get('proxy_url') and proxy_config.get('proxy_port'):
            proxy_url = f"{proxy_config['proxy_type']}://{proxy_config['proxy_username']}:{proxy_config['proxy_password']}@{proxy_config['proxy_url']}:{proxy_config['proxy_port']}"
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }

        try:
            self.server = Server(
                self.taxii_server_url,
                user=self.username,
                password=self.api_key,
                proxies=proxies,
            )
            _ = list(self.server.api_roots[0].collections)
            self.should_run = True
        except TAXIIServiceException as e:
            self.helper.save_check_point(self.invalid_key_checkpoint_key, self.api_key)
            self.helper.log_error("API key is invalid or server unreachable.")
            self.helper.log_error(str(e))
            self.should_run = False
            return
        except Exception as e:
            last_error_time_key = "last_taxii_error_time"
            last_error_time = self.helper.get_check_point(last_error_time_key)
            now = time.time()

            if last_error_time and (now - last_error_time) < self.retry_interval_seconds:
                self.helper.log_info("TAXII server appears down. Retry postponed.")
                self.should_run = False
                return

            self.helper.save_check_point(last_error_time_key, now)
            self.helper.log_error("Error during connection to TAXII server.")
            self.helper.log_error(str(e))
            self.should_run = False
            return

        self.helper.delete_check_point(self.invalid_key_checkpoint_key)
        self.helper.delete_check_point("last_taxii_error_time")

        self.default_collection_id = "22fa3f3d-8f8a-4d50-8c41-c62deaf92cd2"
        self.collection_id = helper.get_arg("collection_id") or self.default_collection_id

    def get_collection(self):
        try:
            for collection in self.server.api_roots[0].collections:
                if collection.id == self.collection_id:
                    self.helper.log_info(f"Using collection with ID {self.collection_id}.")
                    return collection
            self.helper.log_error(f"Collection with ID {self.collection_id} not found on the TAXII server.")
            return None
        except TAXIIServiceException as e:
            self.helper.log_error("Error fetching collections from TAXII server.")
            self.helper.log_error(str(e))
            return None

    def fetch_objects_from_collection(self, collection, last_taxii_id, processed_ids):
        objects = []
        page_count = 0
        most_recent_id = None
        max_retries = 10

        for attempt in range(1, max_retries + 1):
            try:
                for envelope in as_pages(collection.get_objects, per_request=500):
                    page_count += 1
                    self.helper.log_info(f"Fetching page {page_count} from collection {collection.title}")

                    for obj in envelope.get("objects", []):
                        if not most_recent_id:
                            most_recent_id = obj["id"]

                        if obj["id"] == last_taxii_id:
                            self.helper.log_info(f"Reached the last checkpointed id {last_taxii_id}. Stopping further retrieval.")
                            return objects, most_recent_id

                        if obj["id"] in processed_ids:
                            self.helper.log_debug(f"Skipping duplicate taxii_id: {obj['id']}")
                            continue

                        obj["collection_id"] = collection.id
                        obj["collection_title"] = collection.title
                        objects.append(obj)

                    if last_taxii_id and any(obj["id"] == last_taxii_id for obj in envelope.get("objects", [])):
                        break

                self.helper.log_info(f"Fetched total {len(objects)} new objects from {page_count} pages of collection '{collection.title}'.")
                return objects, most_recent_id

            except TAXIIServiceException as e:
                if "429" in str(e):
                    self.helper.log_error("Rate limit exceeded (HTTP 429). Stopping collection for now.")
                    return [], None
                self.helper.log_error(f"TAXIIServiceException: {str(e)}")
                return [], None

            except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
                self.helper.log_warning(f"Connection error (attempt {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    delay = 2 ** attempt
                    self.helper.log_info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    self.helper.log_error(f"Max retries reached. Giving up after {max_retries} attempts.")
                    return [], None

            except requests.exceptions.HTTPError as e:
                # Check for 504 specifically, as other HTTP errors (like 404) should not be retried
                if e.response.status_code == 504:
                    self.helper.log_warning(f"HTTP 504 Gateway Timeout (attempt {attempt}/{max_retries}): {e}")
                    if attempt < max_retries:
                        delay = 2 ** attempt
                        self.helper.log_info(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
                        # Continue the loop to retry
                        continue
                    else:
                        self.helper.log_error(f"Max retries reached. Giving up after {max_retries} attempts.")
                        return [], None
                else:
                    # Handle other HTTP errors (e.g., 404, 500) as non-retriable failures
                    self.helper.log_error(f"Non-retriable HTTP error while fetching from collection: {str(e)}")
                    return [], None

            except Exception as e:
                self.helper.log_error(f"Unexpected error while fetching from collection: {str(e)}")
                return [], None

    def event_obj_gen(self, taxii_object, ts_format=None):
        def parse_timestamp(timestamp_str):
            formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%S.%f000Z",
                "%Y-%m-%dT%H:%M:%SZ"
            ]
            for fmt in formats:
                try:
                    dt = datetime.strptime(timestamp_str, fmt)
                    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
                except ValueError:
                    continue
            self.helper.log_error(f"Unrecognized timestamp format: {timestamp_str}")
            return None

        try:
            timestamp_str = taxii_object.get("modified") or taxii_object.get("created")
            timestamp_epoch_ms = parse_timestamp(timestamp_str) if timestamp_str else None

            event_obj = OrderedDict({
                "timestamp": format_timestamp_ms(timestamp_epoch_ms, ts_format) if ts_format else timestamp_epoch_ms,
                "timestamp_epoch_ms": timestamp_epoch_ms,
                "taxii_id": taxii_object.get("id"),
                "collection_id": taxii_object.get("collection_id"),
                "collection_title": taxii_object.get("collection_title"),
                "description": taxii_object.get("description", "No description"),
                "pattern": taxii_object.get("pattern", "No pattern"),
                "pattern_type": taxii_object.get("pattern_type", "unknown"),
                "valid_from": taxii_object.get("valid_from"),
                "valid_until": taxii_object.get("valid_until"),
            })

            extensions = taxii_object.get("extensions", {})
            if extensions:
                ext = extensions.get('extension-definition--ea279b3e-5c71-4632-ac08-831c66a786ba', {})
                event_obj["main_observable_type"] = ext.get("main_observable_type", "unknown")
                created_at = ext.get("created_at")
                updated_at = ext.get("updated_at")
                event_obj["extension_created_at"] = parse_timestamp(created_at) if created_at else None
                event_obj["extension_updated_at"] = parse_timestamp(updated_at) if updated_at else None
            
            # Format first_seen and last_seen fields if present
            if "first_seen" in event_obj and event_obj["first_seen"]:
                first_seen_ms = parse_timestamp(event_obj["first_seen"]) if isinstance(event_obj["first_seen"], str) else event_obj["first_seen"]
                if first_seen_ms:
                    event_obj["first_seen"] = format_timestamp_ms(first_seen_ms, ts_format) if ts_format else first_seen_ms
            if "last_seen" in event_obj and event_obj["last_seen"]:
                last_seen_ms = parse_timestamp(event_obj["last_seen"]) if isinstance(event_obj["last_seen"], str) else event_obj["last_seen"]
                if last_seen_ms:
                    event_obj["last_seen"] = format_timestamp_ms(last_seen_ms, ts_format) if ts_format else last_seen_ms

            return event_obj, timestamp_epoch_ms
        except Exception as e:
            self.helper.log_error(f"Error generating event object: {str(e)}")
            return None, None

    def push_events(self, event_writer):
        if not getattr(self, "should_run", True):
            self.helper.log_info("Skipping event push due to invalid or unavailable API key.")
            return

        index = self.helper.get_output_index()
        source_type = self.helper.get_sourcetype()

        # ---- User-configurable timestamp format ----
        ts_format = get_timestamp_format(self.helper)
        self.helper.log_info(f"Using timestamp format: {ts_format}")

        collection = self.get_collection()
        if not collection:
            self.helper.log_error(f"Collection with ID {self.collection_id} could not be found. Exiting.")
            return

        checkpoint_key_processed = f"{collection.id}_processed_ids"
        checkpoint_key_last = f"{collection.id}_last_taxii_id"

        processed_ids = self.helper.get_check_point(checkpoint_key_processed) or {}
        last_taxii_id = self.helper.get_check_point(checkpoint_key_last)

        taxii_objects, most_recent_id = self.fetch_objects_from_collection(
            collection, last_taxii_id, set(processed_ids.keys())
        )
        new_ids = {}

        for obj in taxii_objects:
            event_obj, event_epoch_ms = self.event_obj_gen(obj, ts_format)
            if event_obj:
                event = self.helper.new_event(
                    data=json.dumps(event_obj),
                    time=epoch_ms_to_seconds(event_epoch_ms),
                    index=index,
                    source="taxii",
                    sourcetype=source_type,
                )
                event_writer.write_event(event)
                new_ids[obj["id"]] = True

        if new_ids:
            processed_ids.update(new_ids)
            self.helper.save_check_point(checkpoint_key_processed, processed_ids)
        if most_recent_id:
            self.helper.save_check_point(checkpoint_key_last, most_recent_id)


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    taxii_feed = TaxiiFeed(helper)
    taxii_feed.push_events(ew)
