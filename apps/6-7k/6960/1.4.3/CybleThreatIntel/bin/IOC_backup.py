import requests as req
import json
import PasswordUtil
import sys, os
from datetime import datetime, timedelta
import HTTPUtil
import ApiConstants
import traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *
import splunklib.client as client
import time


class IOCFetcher(Script):

    def get_scheme(self):
        # Returns scheme.
        """
        Defines the scheme for the Cyble IOCV2 modular input.

        This scheme includes two arguments:
        - "api_key": A required string argument for the API Key, needed to access the service.
        - "days": A required number argument specifying the number of days for which data should be sourced. The value should be between 1 and 90.

        The scheme has external validation enabled and does not use a single instance.
        :return: A Scheme object representing the parameters for the Cyble IOCV2 modular input.
        """

        scheme = Scheme("Cyble IOCV2")
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        scheme.description = "Cyble IOCV2"

        api_key = Argument("api_key")
        api_key.title = "API Key"
        api_key.data_type = Argument.data_type_string
        api_key.description = "Enter API Key"
        api_key.required_on_create = True
        api_key.required_on_edit = True
        scheme.add_argument(api_key)

        days = Argument("days")
        days.title = "Days"
        days.data_type = Argument.data_type_number
        days.description = "Please specify the number of days you would like the data to be sourced from. The value should be between 1 and 15."
        days.required_on_create = True
        days.required_on_edit = True
        scheme.add_argument(days)
        return scheme

    def validate_input(self, validation_definition):
        """
        Validates the input configuration for the IOC Fetcher.

        This function checks the validity of the API key and the number of days provided in the input configuration.
        If the API key is masked, it retrieves the clear password using the session key. The clear password is then
        validated using the validate_ioc_api_key method. It also ensures that the number of days is within the
        acceptable range defined by MAX_ALLOWED_DAYS.

        :param validation_definition: The input definition that includes parameters and metadata for validation.
        :raises ValueError: If the API key is invalid or the number of days is outside the allowed range.
        """
        api_key = validation_definition.parameters["api_key"]

        session_key = validation_definition.metadata["session_key"]

        if api_key != ApiConstants.MASK:
            clear_password = api_key
        else:
            clear_password = PasswordUtil.get_password(session_key, ApiConstants.IOCV2_USERNAME)
        if not self.validate_api_key(clear_password):
            raise ValueError(f"Invalid API key provided for input '{clear_password}'")

        day = int(validation_definition.parameters["days"])
        if day > ApiConstants.MAX_ALLOWED_DAYS or day < 1:
            raise ValueError("Please enter days between 1 and %s" % str(ApiConstants.MAX_ALLOWED_DAYS))


    def validate_api_key(self, api_key):
        """
        Validates the given API key by making a request to the specified host.

        :param api_key: The API key to be validated.
        :return: True if the API key is valid, False otherwise.
        """

        return HTTPUtil.validate_api_key(ApiConstants.HOST, ApiConstants.PAYLOAD_VALIDATE, api_key)

    def get_time_range(self, session_key, days, interval_sec, ew):
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
        TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"  # Standard ISO format for consistent timestamp storage and parsing

        ew.log("INFO", "[CYBLE IOCS] Fetching time range started")
        lte = datetime.utcnow()
        gte = lte  # Initialize gte, will be updated
        days = int(days)

        args, service = {'token': session_key}, None
        for _ in range(5):
            try:
                service = client.connect(**args, app="CybleThreatIntel")
                ew.log("INFO", "[CYBLE IOCS] Connected to Splunk KV store client")
                break
            except Exception as e:
                ew.log("WARNING", f"[CYBLE IOCS] KV store not ready, retrying in 2 sec... Error: {e}")
                time.sleep(2)

        collection_name = "IOCs Fetch History"
        record_key = "lastFetchIOC"

        if service is None:
            ew.log("WARNING", f"[CYBLE IOCS] KV store not ready, retrying in 2 sec...")

        try:
            if collection_name not in service.kvstore:
                ew.log("INFO", "[CYBLE IOCS] First-time fetch, creating KV store collection")
                service.kvstore.create(collection_name)

            collection = service.kvstore[collection_name]
            try:
                record = collection.data.query_by_id(record_key)
            except Exception as query_err:
                if "404" in str(query_err) or "Not Found" in str(query_err):
                    ew.log("INFO", "[CYBLE IOCS] lastFetchIOC record not found, assuming first run")
                    record = None
                else:
                    raise Exception(query_err)

            if record and "timestamp" in record:
                ew.log("INFO", "[CYBLE IOCS] Found previous fetch timestamp: %s" % record["timestamp"])
                try:
                    gte = datetime.strptime(record["timestamp"], TIMESTAMP_FORMAT)
                except Exception as parse_err:
                    ew.log("WARNING",
                           f"[CYBLE IOCS] Failed to parse timestamp, falling back to interval_sec: {parse_err}")
                    gte = lte - timedelta(seconds=interval_sec)
            else:
                ew.log("INFO", "[CYBLE IOCS] No previous fetch timestamp found, using historical days: %d" % days)
                gte = lte - timedelta(days=days)
                collection.data.insert({
                    "_key": record_key,
                    "timestamp": gte.strftime(TIMESTAMP_FORMAT)
                })
                ew.log("INFO", "[CYBLE IOCS] Initialized lastFetchIOC timestamp in KV store")
        except Exception as e:
            gte = lte - timedelta(seconds=interval_sec)
            ew.log("INFO", "[CYBLE IOCS] Can't access KV Store for timestamp, Using fallback mechanism")

        return gte, lte

    def stream_events(self, inputs, ew):
        """
        Streams events from the given time range.

        This function streams events from the given time range by calling the get_iocs_count and get_iocs_page functions
        for each page of IOCs. The data is streamed in batches of 100 IOCs at a time.
        :param inputs: The input definition object.
        :param ew: The event writer object to be used for logging.
        :raises Exception: If any exception occurs during the streaming process.
        """
        try:
            ew.log("INFO", "[CYBLE IOCS] Starting IOC streaming")
            self.input_name, self.input_items = inputs.inputs.popitem()
            api_key = self.input_items["api_key"]
            days = self.input_items['days']
            interval_sec = int(self.input_items["interval"])
            ew.log("INFO",
                   f"[CYBLE IOCS] Input details - api_key: ***masked***, days: {days}, interval_sec: {interval_sec}, input_name: {self.input_name}")
            session_key = self._input_definition.metadata["session_key"]
        except Exception as e:
            ew.log("ERROR", "[CYBLE IOCS] Error reading input values: %s" % str(e))
            ew.log("ERROR", "[CYBLE IOCS] Traceback:\n%s" % traceback.format_exc())
            return

        try:
            if api_key != ApiConstants.MASK:
                PasswordUtil.encrypt_password(ApiConstants.IOCV2_USERNAME, api_key, session_key)
                PasswordUtil.mask_password(session_key, days, self.input_name)

            self.CLEAR_PASSWORD = PasswordUtil.get_password(session_key, ApiConstants.IOCV2_USERNAME)
            ew.log("INFO", "[CYBLE IOCS] Decrypted API key obtained successfully")
        except Exception as e:
            ew.log("ERROR", "[CYBLE IOCS] Issue decrypting API key: %s" % str(e))
            ew.log("ERROR", "[CYBLE IOCS] Traceback:\n%s" % traceback.format_exc())
            return

        if self.CLEAR_PASSWORD is None:
            ew.log("ERROR", "[CYBLE IOCS] Decrypted API key is None, aborting streaming")
            return

        gte, lte = self.get_time_range(session_key, days, interval_sec, ew)
        if gte is None or lte is None:
            ew.log("ERROR", "[CYBLE IOCS] Failed to determine time range, aborting streaming")
            return

        ew.log("INFO", f"[CYBLE IOCS] Pulling IOCs from {gte} to {lte}")

        more, page = True, 1
        try:
            while more:
                ew.log("INFO", f"[CYBLE IOCS] Fetching IOCs - page: {page}, gte: {gte}, lte: {lte}")
                page_array, more = HTTPUtil.get_iocs_page(self.CLEAR_PASSWORD, page, gte, lte, ew)
                if not page_array:
                    ew.log("INFO", "[CYBLE IOCS] No IOCs found on this page, ending fetch")
                    break
                
                for r in page_array:
                    event = Event()
                    event.stanza = self.input_name
                    event.data = json.dumps(r)
                    try:
                        ew.write_event(event)
                        ew.log("INFO", f"[CYBLE IOCS] Successfully inserted IOC: {r.get('ioc', 'unknown')}")
                    except Exception as e:
                        ew.log("ERROR",
                               f"[CYBLE IOCS] Failed to insert IOC: {r.get('ioc', 'unknown')} | Error: {str(e)}")
                        ew.log("ERROR", "[CYBLE IOCS] Traceback:\n%s" % traceback.format_exc())
                page += 1


            # Update last fetch time after successful streaming
            try:
                service = client.connect(token=session_key, app="CybleThreatIntel")
                collection = service.kvstore["IOCs Fetch History"]
                collection.data.update("lastFetchIOC", {"timestamp": lte.strftime("%Y-%m-%dT%H:%M:%SZ")})
                ew.log("INFO", "[CYBLE IOCS] Updated lastFetchIOC timestamp in KV store to %s" % lte.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"))
            except Exception as update_err:
                ew.log("ERROR",
                       "[CYBLE IOCS] Failed to update lastFetchIOC timestamp in KV store: %s" % str(update_err))
                ew.log("ERROR", "[CYBLE IOCS] Traceback:\n%s" % traceback.format_exc())

        except Exception as e:
            ew.log("ERROR", "[CYBLE IOCS] Error during IOC streaming: %s" % str(e))
            ew.log("ERROR", "[CYBLE IOCS] Traceback:\n%s" % traceback.format_exc())


if __name__ == "__main__":
    sys.exit(IOCFetcher().run(sys.argv))
