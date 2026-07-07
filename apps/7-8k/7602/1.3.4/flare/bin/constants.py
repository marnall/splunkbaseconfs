from datetime import timedelta
from enum import Enum


APP_NAME = "flare"
HOST = "localhost"
SPLUNK_PORT = 8089
REALM = APP_NAME + "_realm"
CRON_JOB_THRESHOLD_SINCE_LAST_FETCH = timedelta(minutes=10)


class PasswordKeys(Enum):
    API_KEY = "api_key"
    TENANT_IDS = "tenant_ids"
    INGEST_FULL_EVENT_DATA = "ingest_full_event_data"
    SEVERITIES_FILTER = "severities_filter"
    SOURCE_TYPES_FILTER = "source_types_filter"
    NUMBER_OF_DAYS_TO_BACKFILL = "number_of_days_to_backfill"


class DataStoreKeys(Enum):
    START_DATE = "start_date"
    TIMESTAMP_LAST_FETCH = "timestamp_last_fetch"

    SECTION_METADATA = "metadata"
    SECTION_TENANT_DATA = "tenant_data"

    @staticmethod
    def get_next_token(tenant_id: int) -> str:
        return f"next_{tenant_id}"

    @staticmethod
    def get_earliest_ingested(tenant_id: int) -> str:
        return f"timestamp_earliest_ingested_{tenant_id}"
