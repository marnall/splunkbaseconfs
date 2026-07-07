import sys
import time
import traceback
from datetime import datetime, timedelta
import splunklib.client as client
import splunklib.results as results
import HTTPUtil
import json
from logger_module import Logger
from splunk_config_module import SplunkConfig
from CybleVisionConfig import CybleConfig
from uuid import uuid4

class DatacollectionIOC:
    """
    Handles the collection of Indicators of Compromise (IOCs) from Cyble Vision APIs 
    and ingestion into Splunk indexes.

    This class manages the complete IOC data collection workflow, including:
      - Reading configuration values (days, interval, proxy settings, credentials)
      - Calculating time ranges for IOC fetching
      - Fetching paginated IOC data via HTTP requests
      - Storing IOCs in the Splunk index
      - Updating the fetch timestamp in KV store
    """
    def __init__(self, script_location, log_file):
        """
        Initialize the DatacollectionIOC class with configuration and logging setup.

        Args:
            script_location (str): The path to the current script file, used for configuration.
            log_file (str): The log file name for writing application logs.
        """
        self.logger = Logger(log_file_name=log_file).get_logger()
        self.splunk_config = SplunkConfig(script_location=script_location)
        self.session_key = sys.stdin.readline().strip()

        self.days = self.splunk_config.get_config('user_configuration_ioc', 'main', 'days')
        interval_value = self.splunk_config.get_config('user_configuration_ioc', 'main', 'interval')
        self.interval_sec = int(interval_value) if interval_value.isdigit() else 3600 
        self.proxy_enabled = self.splunk_config.get_config('user_configuration_ioc', 'main', 'proxy.enabled')
        self.proxy_url = self.splunk_config.get_config('user_configuration_ioc', 'main', 'proxy_url')
        self.proxy_username = self.splunk_config.get_config('user_configuration_ioc', 'main', 'proxy_username')
        self.certificate = self.splunk_config.get_config('user_configuration_certificates', 'main', 'certificate_name_ioc')

        self.api_key = self.splunk_config.get_credentials("main", session_key=self.session_key)
        self.proxy_password = self.splunk_config.get_credentials("proxy_main", session_key=self.session_key)

    def get_time_range(self, session_key, days, interval_sec, logger):
        """
        Determines the time range for fetching IOCs.
 
        This method calculates the time range for fetching Indicators of Compromise (IOCs) based on the session key,
        number of days, and interval. It connects to the key-value store and checks if a collection for IOC fetch history exists.
        If the collection exists, it sets the start time (gte) to the current time minus the specified interval in seconds.
        If the collection does not exist, it creates the collection and sets the start time (gte) to the current time minus
        the specified number of days. The calculated time range is returned as a tuple of gte and lte.
        :param session_key: The session key used to connect to the KV store.
        :param days: The number of days specified for fetching.
        :param interval_sec: The interval in seconds for fetching.
        :param ew: The event writer object for logging.
        :return: A tuple (gte, lte) representing the start and end times for fetching IOCs.
        """
        TIMESTAMP_FORMAT = f"%Y-%m-%dT%H:%M:%SZ"  # Standard ISO format for consistent timestamp storage and parsing

        logger.info("[Cyble IOCs] Fetching time range started")
        lte = datetime.utcnow()
        days = int(days)
        cyble_vision = None
        tmp = None

        gte = lte - timedelta(days=days)  # Initialize gte, will be updated
 
        args, service = {'token': session_key}, None
        for _ in range(5):
            try:
                service = client.connect(**args, app="CybleThreatIntel")
                logger.info("[Cyble IOCs] Connected to Splunk KV store client")
                break
            except Exception as e:
                logger.warning(f"[Cyble IOCs] KV store not ready, retrying in 2 sec... Error: {e}")
                time.sleep(2)
 
        collection_name, collection = "IOCs_Fetch_History", None
 
        if service is None:
            logger.warning(f"[Cyble IOCs] KV store not ready")

        try:
            if collection_name not in service.kvstore:
                logger.info("[Cyble IOCs][KV-DEBUG] Collection not found. Creating KV store collection.")
                service.kvstore.create(collection_name)
                logger.info("[Cyble IOCs][KV-DEBUG] Collection created successfully.")

            collection = service.kvstore[collection_name]

            dataLst = collection.data.query()
            logger.info(f"[Cyble IOCs][KV-DEBUG] Existing KV records count: {len(dataLst)}")

            if len(dataLst) == 0:
                logger.info(f"[Cyble IOCs][KV-DEBUG] First insert scenario. Interval: {interval_sec}")

                gte = max(lte - timedelta(days=days), gte)

                kv_key = f"ioc-{uuid4()}"
                kv_payload = {
                    "_key": kv_key,
                    "timestamp": gte.strftime(TIMESTAMP_FORMAT)
                }

                logger.info(f"[Cyble IOCs][KV-DEBUG] Attempting KV insert: {kv_payload}")

                collection.data.insert(kv_payload)

                # 🔥 VERIFY INSERT
                verify_result = collection.data.query(query={"_key": kv_key})
                logger.info(f"[Cyble IOCs][KV-DEBUG] KV query result after insert: {verify_result}")

                if not verify_result:
                    logger.error("[Cyble IOCs][KV-DEBUG] ❌ SILENT FAILURE: Inserted record NOT found in KV store")
                else:
                    logger.info("[Cyble IOCs][KV-DEBUG] ✅ KV insert verified successfully")

        except Exception as e:
            logger.error("[Cyble IOCs][KV-DEBUG] KV store access FAILED")
            logger.error(str(e))
            logger.error(traceback.format_exc())

        # ---------------------------
        # CONFIG READ + VERIFY
        # ---------------------------
        try:
            logger.info("[Cyble IOCs][CONF-DEBUG] Initializing CybleConfig")
            cyble_vision = CybleConfig(logger)

            logger.info("[Cyble IOCs][CONF-DEBUG] Attempting to read ioc_timestamp")
            tmp = cyble_vision.get("ioc_timestamp")

            logger.info(f"[Cyble IOCs][CONF-DEBUG] ioc_timestamp READ VALUE: {tmp}")
            logger.info(f"[Cyble IOCs][CONF-DEBUG] Type of value returned: {type(tmp)}")

            if tmp:
                try:
                    tmp = datetime.strptime(tmp, TIMESTAMP_FORMAT)
                except Exception:
                    logger.error("[Cyble IOCs][CONF-DEBUG] Timestamp format invalid")
                    tmp = lte - timedelta(days=days)
            else:
                tmp = lte - timedelta(days=days)

            gte = max(tmp, gte)

        except Exception as e:
            logger.error("[Cyble IOCs][CONF-DEBUG] Error during config read")
            logger.error(str(e))
            logger.error(traceback.format_exc())

        current_value = None

        if cyble_vision:
            try:
                current_value = cyble_vision.get("ioc_timestamp")
            except Exception:
                current_value = "READ_FAILED"

        logger.info(f"[Cyble IOCs] Time range: {gte} to {lte} | Current ioc_timestamp: {current_value}")

        return gte, lte

    def collect_feeds(self):
        """
        Collect IOC feeds and store them in Splunk.

        This method:
          - Validates the presence of the API key.
          - Determines the time range for data collection.
          - Fetches IOCs in a paginated manner using `HTTPUtil.get_iocs_page`.
          - Submits fetched data to the configured Splunk index.
          - Updates the KV store with the latest fetch timestamp.

        It supports proxy configuration for outbound requests and handles
        exception cases gracefully to avoid incomplete data ingestion.
        """
        if not self.api_key or self.api_key in ["", None, "NO_PASSWORD_FOUND_FOR_THIS_USER"]:
            self.logger.info("[Cyble IOCs] API Key is missing, invalid, or not configured. Aborting IOC data collection.")
            return
        
        gte, lte = self.get_time_range(self.session_key, self.days, self.interval_sec, self.logger)
        if gte is None or lte is None:
            self.logger.error("[Cyble IOCs] Failed to determine time range, aborting streaming")
            return

        self.logger.info(f"[Cyble IOCs] Pulling IOCs from {gte} to {lte}")
        total_received, inserted_count, skipped_count = 0, 0, 0
        more, page = True, 1
        try:
            while more:
                self.logger.info(f"[Cyble IOCs] Fetching IOCs - page: {page}, gte: {gte}, lte: {lte}")
                page_array, more = HTTPUtil.get_iocs_page(self.api_key, page, gte, lte, self.logger,proxy_enabled=self.proxy_enabled, proxy_url=self.proxy_url,proxy_username=self.proxy_username,proxy_password=self.proxy_password,certificate=self.certificate)
                service = client.connect(token=self.session_key, app="CybleThreatIntel")
                index = service.indexes["cyble_iocv2"]

                if not page_array:
                    self.logger.info("[Cyble IOCs] No IOCs found on this page, ending fetch")
                    break

                total_received += len(page_array)

                for r in page_array:
                    try:
                        ioc_value = r.get("ioc")
                        search_query = f'search index="cyble_iocv2" ioc="{ioc_value}" earliest=-180d latest=now'
                        self.logger.info(f"[Cyble IOCs] Checking for existing IOC: {search_query}")
                        results_found = False
                        rr = results.JSONResultsReader(service.jobs.oneshot(search_query, output_mode="json"))
                        for result in rr:
                            if isinstance(result, results.Message):
                                self.logger.info(
                                    f"[Cyble IOCs] Splunk Message - {result.type}: {result.message}"
                                )
                            elif isinstance(result, dict):
                                self.logger.info(f"[Cyble IOCs] Duplicate IOC found in Splunk index: {ioc_value}, skipping insertion.")
                                self.logger.info(f"[Cyble IOCs] Existing IOC details: {result}")
                                results_found = True
                                skipped_count += 1

                        if not results_found:
                            self.logger.info(f"[Cyble IOCs] Inserting new IOC: {ioc_value}")
                            index.submit(json.dumps(r))
                            inserted_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"[Cyble IOCs] Failed to insert IOC: {r.get('ioc', 'unknown')} | Error: {str(e)}")
                        self.logger.error(f"[Cyble IOCs] Traceback:\n{traceback.format_exc()}")
                page += 1

            self.logger.info(
                "[Cyble IOCs] Summary | Total received: %s | Inserted: %s | Skipped (duplicates): %s",
                total_received,
                inserted_count,
                skipped_count
            )

            cyble_vision = CybleConfig(self.logger)
            TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

            try:
                self.logger.info("[Cyble IOCs][CONF-DEBUG] Attempting to write ioc_timestamp")

                value_to_set = lte.strftime(TIMESTAMP_FORMAT)
                self.logger.info(f"[Cyble IOCs][CONF-DEBUG] VALUE BEING WRITTEN: {value_to_set}")

                cyble_vision.set("ioc_timestamp", value_to_set)

                # 🔥 VERIFY WRITE IMMEDIATELY
                verify_value = cyble_vision.get("ioc_timestamp")
                self.logger.info(f"[Cyble IOCs][CONF-DEBUG] VALUE READ AFTER WRITE: {verify_value}")

                if verify_value != value_to_set:
                    self.logger.error(
                        "[Cyble IOCs][CONF-DEBUG]  SILENT FAILURE: Written value does NOT match read value")
                else:
                    self.logger.info("[Cyble IOCs][CONF-DEBUG]  WRITE VERIFIED SUCCESSFULLY")

            except Exception as e:
                self.logger.error(f"[Cyble IOCs][CONF-DEBUG] ioc_timestamp WRITE FAILED: {str(e)}")
                self.logger.error(traceback.format_exc())

        except Exception as e:
            self.logger.error(f"[Cyble IOCs] Error during IOC streaming: {str(e)}")
            self.logger.error(f"[Cyble IOCs] Traceback:\n{traceback.format_exc()}")

def main():
    """
    Entry point for the IOC data collection script.

    Initializes the DatacollectionIOC instance and triggers the collection process.
    Designed for scheduled or scripted execution within Splunk.
    """
    collector = DatacollectionIOC(
        script_location=__file__,
        log_file="CybleThreatIntel_datacollection_IOC.log"
    )
    collector.collect_feeds()


if __name__ == '__main__':
    main()

