import os
import sys
import time

import exec_anaconda

exec_anaconda.exec_anaconda()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Add the directory where this script resides to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util.constants import (
    ITSI_TIMESTAMP_FORMAT,
    COL_VALUE, 
    COL_DATE,
    COL_SPLUNK_TIME,
    DEFAULT_THRESHOLD,
    DRIFT_DIRECTION_BOTH,
    DRIFT_DIRECTION_UP,
    DRIFT_DIRECTION_DOWN,
    ComparisonStatusConstants,
    ALERT_VALUE,
    KPI_ID,
    SERVICE_ID,
    DRIFT_DETECTION_RESULTS_COLLECTION,
    DRIFT_TIME_WINDOWS,
    KVSTORE_KEY,
    IS_DRIFT_DETECTED,
    LAST_DRIFT_AT,
    START_TIME,
    END_TIME,
    DRIFT_TYPE,
    THRESHOLD_TIME,
    PERCENT_DRIFT,
    PART_OR_WHOLE,
    ITSI_ALERT_URI,
    ITSI_APP_OWNER,
    ITSI_APP_NAME,
    ALERT_TYPE,
    AlertTypeConstants,
    PostReturnStatusConstants,
)
from util.csc_output import (
    CONSTANT_INPUT,
    INPUT_MIN_DATA_POINT,
    INPUT_MIN_TIME_LENGTH,
    SHORT_INPUT, EMPTY_INPUT,
    summarize_drift_result,
    TREND_DRIFT_TYPE
)
from util.csc_input import parse_timestamp
from util.compare_drift import compare_drift
from algo.drift_detection import detect_drifts

import splunklib
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

import numpy as np
import pandas as pd

from logger import get_logger
from util.telemetry_logger import log_telemetry

logger = get_logger()


class DriftDetector:
    """
    The DriftDetector class provides static methods for preparing time series data and detecting drifts within it.

    The class is designed to operate on pandas DataFrames, expecting a specific structure and formatting of the
    input data.
    """

    @staticmethod
    def prepare_dataframe(df, time_field, alert_value_field, timestamp_format):
        """
        Prepares the dataframe for drift detection.
        """
        column_renames = {
            time_field: COL_DATE,
            alert_value_field: COL_VALUE,
        }
        df.rename(columns=column_renames, inplace=True)

        # Replace cell that's entirely space (or empty) with NaN
        #       '^' matches the beginning of a string, and '$' matches the end of a string
        df = df.replace(r'^\s*$', np.nan, regex=True) 

        df = parse_timestamp(df, timestamp_format)
        df[COL_VALUE] = df[COL_VALUE].astype(float)
        df.dropna(inplace=True)

        df.set_index(COL_DATE, inplace=True)
        return df.sort_index()

    @staticmethod
    def detect_drifts(df, threshold, threshold_direction):
        """
        Detects drifts in the provided dataframe.
        """
        detected_drifts, _, _ = detect_drifts(
            series=df[COL_VALUE],
            threshold=threshold,
            threshold_direction=threshold_direction,
        )
        return detected_drifts


@Configuration()
class DriftDetectionCommand(StreamingCommand):
    alert_value_field = Option(require=False, default=ALERT_VALUE)
    kpi_id_field = Option(require=False, default=KPI_ID)
    service_id_field = Option(require=False, default=SERVICE_ID)

    time_field = COL_SPLUNK_TIME

    timestamp_format = Option(require=False, default=ITSI_TIMESTAMP_FORMAT)
    threshold = Option(require=False, default=DEFAULT_THRESHOLD, validate=validators.Integer())
    threshold_direction = Option(
        require=False,
        default=DRIFT_DIRECTION_BOTH,
        validate=validators.Set(DRIFT_DIRECTION_BOTH, DRIFT_DIRECTION_UP, DRIFT_DIRECTION_DOWN)
    )

    # Add the two options for debugging/investigating purpose
    # The check_time_length option will be handy when testing a time series 
    #       with enough data points but its time span is less than the configured limit. 
    check_time_length = Option(require=False, default=True, validate=validators.Boolean())
    # The output_epoch_time option will be handy when one needs to have more readable timestamps in an investigation
    output_epoch_time = Option(require=False, default=True, validate=validators.Boolean())


    collection_name = DRIFT_DETECTION_RESULTS_COLLECTION

    def __init__(self):
        super().__init__()
        self.df = None
        self.buffer = []  # Buffer to store records for a single KPI

    @Configuration()
    def map(self, records):
        return records

    def get_or_create_collection(self):
        try:
            kvstore = self.service.kvstore
            return kvstore.create(self.collection_name) if self.collection_name not in kvstore else kvstore[
                self.collection_name]
        except splunklib.binding.HTTPError as e:
            # Handling KV store binding error
            logger.info(f"Failed to query KV Store for kpi_id={self.kpi_id}, error: {e}")
        except Exception as e:
            # Handling any other exceptions that may occur
            logger.info(f"An unexpected error occurred: {e}")
        
    @staticmethod
    def _find_latest_end_time(data):
        """
        Finds the latest end_time in a list of dictionaries.

        :param data: A list of dictionaries, each containing an 'end_timestamp' key with an epoch value.
        :return: The latest end_timestamp value found in the data list, or None if no end_time is found.
        """
        max_end_time = None

        for entry in data:
            if END_TIME in entry and (max_end_time is None or entry[END_TIME] > max_end_time):
                # Update the max_end_time with the current entry's end_time value
                max_end_time = entry[END_TIME]

        return max_end_time

    def save_to_kvstore(self, kpi_id, service_id, data):
        # Get or create KV Store collection
        collection = self.get_or_create_collection()
        if collection is None:
            logger.exception((
                f"Fail to save drifts into kv store due to collection not found, "
                f"kpi_id: {kpi_id}, service id: {service_id}"
            ))
            return

        latest_end_timestamp = self._find_latest_end_time(data)

        document_to_upsert = [{
            KVSTORE_KEY: kpi_id,
            SERVICE_ID: service_id,
            IS_DRIFT_DETECTED: bool(data),
            LAST_DRIFT_AT: latest_end_timestamp,
            DRIFT_TIME_WINDOWS: data  # 'data' is the list of dictionaries to be upserted
        }]

        collection.data.batch_save(*document_to_upsert)

    def validate_record_fields(self, record):
        # Method to validate required fields in the record
        required_fields = [self.time_field, self.alert_value_field, self.kpi_id_field, self.service_id_field]

        for field in required_fields:
            if field not in record:
                raise ValueError(f'The field {field} is not a field in the dataset, or its value is empty. \
                                 Ensure the field is passed correctly to the {field} argument of detectdrift.')

    def buffer_record(self, record):
        buffer_entry = {
            self.time_field: record[self.time_field],
            self.alert_value_field: record[self.alert_value_field],
            self.kpi_id_field: record[self.kpi_id_field],
            self.service_id_field: record[self.service_id_field]
        }
        self.buffer.append(buffer_entry)

    def handle_record(self, record):
        self.validate_record_fields(record)
        self.buffer_record(record)

    def prepare_dataframe(self):
        df = pd.DataFrame.from_records(self.buffer)
        self.df = DriftDetector.prepare_dataframe(df, self.time_field, self.alert_value_field, self.timestamp_format)

    @property
    def kpi_id(self):
        """
        Returns the KPI ID from the DataFrame.

        Returns:
            str: The KPI ID.
        """
        return self.df.iloc[0][KPI_ID]

    @property
    def service_id(self):
        """
        Returns the Service ID from the DataFrame.

        Returns:
            str: The Service ID.
        """
        return self.df.iloc[0][SERVICE_ID]

    def is_buffer_empty(self):
        return len(self.buffer) == 0

    @staticmethod
    def generate_warning_response(message, reason_code):
        logger.warning(message)
        return {'No Drifts': 'True', 'Reason Code': reason_code}

    def telemetry_logging_results(self, results_summary):
        def drift_to_telemetry_str(drift_types, drift_len):
            if len(drift_types) > 1: # accumulated drift
                return f'Accumulated drift of {len(drift_types)} segments, total_length={drift_len}, segment_types=({" ".join(drift_types)})'
            else:
                return f'{drift_types[0]} drift, length={drift_len}'

        if len(results_summary) > 0:
            log_telemetry(
                event_type = 'drifts_found',
                kpi_id = self.kpi_id,
                service_id = self.service_id,
                drifts = [drift_to_telemetry_str(drift_types, drift_len) for (drift_types, drift_len) in results_summary]
            )

    def post_drift_alert(self, drift, alert_type):
        try:
            json_body = {
                "service_id": self.service_id,
                PART_OR_WHOLE: drift[PART_OR_WHOLE],
                DRIFT_TYPE: drift[DRIFT_TYPE],
                PERCENT_DRIFT: drift[PERCENT_DRIFT],
                START_TIME: drift[START_TIME],
                END_TIME: drift[END_TIME],
                THRESHOLD_TIME: drift[THRESHOLD_TIME],
                "kpi_id": self.kpi_id,
                ALERT_TYPE: alert_type
            }
            # Send the POST request
            response = self.service.post(ITSI_ALERT_URI,
                                         owner=ITSI_APP_OWNER,
                                         app=ITSI_APP_NAME,
                                         body=json_body)
            # Check the response status
            if response.status == 200:
                logger.info(f"Data successfully posted for service ID: {self.service_id}, KPI ID: {self.kpi_id}.")
                return PostReturnStatusConstants.SUCCESS
            else:
                logger.error(f"Failed to post data. Status: {response.status}, Reason: {response.reason}")
                return PostReturnStatusConstants.FAILURE
        except Exception as e:
            logger.exception(f"An error occurred while posting data for service ID: {self.service_id}. Exception: {e}")
            return PostReturnStatusConstants.EXCEPTION
        
    def _fetch_existing_drifts(self, collection):
        """
        Fetch existing drifts from the collection using the KPI ID.

        Args:
            collection: The collection object from which to fetch the drifts.

        Returns:
            list[dict]: List of existing drifts, or None if an error occurs.
        """
        try:
            # Query the collection for existing drifts using the KPI ID
            return collection.data.query_by_id(str(self.kpi_id)).get(DRIFT_TIME_WINDOWS, None)
        except Exception as e:
            # Log any exceptions that occur during the drift fetching process
            logger.info(f"Error fetching existing drifts for KPI ID {self.kpi_id}: {e}")

    def _compare_drifts(self, existing_drift_list, new_drift_list, message_list):
        """
        Compare existing drifts with new drifts and generate comparison results.

        Args:
            existing_drift_list (list[dict]): List of existing drifts to compare against.
            new_drift_list (list[dict]): List of new drifts to compare.

        Returns:
            list[ComparisonStatusConstants]: List of comparison results.
        """
        matched_existing_drifts_indices = set()
        logger.debug(f"check input: existing: {existing_drift_list}, new {new_drift_list}")
        # Check new drifts against existing drifts and mark matched ones
        self._check_new_drifts(existing_drift_list, new_drift_list, message_list, matched_existing_drifts_indices)
        # Check for unmatched existing trend drifts
        self._check_unmatched_existing_trends(existing_drift_list, message_list, matched_existing_drifts_indices)

        return message_list

    def _check_new_drifts(self, existing_drift_list, new_drift_list, message_list, matched_existing_drifts_indices):
        """
        Check if new drifts exist in the list of existing drifts, if not exist before, 
        send an alert to ITSI accrodingly.
        """
        for new_drift in new_drift_list:
            drift_found = False
            for existing_drift_index, existing_drift in enumerate(existing_drift_list):
                if compare_drift(existing_drift, new_drift):
                    drift_found = True
                    message_list.append(ComparisonStatusConstants.SAME_DRIFT_FOUND)
                    matched_existing_drifts_indices.add(existing_drift_index)
            if not drift_found:
                # The new drift was not found in the existing drifts, indicating a new drift detection
                message_list.append(ComparisonStatusConstants.NEW_DRIFT_DETECTED)
                # Sending new drift detected action for new drifts
                self.post_drift_alert(new_drift, AlertTypeConstants.NEW_DRIFT_DETECTED)

    def _check_unmatched_existing_trends(self, existing_drift_list, message_list, matched_existing_drifts_indices):
        """
        Check for unmatched existing trend drifts and determine if they should be cleared,
        and send alert to ITSI accrodingly
        """
        for existing_drift_index, existing_drift in enumerate(existing_drift_list):
            if existing_drift_index not in matched_existing_drifts_indices and existing_drift[DRIFT_TYPE] == TREND_DRIFT_TYPE:
                # If an existing trend drift is unmatched, it means the trend has ended, 
                # and a clearing action should be sent
                message_list.append(ComparisonStatusConstants.EXISTING_TREND_CLEARING)
                # Sending clearing action for existing drifts
                self.post_drift_alert(existing_drift, AlertTypeConstants.CLEARING) 

    def fetch_existing_drifts_and_compare_with_new_drifts(self, new_drift_list):
        """
        Fetches existing drifts from the collection and compares them with new drifts.
        
        Args:
            new_drift_results list(dict): List of new drifts to compare against existing drifts.
        
        Returns:
            list(ComparisonStatusConstants): List of comparison results, each represented by ComparisonStatusConstants
        """
        message_list = []
        if not new_drift_list or len(new_drift_list) == 0:
            new_drift_list = []
            message_list.append(ComparisonStatusConstants.NO_NEW_DRIFTS)
        
        # Attempt to retrieve the collection
        collection = self.get_or_create_collection()
        if collection is None:
            return [ComparisonStatusConstants.COLLECTION_NOT_FOUND]
        
        # Fetch existing drifts from the collection
        existing_drift_list = self._fetch_existing_drifts(collection)
        if not existing_drift_list:
            existing_drift_list = []
            message_list.append(ComparisonStatusConstants.NO_EXISTING_DRIFTS)
        
        # Compare the existing drifts with the new drifts and return the comparison results
        message_list = self._compare_drifts(existing_drift_list, new_drift_list, message_list)
        return message_list


    def stream(self, records):
        time_0 = time.time()

        for record in records:
            self.handle_record(record)

        if self.is_buffer_empty():
            yield self.generate_warning_response('The input KPI time series is empty. No Drifts.', EMPTY_INPUT)

        if not self.is_buffer_empty() and self._finished:
            self.prepare_dataframe()

            cnt_data_points = self.df[COL_VALUE].count()
            df_time_span = self.df.index[-1] - self.df.index[0]
            if self.check_time_length:
                is_short = cnt_data_points < INPUT_MIN_DATA_POINT or self.df.index[-1] - self.df.index[0] < INPUT_MIN_TIME_LENGTH
            else:
                is_short = cnt_data_points < INPUT_MIN_DATA_POINT

            if is_short:
                yield self.generate_warning_response(f'The input KPI time series is too short ({cnt_data_points}, {df_time_span}). No Drifts.', SHORT_INPUT)
                return

            if self.df[COL_VALUE].min() == self.df[COL_VALUE].max():
                yield self.generate_warning_response('The input KPI time series is constant. No Drifts.',
                                                     CONSTANT_INPUT)
                return

            time_1 = time.time()

            log_telemetry(
                event_type = 'calling_detect_drifts',
                kpi_id = self.kpi_id,
                service_id = self.service_id,
                df_length = len(self.df),
                df_time_span = str(self.df.index[-1] - self.df.index[0]),
                threshold = self.threshold,
                threshold_direction = self.threshold_direction,                
            )

            drifts_detected = DriftDetector.detect_drifts(self.df, self.threshold, self.threshold_direction)

            self.telemetry_logging_results(summarize_drift_result(drifts_detected))

            results = []

            for drift in drifts_detected:
                result = drift.format_drift_output(self.output_epoch_time)
                yield result
                results.append(result)

            time_2 = time.time()

            self.fetch_existing_drifts_and_compare_with_new_drifts(new_drift_list=results)

            self.save_to_kvstore(kpi_id=self.kpi_id, service_id=self.service_id, data=results)
            
            log_telemetry(
                event_type = 'detectdrift_complete',
                kpi_id = self.kpi_id,
                service_id = self.service_id,
                total_time = f'{time.time() - time_0:.3f}s',
                data_prepare_time = f'{time_1 - time_0:.3f}s',
                detect_drifts_time = f'{time_2 - time_1:.3f}s',
                kvstore_time = f'{time.time() - time_2:.3f}s',
            )


dispatch(DriftDetectionCommand, sys.argv, sys.stdin, sys.stdout, __name__)
