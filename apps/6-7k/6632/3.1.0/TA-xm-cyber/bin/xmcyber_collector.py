"""Module for collecting and processing data from XM Cyber API."""
import json
import traceback
import import_declare_test    # noqa: F401
from import_declare_test import ta_prefix
from log_helper import setup_logging
from splunklib import modularinput as smi
from xmcyber_client import XMCyberClient
from xmcyber_utils import get_parameters, update_checkpoint, get_checkpoint, get_account
from solnlib.utils import is_true
from xmcyber_constants import (
    CHOKEPOINT_COUNT_SOURCETYPE,
    RISKSCORE_SCENARIO_SOURCETYPE,
    PAGE_SIZE,
    DEVICES_SOURCETYPE,
    PRODUCTS_SOURCETYPE,
    VULNERABILITIES_SOURCETYPE,
    DEVICES_PAGE_SIZE
)
from datetime import datetime, timezone
from time import time
from xmcyber_datetime_validation import DateTimeValidator
from urllib.parse import urlparse, parse_qs


class XMCyberCollector:
    """Collector class for retrieving and processing data from XM Cyber API."""

    def __init__(self, inputs, ew):
        """Initialize the XMCyberCollector.

        Args:
            inputs (dict): A dictionary containing input parameters for the collector.
            event_writer (EventWriter): An object for writing events to Splunk.

        The constructor sets up logging, initializes parameters, and creates an XMCyberClient
        instance for API interactions.
        """
        self.ew = ew
        self.session_key = inputs.metadata["session_key"]
        self.input_name = list(inputs.inputs.keys())[0]
        self.input_item = inputs.inputs[self.input_name]
        self.input_type = self.input_name.split(":")[0]
        self.normalized_input_name = self.input_name.split("/")[-1]
        self.logger = setup_logging(f"{ta_prefix}_{self.input_type}_{self.normalized_input_name}")
        self.parameters = get_parameters(self.input_type, self.input_item)
        self.xm_cyber_account = self.input_item["account"]
        self.account = get_account(self.xm_cyber_account, self.session_key)
        self.base_url = f"{self.account.get('base_url')}"
        self.input_time_id = self.input_item.get("time_id", None)
        self.xm_cyber_client = XMCyberClient(
            self.session_key, self.xm_cyber_account, self.logger, self.normalized_input_name
        )

    def collect_events(self, data_collection_function):
        """
        Collect Data of configured input.

        Args:
            data_collection_function: function of XMCyberClient class managing the API invocations.
        """
        start_time = time()
        count = 0
        try:
            self.check_audit_trail_auth()
            self.logger.info(
                f"input_name={self.normalized_input_name} Starting {self.input_type} data collection."
            )

            if self.input_type == "vrm_data":
                count = self._collect_vrm_data(data_collection_function)
            elif self.input_type == "all_entities":
                count = self._collect_all_entities_merged()
            else:
                count = self._collect_data(data_collection_function)

        except Exception as e:
            self.logger.error(
                f"input_name={self.normalized_input_name} Error occurred during {self.input_type} data collection: {e}"
                f" {traceback.format_exc()}"
            )
        finally:
            end_time = time()
            time_taken = end_time-start_time
            self.logger.info(
                f"input_name={self.normalized_input_name} Finished {self.input_type} data collection. "
                f"Collected total={count} {self.input_type} events in {time_taken} seconds."
            )

    def _collect_device_data(self, data_collection_function, sourcetype):
        """Collect device data."""
        count = 0
        page = self.parameters.get('page', 1)
        total_pages = page
        parameters = self.parameters.copy()
        parameters["pageSize"] = DEVICES_PAGE_SIZE
        while (page is not None and page <= total_pages):
            try:
                response = data_collection_function(parameters)
                total_pages = response.get("paging", {}).get("totalPages")
                page = response.get("paging", {}).get("page")
                event_data = response.get("data", [])
                event_count = len(event_data)

                self.ingest_events_helper(event_data, sourcetype)
                self.logger.debug(
                    f"input_name={self.normalized_input_name} Collected {event_count} events for {self.input_type}."
                )

                count += event_count
                page += 1
                parameters["page"] = page
            except Exception as e:
                self.logger.error(
                    f"input_name={self.normalized_input_name} Error occurred during data collection pagination: {e} "
                    f"page={page} {traceback.format_exc()}"
                )
                # Break the loop and return the count collected so far
                break
        return count

    def _determine_collection_type_and_sourcetype(self, data_collection_function):
        """Determine collection type and sourcetype based on function name."""
        if data_collection_function.original_func_name.endswith("devices"):
            return "devices", DEVICES_SOURCETYPE
        elif data_collection_function.original_func_name.endswith("products"):
            return "products", PRODUCTS_SOURCETYPE
        else:
            return "vulnerabilities", VULNERABILITIES_SOURCETYPE

    def _collect_vrm_data(self, data_collection_function):
        """
        Collect VRM data.

        Args:
            data_collection_function: function of XMCyberClient class managing the API invocations.

        Returns:
            int: Count of collected events.
        """
        collection_type, sourcetype = self._determine_collection_type_and_sourcetype(data_collection_function)

        count = 0
        if collection_type == "devices":
            count = self._collect_device_data(data_collection_function, sourcetype)
        else:
            count = self._collect_cursor_based_data(data_collection_function, collection_type, sourcetype)

        self.logger.debug(
            f"input_name={self.normalized_input_name} Collected {count} events for {self.input_type}."
        )
        return count

    def _collect_cursor_based_data(self, data_collection_function, collection_type, sourcetype):
        """Collect data using cursor-based pagination for non-device VRM data."""
        iter_next_page = True
        count = 0

        try:
            while iter_next_page:
                try:
                    response = data_collection_function(self.parameters)
                    event_data = response.get("data", [])
                    event_meta = response.get("meta", {})
                    meta_next = event_meta.get("next")
                    if meta_next is not None:
                        parsed_url = urlparse(meta_next)
                        cursor_value = parse_qs(parsed_url.query)["cursor"][0]
                        self.parameters["cursor"] = cursor_value
                        iter_next_page = True
                    else:
                        iter_next_page = False
                        if "cursor" in self.parameters:
                            self.parameters.pop("cursor")

                    self.ingest_events_helper(event_data, sourcetype)
                    count += len(event_data)
                except Exception as e:
                    cursor_info = (
                        f"cursor={self.parameters.get('cursor', 'N/A')}"
                        if "cursor" in self.parameters else "cursor=N/A"
                    )
                    self.logger.error(
                        f"input_name={self.normalized_input_name} Error occurred during VRM "
                        f"{collection_type} collection pagination: {e} {cursor_info} {traceback.format_exc()}"
                    )
                    # Break the loop and return the count collected so far
                    iter_next_page = False
        finally:
            # Ensure cursor is cleaned up even if an exception occurs
            if "cursor" in self.parameters:
                self.parameters.pop("cursor")

        return count

    def _collect_data(self, data_collection_function):
        """
        Collect data for non-VRM input types.

        Args:
            data_collection_function: function of XMCyberClient class managing the API invocations.

        Returns:
            int: Count of collected events.
        """
        count = 0
        page = self.parameters.get('page', 1)
        from_timestamp = self.parameters.get('timeId')
        total_pages = page
        to_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + 'Z'
        while (page is not None and page <= total_pages):
            try:
                if self.input_type == "audit_trail":
                    from_timestamp = self.process_audit_trail_params(self.parameters, from_timestamp, to_timestamp)
                    if page == 1:
                        self.logger.info(
                            f"input_name={self.normalized_input_name} Collecting data from {from_timestamp}"
                            f" to {to_timestamp}."
                        )
                response = data_collection_function(self.parameters)
                total_pages = response.get("paging", {}).get("totalPages")
                page = response.get("paging", {}).get("page")
                event_data = response.get("data", [])
                if not isinstance(event_data, list):  # response of security_risk_score returns dictionary
                    event_count = self.risk_score_count(event_data)
                else:
                    event_count = len(event_data)
                self.ingest_events_helper(event_data)
                self.logger.debug(
                    f"input_name={self.normalized_input_name} Collected {event_count} events for {self.input_type}."
                )
                self.update_input_checkpoint(page, total_pages, from_timestamp, to_timestamp)
                count += event_count
                page = self.get_next_page(page, total_pages)
            except Exception as e:
                self.logger.error(
                    f"input_name={self.normalized_input_name} Error occurred during data collection pagination: {e} "
                    f"page={page}, from_timestamp={from_timestamp}, to_timestamp={to_timestamp} "
                    f"{traceback.format_exc()}"
                )
                # Break the loop and return the count collected so far
                break
        return count

    def _extract_compromised_fields(self, entity):
        """Extract required compromised fields from an entity."""
        compromised_fields = {}

        # Extract basic risk fields
        if entity.get("riskScore") is not None:
            compromised_fields["riskScore"] = entity.get("riskScore")
        if entity.get("chokePointScore") is not None:
            compromised_fields["chokePointScore"] = entity.get("chokePointScore")
        if entity.get("affectedCriticalAssetsCount") is not None:
            compromised_fields["affectedCriticalAssetsCount"] = entity.get("affectedCriticalAssetsCount")
        if entity.get("inboundTechniques") is not None:
            compromised_fields["inboundTechniques"] = entity.get("inboundTechniques")
        if entity.get("outboundTechniques") is not None:
            compromised_fields["outboundTechniques"] = entity.get("outboundTechniques")

        if entity.get("xmLabels") is not None:
            compromised_fields["xmLabels"] = entity.get("xmLabels")
        if entity.get("remoteAddress") is not None:
            compromised_fields["remoteAddress"] = entity.get("remoteAddress")
        if entity.get("lastCompromised") is not None:
            compromised_fields["lastCompromised"] = entity.get("lastCompromised")

        # Add asset field if it exists
        if entity.get("source_entity", {}).get("isAsset") is not None:
            compromised_fields["asset"] = entity.get("source_entity", {}).get("isAsset")

        # Add name field if it exists
        if entity.get("source_entity", {}).get("name") is not None:
            compromised_fields["name"] = entity.get("source_entity", {}).get("name")

        return compromised_fields

    def _collect_compromised_entities(self):
        """
        Collect compromised entities and extract required fields.

        Returns:
            dict: Dictionary mapping entityId to compromised fields.
        """
        compromised_data = {}
        # Reset page to 1 for compromised entities collection
        self.parameters['page'] = 1
        self.parameters['pageSize'] = PAGE_SIZE
        page = 1
        total_pages = 1

        self.logger.info(
            f"input_name={self.normalized_input_name} Collecting compromised entities data."
        )

        while (page is not None and page <= total_pages):
            self.parameters['page'] = page
            response = self.xm_cyber_client.get_all_entities(self.parameters)
            total_pages = response.get("paging", {}).get("totalPages")
            page = response.get("paging", {}).get("page")
            event_data = response.get("data", [])

            # Process entities for this page
            page_compromised_data = self._process_entities_page(event_data)
            compromised_data.update(page_compromised_data)

            self.logger.debug(
                f"input_name={self.normalized_input_name} Collected {len(event_data)} compromised entities "
                f"from page {page}."
            )
            # Handle pagination: check if we've reached the last page
            if page is not None and page < total_pages:
                page += 1
                self.parameters['page'] = page
            else:
                page = None

        self.logger.info(
            f"input_name={self.normalized_input_name} Collected {len(compromised_data)} unique compromised entities."
        )
        return compromised_data

    def _process_entities_page(self, event_data):
        """Process entities from a single page and return compromised data."""
        page_data = {}
        for entity in event_data:
            entity_id = entity.get("entityId") or entity.get("id")
            if entity_id:
                compromised_fields = self._extract_compromised_fields(entity)
                if compromised_fields:
                    page_data[entity_id] = compromised_fields
        return page_data

    def _is_entity_compromised(self, entity_data):
        """
        Determine if an entity is compromised based on riskScore or CompromisedRiskScore.

        Checks CompromisedRiskScore first (future-proof), then falls back to riskScore.
        Returns True if severityScore > 0, False otherwise.

        Args:
            entity_data: Dictionary containing entity data with riskScore/CompromisedRiskScore

        Returns:
            bool: True if compromised (severityScore > 0), False otherwise
        """
        # Check CompromisedRiskScore first
        compromised_risk_score = entity_data.get("CompromisedRiskScore")
        if compromised_risk_score and isinstance(compromised_risk_score, dict):
            severity_score = compromised_risk_score.get("severityScore")
            if severity_score is not None and severity_score > 0:
                return True
            else:
                return False

        # Fall back to riskScore
        risk_score = entity_data.get("riskScore")
        if risk_score and isinstance(risk_score, dict):
            severity_score = risk_score.get("severityScore")
            if severity_score is not None and severity_score > 0:
                return True

        return False

    def _convert_xm_labels(self, value):
        """Convert xmLabels from Critical entity format to Inventory entity format."""
        if isinstance(value, dict) and "id" in value and isinstance(value["id"], list):
            return [{"id": label_id} for label_id in value["id"]]
        return value

    def _merge_compromised_fields(self, merged_entity, compromised_entity):
        """Merge fields from compromised entity into merged entity."""
        restricted_fields = {"xmLabels", "remoteAddress", "lastCompromised", "affectedCriticalAssetsCount"}

        for field, value in compromised_entity.items():
            # Only add if field doesn't exist in inventory entity
            if field in restricted_fields:
                if field not in merged_entity:
                    # Convert xmLabels format from {"id": ["a", "b"]} to [{"id": "a"}, {"id": "b"}]
                    if field == "xmLabels":
                        merged_entity[field] = self._convert_xm_labels(value)
                    else:
                        merged_entity[field] = value
            elif field not in merged_entity:
                merged_entity[field] = value

    def _process_inventory_entities_page(self, event_data, compromised_data):
        """Process inventory entities from a single page and return merged entities."""
        merged_entities = []
        for inventory_entity in event_data:
            # Extract entityId from entityDetails.id or fallback to top-level id
            entity_details = inventory_entity.get("entityDetails", {})
            entity_id = entity_details.get("id") or inventory_entity.get("id")

            if not entity_id:
                self.logger.warning(
                    f"input_name={self.normalized_input_name} Skipping entity without id: {inventory_entity}"
                )
                continue

            # Add entityId field for consistency
            merged_entity = inventory_entity.copy()
            merged_entity["entityId"] = entity_id

            # Merge compromised fields if available
            if entity_id in compromised_data:
                self._merge_compromised_fields(merged_entity, compromised_data[entity_id])
                compromised_data.pop(entity_id)

            # Ensure asset field is always present
            if "asset" not in merged_entity:
                merged_entity["asset"] = False

            # Determine compromised status based on riskScore/CompromisedRiskScore
            merged_entity["compromised"] = self._is_entity_compromised(merged_entity)

            merged_entities.append(merged_entity)

        return merged_entities

    def _collect_all_entities_merged(self):
        """
        Collect inventory entities, merge with compromised data, and ingest.

        Returns:
            int: Count of collected events.
        """
        compromised_data = self._collect_compromised_entities()

        self.parameters['page'] = 1

        count = 0
        page = self.parameters.get('page', 1)
        total_pages = page

        self.logger.info(
            f"input_name={self.normalized_input_name} Collecting inventory entities"
        )

        while (page is not None and page <= total_pages):
            try:
                response = self.xm_cyber_client.get_all_inventory_entities(self.parameters)
                total_pages = response.get("paging", {}).get("totalPages")
                page = response.get("paging", {}).get("page")
                event_data = response.get("data", [])

                merged_entities = self._process_inventory_entities_page(event_data, compromised_data)

                # Ingest merged entities
                self.ingest_events_helper(merged_entities)
                self.logger.debug(
                    f"input_name={self.normalized_input_name} Collected and merged {len(merged_entities)} "
                    f"entities from page {page}."
                )
                count += len(merged_entities)
                # Handle pagination: check if we've reached the last page
                if page is not None and page < total_pages:
                    page += 1
                    self.parameters['page'] = page
                else:
                    page = None
            except Exception as e:
                self.logger.error(
                    f"input_name={self.normalized_input_name} Error occurred during all entities "
                    f"collection pagination: {e} page={page} {traceback.format_exc()}"
                )
                # Break the loop and return the count collected so far
                break

        if compromised_data:
            dropped_ids = list(compromised_data.keys())
            self.logger.warning(
                f"input_name={self.normalized_input_name} The following critical entity IDs could not be mapped to "
                f"any inventory entity and will be dropped: {dropped_ids}"
            )

        # Step 4: Handle chokepoint stats (existing behavior)
        chokepoint_count = self.fetch_ingest_chokepoint_stats()
        count = count + chokepoint_count

        # Reset page parameter to prevent stale state affecting subsequent calls
        self.parameters['page'] = 1

        self.logger.info(
            f"input_name={self.normalized_input_name} Completed merged entities collection. "
            f"Total entities ingested: {count}."
        )
        return count

    def risk_score_count(self, event_data):
        """
        Calculate event counts that will be ingested based on configurations.

        Args:
            event_data: Collection of Events to be ingested into Splunk.
        """
        if self.input_type == "security_risk_score" and is_true(self.input_item.get('ingest_scenarios')):
            return 1 + len(event_data.get("scenarios"))
        elif self.input_type == "security_risk_score":
            return 1

    def ingest_events_helper(self, events, sourcetype=None):
        """
        Preprocess events and ingest them into splunk.

        Args:
            events: Collection of Events to be ingested into Splunk.
        """
        if isinstance(events, dict):  # response of security_risk_score returns dictionary
            if self.input_type == "security_risk_score":
                scenarios = events.pop('scenarios')
                self.ingest_risk_score_scenarios(scenarios)
                self.ingest_events(events)
        else:
            for event in events:
                if self.input_type == "findings_exposures":
                    event["time_id"] = self.input_time_id
                self.ingest_events(event, sourcetype=sourcetype)

    def ingest_events(self, event, index=None, sourcetype=None):
        """
        Ingest events into Splunk.

        Args:
            event: Single event to ingest into Splunk.
            index: Index to collect event into.
            sourcetype: The sourcetype to parse data accordingly.
        """
        event["tenant"] = self.base_url

        event = smi.Event(
            data=json.dumps(event, ensure_ascii=False),
            stanza=self.input_name,
            index=index,
            sourcetype=sourcetype
        )
        self.ew.write_event(event)

    def process_audit_trail_params(self, parameters, from_timestamp, to_timestamp):
        """
        Process audit trail parameters.

        Args:
            parameters: Audit trail parameters.
            from_timestamp: The timestamp to collect audit data from.

        Returns:
            Audit Trail request parameters.
        """
        ckpt_value = get_checkpoint(self.session_key, self.normalized_input_name, self.logger)
        page = None
        if ckpt_value is None:
            dt_validator = DateTimeValidator()
            is_valid = dt_validator.validate(from_timestamp, None)
            if not is_valid:
                raise Exception(dt_validator.msg)
            page = parameters.get('page')
        elif ckpt_value.get("page", None) is not None:
            page = ckpt_value.get("page")
            from_timestamp = ckpt_value.get("last_time")
        else:
            from_timestamp = ckpt_value.get("last_time")
            page = parameters.get('page')
        params = {
            'filter': json.dumps({
                'timestamp': {
                    '$gt': from_timestamp,
                    '$lte': to_timestamp
                }
            }),
            'page': page,
            'pageSize': PAGE_SIZE,
            'sort': "timestamp",
        }
        self.parameters = params
        return from_timestamp

    def update_input_checkpoint(self, page, total_pages, from_timestamp, to_timestamp):
        """
        Update the checkpoint for Audit trail data.

        Args:
            event_data: data from API response.
            page: current page.
            total_page: Total number of pages
        """
        if self.input_type == "audit_trail" and page == total_pages:
            ckpt_value = {"last_time": to_timestamp}
            update_checkpoint(self.session_key, self.normalized_input_name, ckpt_value, self.logger)
        elif self.input_type == "audit_trail":
            ckpt_value = {"last_time": from_timestamp, "page": page+1}
            update_checkpoint(self.session_key, self.normalized_input_name, ckpt_value, self.logger)

    def get_next_page(self, page, total_pages):
        """
        Get next page number for paginated data.

        Args:
            page: Current page.
            total_pages: Total pages from API response.

        Returns:
            Next sequential page.
        """
        if page is None or total_pages is None:
            page = None
        else:
            page += 1
            self.parameters["page"] = page
        return page

    def fetch_ingest_chokepoint_stats(self):
        """
        Fetch the checkpoint Stats.

        Returns:
            Events count.
        """
        if self.input_type == "all_entities" and is_true(self.input_item.get("ingest_chokepoints")):
            self.logger.info(
                f"input_name={self.normalized_input_name} Collecting checkpoint stats."
            )
            response = self.xm_cyber_client.get_chokepoint_stats()
            choke_point = response.get("paging").get("total")
            event_data = {"totalChokepoint": choke_point}
            self.ingest_events(
                event_data,
                index=self.input_item.get("index"),
                sourcetype=CHOKEPOINT_COUNT_SOURCETYPE
            )
            self.logger.info(
                f"input_name={self.normalized_input_name} Completed checkpoint stats."
            )
            return 1
        return 0

    def ingest_risk_score_scenarios(self, scenarios):
        """
        Ingest Risk score scenarios data.

        Args:
            Risk score event scenarios.
        """
        if is_true(self.input_item.get('ingest_scenarios')):
            for scenario in scenarios:
                self.ingest_events(
                    scenario,
                    index=self.input_item.get("index"),
                    sourcetype=RISKSCORE_SCENARIO_SOURCETYPE
                )
            self.logger.info(
                f"input_name={self.normalized_input_name} Collected {len(scenarios)} Risk score scenario events."
            )

    def check_audit_trail_auth(self):
        """
        Check if audit trail input is configured with basic Auth.

        Returns:
            Exception
        """
        if self.input_type == "audit_trail" and self.account.get("auth_type") == "basic":
            self.logger.error(
                f"input_name={self.normalized_input_name} Audit Trail input with account {self.xm_cyber_account} "
                f" using basic authentication is not supported."
            )
            raise Exception(
                f"input_name={self.normalized_input_name} Audit Trail input with account {self.xm_cyber_account} "
                f" using basic authentication is not supported."
            )
