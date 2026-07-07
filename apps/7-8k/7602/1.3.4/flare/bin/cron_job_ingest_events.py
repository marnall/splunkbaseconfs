import json
import os
import sys


if sys.version_info < (3, 9):
    sys.exit("Error: This application requires Python 3.9 or higher.")

from data_store import ConfigDataStore
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Iterator
from typing import Optional


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vendor"))
import vendor.splunklib.client as client

from constants import APP_NAME
from constants import CRON_JOB_THRESHOLD_SINCE_LAST_FETCH
from constants import HOST
from constants import SPLUNK_PORT
from constants import PasswordKeys
from flare import FlareAPI
from logger import Logger


def main(
    logger: Logger,
    storage_passwords: client.StoragePasswords,
    flare_api_cls: type[FlareAPI],
    data_store: ConfigDataStore,
) -> None:
    # To avoid cron jobs from doing the same work at the same time, exit new cron jobs if a cron job is already doing work
    last_fetched_timestamp = data_store.get_last_fetch()
    if last_fetched_timestamp and last_fetched_timestamp > (
        datetime.now(timezone.utc) - CRON_JOB_THRESHOLD_SINCE_LAST_FETCH
    ):
        logger.info(
            f"Fetched events less than {int(CRON_JOB_THRESHOLD_SINCE_LAST_FETCH.seconds / 60)} minutes ago, exiting"
        )
        return

    api_key = get_api_key(storage_passwords=storage_passwords)
    tenant_ids = get_tenant_ids(storage_passwords=storage_passwords)
    ingest_full_event_data = get_ingest_full_event_data(
        storage_passwords=storage_passwords
    )
    number_of_days_to_backfill = get_number_of_days_to_backfill(
        storage_passwords=storage_passwords
    )
    severities_filter = get_severities_filter(storage_passwords=storage_passwords)
    source_types_filter = get_source_types_filter(storage_passwords=storage_passwords)

    data_store.set_last_fetch(datetime.now(timezone.utc))

    total_events_fetched_count = 0

    for tenant_id in tenant_ids:
        events_fetched_count = 0

        # The earliest ingested date serves as a low water mark to look
        # for identifiers 30 days prior to the day a tenant was first configured.
        start_date = data_store.get_earliest_ingested_by_tenant(tenant_id)
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(
                days=number_of_days_to_backfill
            )
            data_store.set_earliest_ingested_by_tenant(tenant_id, start_date)

        for event, next_token in fetch_feed(
            logger=logger,
            api_key=api_key,
            tenant_id=tenant_id,
            ingest_full_event_data=ingest_full_event_data,
            severities=severities_filter,
            source_types=source_types_filter,
            flare_api_cls=flare_api_cls,
            data_store=data_store,
        ):
            data_store.set_last_fetch(datetime.now(timezone.utc))

            data_store.set_next_by_tenant(tenant_id, next_token)

            event["tenant_id"] = tenant_id

            # stdout is picked up by splunk and this is how events
            # are ingested after being retrieved from Flare.
            print(json.dumps(event), flush=True)

            events_fetched_count += 1
        logger.info(f"Fetched {events_fetched_count} events on tenant {tenant_id}")
        total_events_fetched_count += events_fetched_count

    logger.info(f"Fetched {total_events_fetched_count} events across all tenants")


def fetch_feed(
    logger: Logger,
    api_key: str,
    tenant_id: int,
    ingest_full_event_data: bool,
    severities: list[str],
    source_types: list[str],
    flare_api_cls: type[FlareAPI],
    data_store: ConfigDataStore,
) -> Iterator[tuple[dict, str]]:
    flare_api: FlareAPI = flare_api_cls(
        api_key=api_key,
        tenant_id=tenant_id,
        logger=logger,
    )

    try:
        next = data_store.get_next_by_tenant(tenant_id)
        start_date = data_store.get_earliest_ingested_by_tenant(tenant_id)
        logger.info(f"Fetching {tenant_id=}, {next=}, {start_date=}")
        for event_next in flare_api.fetch_feed_events(
            next=next,
            start_date=start_date,
            ingest_full_event_data=ingest_full_event_data,
            severities=severities,
            source_types=source_types,
        ):
            yield event_next
    except Exception as e:
        logger.error(f"Exception={e}")


def get_storage_password_value(
    storage_passwords: client.StoragePasswords, password_key: str
) -> Optional[str]:
    for item in storage_passwords.list():
        if item.content.username == password_key:
            return item.clear_password

    return None


def get_api_key(storage_passwords: client.StoragePasswords) -> str:
    api_key = get_storage_password_value(
        storage_passwords=storage_passwords, password_key=PasswordKeys.API_KEY.value
    )
    if not api_key:
        raise Exception("API key not found")
    return api_key


def get_number_of_days_to_backfill(storage_passwords: client.StoragePasswords) -> int:
    number_of_days_to_backfill = get_storage_password_value(
        storage_passwords=storage_passwords,
        password_key=PasswordKeys.NUMBER_OF_DAYS_TO_BACKFILL.value,
    )

    try:
        return int(number_of_days_to_backfill) if number_of_days_to_backfill else 30
    except Exception as e:
        raise Exception("Number of days to backfill not a number") from e


def get_tenant_ids(storage_passwords: client.StoragePasswords) -> list[int]:
    stored_tenant_ids = get_storage_password_value(
        storage_passwords=storage_passwords, password_key=PasswordKeys.TENANT_IDS.value
    )
    tenant_ids = None
    try:
        tenant_ids = json.loads(stored_tenant_ids) if stored_tenant_ids else None
    except Exception:
        pass

    if tenant_ids is None:
        raise Exception("Tenant IDs not found")
    return tenant_ids


def get_ingest_full_event_data(storage_passwords: client.StoragePasswords) -> bool:
    return (
        get_storage_password_value(
            storage_passwords=storage_passwords,
            password_key=PasswordKeys.INGEST_FULL_EVENT_DATA.value,
        )
        == "true"
    )


def get_severities_filter(storage_passwords: client.StoragePasswords) -> list[str]:
    severities_filter = get_storage_password_value(
        storage_passwords=storage_passwords,
        password_key=PasswordKeys.SEVERITIES_FILTER.value,
    )

    if severities_filter:
        return severities_filter.split(",")

    return []


def get_source_types_filter(storage_passwords: client.StoragePasswords) -> list[str]:
    source_types_filter = get_storage_password_value(
        storage_passwords=storage_passwords,
        password_key=PasswordKeys.SOURCE_TYPES_FILTER.value,
    )

    if source_types_filter:
        return source_types_filter.split(",")

    return []


def get_splunk_service(logger: Logger, token: str) -> client.Service:
    try:
        splunk_service = client.connect(
            host=HOST,
            port=SPLUNK_PORT,
            app=APP_NAME,
            token=token,
            autologin=True,
        )
    except Exception as e:
        logger.error(str(e))
        raise Exception(str(e))

    return splunk_service


if __name__ == "__main__":
    logger = Logger(class_name=__file__)
    data_store = ConfigDataStore()
    token = sys.stdin.readline().strip()  # SEE: passAuth in https://docs.splunk.com/Documentation/Splunk/9.4.0/Admin/Inputsconf
    if not token:
        raise Exception(
            "Token not found - Go through the complete app configuration to update the user token."
        )

    splunk_service = get_splunk_service(logger=logger, token=token)
    app: client.Application = splunk_service.apps[APP_NAME]

    main(
        logger=logger,
        storage_passwords=app.service.storage_passwords,
        flare_api_cls=FlareAPI,
        data_store=data_store,
    )
