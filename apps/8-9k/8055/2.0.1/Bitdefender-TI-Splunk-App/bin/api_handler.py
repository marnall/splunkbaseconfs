import json
import requests
import splunklib.results as results
import splunklib.client as client
from splunk_config_module import SplunkConfig
import threading
import time
import traceback

class APIHandler:
    OLDEST_TIMESTAMP_SUPPORTED = int(time.time() - (24 * 60 * 60))  # 1 day ago
    MAX_QUERY_INTERVAL_SECONDS = 3600  # 1 hour
    SECONDS_BEFORE_PRESENT_TIME = 60  # 1 minutes buffer

    def __init__(self, logger):
        self.logger = logger
        self.stats = {
            'new_iocs_count': 0,                        # New IOCs added
            'revoked_count': 0,                         # IOCs removed (false positives)
            'skipped_missing_ioc_value_count': 0,       # Events missing IOC value
            'skipped_missing_ioc_timestamp_count': 0,   # Events missing IOC timestamp
            'error_count': 0,                           # JSON parsing errors
        }
        self.stats_lock = threading.Lock()


    def get_timestamp_checkpoint(self, service, feed_name):
        """
        Retrieve the last ingestion timestamp checkpoint for the given feed:
        1. From KV store checkpoint collection
        2. If not found or error, from maximum timestamp in indexed events
        3. If not found, return OLDEST_TIMESTAMP_SUPPORTED (fresh install of app)
        """
        try:
            collection = service.kvstore['bitdefender_ingestion_checkpoint']
            query = {'_key': feed_name}
            kv_results = collection.data.query(query=query)
            if kv_results:
                last_ingestion_time = kv_results[0].get('last_ingestion_time')
                self.logger.info(f"Just read timestamp checkpoint from KV store for feed '{feed_name}': {last_ingestion_time}")
                if last_ingestion_time < APIHandler.OLDEST_TIMESTAMP_SUPPORTED:
                    self.logger.warning(f"Existing timestamp checkpoint {last_ingestion_time} for feed '{feed_name}' is older than oldest supported timestamp {APIHandler.OLDEST_TIMESTAMP_SUPPORTED}. Using oldest supported timestamp instead.")
                    return APIHandler.OLDEST_TIMESTAMP_SUPPORTED
                return int(last_ingestion_time)
            else:
                self.logger.info(f"No existing timestamp checkpoint found for feed '{feed_name}'. Starting fresh from oldest supported timestamp {APIHandler.OLDEST_TIMESTAMP_SUPPORTED}")
                return APIHandler.OLDEST_TIMESTAMP_SUPPORTED
        except Exception as e:
            self.logger.error(f"Failed to retrieve timestamp checkpoint for feed '{feed_name}. Getting maximum timestamp from index as fallback': {e}. Traceback:\n{traceback.format_exc()}")

            # Try to read the maximum timestamp from the existing events in the index as a fallback
            maximum_timestamp = self.get_maximum_timestamp_from_indexed_events(service, feed_name)
            return maximum_timestamp


    def get_maximum_timestamp_from_indexed_events(self, service, feed_name):
        """
        Retrieve the oldest timestamp from existing events in the index for the given feed
        """
        try:
            search_query = f'search index="bitdefender_ti_index" sourcetype="bitdefender-{feed_name}"| stats max(_time) as max_time'
            self.logger.info(f"Running search to get maximum timestamp from index 'bitdefender_ti_index' for feed '{feed_name}': {search_query}")
            job = service.jobs.create(search_query, exec_mode="blocking")
            results_stream = job.results(output_mode="json")
            self.logger.info(f"Fetching results...")
            results_reader = results.JSONResultsReader(results_stream)
            for result in results_reader:
                max_time = int(float(result['max_time']))
                self.logger.info(f"Found maximum timestamp {max_time} from existing events in index 'bitdefender_ti_index' for feed '{feed_name}'")
                return max_time + 1  # Start from the next second

            self.logger.warning(f"No existing events found in index 'bitdefender_ti_index' for feed '{feed_name}'. Using oldest supported timestamp {APIHandler.OLDEST_TIMESTAMP_SUPPORTED}")
            return APIHandler.OLDEST_TIMESTAMP_SUPPORTED
        except Exception as e:
            self.logger.error(f"Failed to retrieve maximum timestamp from index for feed '{feed_name}': {e}. Using oldest supported timestamp {APIHandler.OLDEST_TIMESTAMP_SUPPORTED}\n Traceback:\n{traceback.format_exc()}")
            return APIHandler.OLDEST_TIMESTAMP_SUPPORTED


    def save_timestamp_checkpoint(self, service, feed_name, previous_checkpoint, checkpoint_timestamp):
        """
        Save the last ingestion timestamp checkpoint for the given feed to KV store
        """
        try:
            collection = service.kvstore['bitdefender_ingestion_checkpoint']
            # Create new record / update existing record
            kv_checkpoint_entries = [{'_key': feed_name, 'feed_name': feed_name, 'last_ingestion_time': checkpoint_timestamp}]
            collection.data.batch_save(*kv_checkpoint_entries)
            self.logger.info(f"Created new timestamp checkpoint for feed '{feed_name}' with value {checkpoint_timestamp}. Previous checkpoint was {previous_checkpoint}.")
        except Exception as e:
            self.logger.error(f"Failed to save timestamp checkpoint for feed '{feed_name}': {e}, Traceback:\n{traceback.format_exc()}")


    def process_events(self, iocs, index, feed_id, ioc_key):
        """
        Process all events in batch with efficient in-memory deduplication
        """
        to_submit = []  # New IOCs to add

        # Collect all revoked IOCs for batch deletion and determine new/updated IOCs
        for ioc in iocs:
            try:
                ioc_value = ioc.get(ioc_key, None)
                is_revoked = ioc.get('revoked', False)
                timestamp = int(ioc.get('timestamp', None))

                if not ioc_value:
                    with self.stats_lock:
                        self.stats['skipped_missing_ioc_value_count'] += 1
                    continue

                if timestamp is None:
                    with self.stats_lock:
                        self.stats['skipped_missing_ioc_timestamp_count'] += 1
                    continue

                if is_revoked:
                    ioc['revoked'] = is_revoked

                to_submit.append(ioc)
                with self.stats_lock:
                    if is_revoked:
                        self.stats['revoked_count'] += 1
                    else:
                        self.stats['new_iocs_count'] += 1

            except Exception as e:
                with self.stats_lock:
                    self.stats['error_count'] += 1
                self.logger.warning(f'Error processing ioc "{ioc}": {e}. Traceback:\n{traceback.format_exc()}')

        # Submit all IOCs
        if to_submit:
            self.logger.info(f"Submitting {len(to_submit)} IOCs ...")
            for ioc in to_submit:
                index.submit(json.dumps(ioc), sourcetype=feed_id)
            self.logger.info(f"Submitting {len(to_submit)} IOCs completed")


    def call_api(self, api_key, feed_id, index_name, session_key, feed_name, permission, ioc_key):
        """
        Calls the Bitdefender API and indexes new events into Splunk
        """
        try:
            start_time=time.time()
            config = SplunkConfig(script_location=__file__)
            permissions = config.get_config('user_configuration', 'main', 'selected_permission')
            self.logger.info(f"Checking permission {permission} for feed '{feed_name}' against allowed permissions: {permissions}")
            if permission not in permissions:
                self.logger.info(f"Feed '{feed_name}' not in selected permissions. Skipping.")
                return

            service = client.connect(token=session_key, owner="nobody", app="Bitdefender-TI-Splunk-App")
            index = service.indexes[index_name]

            # Get timestamp checkpoint from KV store
            timestamp_checkpoint = self.get_timestamp_checkpoint(service, feed_name)
            query_start_time = timestamp_checkpoint

            # Double-check query_start_time to see if it's not in the future
            current_time = int(time.time())
            if query_start_time > current_time - APIHandler.SECONDS_BEFORE_PRESENT_TIME:
                self.logger.error(f"Query start time {query_start_time} for feed '{feed_name}' is in the future. Stopping feed ingestion.")
                return

            # Ensure query_start_time is not older than oldest supported timestamp
            if query_start_time < APIHandler.OLDEST_TIMESTAMP_SUPPORTED:
                self.logger.warning(f"Query start time {query_start_time} for feed '{feed_name}' is older than oldest supported timestamp {APIHandler.OLDEST_TIMESTAMP_SUPPORTED}. Adjusting to oldest supported timestamp.")
                query_start_time = APIHandler.OLDEST_TIMESTAMP_SUPPORTED

            # Determine query end time based on max interval
            if query_start_time + APIHandler.MAX_QUERY_INTERVAL_SECONDS > int(start_time) - APIHandler.SECONDS_BEFORE_PRESENT_TIME:
                query_end_time = int(start_time) - APIHandler.SECONDS_BEFORE_PRESENT_TIME
            else:
                query_end_time = query_start_time + APIHandler.MAX_QUERY_INTERVAL_SECONDS
            self.logger.info(f"Using query interval for feed '{feed_name}': start_time={query_start_time}, end_time={query_end_time} - a total of {query_end_time - query_start_time} seconds")

            # Call the Bitdefender Feeds API
            full_url = f"https://feeds.ti.bitdefender.com/reputation?feed_name={feed_name}&include_revoked=true&from={query_start_time}&to={query_end_time}"
            headers = {'Auth-Token': api_key}
            response = requests.get(full_url, headers=headers)
            self.logger.info(f"Requesting feed: {response.url}")
            response.raise_for_status()

            for key in self.stats:
                self.stats[key] = 0

            iocs = [json.loads(line) for line in response.text.splitlines() if line.strip()]

            self.logger.info(f'Processing {len(iocs)} iocs for feed {feed_name}')

            # Process all events (much more efficient than threading for this use case)
            self.process_events(iocs, index, feed_id, ioc_key)

            self.save_timestamp_checkpoint(service, feed_name, query_start_time, query_end_time)

            total_processed = sum(self.stats.values())

            self.logger.info(f"Summary for feed '{feed_name}':")
            self.logger.info(f"New IOCs submitted: {self.stats['new_iocs_count']}")
            self.logger.info(f"IOCs revoked (false positives): {self.stats['revoked_count']}")
            self.logger.info(f"Skipped (missing IOC value): {self.stats['skipped_missing_ioc_value_count']}")
            self.logger.info(f"Skipped (missing IOC timestamp): {self.stats['skipped_missing_ioc_timestamp_count']}")
            self.logger.info(f"Skipped (processing errors): {self.stats['error_count']}")
            self.logger.info(f"Total events processed: {total_processed}")
            self.logger.info(f"Elapsed time: %.2fs\n" % (time.time()-start_time))

        except Exception as e:
            import traceback
            self.logger.error(f"API call failed: {e}, traceback:\n{traceback.format_exc()}")
