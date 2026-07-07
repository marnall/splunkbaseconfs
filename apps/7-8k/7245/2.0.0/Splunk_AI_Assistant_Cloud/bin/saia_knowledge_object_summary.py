# Copyright 2026 Cisco, Inc.
import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Sequence

import splunk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from spl_gen.remote.factory import SaiaApiFactory
from spl_gen.utils import deterministic_hash, get_app_version, log_kwargs
from spl_gen.utils.log import add_log_extra_metadata, setup_logger
from spl_gen.utils.modinput.fields import BooleanField
from spl_gen.utils.modinput.json_modinput import JsonModularInput
from spl_gen.utils.requests import OutputMode, send_request
from splunklib.binding import handler
from splunklib.client import connect
from splunklib.searchcommands import environment

try:
    from .xml_nested_html_udf_dashboard_utils import enrich_dashboard_entries
except ImportError:
    from xml_nested_html_udf_dashboard_utils import enrich_dashboard_entries

SECONDS_IN_DAY = 86400
DEFAULT_MAX_SEARCH_RANGE_SECONDS = 7 * SECONDS_IN_DAY
D_MAXIMUM_OBJECTS_SEARCH_COUNT = 5000000
DEFAULT_PAGINATION_PAGE_SIZE = 100

SA_CONF_URL = f"{splunk.rest.makeSplunkdUri()}servicesNS/nobody/Splunk_AI_Assistant_Cloud/configs/conf-saiaknowledgeobjsummary"

logger = setup_logger("saia_knowledge_object_summary_modinput")
LOGGER_METADATA_TAG = "saia_knowledge_object_summary_modinput"


SAIASettings = Dict[str, int]
SAIAStatus = Dict[str, int]
SAIASearchParams = Dict[str, int]
SAIAConfig = Dict[str, Dict[str, int]]
SplunkEntryPayload = Dict[str, List[Dict[str, Any]]]
DashboardsPayload = Dict[str, SplunkEntryPayload]
ParsedKnowledgeObjectPayload = Dict[str, List[Dict[str, Any]]]


class SAIAKnowledgeObjectSummaryModularInputConfig:
    """
    A class responsible for managing the Security Assistant mod_input configuration.
    """

    def __init__(self, session_key: str, this_logger: logging.Logger = logger):
        """Load and cache the modular input configuration for this run."""
        self.session_key = session_key
        self.logger = this_logger
        config_data = self._retrieve_sa_config_data()
        config = self._parse_sa_config_data(config_data)
        self.settings = config["settings"]
        self.status = config["status"]
        self.search_params = config["search_params"]

    def _retrieve_sa_config_data(self) -> Dict[str, Any]:
        """Fetch raw modular input configuration from the Splunk conf endpoint."""
        self.logger.debug(f"Fetching SA configuration data from {SA_CONF_URL}")
        return send_request(
            url=SA_CONF_URL,
            method="get",
            headers={
                "Authorization": f"Splunk {self.session_key}",
                "Accept": "application/json",
            },
            output_mode=OutputMode.PARSE_JSON,
        )

    def _update_sa_config_data(self) -> Dict[str, Any]:
        """Persist the current status block back to the Splunk conf endpoint."""
        self.logger.debug(f"Updating SA configuration data at {SA_CONF_URL}/status")
        return send_request(
            url=f"{SA_CONF_URL}/status",
            method="post",
            data={
                "last_context_update_timestamp": self.status[
                    "last_context_update_timestamp"
                ],
            },
            headers={
                "Authorization": f"Splunk {self.session_key}",
                "Accept": "application/json",
            },
            output_mode=OutputMode.PARSE_JSON,
        )

    def _parse_sa_config_data(self, config_data: Dict[str, Any]) -> SAIAConfig:
        """Convert raw conf entries into typed settings, status, and search params."""
        self.logger.debug(
            "Parsing configuration entries into structured settings and status"
        )
        config: SAIAConfig = {
            "settings": {
                "context_update_interval_seconds": 0,
                "max_search_range_seconds": DEFAULT_MAX_SEARCH_RANGE_SECONDS,
            },
            "status": {
                "last_context_update_timestamp": 0,
            },
            "search_params": {
                "maximum_objects_search_count": D_MAXIMUM_OBJECTS_SEARCH_COUNT,
            },
        }
        for entry in config_data["entry"]:
            content = entry["content"]
            if entry["name"] == "settings":
                config["settings"] = {
                    "context_update_interval_seconds": int(
                        content["context_update_interval_seconds"].strip() or 0
                    ),
                    "max_search_range_seconds": int(
                        content["max_search_range_seconds"].strip()
                        or DEFAULT_MAX_SEARCH_RANGE_SECONDS
                    )
                    or DEFAULT_MAX_SEARCH_RANGE_SECONDS,
                }
            elif entry["name"] == "status":
                config["status"] = {
                    "last_context_update_timestamp": int(
                        content["last_context_update_timestamp"].strip() or 0
                    ),
                }
            elif entry["name"] == "search_params":
                config["search_params"] = {
                    "maximum_objects_search_count": int(
                        content["maximum_objects_search_count"].strip()
                        or D_MAXIMUM_OBJECTS_SEARCH_COUNT
                    )
                }

        return config

    def update(
        self,
        *,
        last_context_update_timestamp: Optional[int] = None,
    ) -> None:
        """Update cached status values and write them to persistent configuration."""
        if last_context_update_timestamp is not None:
            self.status["last_context_update_timestamp"] = last_context_update_timestamp
        try:
            self._update_sa_config_data()
        except Exception as e:
            self.logger.exception("Failed to update SA configuration data: %s", e)

    def get_search_params(self) -> SAIASearchParams:
        """Return search parameters used by the knowledge object collector."""
        return self.search_params

    def is_context_update_due(self) -> bool:
        """Return whether enough time has elapsed to refresh context data."""
        return (
            int(time.time()) - self.status["last_context_update_timestamp"]
            >= self.settings["context_update_interval_seconds"]
        )

    def __str__(self) -> str:
        """Return a compact debug string for configuration state."""
        return f"settings={self.settings}, status={self.status}, search_params={self.search_params}"


class SAIAKnowledgeObjectSummaryModularInput(JsonModularInput):
    def __init__(self, this_logger: logging.Logger = logger):
        """Initialize modular input metadata and runtime defaults."""
        environment.app_root = os.path.join(os.path.dirname(__file__), "..")
        scheme_args = {
            "title": "Splunk AI Assistant Knowledge Object Summary Modular Input",
            "description": "Collects knowledge object summary context for Ai search",
            "use_external_validation": "true",
            "streaming_mode": "json",
            "use_single_instance": "true",
            "supported_on_cloud": "true",
            "supported_on_onprem": "true",
            "supported_on_fedramp": "false",
        }
        self._chunk_count = 0
        self.search_params: SAIASearchParams = {
            "maximum_objects_search_count": D_MAXIMUM_OBJECTS_SEARCH_COUNT
        }
        self._dashboard_studio_example_bundle_base_url: Optional[str] = None
        args = [
            BooleanField(
                "debug",
                "Debug",
                "If true, debug logging is enabled.",
                required_on_create=False,
            )
        ]
        super().__init__(scheme_args, args, this_logger)

    def _connect_service(self, user: str) -> Any:
        """Create a Splunk SDK service connection using the modular input token."""
        self.logger.info("Connecting to Splunkd")
        return connect(
            token=self._input_config.session_key,
            handler=handler(timeout=60),
            host="127.0.0.1",
            app="-",
            owner="-",
            retries=2,
        )

    def _submit_metadata(
        self,
        *,
        submit_callable: Callable[..., Any],
        kind: str,
        payload: ParsedKnowledgeObjectPayload,
        request_id: str,
        app_version: str,
        run_start: float,
    ) -> None:
        """Submit parsed knowledge object metadata and log request telemetry."""
        run_end = time.time()
        self.logger.info(
            log_kwargs(
                message="submitting data", apply_time=round(run_end - run_start, 5)
            )
        )
        field_data = payload["data"]
        self.logger.info(
            log_kwargs(
                request_id=request_id,
                anticipated_entry_count=len(field_data),
                saia_app_version=app_version,
            )
        )
        try:
            submit_callable(field_data=field_data, request_id=request_id)
        except Exception as exc:
            self.logger.exception(
                "Error updating %s knowledge object metadata: %s", kind, exc
            )

    def _fetch_paginated_entries(
        self,
        *,
        service: Any,
        endpoint: str,
        page_size: int = DEFAULT_PAGINATION_PAGE_SIZE,
        **request_params: Any,
    ) -> List[Dict[str, Any]]:
        """Fetch all entries from a paginated endpoint using count/offset."""
        if page_size <= 0:
            raise ValueError("page_size must be positive")

        max_objects = self.search_params.get(
            "maximum_objects_search_count", D_MAXIMUM_OBJECTS_SEARCH_COUNT
        )
        if max_objects <= 0:
            max_objects = D_MAXIMUM_OBJECTS_SEARCH_COUNT

        all_entries: List[Dict[str, Any]] = []
        previous_page_entries: Optional[List[Dict[str, Any]]] = None
        offset = 0

        while True:
            remaining = max_objects - len(all_entries)
            if remaining <= 0:
                self.logger.warning(
                    "Reached maximum_objects_search_count=%s for endpoint=%s",
                    max_objects,
                    endpoint,
                )
                break

            requested_count = min(page_size, remaining)
            response = service.get(
                endpoint,
                output_mode="json",
                sort_mode="auto",
                count=requested_count,
                offset=offset,
                **request_params,
            )
            payload = json.loads(response.body.read())
            entries = payload.get("entry", [])

            if not isinstance(entries, list):
                self.logger.warning(
                    "Unexpected payload for endpoint=%s at offset=%s: entry is %s",
                    endpoint,
                    offset,
                    type(entries),
                )
                break
            if not entries:
                break
            if previous_page_entries is not None and entries == previous_page_entries:
                self.logger.warning(
                    "Pagination appears stuck for endpoint=%s at offset=%s, stopping to avoid duplicate loop",
                    endpoint,
                    offset,
                )
                break

            all_entries.extend(entries)
            page_entry_count = len(entries)
            self.logger.debug(
                "Fetched %s entries from endpoint=%s offset=%s",
                page_entry_count,
                endpoint,
                offset,
            )
            if page_entry_count < requested_count:
                break

            offset += page_entry_count
            previous_page_entries = entries

        return all_entries

    def _get_datamodels_metadata(self, service: Any, user: str) -> SplunkEntryPayload:
        """Fetch raw datamodel metadata entries from Splunk."""
        try:
            service = self._connect_service(user)
            entries = self._fetch_paginated_entries(
                service=service,
                endpoint="datamodel/model",
                page_size=DEFAULT_PAGINATION_PAGE_SIZE,
                concise="true",
            )
            self.logger.info(
                "Fetching data from datamodel/model after formatting ...%s",
                len(entries),
            )
            return {"entry": entries}
        except Exception as e:
            self.logger.exception("Error fetching datamodels metadata: %s", e)
            return {"entry": []}

    def _get_dashboards_metadata(self, service: Any, user: str) -> DashboardsPayload:
        """Fetch raw dashboard metadata entries from Splunk."""
        try:
            service = self._connect_service(user)
            search_filter = '((isDashboard=1 AND (rootNode="dashboard" OR rootNode="form" OR rootNode="view" OR rootNode="html") AND isVisible=1))'
            entries = self._fetch_paginated_entries(
                service=service,
                endpoint="data/ui/views",
                page_size=DEFAULT_PAGINATION_PAGE_SIZE,
                search=search_filter,
            )
            (
                entries,
                self._dashboard_studio_example_bundle_base_url,
            ) = enrich_dashboard_entries(
                entries,
                service=service,
                logger=self.logger,
                session_key=getattr(
                    getattr(self, "_input_config", None), "session_key", None
                ),
                send_request_fn=send_request,
                output_mode=OutputMode.RETURN_RAW,
                splunkd_uri=splunk.rest.makeSplunkdUri(),
                cached_bundle_base_url=self._dashboard_studio_example_bundle_base_url,
            )
            self.logger.info(
                "Fetching data from data/ui/views after formatting ...%s",
                len(entries),
            )
            return {"data": {"entry": entries}}
        except Exception as e:
            self.logger.exception("Error fetching dashboards metadata: %s", e)
            return {"data": {"entry": []}}

    def parse_dashboards(
        self, raw_data: DashboardsPayload
    ) -> ParsedKnowledgeObjectPayload:
        """Normalize dashboard entries to the payload schema expected by the API."""
        saved_dashboards = []
        for i in raw_data["data"]["entry"]:
            temp = dict(i)
            temp["owner"] = i["acl"]["owner"]
            temp["sharing"] = i["acl"]["sharing"]
            saved_dashboards.append(temp)
        return {"data": saved_dashboards}

    def _get_saved_search_metadata(self, service: Any, user: str) -> SplunkEntryPayload:
        """Fetch saved search metadata entries from Splunk."""
        try:
            service = self._connect_service(user)
            response = service.get(
                "saved/searches",
                output_mode="json",
                sort_mode="auto",
                count=3000,
                # search="is_visible=1"
            )
            self.logger.info(f"Fetching data from saved/searches...{response}")
            payload = json.loads(response.body.read())
            self.logger.info(
                f"Fetching data from saved/searches after formatting ...{type(payload)}"
            )
            return {"entry": payload.get("entry", [])}
        except Exception as e:
            self.logger.exception("Error fetching reports metadata: %s", e)
            return {"entry": []}

    def parse_data_models(
        self, raw_data: SplunkEntryPayload
    ) -> ParsedKnowledgeObjectPayload:
        """Normalize datamodel entries to the payload schema expected by the API."""
        saved_datamodels = []
        for i in raw_data["entry"]:
            temp = {}
            temp["name"] = i["name"]
            temp["author"] = i["author"]
            temp["owner"] = i["acl"]["owner"]
            temp["description"] = i["content"].get(
                "description", ""
            )  # Commented out as in original
            temp["disabled"] = i["content"].get("disabled", False)
            temp["title"] = i["content"].get("displayName", "")
            dataset_type = i["content"].get("dataset.type")
            temp["type"] = (
                dataset_type
                if dataset_type not in (None, "")
                else i["content"].get("eai:type", "")
            )
            temp["app"] = i["acl"].get("app", None)
            temp["link"] = i["id"]
            temp["sharing"] = i["acl"]["sharing"]
            saved_datamodels.append(temp)
        return {"data": saved_datamodels}

    def _get_reports_metadata(self, service: Any, user: str) -> SplunkEntryPayload:
        """Fetch report metadata entries from Splunk saved searches."""
        try:
            service = self._connect_service(user)
            search_filter = (
                'NOT ((is_scheduled=1 AND (alert_type!=always OR alert.track=1 OR (dispatch.earliest_time="rt*" AND dispatch.latest_time="rt*" AND actions="*" AND actions!=""))) ) '
                "AND is_visible=1"
            )

            entries = self._fetch_paginated_entries(
                service=service,
                endpoint="saved/searches",
                page_size=DEFAULT_PAGINATION_PAGE_SIZE,
                search=search_filter,
            )
            self.logger.info(
                f"Fetching reports data from saved/searches after formatting ...{len(entries)}"
            )
            return {"entry": entries}
        except Exception as e:
            self.logger.exception("Error fetching reports metadata: %s", e)
            return {"entry": []}

    def _get_alerts_metadata(self, service: Any, user: str) -> SplunkEntryPayload:
        """Fetch alert metadata entries from Splunk saved searches."""
        try:
            service = self._connect_service(user)
            search_filter = (
                '((is_scheduled=1 AND (alert_type!=always OR alert.track=1 OR (dispatch.earliest_time="rt*" AND dispatch.latest_time="rt*" AND actions="*" AND actions!=""))) ) '
                "AND is_visible=1"
            )
            entries = self._fetch_paginated_entries(
                service=service,
                endpoint="saved/searches",
                page_size=DEFAULT_PAGINATION_PAGE_SIZE,
                search=search_filter,
            )
            self.logger.info(
                f"Fetching alerts data from saved/searches after formatting ...{len(entries)}"
            )
            return {"entry": entries}
        except Exception as e:
            self.logger.exception("Error fetching alerts metadata: %s", e)
            return {"entry": []}

    def parse_reports_and_alerts_metadata(
        self, raw_data: SplunkEntryPayload
    ) -> ParsedKnowledgeObjectPayload:
        """Normalize saved-search entries for report and alert metadata submission."""
        # Parse saved searches
        reports = []

        for i in raw_data["entry"]:
            temp = {}
            temp["title"] = i["name"]
            temp["author"] = i["author"]
            temp["owner"] = i["acl"]["owner"]
            temp["alert_threshold"] = i["content"].get("alert_threshold", None)
            temp["alert_type"] = i["content"].get("alert_type", None)
            temp["alert_condition"] = i["content"].get("alert_condition", None)
            temp["is_visible"] = i["content"].get("is_visible", None)
            temp["is_scheduled"] = i["content"].get("is_scheduled", None)
            temp["actions"] = i["content"].get("actions", None)
            temp["alert.track"] = i["content"].get("alert.track", None)
            temp["dispatch.earliest_time"] = i["content"].get(
                "dispatch.earliest_time", None
            )
            temp["dispatch.latest_time"] = i["content"].get(
                "dispatch.latest_time", None
            )
            temp["query"] = i["content"].get("search", None)
            temp["app"] = i["acl"].get("app", None)
            temp["link"] = i["id"]
            temp["sharing"] = i["acl"]["sharing"]
            reports.append(temp)
        return {"data": reports}

    def update_knowledge_objects(self, *, earliest: int = -1, latest: int = -1) -> None:
        """Collect, parse, and submit all supported knowledge object metadata."""
        request_id = str(uuid.uuid4())
        run_start = time.time()
        user = "splunk-system-user"
        hashed_user = deterministic_hash(user)

        for kind in ("reports", "alerts", "datamodels", "dashboards"):
            self.logger.info("Updating %s knowledge objects metadata", kind)
            try:
                service = self._connect_service(user)
                app_version = get_app_version(service)
                api = SaiaApiFactory.from_agent_mode_setting(
                    service,
                    service,
                    user,
                    None,
                    hashed_user,
                )
                payload: ParsedKnowledgeObjectPayload = {"data": []}
                if kind == "reports":
                    # payload = final_data["reports"]
                    submitter = api.submit_reports_knowledge_object_metadata
                    reports_raw_data = self._get_reports_metadata(service, user)
                    payload = self.parse_reports_and_alerts_metadata(reports_raw_data)

                    self.logger.info(f"len of reports payload: {len(payload['data'])}")
                elif kind == "alerts":
                    submitter = api.submit_alerts_knowledge_object_metadata
                    alerts_raw_data = self._get_alerts_metadata(service, user)
                    # payload = final_data["alerts"]
                    payload = self.parse_reports_and_alerts_metadata(alerts_raw_data)
                    self.logger.info(f"len of alerts payload: {len(payload['data'])}")
                elif kind == "dashboards":
                    submitter = api.submit_dashboards_knowledge_object_metadata
                    dashboards_raw_data = self._get_dashboards_metadata(service, user)
                    payload = self.parse_dashboards(dashboards_raw_data)
                    self.logger.info(
                        f"len of dashboards payload: {len(payload['data'])}"
                    )
                elif kind == "datamodels":
                    submitter = api.submit_datamodels_knowledge_object_metadata
                    datamodels_raw_data = self._get_datamodels_metadata(service, user)
                    payload = self.parse_data_models(datamodels_raw_data)
                    self.logger.info(
                        f"len of datamodels payload: {len(payload['data'])}"
                    )

                self._submit_metadata(
                    submit_callable=submitter,
                    kind=kind,
                    payload=payload,
                    request_id=request_id,
                    app_version=app_version,
                    run_start=run_start,
                )
            except Exception as e:
                self.logger.exception(
                    "Error in while submitting data %s knowledge object metadata: %s",
                    kind,
                    e,
                )

    def run(self, stanza: Sequence[Dict[str, Any]]) -> None:
        """Entry point invoked by Splunk to execute one modular input cycle."""
        self.logger.info("Starting Knowledge objects Summary Modular Input")
        self.logger.setLevel(self.get_log_level(stanza))
        self.logger.info(f"Input configuration: {self._input_config}, stanza: {stanza}")
        config = SAIAKnowledgeObjectSummaryModularInputConfig(
            self._input_config.session_key, self.logger
        )
        self.search_params = config.get_search_params()
        if config.is_context_update_due():
            # for POC, setting max lookback to be 24 hours ago
            latest = int(time.time())
            try:
                self.logger.info("updating Knowledge objects metadata")
                self.update_knowledge_objects()
            except Exception as e:
                self.logger.exception("Error in updating knowledge context: %s", e)
            else:
                config.update(last_context_update_timestamp=latest)
            self._chunk_count += 1


if __name__ == "__main__":
    add_log_extra_metadata("tag", LOGGER_METADATA_TAG)
    add_log_extra_metadata("context", "modinput")
    mod_input = SAIAKnowledgeObjectSummaryModularInput()
    mod_input.execute()
