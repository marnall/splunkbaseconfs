# KV Store collection name
KV_AT_TIME_POLICIES_COLLECTION = "kpis_at_configurations"

# HTTP error messages
MISSING_JOB_ID = "Missing job_id."
METHOD_NOT_ALLOWED = "Method not allowed."
JOB_ID_NOT_FOUND = "job_id not found"

# Constants for Column and Field Names
ITSI_KPI_ID = 'itsi_kpi_id'
ITSI_SERVICE_ID = 'itsi_service_id'
KPI_AT_CONFIGURATION = "kpi_at_configurations"
RECOMMENDATION_FLAG = 'Recommendation Flag'
ALGORITHM = 'Algorithm'
CRON_EXPRESSION = 'Cron Expression'
DURATION = 'Duration'
THRESHOLD_DIRECTION = 'Threshold Direction'
THRESHOLDS = 'Thresholds'
MEAN = 'Mean'
STD = 'Std'
SENSITIVITY = 'Sensitivity'
SCORE = 'Score'
CONFIDENCE = 'Confidence'
TIME_POLICY_DESCRIPTION = 'Time Policy Description'
ANALYSIS_WINDOW = 'Analysis Window'
USE_STATIC = 'Use Static'
NON_NEGATIVE = "Non_negative"
SENSITIVITY_LEVEL = "Sensitivity Level"

ALL_DATA_RECEIVED = "all_data_received"
CONSTANT_KPI = 'CONSTANT_KPI'
ENTITY_KEY = 'entity_key'
ENTITY_TITLE = 'entity_title'
ALERT_VALUE = 'alert_value'
ENTITY_AT_CONFIGURATIONS = 'entity_at_configurations'
NA = 'N/A'

FIELD_TO_SNAKE_CASE_DICT = {
    ITSI_SERVICE_ID: 'itsi_service_id',
    ITSI_KPI_ID: 'itsi_kpi_id',
    # ITSI_SERVICE_ID is required in this dictionary for validation/formatting 
    # when reading the data from the KVStore.
    ITSI_SERVICE_ID: "itsi_service_id",
    RECOMMENDATION_FLAG: 'recommendation_flag',
    ALGORITHM: 'algorithm',
    CRON_EXPRESSION: 'cron_expression',
    DURATION: 'duration',
    THRESHOLD_DIRECTION: 'threshold_direction',
    THRESHOLDS: 'thresholds',
    MEAN: 'mean',
    STD: 'std',
    SENSITIVITY: 'sensitivity',
    SCORE: 'score',
    CONFIDENCE: 'confidence',
    TIME_POLICY_DESCRIPTION: 'time_policy_description',
    ANALYSIS_WINDOW: 'analysis_window',
    USE_STATIC: 'use_static',
    NON_NEGATIVE: "non_negative",
    SENSITIVITY_LEVEL: "sensitivity_level",
    ENTITY_KEY: ENTITY_KEY,
    ENTITY_TITLE: ENTITY_TITLE,
}

# This endpoint is only for entity level, though there is "kpi" in its name.
ITSI_ENTITIES_AT_RESULTS_POST_URI = "itoa_interface/kpi_entity_threshold_recommendations"
# This endpoint is for kpi level
ITSI_KPI_RESULTS_POST_URI = "itoa_interface/kpi_threshold_recommendations"

# post Api response status
class PostReturnStatusConstants:
    """
    A class containing constants that represent the status of posting,
    used for checking return status of sending results to ITSI
    """
    SUCCESS = "success"
    FAILURE = "failure"
    EXCEPTION = "exception" 

# Constants for testing
FLOAT_NUMBER_TOLERANCE = 0.1
FLOAT_PERCENTAGE_TOLERANCE = 0.1
FLOAT_ABS_TOLERANCE = 1e-6

## Sensitivity Adjustment
class SensitivityLevelConstants:
    """
    A class containing constants that represent the status of posting,
    used for checking return status of sending alerts to ITSI
    """
    LOW = "0"
    MEDIUM = "1"
    HIGH = "2"

class FilterConfig:
    """
    A configuration class for defining filter parameters.

    Attributes:
        percentile_lower_threshold (float): The lower threshold for filtering data,
                                        represented as a percentile (0-100).
        percentile_upper_threshold (float): The upper threshold for filtering data,
                                        represented as a percentile (0-100),
                                        should be larger than `percentile_lower_thres`
        variation_unit_multiplier (float): A multiplier that adjusts the sensitivity of the variation unit,
                                            larger value means less sensitivity.
    """
    # Predefined configurations for different sensitivity levels.
    FILTER_CONFIGS = {
        SensitivityLevelConstants.LOW: {
            "percentile_lower_threshold": 0,
            "percentile_upper_threshold": 100,
            # With larger variation_unit_multiplier, the threshold boundary will be wider and result in a lower sensitivity.
            # Infinite multiplier means use all the data, no filter.
            "variation_unit_multiplier": float("inf")
        },
        SensitivityLevelConstants.MEDIUM: {
            "percentile_lower_threshold": 15,
            "percentile_upper_threshold": 85,
            "variation_unit_multiplier": 2.5
        },
        SensitivityLevelConstants.HIGH: {
            "percentile_lower_threshold": 25,
            "percentile_upper_threshold": 75,
            "variation_unit_multiplier": 1.5
        }
    }

    def __init__(self, percentile_lower_threshold, percentile_upper_threshold, variation_unit_multiplier):
        self.percentile_lower_threshold = percentile_lower_threshold
        self.percentile_upper_threshold = percentile_upper_threshold
        self.variation_unit_multiplier = variation_unit_multiplier

    @classmethod
    def getSensitivityConfig(cls, sensitivity_level):
        """
        Retrieve the filter configuration for a given sensitivity level.

        Args:
            level (str): The sensitivity level choose from
                SensitivityLevelConstants.LOW,
                SensitivityLevelConstants.MEDIUM,
                SensitivityLevelConstants.HIGH.

        Returns:
            FilterConfig: An instance of the FilterConfig class for the specified level.
        """
        # if sensitivity level is not in range, we return default value "low"
        config = cls.FILTER_CONFIGS.get(sensitivity_level, cls.FILTER_CONFIGS[SensitivityLevelConstants.LOW])
        return cls(
            config['percentile_lower_threshold'],
            config['percentile_upper_threshold'],
            config['variation_unit_multiplier']
        )

CONSTANT_TIME_SERIES_THRESHOLD = 0.01
CONSTANT_TIMESERIES_SENSITIVITY_DICT = {
    SensitivityLevelConstants.LOW: 0.05,
    SensitivityLevelConstants.MEDIUM: 0.03,
    SensitivityLevelConstants.HIGH: 0.01
}
    
