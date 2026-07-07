import configparser
import os

from constants import APP_NAME
from constants import DataStoreKeys
from datetime import datetime
from typing import Optional


# Define the config file path
splunk_home = os.environ.get("SPLUNK_HOME", "/opt/splunk")
config_path = os.path.join(
    splunk_home, "etc", "apps", f"{APP_NAME}", "local", "data_store.conf"
)


class ConfigDataStore:
    def __init__(self) -> None:
        config_store = configparser.RawConfigParser()
        config_store.read(config_path)

        # Add data sections
        if DataStoreKeys.SECTION_METADATA.value not in config_store.sections():
            config_store.add_section(DataStoreKeys.SECTION_METADATA.value)
        if DataStoreKeys.SECTION_TENANT_DATA.value not in config_store.sections():
            config_store.add_section(DataStoreKeys.SECTION_TENANT_DATA.value)
        self._store = config_store

    def _commit(self) -> None:
        with open(config_path, "w") as configfile:
            self._store.write(configfile)

    def _sync(self) -> None:
        self._store.read(config_path)

    def reset(self) -> None:
        self._store.clear()
        self._commit()

    def get_last_fetch(self) -> Optional[datetime]:
        self._sync()
        last_fetched = self._store.get(
            DataStoreKeys.SECTION_METADATA.value,
            DataStoreKeys.TIMESTAMP_LAST_FETCH.value,
            fallback=None,
        )

        if last_fetched:
            try:
                return datetime.fromisoformat(last_fetched)
            except Exception:
                pass
        return None

    def set_last_fetch(self, last_fetch: datetime) -> None:
        self._store.set(
            DataStoreKeys.SECTION_METADATA.value,
            DataStoreKeys.TIMESTAMP_LAST_FETCH.value,
            last_fetch.isoformat(),
        )
        self._commit()

    def get_next_by_tenant(self, tenant_id: int) -> Optional[str]:
        self._sync()
        return self._store.get(
            DataStoreKeys.SECTION_TENANT_DATA.value,
            DataStoreKeys.get_next_token(tenant_id=tenant_id),
            fallback=None,
        )

    def set_next_by_tenant(self, tenant_id: int, next: Optional[str]) -> None:
        if not next:
            return

        self._store.set(
            DataStoreKeys.SECTION_TENANT_DATA.value,
            DataStoreKeys.get_next_token(tenant_id=tenant_id),
            next,
        )
        self._commit()

    def get_earliest_ingested_by_tenant(self, tenant_id: int) -> Optional[datetime]:
        self._sync()
        earliest_ingested = self._store.get(
            DataStoreKeys.SECTION_TENANT_DATA.value,
            DataStoreKeys.get_earliest_ingested(tenant_id=tenant_id),
            fallback=None,
        )

        if earliest_ingested:
            try:
                return datetime.fromisoformat(earliest_ingested)
            except Exception:
                pass
        return None

    def set_earliest_ingested_by_tenant(
        self, tenant_id: int, earliest_ingested: datetime
    ) -> None:
        self._store.set(
            DataStoreKeys.SECTION_TENANT_DATA.value,
            DataStoreKeys.get_earliest_ingested(tenant_id=tenant_id),
            earliest_ingested.isoformat(),
        )
        self._commit()
