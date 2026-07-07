import json
import os
import sys
import time
from collections import defaultdict, deque, OrderedDict

import exec_anaconda

exec_anaconda.exec_anaconda()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Add the directory where this script resides to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util.data_prepare import (ITSI_TIMESTAMP_FORMAT, COL_VALUE, COL_DATE, COL_HOUR, COL_DAY_OF_WEEK, COL_KPI_ID,
                               COL_SERVICE_ID)
from util.csc_input import parse_timestamp
from util.csc_output import (
    confidence_description, output_thresholds_dict, calc_constant_time_series_thresholds,
    THR_DIR_BOTH, THR_DIR_LO, THR_DIR_UP, THR_DIR_AUTO
)
from util.timepolicy import (generate_cron_output, NO_PATTERN, INSUFFICIENT_DATA, PATTERN_SWITCH, SUCCESSFUL)

from splunklib.searchcommands import dispatch, Configuration, Option, validators, StreamingCommand

from util import setup_logging
from util.telemetry_logger import log_telemetry

import numpy as np
import pandas as pd

from constants import (
    ALERT_VALUE,
    ALGORITHM,
    ALL_DATA_RECEIVED,
    ANALYSIS_WINDOW,
    CONFIDENCE,
    CONSTANT_KPI,
    CONSTANT_TIME_SERIES_THRESHOLD,
    CRON_EXPRESSION,
    DURATION,
    ENTITY_KEY,
    ENTITY_TITLE,
    FilterConfig,
    ITSI_ENTITIES_AT_RESULTS_POST_URI,
    ITSI_KPI_ID,
    ITSI_KPI_RESULTS_POST_URI,
    ITSI_SERVICE_ID,
    KPI_AT_CONFIGURATION,
    KV_AT_TIME_POLICIES_COLLECTION,
    MEAN,
    PostReturnStatusConstants,
    RECOMMENDATION_FLAG,
    SCORE,
    SENSITIVITY,
    STD,
    SensitivityLevelConstants,
    THRESHOLDS,
    THRESHOLD_DIRECTION,
    TIME_POLICY_DESCRIPTION,
    USE_STATIC,
    NON_NEGATIVE,
    SENSITIVITY_LEVEL,
)

from kpis_utils import is_valid_value, get_valid_entity_identifier

# Set up logger
logger = setup_logging.get_logger()

# Define a minimum number of events needed for processing.
MIN_EVENTS_FOR_PROCESSING = 100

# Map time policy descriptions to log messages
LOG_MESSAGES = {
    NO_PATTERN: 'We were unable to find a time policy that fits your data.',
    INSUFFICIENT_DATA: f'There is not enough data to make a recommendation on your data. We require at least 1 day worth of data and at least {MIN_EVENTS_FOR_PROCESSING} events.',
    PATTERN_SWITCH: 'We could not detect a consistent pattern in your data. It seems that there is more than one pattern.'
}


class KPIResponseBuilder:
    """
    KPIResponseBuilder provides static methods for preprocessing, structuring, and enhancing KPI data.
    """

    @staticmethod
    def preprocess(df):
        """
        Preprocesses the DataFrame by setting appropriate column data types
        and making the date column the DataFrame index.

        Parameters:
        - df (DataFrame): The DataFrame to be preprocessed.

        Returns:
        - DataFrame: The preprocessed DataFrame.
        """
        df[COL_DAY_OF_WEEK] = df[COL_DATE].dt.dayofweek.astype(int)
        df[COL_HOUR] = df[COL_DATE].dt.hour.astype(int)
        df[COL_VALUE] = df[COL_VALUE].astype(float)
        df.set_index(COL_DATE, inplace=True)
        return df

    @staticmethod
    def structure_kpi_output(
            itsi_kpi_id,
            itsi_service_id,
            recommendation_flag,
            cron_lists=None,
            score=None,
            threshold_rounding=None,
            threshold_direction=None,
            time_policy_description=None,
            analysis_window=None,
            non_negative=True,
            sensitivity_level=SensitivityLevelConstants.LOW,
            use_static=False,
            mean=None,
            stdev=None,
    ):
        """
        Structures the KPI data based on various parameters.

        Returns:
        - list: Structured KPI data.
        """
        use_static_flag = "False" if use_static is None else str(use_static)
        non_negative_flag = "True" if non_negative is None else str(non_negative)
        
        if recommendation_flag == SUCCESSFUL:
            res_list = []
            for cron in cron_lists or []:
                thres_res = output_thresholds_dict(cron.z_value, cron.mean, cron.std,
                                        threshold_rounding, threshold_direction,
                                        non_negative=non_negative,
                                        use_static=use_static)
                res_list.append(
                    {
                        ITSI_KPI_ID: itsi_kpi_id,
                        ITSI_SERVICE_ID: itsi_service_id,
                        RECOMMENDATION_FLAG: recommendation_flag,
                        ALGORITHM: 'stdev',
                        CRON_EXPRESSION: cron.cron_expression,
                        DURATION: cron.time_length,
                        THRESHOLD_DIRECTION: threshold_direction,
                        THRESHOLDS: f"{thres_res}",
                        MEAN: round(cron.mean, threshold_rounding),
                        STD: round(cron.std, threshold_rounding),
                        SENSITIVITY: round(cron.sensitivity, threshold_rounding),
                        SCORE: score,
                        CONFIDENCE: confidence_description(score),
                        TIME_POLICY_DESCRIPTION: time_policy_description,
                        ANALYSIS_WINDOW: analysis_window,
                        USE_STATIC: use_static_flag,
                        NON_NEGATIVE: non_negative_flag,
                        SENSITIVITY_LEVEL: sensitivity_level,
                    }
                )
            return res_list

        if recommendation_flag == NO_PATTERN:
            use_static, use_static_flag = True, "True"
            res_list = []
            for cron in cron_lists or []:
                thres_res = output_thresholds_dict(cron_lists[0].z_value, mean, stdev,
                                            threshold_rounding, threshold_direction,
                                            non_negative=non_negative,
                                            use_static=use_static)
                res_list.append(
                    {
                        ITSI_KPI_ID: itsi_kpi_id,
                        ITSI_SERVICE_ID: itsi_service_id,
                        RECOMMENDATION_FLAG: recommendation_flag,
                        ALGORITHM: 'static',
                        CRON_EXPRESSION: 'None',
                        DURATION: 'None',
                        THRESHOLD_DIRECTION: threshold_direction,
                        THRESHOLDS: f"{thres_res}",
                        MEAN: round(cron_lists[0].mean, threshold_rounding),
                        STD: round(cron_lists[0].std, threshold_rounding),
                        SENSITIVITY: round(cron_lists[0].sensitivity, threshold_rounding),
                        SCORE: score,
                        CONFIDENCE: confidence_description(score),
                        TIME_POLICY_DESCRIPTION: 'Static thresholding',
                        ANALYSIS_WINDOW: analysis_window,
                        USE_STATIC: use_static_flag,
                        NON_NEGATIVE: non_negative_flag,
                        SENSITIVITY_LEVEL: sensitivity_level,
                    }
                )
            return res_list
        if recommendation_flag == CONSTANT_KPI:
            # in constant timeseries case, we use static values for threshold instead of the way based on zscore,
            # so the use_static_flag is always true in constant cases, while non_negative_flag depends on user choices.
            use_static_flag, non_negative_flag = "True", str(non_negative)
            cron = cron_lists[0]
            return [{
                ITSI_SERVICE_ID: itsi_service_id,
                ITSI_KPI_ID: itsi_kpi_id,
                RECOMMENDATION_FLAG: recommendation_flag,
                ALGORITHM: 'static',
                CRON_EXPRESSION: 'None',
                DURATION: 'None',
                THRESHOLD_DIRECTION: threshold_direction,
                THRESHOLDS: f"{cron[THRESHOLDS]}",
                MEAN: str(cron[MEAN]),
                STD: str(cron[STD]),
                SENSITIVITY: 'None',
                SCORE: 'None',
                CONFIDENCE: 'None',
                TIME_POLICY_DESCRIPTION: time_policy_description,
                ANALYSIS_WINDOW: analysis_window,
                USE_STATIC: use_static_flag,
                NON_NEGATIVE: non_negative_flag,
                SENSITIVITY_LEVEL: sensitivity_level,
            }]

        return [{
            ITSI_KPI_ID: itsi_kpi_id,
            ITSI_SERVICE_ID: itsi_service_id,
            RECOMMENDATION_FLAG: recommendation_flag,
            ALGORITHM: 'None',
            CRON_EXPRESSION: 'None',
            DURATION: 'None',
            SENSITIVITY: 'None',
            THRESHOLDS: 'None',
            MEAN: 'None',
            STD: 'None',
            SCORE: 'None',
            CONFIDENCE: 'None',
            TIME_POLICY_DESCRIPTION: 'None',
            ANALYSIS_WINDOW: analysis_window,
            USE_STATIC: use_static_flag,
            NON_NEGATIVE: non_negative_flag,
            SENSITIVITY_LEVEL: sensitivity_level,
        }]

    @staticmethod
    def append_entity_details(formatted_data, entity_key, entity_title):
        """
        Enhances formatted KPI data with entity_key and entity_title if they are non-empty.

        Parameters:
            formatted_data (list): Structured KPI data.
            entity_key (str): The entity key to add.
            entity_title (str): The entity title to add.

        Returns:
            list: Enhanced KPI data with entity details.
        """
        if not entity_key and not entity_title:
            return formatted_data

        def add_entity_fields(entry):
            if entity_key:
                entry[ENTITY_KEY] = entity_key
            if entity_title:
                entry[ENTITY_TITLE] = entity_title
            return entry

        return [add_entity_fields(entry) for entry in formatted_data]

    @staticmethod
    def prepare_kpi_response(itsi_kpi_id,
                             itsi_service_id,
                             entity_key,
                             entity_title,
                             recommendation_flag,
                             entity_level_processing,
                             **kwargs):
        """
        Prepares the KPI response by structuring the KPI data and enhancing it with entity information if entity_level_processing is enabled.

        Parameters:
            itsi_kpi_id (str): The KPI ID.
            itsi_service_id (str): The Service ID
            entity_key (str): The entity key.
            entity_title (str): The entity title.
            recommendation_flag (str): The recommendation flag.
            entity_level_processing (bool): Flag to determine if entity-level processing is enabled.
            **kwargs: Additional keyword arguments for format_kpi_data.

        Returns:
            list: Prepared KPI response.
        """
        formatted_data = KPIResponseBuilder.structure_kpi_output(itsi_kpi_id, itsi_service_id, recommendation_flag,
                                                                 **kwargs)

        if entity_level_processing:
            return KPIResponseBuilder.append_entity_details(formatted_data, entity_key, entity_title)

        return formatted_data


class KPIThresholdRecommender:
    """
    KPIThresholdRecommender is responsible for recommending thresholds for Key Performance Indicators (KPIs).
    It performs various checks like data sufficiency and constancy of KPI before proceeding to the recommendation.
    """

    def __init__(self, df):
        """
        Initialize the KPIThresholdRecommender with a DataFrame.

        Parameters:
        - dataframe (pd.DataFrame): The DataFrame containing the KPI data.
        """
        self.df = df

    @property
    def kpi_id(self):
        """
        Returns the KPI ID from the DataFrame.

        Returns:
            str: The KPI ID.
        """
        return self.df[COL_KPI_ID].iloc[0]

    @property
    def service_id(self):
        """
        Returns the Service ID from the DataFrame.

        Returns:
            str: The Service ID.
        """
        return self.df[COL_SERVICE_ID].iloc[0]

    @property
    def entity_key(self):
        """
        Returns the entity key from the DataFrame, if it exists.

        Returns:
            str or None: The entity key, or None if the column doesn't exist.
        """
        return self.df.get(ENTITY_KEY).iloc[0] if ENTITY_KEY in self.df else None

    @property
    def entity_title(self):
        """
        Returns the entity title from the DataFrame, if it exists.

        Returns:
            str or None: The entity title, or None if the column doesn't exist.
        """
        return self.df.get(ENTITY_TITLE).iloc[0] if ENTITY_TITLE in self.df else None

    def has_insufficient_data(self, min_events=MIN_EVENTS_FOR_PROCESSING):
        """
        Check if the DataFrame has a sufficient number of events for processing.

        Parameters:
            min_events (int, optional): The minimum number of events required for processing. Defaults to MIN_EVENTS_FOR_PROCESSING.

        Returns:
            bool: True if data is insufficient, False otherwise.
        """

        if self.df[COL_VALUE].count() < min_events:
            logger.warning(f"{self.kpi_id} ({self.entity_title}) - Not enough data. Requires at least {min_events} events.")
            return True
        return False

    def is_nearly_constant_timeseries(self):
        """
        Check if the KPI/entity timeseries is nearly constant across all events.

        Returns:
            bool: True if timeseries is nearly constant, False otherwise.
        """

        return (self.df[COL_VALUE].max() - self.df[COL_VALUE].min()) < CONSTANT_TIME_SERIES_THRESHOLD * self.df[COL_VALUE].median()

    def process(self, threshold_rounding, threshold_direction, analysis_window, non_negative, use_static, sensitivity_level,
                entity_level_processing=False):
        """
        The main function to process the DataFrame and produce KPI recommendations.

        Parameters:
            threshold_rounding (float): Rounding to apply to calculated thresholds.
            threshold_direction (str): Direction for threshold calculations.
            analysis_window (str): Represents analysis window, returned without modification
            non_negative(bool): Represents whether we want to have non-negative threshold or not
            use_static (bool): Represents whether we are using one-time static values or not, returned without modification
            entity_level_processing (bool): Flag to determine if entity-level processing is enabled.

        Returns:
            dict: Recommendations for the KPI.
        """
        if self.has_insufficient_data():
            return KPIResponseBuilder.prepare_kpi_response(itsi_kpi_id=self.kpi_id,
                                                           itsi_service_id=self.service_id,
                                                           entity_key=self.entity_key,
                                                           entity_title=self.entity_title,
                                                           recommendation_flag=INSUFFICIENT_DATA,
                                                           entity_level_processing=entity_level_processing,
                                                           analysis_window=analysis_window,
                                                           non_negative=non_negative,
                                                           sensitivity_level=sensitivity_level,
                                                           use_static=use_static,
                                                           )
        KPIResponseBuilder.preprocess(self.df)
        
        # Check if the time series is nearly constant, which defined as 
        # difference between maxium and minium is smaller than CONSTANT_TIME_SERIES_THRESHOLD * median
        if self.is_nearly_constant_timeseries():
            # Log a warning that the KPI is a nearly constant time series
            # and standard deviation-based thresholds are not appropriate
            logger.warning(
                f"KPI '{self.kpi_id}' is a nearly constant time series; recommendations are not based " 
                "on standard deviation, use static thresholds instead."
            )
            max_value, min_value, median = self.df[COL_VALUE].max(), self.df[COL_VALUE].min(), self.df[COL_VALUE].median()
            mean, std = self.df[COL_VALUE].mean(), self.df[COL_VALUE].std()
            thres_res = calc_constant_time_series_thresholds(max_value, min_value, median,
                                            threshold_rounding, threshold_direction,
                                            sensitivity_level,
                                            non_negative=non_negative)
            # Note: the constant timeseries case is special, 
            # so the format of constant_cron_list is different with normal cron format
            constant_cron_lists = [{MEAN: mean, STD: std, THRESHOLDS: thres_res}]
            return KPIResponseBuilder.prepare_kpi_response(
                itsi_kpi_id=self.kpi_id,
                itsi_service_id=self.service_id,
                entity_key=self.entity_key,
                entity_title=self.entity_title,
                recommendation_flag=CONSTANT_KPI,
                entity_level_processing=entity_level_processing,
                cron_lists=constant_cron_lists, # here is constant_cron_lists
                threshold_rounding=threshold_rounding,
                threshold_direction=threshold_direction,
                time_policy_description='Static thresholding', # Explanation of the thresholding approach
                analysis_window=analysis_window,
                non_negative=non_negative,
                sensitivity_level=sensitivity_level,
                use_static="True",
                mean=mean,
                stdev=std,
            )

        # Get the cron output, time policy description, and score.
        # Choose threshold direction only if input threshold_direction is auto

        # Determine if automatic threshold direction should be used
        choose_auto_direction = (threshold_direction == THR_DIR_AUTO)

        # Generate required output and automatically detect threshold direction if needed
        filter_config = FilterConfig.getSensitivityConfig(sensitivity_level)
        timepolicy_output = generate_cron_output(self.df, filter_config, choose_auto_direction)

        # Decide on the final threshold direction
        final_direction = timepolicy_output.threshold_direction if choose_auto_direction else threshold_direction

        # Sort and prepare cron lists
        cron_dict = timepolicy_output.cron_dict
        cron_lists = [cron_dict[k] for k in sorted(cron_dict.keys())]

        time_policy_desc = timepolicy_output.time_policy_desc
        recommendation_flag = 'SUCCESSFUL' if time_policy_desc not in ['NO_PATTERN', 'INSUFFICIENT_DATA',
                                                                       'PATTERN_SWITCH'] else time_policy_desc

        return KPIResponseBuilder.prepare_kpi_response(
            itsi_kpi_id=self.kpi_id,
            itsi_service_id=self.service_id,
            entity_key=self.entity_key,
            entity_title=self.entity_title,
            recommendation_flag=recommendation_flag,
            entity_level_processing=entity_level_processing,
            cron_lists=cron_lists,
            score=timepolicy_output.time_policy_score,
            threshold_rounding=threshold_rounding,
            threshold_direction=final_direction,
            time_policy_description=time_policy_desc,
            analysis_window=analysis_window,
            non_negative=non_negative,
            sensitivity_level=sensitivity_level,
            use_static=use_static,
            mean=self.df[COL_VALUE].mean(),
            stdev=self.df[COL_VALUE].std(),
        )


@Configuration()
class RecommendThresholdTemplateCommand(StreamingCommand):
    """
    The RecommendThresholdTemplateCommand class is responsible for real-time KPI threshold recommendations based on incoming streaming data.

    This class takes streaming records as input, groups them by a specified 'itsi_kpi_id_field', and then applies a set of computations
    to recommend appropriate KPI thresholds for each group of records.
    """

    alert_value_field = Option(require=False, default=ALERT_VALUE)

    # An option to specify the field for ITSI KPI IDs. Defaults to 'itsi_kpi_id' if not provided.
    itsi_kpi_id_field = Option(require=False, default=ITSI_KPI_ID)

    itsi_service_id_field = Option(require=False, default=ITSI_SERVICE_ID)

    entity_key_field = Option(require=False, default=ENTITY_KEY)

    entity_title_field = Option(require=False, default=ENTITY_TITLE)

    entity_level_processing = Option(require=False, default=False, validate=validators.Boolean())

    send_to_api = Option(require=False, default=False, validate=validators.Boolean())

    time_field = '_time'

    # An option for the timestamp format. Defaults to a pre-defined ITSI timestamp format if not provided.
    timestamp_format = Option(require=False, default=ITSI_TIMESTAMP_FORMAT)

    # An option to specify if the input data has a header. Defaults to False if not provided.
    has_header = Option(require=False, default=False)

    # An option for the precision to round threshold values. Defaults to 2 decimal places.
    threshold_rounding = Option(require=False, default=2, validate=validators.Integer())

    # An option to specify the direction in which to consider thresholds (both, up, or low).
    # Validates the provided value against a predefined set of values (both, up, or low).
    threshold_direction = Option(
        require=False,
        default=THR_DIR_AUTO,
        validate=validators.Set(THR_DIR_AUTO, THR_DIR_BOTH, THR_DIR_UP, THR_DIR_LO)
    )

    # An option to specify a specific analysis window, serves no other function than to make it clear what timerange was chosen by the user.
    analysis_window = Option(require=False, default="")

    # An option to enforce returned threshold non-negative
    non_negative = Option(require=False, default=True, validate=validators.Boolean())

    # An option to force one-time static recommendations, serves no other function than to make it clear whether mean and stdev values should be recomputed nightly or not.
    use_static = Option(require=False, default=False, validate=validators.Boolean())

    # An option to set user defined sensitivity level,
    sensitivity_level = Option(
        require=False,
        default=SensitivityLevelConstants.LOW,
        validate=validators.Set(
            SensitivityLevelConstants.LOW,
            SensitivityLevelConstants.MEDIUM,
            SensitivityLevelConstants.HIGH
        )
    )

    # Buffer to store records by record key
    buffer = defaultdict(deque)

    # List to maintain the order in which keys are received
    order_of_received_keys = []

    start_time = time.time()

    collection_name = KV_AT_TIME_POLICIES_COLLECTION

    def __init__(self):
        super().__init__()
        self.df = None
        self.count_of_processed_ids = 0

    def generate_kpi_recommendations(self, records):
        """
        Convert a list of records to a DataFrame and apply KPI threshold recommendations processing.

        Parameters:
            records (deque[dict]): A list of dictionaries where each dictionary represents a record with keys
                                  corresponding to the fields in the DataFrame.

        Returns:
            dict: Recommendations for KPI thresholds.
        """
        # Create DataFrame 'df' from 'records'; skip first row if 'has_header' is True.
        # Note: The DataFrame will have columns in the order of 'time_field', 'value_field', and 'kpi_id_field'.
        df = pd.DataFrame(records[1:] if self.has_header else records)

        # Renaming ignored if column does not exist in DataFrame
        column_renames = {
            self.time_field: COL_DATE,
            self.alert_value_field: COL_VALUE,
            self.itsi_service_id_field: COL_SERVICE_ID,
            self.itsi_kpi_id_field: COL_KPI_ID,
            self.entity_key_field: ENTITY_KEY,
            self.entity_title_field: ENTITY_TITLE
        }

        df.rename(columns=column_renames, inplace=True)

        # Replace field that's entirely space (or empty) with NaN
        df = df.replace(r'^\s*$', np.nan, regex=True)

        # Parse and update the timestamps in the DataFrame 'df' using the given 'timestamp_format'.
        # It converts 'COL_DATE' column in the DataFrame 'df' into a DateTime object.
        df = parse_timestamp(df, self.timestamp_format)

        return KPIThresholdRecommender(df).process(
            threshold_rounding=self.threshold_rounding,
            threshold_direction=self.threshold_direction,
            analysis_window=self.analysis_window,
            non_negative=self.non_negative,
            use_static=self.use_static,
            sensitivity_level=self.sensitivity_level,
            entity_level_processing=self.entity_level_processing,
        )

    def save_to_kvstore(self, records, all_data_received=False):
        job_id = self.metadata.searchinfo.sid  # Get the unique Splunk job ID

        # Get or create KV Store collection
        collection = self.get_or_create_collection()

        # Fetch existing record if available
        existing_record = self.fetch_existing_record(collection, job_id)

        if existing_record:
            self.update_existing_record(collection, job_id, existing_record, records, all_data_received)
        else:
            self.create_new_record(collection, job_id, records, all_data_received)

    def get_or_create_collection(self):
        kvstore = self.service.kvstore
        return kvstore.create(self.collection_name) if self.collection_name not in kvstore else kvstore[
            self.collection_name]

    @staticmethod
    def fetch_existing_record(collection, job_id):
        try:
            return collection.data.query_by_id(job_id)
        except Exception as e:
            logger.error(f"Unable to find record with _key={job_id} in KV Store due to error: {str(e)}")
            return None

    @staticmethod
    def update_existing_record(collection, job_id, existing_record, records, all_data_received):
        existing_data = json.loads(existing_record['data'])
        existing_data.extend(records)
        updated_data = json.dumps(existing_data)
        collection.data.update(job_id, {'data': updated_data, ALL_DATA_RECEIVED: all_data_received})

    def log_kv_store_record_by_id(self, job_id):
        collection = self.get_or_create_collection()
        record = self.fetch_existing_record(collection, job_id)
        logger.info(f"KVStore job_id={job_id}, record={record}")

    @staticmethod
    def create_new_record(collection, job_id, records, all_data_received):
        new_data = json.dumps(records)
        insert_result = collection.data.insert(
            json.dumps({'_key': job_id, 'data': new_data, ALL_DATA_RECEIVED: all_data_received}))
        logger.info(f"KVStore insert operation result, job_id={job_id}, insert_result={insert_result}")

    @staticmethod
    def generate_empty_records_response(use_static, analysis_window, non_negative, sensitivity_level):
        # the kpi id and service id set to none since it should be given by data
        return KPIResponseBuilder.structure_kpi_output(
            itsi_kpi_id='None',
            itsi_service_id="None",
            recommendation_flag=INSUFFICIENT_DATA,
            use_static=use_static,
            analysis_window=analysis_window,
            non_negative=non_negative,
            sensitivity_level=sensitivity_level,
        )

    @staticmethod
    def kpi_post_formatting(data):
        # This post body format of KPI level is from the ITSI api design, please refer the api doc here
        # https://splunk.atlassian.net/wiki/spaces/PROD/pages/1078561114681/Documentation+for+Saving+Threshold+Recommendations+for+KPIs
        kpi_formatted_data = []
        for entry in data:
            new_entry = {
                ITSI_KPI_ID: entry[ITSI_KPI_ID],
                ITSI_SERVICE_ID: entry[ITSI_SERVICE_ID],
                KPI_AT_CONFIGURATION: [{}]
            }
            for field in entry.keys():
                if field not in [ITSI_KPI_ID, ITSI_SERVICE_ID]:
                    new_entry[KPI_AT_CONFIGURATION][0][field] = entry[field]
            kpi_formatted_data.append(new_entry)
        return kpi_formatted_data

    def save_empty_records_response_to_kvstore(self, empty_records_response):
        self.save_to_kvstore(records=empty_records_response, all_data_received=True)

    def _record_processing_metrics(self, results, id_, kpi_rec_start_time, is_end_of_kpis, entity_level_processing):
        first_row = results[0]
        log_telemetry(
            event_type="pattern_detection_completed",
            kpi_id=first_row.get(ITSI_KPI_ID),
            entity_level_processing=entity_level_processing,
            entity_key=first_row.get(ENTITY_KEY),
            entity_title=first_row.get(ENTITY_TITLE),
            recommendation_flag=first_row.get(RECOMMENDATION_FLAG),
            algorithm=first_row.get(ALGORITHM),
            cron_expression=f"'{first_row.get(CRON_EXPRESSION, '')}'",
            threshold_direction=first_row.get(THRESHOLD_DIRECTION),
            thresholds=first_row.get(THRESHOLDS),
            mean=first_row.get(MEAN),
            std=first_row.get(STD),
            sensitivity=first_row.get(SENSITIVITY),
            score=first_row.get(SCORE),
            confidence=first_row.get(CONFIDENCE),
            non_negative=first_row.get(NON_NEGATIVE),
            sensitivity_level=first_row.get(SENSITIVITY_LEVEL),
            time_policy_desc=f"'{first_row.get(TIME_POLICY_DESCRIPTION, '')}'",
            processing_time=f"{time.time() - kpi_rec_start_time:.2f}s"
        )

        log_telemetry(
            event_type="kpi_processed",
            kpi_id=id_,
            entity_level_processing=entity_level_processing,
            entity_key=first_row.get(ENTITY_KEY),
            entity_title=first_row.get(ENTITY_TITLE),
            processing_time=f"{time.time() - self.start_time:.5f}s"
        )

        if is_end_of_kpis:
            log_telemetry(
                event_type="kpis_processing_complete",
                count_of_processed_ids=self.count_of_processed_ids,
                entity_level_processing=entity_level_processing,
                entity_key=first_row.get(ENTITY_KEY),
                entity_title=first_row.get(ENTITY_TITLE),
                processing_time=f"{time.time() - self.start_time:.5f}s"
            )

    def process_empty_records(self):
        """
        Handles the scenario when the records are empty.
        """
        empty_records_response = self.generate_empty_records_response(use_static=self.use_static,
                                                                      analysis_window=self.analysis_window,
                                                                      non_negative=self.non_negative,
                                                                      sensitivity_level=self.sensitivity_level)
        if self.send_to_api:
            self.post_results_to_api(empty_records_response)
        else:
            self.save_empty_records_response_to_kvstore(empty_records_response)
        return empty_records_response

    def validate_record_fields(self, record):
        # Method to validate required fields in the record
        required_fields = [self.time_field, self.alert_value_field, self.itsi_service_id_field, self.itsi_kpi_id_field]

        for field in required_fields:
            if field not in record:
                raise ValueError(f'The field {field} is not a field in the dataset. \
                                 Ensure the field is passed correctly to the {field} argument of recommendthresholdtemplate.')

        # Additional validation for entity level processing
        if self.entity_level_processing:
            entity_key_valid = is_valid_value(record.get(self.entity_key_field))
            entity_title_valid = is_valid_value(record.get(self.entity_title_field))

            if not entity_key_valid and not entity_title_valid:  # Check if both are invalid
                raise ValueError(
                    f"Both {self.entity_key_field} and {self.entity_title_field} are missing or invalid in the record. "
                    "At least one is required for entity level processing.")

    def determine_record_key(self, record):
        # Method to determine the key for the record
        if self.entity_level_processing:
            key_to_use = get_valid_entity_identifier(record.get(self.entity_key_field),
                                                     record.get(self.entity_title_field))
            if not key_to_use:
                raise ValueError(
                    f"Both {self.entity_key_field} and {self.entity_title_field} are invalid or missing for entity level processing.")
            return key_to_use.strip()

        # For non-entity level processing, use the itsi_kpi_id_field
        return record[self.itsi_kpi_id_field].strip()

    def create_buffer_entry(self, record):
        # Method to create a buffer entry from the record
        # select which field to enter the buffer, kpi_id and service_id are needed for kpi level
        # entity_id and entity_title are needed for entity level, so we need to include these fields
        buffer_entry = OrderedDict([
            (self.time_field, record[self.time_field]),
            (self.alert_value_field, record[self.alert_value_field]),
            (self.itsi_kpi_id_field, record[self.itsi_kpi_id_field]),
            (self.itsi_service_id_field, record[self.itsi_service_id_field])
        ])
        if self.entity_level_processing:
            if self.entity_key_field in record:
                buffer_entry[self.entity_key_field] = record[self.entity_key_field]
            if self.entity_title_field in record:
                buffer_entry[self.entity_title_field] = record[self.entity_title_field]
        return buffer_entry

    def determine_keys_to_process(self):
        # Check whether to process all ids or just the previous ones based on the _finished flag
        # If not finished, skip the last one
        to_process_ids = []
        for key_current in self.order_of_received_keys:
            if not self._finished and key_current == self.order_of_received_keys[-1]:
                break
            to_process_ids.append(key_current)
        return to_process_ids

    def cleanup_processed_keys(self, processed_ids):
        # Method to clean up processed keys from buffer and list
        for key in processed_ids:
            del self.buffer[key]
            self.order_of_received_keys.remove(key)

    def post_results_to_api(self, data, id_=None):
        """
        Post results (either KPI or entity-level) to the itsi API endpoint.
        kpi level and entity level have different end points, post body formats and
        response statuses, the level is decided by self.entity_level_processing

        Parameters:
        - data: The data to be posted, either KPI or entity-level formatted.
        - id_ (optional): kpi_id if data is kpi_level, entity_id if entity level

        Returns:
        - PostReturnStatusConstants.SUCCESS if the post is successful.
        - PostReturnStatusConstants.FAILURE if the response status is not in the expected success range.
        - PostReturnStatusConstants.EXCEPTION if an exception occurs during the post operation.
        """
        if self.entity_level_processing:
            post_end_point = ITSI_ENTITIES_AT_RESULTS_POST_URI
            # entity level is existing code, in which the status is [201, 200],
            # the kpi level below is new, which follows the api doc:
            # https://splunk.atlassian.net/wiki/spaces/PROD/pages/1078561114681/Documentation+for+Saving+Threshold+Recommendations+for+KPIs
            ok_status = [201, 200]
            json_body = {"data": json.dumps(data)}
        else:
            post_end_point = ITSI_KPI_RESULTS_POST_URI
            ok_status = [200]
            json_body = {"data": json.dumps(self.kpi_post_formatting(data))}

        try:
            response = self.service.post(post_end_point,
                                         owner="nobody",
                                         app="SA-ITOA",
                                         body=json_body)
            # Check if the response status code is within the expected successful status codes.
            if response.status in ok_status:
                logger.info(f"Data successfully posted for ID: {id_}.")
                return PostReturnStatusConstants.SUCCESS
            else:
                logger.error(f"Failed to post data for ID: {id_}. Status: {response.status}, Reason: {response.reason}")
                return PostReturnStatusConstants.FAILURE
        except Exception as e:
            # If any exception occurs during the post process, log the exception and return an EXCEPTION status.
            logger.exception(f"An error occurred while posting data for ID: {id_}. Exception: {e}")
            return PostReturnStatusConstants.EXCEPTION

    def buffer_record(self, key, record):
        buffer_entry = self.create_buffer_entry(record)
        self.buffer[key].append(buffer_entry)

    def process_and_yield_empty_records(self):
        """
        Handles the scenario when no records have been processed.
        """
        log_telemetry(
            event_type="no_data_error",
            error="Received empty records - no data available to process."
        )
        return self.process_empty_records()

    def handle_record(self, record):
        self.validate_record_fields(record)

        key = self.determine_record_key(record)

        if key not in self.order_of_received_keys:
            self.order_of_received_keys.append(key)
        self.buffer_record(key, record)

    def stream(self, records):
        """
        Group, process, and yield processed records based on the entity_key, entity_title, or itsi_kpi_id field,
        depending on the configuration.

        The function performs the following tasks:

        1. Iterates over the incoming records:
        a. If entity_level_processing is enabled, it first tries to use `entity_key` as the primary key for each
        record. If `entity_key` is absent or empty, `entity_title` is used as a fallback. Otherwise, `itsi_kpi_id` is used as the key.
        b. Tracks the order in which unique keys (entity_key/entity_title/itsi_kpi_id) are encountered for the first time.
        c. Buffers each record by its key (entity_key/entity_title/itsi_kpi_id) into an internal data structure.

        2. Determines the keys that should be processed based on the `_finished` flag:
           - If `_finished` flag is unset, the most recent key in the buffer is skipped.

        3. Processes records serially for each determined key using the `process_records` function:
           - Yields the processed records individually if they are returned as a list.
           - Yields the entire result directly otherwise.

        4. Once records of a particular key are processed and yielded, they are removed from the buffer and the
        order list to free up memory.

        Args:
        - records (iterable): Stream of records to be processed.

        Yields:
        - dict: Processed records or results.
        """
        # Use a flag to check if records were processed
        records_processed = False

        for record in records:
            records_processed = True
            self.handle_record(record)

        if records_processed:
            to_process_ids = self.determine_keys_to_process()

            for index, id_ in enumerate(to_process_ids):
                kpi_rec_start_time = time.time()
                results = self.generate_kpi_recommendations(self.buffer[id_])

                is_last_element = (index == len(to_process_ids) - 1)
                self.count_of_processed_ids += 1

                if self.send_to_api:
                    # send result to ITSI api
                    self.post_results_to_api(results, id_)
                else:
                    self.save_to_kvstore(results, self._finished & is_last_element)

                    yield from results

                self._record_processing_metrics(results, id_,
                                                kpi_rec_start_time,
                                                self._finished & is_last_element,
                                                self.entity_level_processing)

            self.cleanup_processed_keys(to_process_ids)
        else:
            yield from self.process_and_yield_empty_records()


dispatch(RecommendThresholdTemplateCommand, sys.argv, sys.stdin, sys.stdout, __name__)
