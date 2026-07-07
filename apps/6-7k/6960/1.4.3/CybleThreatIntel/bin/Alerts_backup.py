import ApiConstants
import PasswordUtil
import HTTPUtil
import sys, os
from datetime import datetime, timedelta, timezone
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *
import splunklib.client as client

import concurrent.futures
import time


class AlertFetcher(Script):

    def get_scheme(self):
        # Returns scheme.
        """
        Defines the scheme for the Cyble Alerts modular input.

        This scheme includes two arguments:
        - "api_key": A required string argument for the API Key, needed to access the service.
        - "days": A required number argument specifying the number of days (between 1 and 90) for which data should be sourced.

        The scheme has external validation enabled and does not use a single instance.
        :return: A Scheme object representing the parameters for the Cyble Alerts modular input.
        """

        scheme = Scheme("Cyble Alerts")
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        scheme.description = "Cyble Alerts"

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
        days.description = "Please specify the number of days you would like the data to be sourced from. The value should be between 1 and %s" % str(ApiConstants.MAX_ALLOWED_DAYS)
        days.required_on_create = True
        days.required_on_edit = True
        scheme.add_argument(days)

        hide_data = Argument("hide_data")
        hide_data.title = ("Hide Sensitive Data")
        hide_data.data_type = Argument.data_type_boolean
        hide_data.description = "Select this box if you wish to hide sensitive data like passwords, card details etc."
        hide_data.required_on_create = False
        hide_data.required_on_edit = False
        scheme.add_argument(hide_data)

        return scheme
    
    def validate_api_key(self, api_key):
        """
        Validates the given API key by making a request to the specified host.

        :param api_key: The API key to be validated.
        :return: True if the API key is valid, False otherwise.
        """

        return HTTPUtil.validate_api_key(ApiConstants.HOST, ApiConstants.PAYLOAD_VALIDATE, api_key)

    def validate_input(self, validation_definition):
        """
        Validates the given input configuration.

        Validates the API key and the number of days provided in the input configuration.
        If the API key is invalid or the number of days is outside the allowed range, an exception is raised.

        :param validation_definition: The input definition to be validated.
        :raises ValueError: If the API key is invalid or the number of days is outside the allowed range.
        """

        api_key = validation_definition.parameters["api_key"]

        session_key = validation_definition.metadata["session_key"]

        if api_key != ApiConstants.MASK:
            clear_password = api_key
        else:
            clear_password = PasswordUtil.get_password(session_key, ApiConstants.ALERTS_USERNAME)
        if not self.validate_api_key(clear_password):
            raise ValueError(f"Invalid API key provided for input '{clear_password}'")
        day = int(validation_definition.parameters["days"])
        if day > ApiConstants.MAX_ALLOWED_DAYS or day < 1:
            raise ValueError("Please enter days between 1 and %s" % str(ApiConstants.MAX_ALLOWED_DAYS))

    def migrate_data(self, api_key, ew, gte : datetime, lte : datetime, input_name, hide_data=False):
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
        ew.log("INFO", "[CYBLE EVENTS] Data migration started" )
        alertService = HTTPUtil.get_all_services(api_key, ew)
        ew.log("INFO", "[CYBLE EVENTS] fetched services")
        chunkedServices = [alertService[i:i + ApiConstants.MAX_CUNCURRENT_REQUESTS] for i in
                           range(0, len(alertService), ApiConstants.MAX_CUNCURRENT_REQUESTS)]
        try:
            for chunk in chunkedServices:
                ew.log("INFO", "[CYBLE EVENTS] processing this chunk: %s " % str(chunk))
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = {executor.submit(HTTPUtil.get_data_with_retry, api_key, gte, lte, ew, input_name, service,
                                               hide_data): service for service in chunk}
                for future in concurrent.futures.as_completed(futures):
                    ew.log("INFO", "[CYBLE EVENTS] Fetching data for service: %s Completed" % str(future.result()))
                    
        except Exception as e:
            ew.log("ERROR", "[CYBLE EVENTS] Issue in migrate_data, Error: %s" % str(e))
    
    def get_time_range(self, session_key, days, interval_sec, ew):
        """
        Gets the time range to be used for fetching alerts.
        
        :param session_key: The session key to be used for connecting to the KV store.
        :param days: The number of days specified in the input configuration.
        :param interval_sec: The interval specified in the input configuration.
        :param ew: The event writer object to be used for logging.
        :return: A tuple containing the gte and lte for the time range to be used for fetching alerts.
        """
        ew.log("INFO", "[CYBLE EVENTS] get time range called")

        lte, gte, days = datetime.utcnow(), datetime.utcnow(), int(days)

        args, service = {'token': session_key}, None
        for _ in range(5):
            try:
                service = client.connect(**args, app="CybleThreatIntel")
                ew.log("INFO", "[CYBLE EVENTS] Connected to Splunk KV store client")
                break
            except Exception as e:
                ew.log("WARNING", f"[CYBLE EVENTS] KV store not ready, retrying in 2 sec... Error: {e}")
                time.sleep(2)

        collection_name = "Alert Fetch History"
        if service is None:
            ew.log("WARNING", f"[CYBLE EVENTS] KV store not ready")

        try:
            if collection_name not in service.kvstore:
                ew.log("INFO", "[CYBLE EVENTS] First-time fetch, creating KV store collection")
                service.kvstore.create(collection_name)
            
            collection = service.kvstore[collection_name]
            dataLst = collection.data.query()
            if len(dataLst) > 0:
                ew.log("INFO", "[CYBLE EVENTS] Subsequent fetching call %s" % str(interval_sec))
                gte = lte - timedelta(seconds=interval_sec)
            else:
                ew.log("INFO", "[CYBLE EVENTS] Fetching for the first time %s" % str(days))
                gte = lte - timedelta(days=days)
                collection.data.insert({"_key": "firstFetch", "timestamp": f"{str(gte)}"})
                
        except Exception as e:
            gte = lte - timedelta(seconds=interval_sec)
            ew.log("INFO", "[CYBLE EVENTS] Can't access KV Store for timestamp, Using fallback mechanism")
        
        ew.log("INFO", "[CYBLE EVENTS] Time range: %s to %s get_time_range" % (str(gte), str(lte)))
        return gte, lte


    def stream_events(self, inputs, ew):
        """
        Streams events from the given time range.

        This function streams events from the given time range by calling the get_data_with_retry function for each service
        in the given list of services. The data is streamed in batches of MAX_CUNCURRENT_REQUESTS services at a time.

        :param inputs: The input definition object.
        :param ew: The event writer object to be used for logging.
        :raises Exception: If any exception occurs during the streaming process.
        """
        ew.log("INFO", "[CYBLE EVENTS] stream events called")

        hide_data = False
        try:
            ew.log("INFO", "[CYBLE EVENTS] Event streaming started")
            self.input_name, self.input_items = inputs.inputs.popitem()
            api_key = self.input_items["api_key"]
            ew.log("INFO", "[CYBLE EVENTS] api_key: API Key Read Successfully")
            days = self.input_items['days']
            ew.log("INFO", "[CYBLE EVENTS] fetching for days: %s" % str(days))
            input_name = self.input_name
            ew.log("INFO", "[CYBLE EVENTS] Input name: %s" % str(input_name))
            session_key = self._input_definition.metadata["session_key"]
            interval_sec = int(self.input_items["interval"])
            if "hide_data" in self.input_items:
                hide_data = self.input_items['hide_data']
        except Exception as e:
            ew.log("ERROR", "[CYBLE EVENTS] Error while reading values, Error: %s" % str(e))
            ew.log("ERROR", "[CYBLE EVENTS] Traceback:\n%s" % traceback.format_exc())

        try:
            if api_key != ApiConstants.MASK:
                PasswordUtil.encrypt_password(ApiConstants.ALERTS_USERNAME, api_key, session_key)
                ew.log("INFO", "[CYBLE EVENTS] password encrypted")
                PasswordUtil.mask_password(session_key, days, input_name)
                ew.log("INFO", "[CYBLE EVENTS] password masked")

                
            self.CLEAR_PASSWORD = PasswordUtil.get_password(session_key, ApiConstants.ALERTS_USERNAME)
        except Exception as e:
            ew.log("ERROR", "[CYBLE EVENTS] Issue in stream_events, Error: %s" % str(e))
            ew.log("ERROR", "[CYBLE EVENTS] Traceback:\n%s" % traceback.format_exc())
        
        if self.CLEAR_PASSWORD is None:
            ew.log("ERROR", "[CYBLE EVENTS] Converted Password obtained is None")
            return

        gte, lte = self.get_time_range(session_key, days, interval_sec, ew)
        ew.log("INFO", "[CYBLE EVENTS] Pulling data from %s to %s" % (str(gte), str(lte)))
        self.migrate_data(self.CLEAR_PASSWORD, ew, gte, lte, input_name, hide_data)


if __name__ == "__main__":
    sys.exit(AlertFetcher().run(sys.argv))
