"""CTIX bulk indicator ingestion engine."""

import ta_cyware_ctix_declare  # noqa: F401

import sys
import time
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration
from splunklib import results
from ta_cyware_ctix.logging_helper import get_logger
from ctix_add_bulk_indicators import CTIXConnector
from ta_cyware_ctix.kvstore_helper import CollectionManager, KvStoreClient
from ta_cyware_ctix.conf_helper import get_account_credentials_for_search_command
from ta_cyware_ctix.ctix_exceptions import CTIXConfigurationError
from datetime import datetime

logger = get_logger("bulk_ingestion_engine")


def convert_to_epoch(timestamp):
    """Convert timestamp to epoch time (float)."""
    if isinstance(timestamp, (int, float)):
        return float(timestamp)
    elif isinstance(timestamp, str):
        try:
            # Try parsing as ISO 8601 format
            if 'T' in timestamp and '+' in timestamp:
                # Remove timezone info and convert
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.timestamp()
            else:
                # Try parsing as float string
                return float(timestamp)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert timestamp '{timestamp}' to epoch, using 0")
            return 0.0
    else:
        return 0.0


@Configuration()
class CTIXBulkIngestionEngineCommand(GeneratingCommand):
    """
    Scheduled search engine for CTIX bulk indicator ingestion.

    Runs every 6 hours to process all active sources.

    Usage:
        | ctixbulkingestionengine
    """

    def _update_source_success(self, collection, source_key, source, result):
        """Update source record after successful processing."""
        existing_record = collection.query_by_id(source_key)
        if existing_record:
            existing_record["last_run"] = int(time.time())
            existing_record["last_status"] = "success"
            existing_record["checkpoint_time"] = result.get("checkpoint_time", source.get("checkpoint_time", 0))
            existing_record["checkpoint_row"] = result.get("checkpoint_row", source.get("checkpoint_row", 0))
            existing_record["updated_time"] = int(time.time())
            collection.upsert([existing_record])

    def _update_source_failure(self, collection, source_key):
        """Update source record after failed processing."""
        try:
            existing_record = collection.query_by_id(source_key)
            if existing_record:
                existing_record["last_run"] = int(time.time())
                existing_record["last_status"] = "failed"
                existing_record["updated_time"] = int(time.time())
                collection.upsert([existing_record])
        except Exception as update_error:
            logger.error(f"Failed to update source status: {str(update_error)}")

    def _process_single_source(self, source, collection):
        """Process a single source and update its status."""
        source_key = source.get("_key")
        source_name = source.get("source_name", "unknown")
        source_type = source.get("source_type")

        logger.info(f"Processing source: {source_name} (type: {source_type})")

        try:
            result = self.process_source(source)

            if result["status"] == "success":
                self._update_source_success(collection, source_key, source, result)
                result["source_key"] = source_key
                result["source_name"] = source_name
                return result, True
            else:
                self._update_source_failure(collection, source_key)
                result["source_key"] = source_key
                result["source_name"] = source_name
                return result, False

        except Exception as e:
            logger.error(f"Error processing source {source_name}: {str(e)}", exc_info=True)
            self._update_source_failure(collection, source_key)
            return {
                "status": "error",
                "message": f"Error processing source: {str(e)}",
                "source_key": source_key,
                "source_name": source_name,
                "_time": time.time()
            }, False

    def generate(self):
        """Generate command results."""
        try:
            # Use CollectionManager for better connection handling (RedHat OS fix)
            collection = CollectionManager(
                collection_name="ctix_bulk_indicator_sources",
                session_key=self._metadata.searchinfo.session_key
            )

            sources = collection.get(query={"status": "active"})

            if not sources:
                logger.info("No active sources found for bulk ingestion")
                yield {
                    "status": "info",
                    "message": "No active sources configured",
                    "sources_processed": 0,
                    "_time": time.time()
                }
                return

            logger.info(f"Found {len(sources)} active source(s) to process")

            total_sources = len(sources)
            successful_sources = 0
            failed_sources = 0

            for source in sources:
                result, success = self._process_single_source(source, collection)
                if success:
                    successful_sources += 1
                else:
                    failed_sources += 1
                yield result

            yield {
                "status": "summary",
                "message": f"Bulk ingestion completed: {successful_sources} successful, {failed_sources} failed",
                "total_sources": total_sources,
                "successful_sources": successful_sources,
                "failed_sources": failed_sources,
                "_time": time.time()
            }

        except Exception as e:
            logger.error(f"Error in bulk ingestion engine: {str(e)}", exc_info=True)
            yield {
                "status": "error",
                "message": f"Bulk ingestion engine error: {str(e)}",
                "_time": time.time()
            }

    def process_source(self, source):
        """Process a single source and return results."""
        source_type = source.get("source_type")
        checkpoint_time = convert_to_epoch(source.get("checkpoint_time", 0))
        checkpoint_row = source.get("checkpoint_row", 0)

        indicators = []
        new_checkpoint_time = checkpoint_time
        new_checkpoint_row = checkpoint_row

        if source_type == "index":
            indicators, _ = self.fetch_from_index(
                source, checkpoint_time
            )
        elif source_type == "cim":
            indicators, _ = self.fetch_from_cim(
                source, checkpoint_time
            )
        elif source_type == "datamodel":
            indicators, _ = self.fetch_from_datamodel(
                source, checkpoint_time
            )
        elif source_type == "lookup":
            indicators, new_checkpoint = self.fetch_from_lookup(
                source, checkpoint_row
            )
            new_checkpoint_row = new_checkpoint
        else:
            return {
                "status": "error",
                "message": f"Unknown source type: {source_type}"
            }

        if not indicators:
            logger.info(f"No new indicators found for source: {source.get('source_name')}")
            return {
                "status": "success",
                "message": "No new indicators to process",
                "indicators_processed": 0,
                "checkpoint_time": new_checkpoint_time,
                "checkpoint_row": new_checkpoint_row
            }

        logger.info(f"Found {len(indicators)} new indicators, posting to Cyware...")

        api_result = self.post_to_ctix(source, indicators)

        return {
            "status": "success",
            "message": f"Processed {len(indicators)} indicators",
            "indicators_found": len(indicators),
            "indicators_processed": api_result.get("total_iocs", 0),
            "indicators_skipped": api_result.get("skipped", 0),
            "created": api_result.get("created", 0),
            "updated": api_result.get("updated", 0),
            "already_exists": api_result.get("already_exists", 0),
            "failed": api_result.get("failed", 0),
            "checkpoint_time": new_checkpoint_time,
            "checkpoint_row": new_checkpoint_row,
            "_time": time.time()
        }

    def fetch_from_index(self, source, checkpoint_time):
        """Fetch indicators from Splunk index."""
        index_name = source.get("index_name")
        sourcetype_filter = source.get("sourcetype", "")
        field_name = source.get("field_name")

        search_query = f'search index="{index_name}"'
        if sourcetype_filter:
            search_query += f' sourcetype="{sourcetype_filter}"'

        if checkpoint_time > 0:
            search_query += f' _time > {checkpoint_time}'
        else:
            search_query += ' earliest=-24h'

        search_query += f' | dedup {field_name} | table {field_name} _time | sort - _time'

        logger.info(f"Executing search: {search_query}")

        # Create service connection using KvStoreClient (RedHat OS fix)
        kvstore_client = KvStoreClient(session_key=self._metadata.searchinfo.session_key)
        service = kvstore_client._connect_splunk_service()

        job = service.jobs.create(search_query, exec_mode="blocking")

        indicators = []
        max_time = checkpoint_time

        for result in results.ResultsReader(job.results(count=0)):
            if isinstance(result, dict):
                indicator_value = result.get(field_name)
                event_time = convert_to_epoch(result.get("_time", 0))

                if indicator_value:
                    indicators.append(indicator_value)

                if event_time > max_time:
                    max_time = event_time

        job.cancel()

        return indicators, int(max_time) if max_time > checkpoint_time else checkpoint_time

    def fetch_from_cim(self, source, checkpoint_time):
        """Fetch indicators from CIM datamodel."""
        datamodel_name = source.get("datamodel_name")
        field_name = source.get("field_name")

        search_query = f'| from datamodel {datamodel_name}'

        if checkpoint_time > 0:
            search_query += f' | where _time > {checkpoint_time}'
        else:
            search_query += ' | where _time >= relative_time(now(), "-24h")'

        search_query += f' | dedup {field_name} | table {field_name} _time | sort - _time'

        logger.info(f"Executing CIM datamodel search: {search_query}")

        # Create service connection using KvStoreClient (RedHat OS fix)
        kvstore_client = KvStoreClient(session_key=self._metadata.searchinfo.session_key)
        service = kvstore_client._connect_splunk_service()

        job = service.jobs.create(search_query, exec_mode="blocking")

        indicators = []
        max_time = checkpoint_time

        for result in results.ResultsReader(job.results(count=0)):
            if isinstance(result, dict):
                indicator_value = result.get(field_name)
                event_time = convert_to_epoch(result.get("_time", 0))

                if indicator_value:
                    indicators.append(indicator_value)

                if event_time > max_time:
                    max_time = event_time

        job.cancel()

        return indicators, int(max_time) if max_time > checkpoint_time else checkpoint_time

    def fetch_from_datamodel(self, source, checkpoint_time):
        """Fetch indicators from custom_datamodel datamodel."""
        datamodel_name = source.get("datamodel_name")
        field_name = source.get("field_name")

        search_query = f'| from datamodel {datamodel_name}'

        if checkpoint_time > 0:
            search_query += f' | where _time > {checkpoint_time}'
        else:
            search_query += ' | where _time >= relative_time(now(), "-24h")'

        search_query += f' | dedup {field_name} | table {field_name} _time | sort - _time'

        logger.info(f"Executing datamodel search: {search_query}")

        # Create service connection using KvStoreClient (RedHat OS fix)
        kvstore_client = KvStoreClient(session_key=self._metadata.searchinfo.session_key)
        service = kvstore_client._connect_splunk_service()

        job = service.jobs.create(search_query, exec_mode="blocking")

        indicators = []
        max_time = checkpoint_time

        for result in results.ResultsReader(job.results(count=0)):
            if isinstance(result, dict):
                indicator_value = result.get(field_name)
                event_time = convert_to_epoch(result.get("_time", 0))

                if indicator_value:
                    indicators.append(indicator_value)

                if event_time > max_time:
                    max_time = event_time

        job.cancel()

        return indicators, int(max_time) if max_time > checkpoint_time else checkpoint_time

    def fetch_from_lookup(self, source, checkpoint_row):
        """Fetch indicators from KV Store/Lookup."""
        lookup_name = source.get("lookup_name")
        field_name = source.get("field_name")

        search_query = f'| inputlookup {lookup_name} | dedup {field_name} | table {field_name}'

        logger.info(f"Executing lookup search: {search_query}")

        # Create service connection using KvStoreClient (RedHat OS fix)
        kvstore_client = KvStoreClient(session_key=self._metadata.searchinfo.session_key)
        service = kvstore_client._connect_splunk_service()

        job = service.jobs.create(search_query, exec_mode="blocking")

        indicators = []
        row_count = 0

        for result in results.ResultsReader(job.results(count=0)):
            if isinstance(result, dict):
                row_count += 1

                if row_count > checkpoint_row:
                    indicator_value = result.get(field_name)
                    if indicator_value:
                        indicators.append(indicator_value)

        job.cancel()

        new_checkpoint = checkpoint_row + len(indicators) if indicators else checkpoint_row

        return indicators, new_checkpoint

    def post_to_ctix(self, source, indicators):
        """Post indicators to CTIX using existing bulk API logic."""
        splunk_account = source.get("splunk_account")
        session_key = self._metadata.searchinfo.session_key

        # Use conf_helper to get account credentials (same as manual workflow)
        try:
            account_creds = get_account_credentials_for_search_command(
                splunk_account, logger, session_key
            )

            api_url = account_creds.get("base_url")
            client_id = account_creds.get("access_id")
            client_secret = account_creds.get("secret_key")

            if not client_id or not client_secret or not api_url:
                raise CTIXConfigurationError(f"Incomplete credentials for account: {splunk_account}")
        except Exception as e:
            logger.error(f"Error fetching account credentials: {str(e)}")
            raise

        tags_list = []
        if source.get("tags"):
            tags_list = [t.strip() for t in source.get("tags").split(",") if t.strip()]

        connector = CTIXConnector(
            api_url=api_url,
            access_id=client_id,
            secret_key=client_secret,
            session_key=session_key
        )

        result = connector.add_indicators_bulk(
            ioc_values=indicators,
            source_name=source.get("source_name_metadata", "Splunk"),
            tlp=source.get("tlp", "AMBER"),
            confidence=int(source.get("confidence", 100)),
            tags=tags_list,
            description=source.get("description", f"Indicators from {source.get('source_name')}"),
            collection_name=source.get("collection_name", "")
        )

        return result


dispatch(CTIXBulkIngestionEngineCommand, sys.argv, sys.stdin, sys.stdout, __name__)
