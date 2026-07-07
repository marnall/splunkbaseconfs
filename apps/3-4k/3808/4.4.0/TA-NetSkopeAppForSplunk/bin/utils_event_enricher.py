
import copy
import csv
import logging
import os
import threading
import time

import const


class UserGroupLookup:
    """
    UserGroupLookup: Singleton class for looking up user groups from CSV files.

    This class implements the singleton pattern using a class method approach.
    Always use get_instance() instead of instantiating directly.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, csv_file_path=None, logger=None):
        """
        Get the singleton instance of UserGroupLookup.

        Args:
            csv_file_path (str): Path to the CSV file containing user group data.
            logger (logging.Logger): Logger instance for logging purposes.

        Returns:
            UserGroupLookup: The singleton instance of UserGroupLookup.
        """
        with cls._lock:
            if cls._instance is None:
                if csv_file_path is None:
                    raise ValueError("CSV file path must be provided for initialization")
                cls._instance = cls(csv_file_path, logger)
            return cls._instance

    def __init__(self, csv_file_path, logger):
        """
        Initialize UserGroupLookup with the path to the CSV file.

        Args:
            csv_file_path (str): Path to the CSV lookup file
            logger (logging.Logger): Logger instance
        """
        if not isinstance(csv_file_path, str) or not csv_file_path.strip():
            raise ValueError("Invalid CSV file path")
        if not isinstance(logger, logging.Logger):
            raise ValueError("Invalid logger")
        self.csv_file_path = csv_file_path
        self.logger = logger
        self.user_group_mapping = {}
        self.last_modified_time = None

    def check_file_exists(self):
        """
        Check if the CSV file exists.

        Returns:
            bool: True if file exists, False otherwise
        """
        if not os.path.isfile(self.csv_file_path):
            return False
        return True

    def is_file_modified(self):
        """
        Check if the file has been modified since the last read.

        Returns:
            bool: True if file has been modified, False otherwise
        """
        if not self.check_file_exists():
            return False

        current_mtime = os.path.getmtime(self.csv_file_path)
        if self.last_modified_time is None or current_mtime > self.last_modified_time:
            self.last_modified_time = current_mtime
            return True
        return False

    def read_csv_file(self):
        """Read the CSV file and update the internal user-group mapping."""
        if not self.is_file_modified():
            self.user_group_mapping = {}
            self.logger.debug("CSV file hasn't been modified, using existing mapping")
            return

        start_time = time.time()
        try:
            self.logger.info("Reading the CSV file from path: {}".format(self.csv_file_path))

            with open(self.csv_file_path, 'r') as f:
                reader = csv.DictReader(f)

                # Check if required fields exist in the CSV
                if const.USER_EMAIL in reader.fieldnames and const.USER_GROUP in reader.fieldnames:
                    self.user_group_mapping = {}
                    for row in reader:
                        user_email = row[const.USER_EMAIL].strip().lower()
                        user_group = row[const.USER_GROUP].strip()
                        if user_email and user_group:  # Only add non-empty entries
                            self.user_group_mapping[user_email] = user_group

                    elapsed_time = time.time() - start_time
                    self.logger.info(
                        "CSV file read successfully. Loaded {} user-group mappings.".format(
                            len(self.user_group_mapping)
                        )
                    )
                    self.logger.debug("metric=csv_lookup_load_time | time={0:.3f} seconds".format(elapsed_time))
                else:
                    self.logger.error(
                        "Required columns '{}' and '{}' not found in CSV file".format(
                            const.USER_EMAIL,
                            const.USER_GROUP
                        )
                    )
                    self.user_group_mapping = {}

        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error("Error reading CSV file: {}".format(str(e)))
            self.logger.debug(
                "metric=csv_lookup_load_time | Failed to load CSV file. | "
                "time={0:.3f} seconds".format(elapsed_time)
            )
            self.user_group_mapping = {}

    def has_valid_data(self):
        """
        Check if the lookup has valid user group mapping data.

        Returns:
            bool: True if user group mapping exists, False otherwise
        """
        return bool(self.user_group_mapping)

    def enrich_event(self, event):
        """
        Enrich events with user_group information.

        Args:
            event (dict): List of event dictionaries (JSON) or a single event dictionary

        Returns:
            list or dict: Enriched events in the same format as input
        """
        if not event:
            return event

        # Check if user field is present in the event
        if 'user' not in event:
            self.logger.debug("User field not found in event. Can't enrich with user_group.")
            return event

        # Check if we need to reload the CSV file
        if self.is_file_modified():
            self.logger.debug("Lookup file has been modified, reloading mapping")
            self.read_csv_file()

        if not self.user_group_mapping:
            return event

        user = event.get('user', '').lower()
        if user in self.user_group_mapping:
            event['user_group'] = self.user_group_mapping[user]
        else:
            event['user_group'] = ''

        return event

    def enrich_csv_data(self, csv_data, headers_dict):
        """
        Enrich an entire CSV dataset with user group information.

        Args:
            csv_data (list): List of CSV rows where first element is version
            headers_dict (dict): Dictionary mapping versions to header strings

        Returns:
            tuple: (enriched_csv_data, updated_headers_dict, enriched_count)
        """
        enriched_count = 0

        # Process each row
        for i, row in enumerate(csv_data):
            if not row or not isinstance(row, list) or len(row) == 0:
                continue

            version = row[0]
            data_row = row[1:] if len(row) > 1 else []

            # Get headers for this version
            if version in headers_dict:
                headers_data = headers_dict[version].split(",")

                # Use the existing enrich_csv_row method
                enriched_row, updated_headers, was_enriched = self.enrich_csv_row(data_row, headers_data)

                if was_enriched:
                    enriched_count += 1
                    # Update the row in the data
                    csv_data[i] = [version] + enriched_row

                    # Update headers if they were modified
                    if updated_headers != headers_data:
                        headers_dict[version] = ",".join(updated_headers)

        return csv_data, headers_dict, enriched_count

    def enrich_csv_row(self, csv_row, headers_data):
        """
        Enrich a single CSV row with user group information.

        Args:
            csv_row (list): List containing CSV row data
            headers_data (list): List of header field names

        Returns:
            tuple: (enriched_row, updated_headers, was_enriched)
        """
        # Check if we have the necessary data
        if not csv_row or not headers_data:
            self.logger.debug("No data to enrich. CSV row or headers_data is empty.")
            return csv_row, headers_data, False

        # Find the user field index
        user_index = -1
        for i, header in enumerate(headers_data):
            if header.lower() == 'user':
                user_index = i
                break

        # If no user field found or index out of bounds, can't enrich
        if user_index == -1 or user_index >= len(csv_row):
            self.logger.debug("User field not found or index out of bounds. Can't enrich data.")
            return csv_row, headers_data, False

        # Get the user and check if we have group info
        user = csv_row[user_index].lower() if user_index < len(csv_row) else ""
        user_group_value = self.user_group_mapping.get(user, "")

        # Check if user_group header already exists
        if 'user_group' in headers_data:
            user_group_index = headers_data.index('user_group')
            csv_row.insert(user_group_index, user_group_value)
        else:
            # Insert user_group header right after user field
            headers_data.insert(user_index + 1, 'user_group')
            # Insert user_group value right after user field in the data row
            csv_row.insert(user_index + 1, user_group_value)

        return csv_row, headers_data, True


def initialize_user_group_lookup(csv_file_path, logger):
    """
    Initialize the user group lookup at the start of data collection.

    Args:
        csv_file_path (str): Path to the CSV lookup file
        logger (logging.Logger): Logger instance

    Returns:
        bool: True if CSV file exists and has valid data, False otherwise
    """
    instance = UserGroupLookup.get_instance(csv_file_path, logger)
    instance.read_csv_file()
    return instance.has_valid_data()


def enrich_events_with_user_groups(event):
    """
    Enrich events with user group information.

    Args:
        event: Event data

    Returns:
        Enriched event in the same format
    """
    instance = UserGroupLookup.get_instance()
    return instance.enrich_event(event)


def enrich_csv_with_user_groups(csv_data, headers_dict):
    """
    Enrich CSV data with user group information.

    Args:
        csv_data (list): List of CSV rows where first element is version
        headers_dict (dict): Dictionary mapping versions to header strings

    Returns:
        tuple: (enriched_csv_data, updated_headers_dict)
    """
    instance = UserGroupLookup.get_instance()
    if not instance.user_group_mapping:
        return csv_data, headers_dict

    # Create copies to avoid modifying originals
    enriched_csv_data = copy.deepcopy(csv_data)
    updated_headers_dict = copy.deepcopy(headers_dict)

    enriched_count = 0

    # Let the UserGroupLookup instance handle the enrichment of the entire dataset
    enriched_csv_data, updated_headers_dict, enriched_count = instance.enrich_csv_data(
        enriched_csv_data, updated_headers_dict
    )

    instance.logger.debug(
        "Enriched {} out of {} CSV events with user_group information".format(enriched_count, len(enriched_csv_data))
    )
    return enriched_csv_data, updated_headers_dict
