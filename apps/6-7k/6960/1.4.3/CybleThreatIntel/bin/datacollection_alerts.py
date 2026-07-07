
import sys
import time
import traceback
from datetime import datetime, timedelta
import splunklib.client as client
import HTTPUtil
from logger_module import Logger
from splunk_config_module import SplunkConfig
import concurrent.futures
import ApiConstants
from CybleVisionConfig import CybleConfig
from uuid import uuid4


class DatacollectionAlerts:
    """
    Handles the automated collection of Cyble Vision alert data and ingestion into Splunk.

    This class manages:
      - Configuration and credential retrieval.
      - Time range calculation for incremental alert fetching.
      - Concurrent data migration for multiple services.
      - Secure API communication with proxy support.
      - KV store timestamp updates for tracking data sync.
    """
    def __init__(self, script_location, log_file):
        """
        Initialize the DatacollectionAlerts class with logger, Splunk configurations, and credentials.

        Args:
            script_location (str): The full path of the current script for configuration reference.
            log_file (str): Name of the log file used for recording execution details.
        """
        self.logger = Logger(log_file_name=log_file).get_logger()
        self.splunk_config = SplunkConfig(script_location=script_location)
        self.session_key = sys.stdin.readline().strip()

        self.input_name = self.splunk_config.get_config('user_configuration_alerts', 'main', 'name_config')
        self.days = self.splunk_config.get_config('user_configuration_alerts', 'main', 'days')
        interval_sec = self.splunk_config.get_config('user_configuration_alerts', 'main', 'interval')
        self.interval_sec =  int(interval_sec) if interval_sec.isdigit() else 3600
        self.hide_data = self.splunk_config.get_config('user_configuration_alerts', 'main', 'hide_data')

        self.proxy_enabled = self.splunk_config.get_config('user_configuration_alerts', 'main', 'proxy.enabled')
        self.proxy_url = self.splunk_config.get_config('user_configuration_alerts', 'main', 'proxy_url')
        self.proxy_username = self.splunk_config.get_config('user_configuration_alerts', 'main', 'proxy_username')
        self.certificate = self.splunk_config.get_config('user_configuration_certificates', 'main', 'certificate_name_alert')

        self.api_key = self.splunk_config.get_credentials("main_alerts", session_key=self.session_key)
        self.proxy_password = self.splunk_config.get_credentials("proxy_main_alerts", session_key=self.session_key)

        
    def get_time_range(self, session_key, days, interval_sec, logger):
        """
        Determine the time range for fetching alerts.

        The method uses KV Store and CybleVision configuration to determine the start (`gte`)
        and end (`lte`) times for data fetching. It ensures incremental data collection by
        using the last recorded fetch timestamp or falling back to a default lookback period.

        Args:
            session_key (str): Splunk session key for KV store connection.
            days (int): Number of days to look back for the first fetch.
            interval_sec (int): Time interval (in seconds) between two fetches.
            logger (logging.Logger): Logger instance for event logging.

        Returns:
            tuple: (gte, lte)
                gte (datetime): Start time for fetching alerts.
                lte (datetime): End time (current UTC).
        """

        lte, days = datetime.utcnow(), int(days)
        gte = lte - timedelta(days=days)
        TIMESTAMP_FORMAT = f"%Y-%m-%dT%H:%M:%SZ"
        cyble_vision = None
        tmp = None

        args, service = {'token': session_key}, None
        for _ in range(5):
            try:
                service = client.connect(**args, app="CybleThreatIntel")
                logger.info("[Cyble Events] Connected to Splunk KV store client")
                break
            except Exception as e:
                logger.info(f"[Cyble Events] KV store not ready, retrying in 2 sec... Error: {e}")
                time.sleep(2)
 
        collection_name, collection = "Alert_Fetch_History", None

        if service is None:
            logger.info(f"[Cyble Events] KV store not ready")

        try:
            if collection_name not in service.kvstore:
                logger.info("[Cyble Events][KV-DEBUG] Collection not found. Creating KV store collection.")
                service.kvstore.create(collection_name)
                logger.info("[Cyble Events][KV-DEBUG] Collection created successfully.")

            collection = service.kvstore[collection_name]

            dataLst = collection.data.query()
            logger.info(f"[Cyble Events][KV-DEBUG] Existing KV records count: {len(dataLst)}")

            if len(dataLst) == 0:
                logger.info(f"[Cyble Events][KV-DEBUG] First insert scenario. Interval: {interval_sec}")

                gte = max(lte - timedelta(days=days), gte)

                kv_key = f"alert-{uuid4()}"
                kv_payload = {
                    "_key": kv_key,
                    "timestamp": gte.strftime(TIMESTAMP_FORMAT)
                }

                logger.info(f"[Cyble Events][KV-DEBUG] Attempting KV insert: {kv_payload}")

                collection.data.insert(kv_payload)

                verify_result = collection.data.query(query={"_key": kv_key})

                logger.info(f"[Cyble Events][KV-DEBUG] KV query result after insert: {verify_result}")

                if not verify_result:
                    logger.error("[Cyble Events][KV-DEBUG]  SILENT FAILURE: Inserted record NOT found in KV store")
                else:
                    logger.info("[Cyble Events][KV-DEBUG]  KV insert verified successfully")

        except Exception as e:
            logger.error("[Cyble Events][KV-DEBUG] KV store access FAILED")
            logger.error(str(e))
            logger.error(traceback.format_exc())

        try:
            try:
                logger.info("[Cyble Events][CONF-DEBUG] Initializing CybleConfig")

                cyble_vision = CybleConfig(logger)

                logger.info("[Cyble Events][CONF-DEBUG] Attempting to read alert_timestamp")

                tmp = cyble_vision.get("alert_timestamp")

                logger.info(f"[Cyble Events][CONF-DEBUG] alert_timestamp READ VALUE: {tmp}")

            except Exception as e:
                logger.error(f"[Cyble Events][CONF-DEBUG] alert_timestamp READ FAILED: {str(e)}")
                logger.error(traceback.format_exc())
                tmp = None

            if tmp is None or len(tmp) == 0:
                tmp = lte - timedelta(days=days)
            else: tmp = datetime.strptime(tmp, TIMESTAMP_FORMAT)
 
            gte = max(tmp, gte)

        except Exception as e:
           logger.info("[Cyble Events] Error occurred in get_time_range from configuration, Error: %s" % str(e))

        logger.info("[Cyble Events] Time range: %s to %s get_time_range" % (str(gte), str(lte)))
        return gte, lte

    def migrate_data(self, api_key, logger, gte: datetime, lte: datetime, input_name, hide_data=False,
                 proxy_enabled=None, proxy_url=None, proxy_username=None, proxy_password=None, session_key=None, certificate=None):
        """
        Migrates data from the given time range.

        This function migrates data from the given time range by calling the get_data_with_retry function for each service
        in the given list of services. The data is migrated in batches of MAX_CUNCURRENT_REQUESTS services at a time.

        :param api_key: The API key to be used for the migration.
        :param ew: The event writer object to be used for logging.
        :param gte: The start time of the time range to be migrated.
        :param lte: The end time of the time range to be migrated.
        :param input_name: The name of the input for which the data is being migrated.
        :param hide_data: Flag to determine if the user wishes to hide the sensitive data.
        :raises Exception: If any exception occurs during the migration process.
        """
       
        logger.info("[Cyble Events] Data migration started")

        # Log proxy configuration
        if str(proxy_enabled).lower() == "true" and proxy_url:
            logger.info(f"[Cyble Events] Proxy is enabled.")
        else:
            logger.info("[Cyble Events] Proxy disabled or not configured.")

        if certificate:
            logger.info(f"[Cyble Events] Using certificate.")
        else:
            logger.warning("[Cyble Events] No SSL certificate configured. ")

        alert_services = HTTPUtil.get_all_services(api_key, logger, certificate,proxy_enabled,proxy_url,proxy_username,proxy_password)

        logger.info("[Cyble Events] Fetched services")

        chunked_services = [
            alert_services[i:i + ApiConstants.MAX_CUNCURRENT_REQUESTS]
            for i in range(0, len(alert_services), ApiConstants.MAX_CUNCURRENT_REQUESTS)
        ]

        try:
            for chunk in chunked_services:
                logger.info(f"[Cyble Events] Processing chunk: {chunk}")

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = {
                        executor.submit(
                            HTTPUtil.get_data_with_retry,
                            api_key,
                            gte,
                            lte,
                            logger,
                            input_name,
                            service,
                            hide_data,
                            proxy_enabled,    
                            proxy_url,        
                            proxy_username,   
                            proxy_password,
                            session_key,
                            certificate
                        ): service for service in chunk
                    }
    
                    for future in concurrent.futures.as_completed(futures):
                        result = future.result()
                        logger.info(f"[Cyble Events] Fetching data for service completed: {result}")

        except Exception as e:
            logger.info(f"[Cyble Events] Issue in migrate_data, Error: {str(e)}")

    def collect_feeds(self):
        """
        Orchestrates the full Cyble alert data collection workflow.

        - Validates API key availability.
        - Determines the incremental fetch window.
        - Triggers parallel data migration using the configured proxy and API credentials.
        - Logs detailed progress and error information for Splunk debugging.
        """

        if not self.api_key or self.api_key in ["", None, "NO_PASSWORD_FOUND_FOR_THIS_USER"]:
            self.logger.info("[Cyble Events] API Key is missing, invalid, or not configured. Aborting Alerts data collection.")
            return
        gte, lte = self.get_time_range(self.session_key, self.days, self.interval_sec, self.logger)

        self.logger.info(f"[Cyble Events] Pulling data from %s to %s" % (str(gte), str(lte)))
        self.migrate_data(
            self.api_key,
            self.logger,
            gte,
            lte,
            self.input_name,
            self.hide_data,
            self.proxy_enabled,
            self.proxy_url,
            self.proxy_username,
            self.proxy_password,
            self.session_key,
            self.certificate
        )
        cyble_vision = CybleConfig(self.logger)
        TIMESTAMP_FORMAT = f"%Y-%m-%dT%H:%M:%SZ"
        try:
            self.logger.info("[Cyble Events][CONF-DEBUG] Attempting to write alert_timestamp")

            value_to_set = lte.strftime(TIMESTAMP_FORMAT)
            self.logger.info(f"[Cyble Events][CONF-DEBUG] VALUE BEING WRITTEN: {value_to_set}")

            cyble_vision.set("alert_timestamp", value_to_set)

            verify_value = cyble_vision.get("alert_timestamp")
            self.logger.info(f"[Cyble Events][CONF-DEBUG] VALUE READ AFTER WRITE: {verify_value}")

            if verify_value != value_to_set:
                self.logger.error("[Cyble Events][CONF-DEBUG] SILENT FAILURE: Written value does NOT match read value")
            else:
                self.logger.info("[Cyble Events][CONF-DEBUG] WRITE VERIFIED SUCCESSFULLY")

        except Exception as e:
            self.logger.error(f"[Cyble Events][CONF-DEBUG] alert_timestamp WRITE FAILED: {str(e)}")
            self.logger.error(traceback.format_exc())


def main():
    """
    Entry point for Cyble Vision Alert data collection.

    Initializes the data collector class and starts the feed collection process.
    Intended to be executed as a standalone script or scheduled Splunk modular input.
    """
    collector = DatacollectionAlerts(
        script_location=__file__,
        log_file="CybleThreatIntel_datacollection_Alerts.log"
    )
    collector.collect_feeds()

if __name__ == '__main__':
    main()
