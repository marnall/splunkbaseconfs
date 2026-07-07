import logging
from datetime import datetime

from solnlib import splunk_rest_client as sr
from splunklib.binding import HTTPError as SplunkHTTPError

from spiderSilk_resonance_config import *


class UpdateTable:
    """
    A helper class to handle updates to different Splunk KV store lookup tables related to resonance,
    including threats, dark web, and assets.

    This utility provides methods to process and update lookup tables
    from given payloads for multiple resonance data sources.
    """

    def __init__(self, logger: logging.Logger, session_key: str, api_meta: dict):
        """
        Initialize the LookupTableUpdater instance.

        Parameters:
        logger (logging.Logger): Logger instance for logging debug and error information.
        session_key (str): A string representing the session key for authentication.
        acc_name (str): Resonance Account name.
        """
        self.logger = logger
        self.session_key = session_key
        self.acc_name = api_meta['account']
        self.uniqueID = api_meta['uniqueID']

        self.kv_conn = sr.SplunkRestClient(session_key=session_key, app=ADDON_NAME).kvstore

    def update_lookup_table(self, source_type: str, payload: dict) -> None:
        """
        Perform an update (or insert) operation on the Splunk KV Store lookup table.

        Parameters:
        source_type (str): The type of source (e.g., "threats", "darkweb") that determines
                           which lookup table to update.
        payload (dict): The data payload containing the key-value pairs for the table update.

        Returns:
        None
        """
        table = self.kv_conn[f"resonance_{source_type}_update_kvstore"]

        try:
            if not self.record_exists(source_type, payload['_key']):
                table.data.insert(payload)
            else:
                table.data.update(payload['_key'], payload)
            self.logger.debug(f"Lookup Table({table}) upsert with payload: {payload}")
        except Exception as e:
            self.logger.error(f"Error upsert Lookup Table({table}) with payload: {payload}, Exception: {e}")
            raise e

    def record_exists(self, source_type: str, uuid: str) -> bool:
        """
        Check if a specific record exists in the Splunk KV Store lookup table.

        Parameters:
        source_type (str): The type of source (e.g., "threats", "darkweb").
        uuid (str): The unique identifier to check in the lookup table.

        Returns:
        bool: True if the record exists, False otherwise.
        """
        table = self.kv_conn[f"resonance_{source_type}_update_kvstore"]

        try:
            result = table.data.query_by_id(uuid)
            return len(result) > 0
        except SplunkHTTPError as e:
            if e.status != 404:
                self.logger.error(f"Error checking record exists for UUID: {uuid} in table {source_type}. Error: {e}")
            return False

    def is_record_old(self, source_type: str, uuid: str, new_data: dict) -> bool:
        """
        Determines if the given record is older or not based on the 'updated' timestamp.

        Parameters:
        source_type (str): The type of source (e.g., "threats", "darkweb" or "assets") to identify
                           the appropriate lookup table.
        uuid (str): The unique identifier to locate the record in the lookup table.
        new_data (dict): A dictionary containing the new data with an 'updated' timestamp
                         in the format "%Y-%m-%d %H:%M:%S".

        Returns:
        bool: True if the new data is equivalent to or newer; False if parsing fails or
              if the new date is earlier than the existing one.
        """
        table = self.kv_conn[f"resonance_{source_type}_update_kvstore"]

        existing_data = {}
        try:
            existing_data = table.data.query_by_id(uuid)
            # Ensure both dates are in the correct format
            existing_updated_date = datetime.strptime(existing_data['updated'], "%Y-%m-%d %H:%M:%S")
            new_updated_date = datetime.strptime(new_data['updated'], "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            self.logger.error(f"Date parsing error for UUID:{uuid}, Existing date: "
                              f"{existing_data['updated']}, New date: {new_data['updated']}. Exception: {e}")
            return False

        # Compare dates and return true if the new date is older
        return new_updated_date > existing_updated_date

    def threats_data_updater(self, data: dict) -> None:
        """
        Updates the threats lookup table in Splunk KV Store with the provided data.

        Parameters:
        data (dict): A dictionary containing threat data with keys like uuid, status, state, and important dates.
                     This data is processed to create an upsert record for the lookup table.

        Returns:
        None
        """
        keys_to_update = ["uuid", "status", "state", "assignee", "dates.acknowledgedDate", "dates.resolutionDate",
                          "closedDate", "updated"]

        uuid = data[self.uniqueID]
        upsert_record = {
            '_key': uuid,
        }

        try:
            # Extract only necessary data
            for key in keys_to_update:
                if key in data:
                    if key == 'assignee' and data[key] is None:
                        upsert_record[key] = {}
                    else:
                        upsert_record[key] = data[key]
                if '.' in key:
                    nested_key1, nested_key2 = key.split('.')
                    upsert_record[nested_key1] = {nested_key2: data[nested_key1][nested_key2]}

            self.update_lookup_table("threats", upsert_record)

            self.logger.debug(f"Updating Threats Lookup table for UUID: {uuid}, Account : {self.acc_name}")
        except Exception as e:
            self.logger.error(f"Error updating Threats lookup table for UUID: {uuid}, "
                              f"Account: {self.acc_name}. Error :{e}")

    def darkweb_data_updater(self, data: dict) -> None:
        """
        Updates the dark web lookup table in Splunk KV Store with the provided data.

        Parameters:
        data (dict): A dictionary containing dark web data with keys like uuid, status, assignee, and updated date.
                     The method ensures any null assignee is set to "Unassigned" before updating the record.

        Returns:
        None
        """
        keys_to_update = ["uuid", "status", "assignee", "updated"]

        uuid = data[self.uniqueID]
        upsert_record = {
            '_key': uuid,
        }

        try:
            # Extract only necessary data
            for key in keys_to_update:
                if key in data:
                    if key == 'assignee' and data[key] is None:
                        upsert_record[key] = {}
                    else:
                        upsert_record[key] = data[key]
                if '.' in key:
                    nested_key1, nested_key2 = key.split('.')
                    upsert_record[nested_key1] = {nested_key2: data[nested_key1][nested_key2]}

            self.update_lookup_table("darkweb", upsert_record)

            self.logger.debug(f"Updating DarkWeb Lookup table for UUID: {uuid}, Account : {self.acc_name}")
        except Exception as e:
            self.logger.error(f"Error updating DarkWeb lookup table for UUID: {uuid}, "
                              f"Account: {self.acc_name}. Error :{e}")

    def assets_data_updater(self, data: dict) -> None:
        """
        Reserved method for updating assets lookup table in the future.

        Parameters:
        data (dict): Placeholder parameter for asset-related data.

        Returns:
        None
        """
        keys_to_update = ["uuid", "updated", "attributes.reactivated"]

        uuid = data[self.uniqueID]
        upsert_record = {
            '_key': uuid,
        }

        try:
            # Extract only necessary data
            for key in keys_to_update:
                if key in data:
                    upsert_record[key] = data[key]
                if '.' in key:
                    nested_key1, nested_key2 = key.split('.')
                    upsert_record[nested_key1] = {nested_key2: data[nested_key1][nested_key2]}

            self.update_lookup_table("assets", upsert_record)

            self.logger.debug(f"Updating Assets Lookup table for UUID: {uuid}, Account : {self.acc_name}")
        except Exception as e:
            self.logger.error(f"Error updating Assets lookup table for UUID: {uuid}, "
                              f"Account: {self.acc_name}. Error :{e}")
