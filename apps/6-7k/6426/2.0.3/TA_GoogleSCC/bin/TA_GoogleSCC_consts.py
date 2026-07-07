"""Class which contain constance used by all files."""
import import_declare_test  # noqa F401


class Constants:
    """Class containing configuration constants."""

    SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
    DEFAULT_INTERVAL_VALUE = 300  # in second
    DEFAULT_MAX_SOURCE_VALUE = 1000
    MIN_INTERVAL_VALUE = 60  # in second
    MAX_INTERVAL_VALUE = 3600  # in second
    CONFIG_TIMEOUT = 30  # in second
    TIMEOUT_TIME = 60  # in second
    PRODUCT_VERSION = "1.0.0"
    RETRY_COUNT = 3
    CONNECTION_TIMEOUT = 2  # In Seconds
    READ_TIMEOUT = 5  # In Seconds
    RETRY_ON_EMPTY = 3
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    ISO_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    TIME_TO_SLEEP_ON_RETRY = 15
    FLAG = True

    # Google SCC path
    ORGANIZATION_PATH = "organizations/{}"
    SOURCE_PATH = "/sources/{}"
    FINDING_PATH = "/findings/{}"
    SCC_URL = "https://console.cloud.google.com/security/command-center/{}?organizationId={}&resourceId={}"
    ASSET_SCC_URL = "https://console.cloud.google.com/security/command-center/{}?organizationId={}&orgonly=true"\
                    "&supportedpurview=organizationId&view_type=vt_asset_type&vt_asset_type=All&columns="\
                    "securityCenterProperties.resourceType,securityCenterProperties.resourceOwners,securityMarks."\
                    "marks&pageState=(%22cscc-asset-inventory%22:(%22f%22:%22%255B%257B_22k_22_3A_22"\
                    "securityCenterProperties.resourceName_22_2C_22t_22_3A10_2C_22v_22_3A_22_5C"\
                    "_22{}_5C_22_22_2C_22i_22_3A_22securityCenterProperties.resourceName_22%257D%255D%22))"
    # Google Pub/Sub helpers
    PROJECT_PATH = "projects/{}"
    SUBSCRIPTION_PATH = "/subscriptions/{}"

    # securitycenter API
    SERVICE_NAME = "securitycenter"
    PUBSUB_SERVICE_NAME = "pubsub"
    SERVICE_VERSION = "v1"
    PUBSUB_SERVICE_VERSION = "v1"

    # cloudasset API
    CAI_SERVICE_NAME = "cloudasset"
    CAI_SERVICE_VERSION = "v1"
    CONTENT_TYPE_RESOURCE = "RESOURCE"
    CONTENT_TYPE_IAM = "IAM_POLICY"
    DEFAULT_ASSET_TYPES = ".*"
    DEFAULT_IAM_ASSET_TYPES = ["cloudresourcemanager.googleapis.com/Project"]
    DEFAULT_MAX_ASSET_VALUE = 1000

    # Collection
    COLLECTION_NAME = "updated_finding_state_collection"

    # Instance Checkpoint
    INSTANCE_CHECKPOINT = "Instance_details"


constants = Constants()
