import sys
import time
import json
import requests
import splunklib.client as client
import splunklib.results as results
from logger_module import Logger
from splunk_config_module import SplunkConfig


class BitdefenderIntelligenceIngestor:
    def __init__(self, session_key: str, logger, feed_name: str, feed_type: str):
        self.session_key = session_key
        self.logger = logger
        self.feed_name = feed_name
        self.feed_type = feed_type 
        self.last_seconds = 330  # Fetch data from the last 5.5 minutes (30s overlap for safety)
        self.config = SplunkConfig(script_location=__file__)

        self.api_token = self.config.get_credentials("main", session_key=self.session_key)
        self.permissions = self.config.get_config('user_configuration', 'main', 'selected_permission')
        self.logger.info(f"Feed {self.feed_name}: Permissions loaded: {self.permissions}")
        max_entries_raw = self.config.get_config('user_configuration', 'main', f'entries_{self.feed_type}')
        self.min_confidence = self.config.get_config('user_configuration', 'main', f'min_confidence_{self.feed_type}_feed')
        self.min_severity = self.config.get_config('user_configuration', 'main', f'min_severity_{self.feed_type}_feed')

        try:
            self.max_lookup_entries = int(max_entries_raw)
            self.logger.info(f"Feed {self.feed_name}: Max entries set to {self.max_lookup_entries}")
        except (TypeError, ValueError):
            self.logger.warning(f"Invalid max entries config '{max_entries_raw}' for feed type '{self.feed_type}'. Using default of 1,000,000.")
            self.max_lookup_entries = 1000000  # Default to 1 million if config is invalid
            
        self.kv_collection_name = f"bitdefender_{self.feed_type}_lookup"
        self.service = client.connect(token=self.session_key, owner="nobody", app="Bitdefender-TI-Splunk-App")
        self.kv_collection = self.service.kvstore[self.kv_collection_name]
        
        self.logger.info(f"Feed {self.feed_name}: Starting...")

    def has_permission(self):
        return self.feed_name in self.permissions

    def build_feed_url(self) -> str:
        base_url = "https://feeds.ti.bitdefender.com/reputation"
        params = f"?feed_name={self.feed_type}-feed"
        params += f"&last_seconds={self.last_seconds}"
        params += "&include_revoked=true"
        params += "&exclude_related_indicators=true"
        if self.feed_type == "file":
            params += "&exclude_similar_files=true"
        return f"{base_url}{params}"

    def get_existing_entry_count(self) -> int:
        query = f'| inputlookup {self.kv_collection_name} | stats count'
        results_list = list(results.JSONResultsReader(self.service.jobs.oneshot(query, output_mode='json')))
        return int(results_list[0].get('count', 0)) if results_list else 0

    def trim_old_entries(self, excess_count: int):
        self.logger.info(f"Feed {self.feed_name}: Trimming {excess_count} old entries to maintain limit.")
        trim_query = (
            f'| inputlookup {self.kv_collection_name} '
            f'| sort 0 + timestamp '
            f'| streamstats count AS row_num '
            f'| where row_num > {excess_count} '
            f'| fields - row_num '
            f'| outputlookup {self.kv_collection_name}'
        )
        list(results.JSONResultsReader(self.service.jobs.oneshot(trim_query, output_mode='json')))

    def fetch_feed_data(self, url: str) -> list:
        headers = {'Auth-Token': self.api_token}
        response = requests.get(url, headers=headers)
        if not response.ok:
            self.logger.error(f"Failed to fetch feed data: {response.status_code} {response.text}")
            return []
        self.logger.debug(f"Raw feed response received: {len(response.text)} characters")
        return response.text.strip().split("\n")[::-1]
    
    def _get_unique_key(self, event: dict) -> str:
        if self.feed_type == "file":
            return event.get("sha256")
        elif self.feed_type == "web":
            return event.get("url")
        elif self.feed_type == "ip":
            return event.get("ip")
        return None

    def process_and_store_events(self, lines: list):
        batch_size = 1000
        total_processed = 0
        total_saved = 0
        total_revoked = 0
        total_skipped = 0
        self.logger.info(f"Feed {self.feed_name}: Processing {len(lines)} entries...")
        for start in range(0, len(lines), batch_size):
            batch = lines[start:start + batch_size]
            self.logger.info(f"Feed {self.feed_name}: Processing from index {start} to index {start+batch_size} entries...")
            to_save = []
            keys_to_revoke = []

            for line in batch:
                total_processed += 1
                try:
                    event = json.loads(line)
                    if "related_indicators" in event:
                        del event["related_indicators"]
                    if "similar_files" in event:
                        del event["similar_files"]
                    if "affected_countries" in event:
                        del event["affected_countries"]
                    if "affected_industries" in event:
                        del event["affected_industries"]
                    if "exploited_vulnerabilities" in event:
                        del event["exploited_vulnerabilities"]
                    unique_key = self._get_unique_key(event)

                    if "revoked" in event and event['revoked']:
                        total_revoked += 1
                        keys_to_revoke.append(unique_key)
                        continue

                    if not unique_key:
                        total_skipped += 1
                        self.logger.warning(f"No valid key found for event, skipping: {event}")
                        continue

                    if (self.min_confidence is None or event.get("confidence", 0) >= int(self.min_confidence)) and \
                            (self.min_severity is None or event.get("severity", 0) >= int(self.min_severity)):
                        event["_key"] = unique_key
                        to_save.append(event)
                    else:
                        total_skipped += 1
                        continue

                except json.JSONDecodeError as e:
                    total_skipped += 1
                    self.logger.warning(f"Malformed JSON line skipped: {e} - {line}")
                    continue

            if len(keys_to_revoke):
                self.logger.info(f"Feed {self.feed_name}: Revoking {len(keys_to_revoke)} entries using KV store delete")
                # Delete each revoked key individually from KV store instead of using SPL query
                for key in keys_to_revoke:
                    try:
                        self.kv_collection.data.delete(json.dumps({"_key": key}))
                        self.logger.info(f"Feed {self.feed_name}: Successfully deleted key: {key}")
                    except Exception as e:
                        self.logger.warning(f"Feed {self.feed_name}: Failed to delete key {key}: {e}")

            if to_save:
                self.logger.info(f"Feed {self.feed_name}: Storing {len(to_save)} entries")
                self.kv_collection.data.batch_save(*to_save)
                total_saved += len(to_save)

        self.logger.info(
            f"Feed {self.feed_name}: Processing summary: Total: {total_processed}, Saved: {total_saved}, "
            f"Feed {self.feed_name}: Revoked: {total_revoked}, Skipped: {total_skipped}\n"
        )

    def run(self):
        if not self.has_permission():
            self.logger.info(f"Feed '{self.feed_name}' not permitted. Skipping ingestion.")
            return

        url = self.build_feed_url()
        self.logger.info(f"Feed {self.feed_name}: Fetching data from URL: {url}")
        existing_count = self.get_existing_entry_count()
        self.logger.info(f"Feed {self.feed_name}: Existing KV count: {existing_count}")

        new_data = self.fetch_feed_data(url)
        new_count = len(new_data)
        self.logger.info(f"Feed {self.feed_name}: Fetched {new_count} new entries.")

        total_count = existing_count + new_count
        if total_count > self.max_lookup_entries:
            excess = total_count - self.max_lookup_entries
            self.trim_old_entries(excess)

        self.process_and_store_events(new_data)


if __name__ == '__main__':
    logger = Logger(log_file_name="bitdefender_TI_kv_store_ingestion.log").get_logger()
    session_key = sys.stdin.readline().strip()

    file_ingestor = BitdefenderIntelligenceIngestor(session_key, logger, feed_name="file_feed", feed_type="file")
    file_ingestor.run()

    web_ingestor = BitdefenderIntelligenceIngestor(session_key, logger, feed_name="web_feed", feed_type="web")
    web_ingestor.run()

    ip_ingestor = BitdefenderIntelligenceIngestor(session_key, logger, feed_name="ip_feed", feed_type="ip")
    ip_ingestor.run()
    logger.info("Ingestion run complete\n\n")
