import sys


if sys.version_info < (3, 9):
    sys.exit("Error: This application requires Python 3.9 or higher.")


import requests
import time

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from logger import Logger
from typing import Any
from typing import Dict
from typing import Iterator
from typing import Optional
from typing import Union
from vendor.flareio import FlareApiClient
from vendor.requests.auth import AuthBase


def ensure_str(value: Union[str, bytes]) -> str:
    if isinstance(value, bytes):
        return value.decode("utf8")
    return value


def get_flare_api_client(
    *,
    api_key: str,
    tenant_id: Union[int, None],
) -> FlareApiClient:
    api_client = FlareApiClient(
        api_key=api_key,
        tenant_id=tenant_id,
    )
    current_user_agent: str = ensure_str(
        api_client._session.headers.get("User-Agent") or ""
    )
    api_client._session.headers["User-Agent"] = (
        f"{current_user_agent} flare-splunk".strip()
    )
    return api_client


class FlareAPI(AuthBase):
    def __init__(
        self,
        *,
        api_key: str,
        tenant_id: Optional[int] = None,
        logger: Logger,
    ) -> None:
        self.flare_client = get_flare_api_client(
            api_key=api_key,
            tenant_id=tenant_id,
        )
        self.logger = logger

    def fetch_feed_events(
        self,
        *,
        next: Optional[str] = None,
        start_date: Optional[datetime] = None,
        ingest_full_event_data: bool,
        severities: list[str],
        source_types: list[str],
    ) -> Iterator[tuple[dict, str]]:
        for response in self._fetch_event_feed_metadata(
            next=next,
            start_date=start_date,
            severities=severities,
            source_types=source_types,
        ):
            event_feed = response.json()
            self.logger.debug(event_feed)
            next_token = event_feed["next"]
            for event in event_feed["items"]:
                try:
                    if ingest_full_event_data:
                        event = self._fetch_full_event_from_uid(
                            uid=event["metadata"]["uid"]
                        )
                        time.sleep(1)  # Don't hit rate limit
                except:
                    # There is already logging in the _fetch_full_event_from_uid
                    # we want to continue getting the other events even if one fails.
                    pass
                finally:
                    yield (event, next_token)

    def _fetch_event_feed_metadata(
        self,
        *,
        next: Optional[str] = None,
        start_date: Optional[datetime] = None,
        severities: list[str],
        source_types: list[str],
    ) -> Iterator[requests.Response]:
        data: Dict[str, Any] = {
            "from": next if next else None,
            "order": "asc",
            "filters": {
                "materialized_at": {
                    "gte": start_date.isoformat()
                    if start_date
                    else (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
                },
            },
        }

        if len(severities):
            data["severity"] = severities

        if len(source_types):
            data["type"] = source_types

        for response in self.flare_client.scroll(
            method="POST",
            url="/firework/v4/events/tenant/_search",
            json=data,
        ):
            yield response
            # Rate limiting.
            time.sleep(1)

    def _fetch_full_event_from_uid(self, *, uid: str) -> dict:
        number_of_retries = 3
        for current_try in range(number_of_retries):
            try:
                event_response = self.flare_client.get(
                    url=f"/firework/v2/activities/{uid}"
                )
                event_response.raise_for_status()
            except Exception as e:
                time.sleep(1)
                self.logger.info(
                    f"Failed to fetch event {current_try + 1}/{number_of_retries} retries: {e}"
                )
                continue
            return event_response.json()["activity"]
        raise Exception(
            f"failed to fetch full event data for {uid} after {number_of_retries} tries"
        )

    def fetch_api_key_validation(self) -> requests.Response:
        return self.flare_client.get(
            url="/tokens/test",
        )

    def fetch_tenants(self) -> requests.Response:
        return self.flare_client.get(
            url="/firework/v2/me/tenants",
        )

    def fetch_filters_severity(self) -> requests.Response:
        return self.flare_client.get(
            url="/firework/v4/events/filters/severities",
        )

    def fetch_filters_source_type(self) -> requests.Response:
        return self.flare_client.get(
            url="/firework/v4/events/filters/types",
        )
