import json
import os
import sys
import time
import traceback

import import_declare_test  # noqa: F401
import kvstore
import splunklib.client as splunkClient
from dataminr_utils import read_conf_file
from log_helper import setup_logging
from splunklib import results
from splunklib.searchcommands import Configuration, EventingCommand, dispatch

logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0].lower())

REDIRECT_TO_LOG_FILE_MSG = "See {} for more details.".format(logger.name)


@Configuration()
class DataminrUpdateAlerts(EventingCommand):
    """Dataminr update alerts custom command - Updates alerts with exact schema."""

    def __init__(self):
        super(DataminrUpdateAlerts, self).__init__()
        self.alert_mgr = None
        self.start_time = None
        self.updated_alerts = []

    def initialize(self):
        """Initialize the alert manager and other resources."""
        self.alert_mgr = kvstore.AlertManager(self.service)
        self.serviceobj = splunkClient.connect(token=self.search_results_info.auth_token, owner="nobody")
        self.index_detail = read_conf_file(self.service.token, "eventtypes", "dataminr_index")
        self.index_query = self.index_detail["search"]

    def parse_event_data(self, event_data, alert_id):
        """Parse event data following the same logic as the JavaScript upsertAlert function."""
        try:
            # Extract headline
            headline = event_data.get("headline", "No headline available")

            # Extract alert timestamp
            alert_timestamp = event_data.get(
                "alertTimestamp", event_data.get("alert_timestamp", "No alert timestamp available")
            )

            # Extract intel agent assessment points
            assessment_points = []
            intel_agents = event_data.get("intelAgents", event_data.get("intelagent", []))

            if intel_agents and isinstance(intel_agents, list) and len(intel_agents) > 0:
                first_agent = intel_agents[0]
                if isinstance(first_agent, dict) and "summary" in first_agent:
                    summary_array = first_agent["summary"]
                    if isinstance(summary_array, list):
                        for item in summary_array:
                            if isinstance(item, dict):
                                title = item.get("title", "")
                                item_type = item.get("type", [])
                                content = item.get("content", [])

                                if title and item_type and content and len(content) > 0:
                                    # Join types with comma and space
                                    type_str = ", ".join(item_type) if isinstance(item_type, list) else str(item_type)
                                    formatted_point = f"{title} ({type_str}): {content[0]}"
                                    assessment_points.append(formatted_point)

            # If no structured intel agents found, try to parse existing intelagent field
            if not assessment_points and "intelagent" in event_data:
                intelagent_data = event_data["intelagent"]
                if isinstance(intelagent_data, list):
                    assessment_points = intelagent_data
                elif isinstance(intelagent_data, str):
                    # Try to split by common delimiters
                    if "|" in intelagent_data:
                        assessment_points = intelagent_data.split("|")
                    elif "," in intelagent_data:
                        assessment_points = [item.strip() for item in intelagent_data.split(",")]
                    else:
                        assessment_points = [intelagent_data]

            # Extract LiveBrief summary
            livebrief_summary = None
            if "liveBrief" in event_data:
                live_brief = event_data["liveBrief"]
                if isinstance(live_brief, list) and len(live_brief) > 0:
                    first_brief = live_brief[0]
                    if isinstance(first_brief, dict) and "summary" in first_brief:
                        livebrief_summary = first_brief["summary"]
                elif isinstance(live_brief, dict) and "summary" in live_brief:
                    livebrief_summary = live_brief["summary"]
                elif isinstance(live_brief, str):
                    livebrief_summary = live_brief

            # Extract discovered entities
            discovered_entities = []
            if intel_agents and isinstance(intel_agents, list):
                for agent in intel_agents:
                    if isinstance(agent, dict) and "discoveredEntities" in agent:
                        discovered_entities_list = agent["discoveredEntities"]
                        if isinstance(discovered_entities_list, list):
                            for entity in discovered_entities_list:
                                if isinstance(entity, dict):
                                    if "name" in entity and entity["name"]:
                                        discovered_entities.append(entity["name"])
                                    elif "ip" in entity and entity["ip"]:
                                        discovered_entities.append(entity["ip"])
                                elif isinstance(entity, str):
                                    discovered_entities.append(entity)

            # If no structured discovered entities found, try existing field
            if not discovered_entities and "discoveredentities" in event_data:
                entities_data = event_data["discoveredentities"]
                if isinstance(entities_data, list):
                    discovered_entities = entities_data
                elif isinstance(entities_data, str):
                    if "|" in entities_data:
                        discovered_entities = entities_data.split("|")
                    elif "," in entities_data:
                        discovered_entities = [item.strip() for item in entities_data.split(",")]
                    else:
                        discovered_entities = [entities_data] if entities_data else []

            # Extract watchlist
            watchlist = []
            lists_matched = event_data.get("listsMatched", event_data.get("watchlist", []))

            if isinstance(lists_matched, list):
                for list_item in lists_matched:
                    if isinstance(list_item, dict) and "name" in list_item:
                        watchlist.append(list_item["name"])
                    elif isinstance(list_item, str):
                        watchlist.append(list_item)
            elif isinstance(lists_matched, str):
                if "|" in lists_matched:
                    watchlist = lists_matched.split("|")
                elif "," in lists_matched:
                    watchlist = [item.strip() for item in lists_matched.split(",")]
                else:
                    watchlist = [lists_matched] if lists_matched else []

            # Create the parsed alert record
            parsed_record = {
                "alert_id": alert_id,
                "headline": headline,
                "alert_timestamp": alert_timestamp,
                "intelagent": assessment_points,
                "livebrief": livebrief_summary,  # Add the livebrief field
                "discoveredentities": discovered_entities,
                "watchlist": watchlist,
                "_user": event_data.get("_user", "nobody"),
                "_key": alert_id,
            }

            logger.debug(
                f"Parsed event data for alert {alert_id}: headline='{headline[:50]}...', "
                f"intelagent_count={len(assessment_points)}, entities_count={len(discovered_entities)}, "
                f"watchlist_count={len(watchlist)}"
            )

            return parsed_record

        except Exception as e:
            logger.error(f"Error parsing event data for alert {alert_id}: {e}")
            return None

    def fetch_latest_alert_data(self, alert_id, days_back=30):
        """Fetch the latest event data for a specific alert_id from Splunk using serviceobj with oneshot."""
        try:
            # Set configurable time range
            earliest_time = f"-{days_back}d@d"
            latest_time = "now"

            logger.debug(f"Searching for latest data for alert_id: {alert_id}.")

            # Targeted search with specific index
            search_query = f'search {self.index_query} earliest={earliest_time} latest={latest_time} alertId="{alert_id}" | sort -_time | head 1'  # noqa: E501

            logger.debug(f"Oneshot query: {search_query}")

            # Execute oneshot search
            search_result = self.serviceobj.jobs.oneshot(search_query, count=0)

            if not search_result:
                logger.warning(f"No search results returned for alert_id: {alert_id}")
                return None

            result_reader = results.ResultsReader(search_result)

            # Flag to track if we found any results
            found_result = False

            for result in result_reader:
                found_result = True
                logger.debug(f"Found event for alert_id: {alert_id}")

                # Convert to dict and handle _raw JSON
                event_data = dict(result)

                if "_raw" in event_data:
                    try:
                        raw_json = json.loads(event_data["_raw"])
                        # Add alert metadata
                        raw_json["alert_id"] = alert_id
                        raw_json["_time"] = event_data.get("_time")

                        # Merge with event_data
                        event_data.update(raw_json)
                        logger.debug(f"Enhanced event data with _raw JSON for alert {alert_id}")
                    except json.JSONDecodeError as json_err:
                        logger.warning(f"Failed to parse _raw JSON for alert {alert_id}: {json_err}")

                # Parse using existing logic
                parsed_record = self.parse_event_data(event_data, alert_id)
                return parsed_record

            if not found_result:
                logger.warning(f"No events found for alert_id: {alert_id}")
                return None

            return None

        except Exception as e:
            logger.error(f"Error in oneshot search for alert_id {alert_id}: {e}")
            return None

    def process_records(self, records):
        """Process incoming records by fetching latest data from Splunk search with JS-style parsing."""
        for record in records:
            alert_id = record.get("alert_id")
            if alert_id:
                logger.debug(f"Processing alert_id: {alert_id}")

                # Fetch and parse the latest event data for this alert_id
                parsed_record = self.fetch_latest_alert_data(alert_id)

                if parsed_record:
                    # Use the parsed data
                    alert_record = parsed_record
                    logger.debug(f"Created alert record from parsed event data for: {alert_id}")

                else:
                    logger.warning(f"No events found for alert_id: {alert_id}")
                    continue

                # Override with any fields provided in the input record
                for field in ["headline", "alert_timestamp", "intelagent", "discoveredentities", "watchlist", "_user"]:
                    if field in record and record[field]:
                        alert_record[field] = record[field]
                        logger.debug(f"Overrode {field} with input data for alert {alert_id}")

                self.updated_alerts.append(alert_record)
                logger.debug(f"Added alert record for: {alert_id}")

            else:
                logger.warning(f"Record missing alert_id field, skipping: {record}")

        logger.info(f"Prepared {len(self.updated_alerts)} alerts for upsert")

    def upsert_alerts(self):
        """Upsert alerts to KVStore."""
        try:
            if not self.updated_alerts:
                logger.info("No records provided, cannot proceed without alert_ids")
                return 0

            logger.debug(f"Upserting {len(self.updated_alerts)} alerts to KV store...")

            # Log details of what we're upserting
            for alert in self.updated_alerts:
                logger.debug(f"Upserting alert: alert_id={alert.get('alert_id')} _key={alert.get('_key')}")

            # Use the upsert method from AlertManager
            self.alert_mgr.upsert_alerts(self.updated_alerts)

            logger.info(
                f"Successfully upserted {len(self.updated_alerts)} alerts to '{kvstore.ALERT_LOOKUP}' collection"
            )
            return len(self.updated_alerts)

        except kvstore.KVStoreUnavailbleError:
            logger.error("KVStore unavailable during upsert")
            raise
        except kvstore.CollectionNotFoundError as ex:
            logger.error(f"Collection not found: {ex}")
            raise
        except Exception as ex:
            logger.error(f"Failed to upsert alerts: count={len(self.updated_alerts)} error={ex}")
            raise

    def _write_error(self, msg):
        """Log error message to Splunk UI."""
        self.write_error(f"{msg} {REDIRECT_TO_LOG_FILE_MSG}")

    def transform(self, records):
        """Transform method - processes records and upserts to KVStore."""
        try:
            if False:
                yield

            if self.metadata.preview:
                return

            self.start_time = time.time()
            logger.info(f'Starting "{self.name}" command execution')

            # Initialize the alert manager
            self.initialize()

            # Process the records (if any)
            self.process_records(records)

            # Upsert alerts to KVStore
            updated_count = self.upsert_alerts()

            logger.info(f"Alert upsert completed successfully. Upserted {updated_count} alerts.")

        except kvstore.KVStoreUnavailbleError as ex:
            logger.error(f"KVStore Unavailable: {ex}")
            self._write_error(f"KVStore Unavailable: {ex}")

        except kvstore.CollectionNotFoundError as ex:
            logger.error(f"Collection Not Found: {ex}")
            self._write_error(f"Collection Not Found: {ex}")

        except Exception as ex:
            logger.error(f"Unknown error occurred: {traceback.format_exc()}")
            self._write_error(f"Unknown Error: {ex}")

        finally:
            if hasattr(self, "start_time") and self.start_time:
                elapsed_seconds = time.time() - self.start_time
                logger.info(f'End of "{self.name}" command execution. Total time: {elapsed_seconds:.3f}s')


dispatch(DataminrUpdateAlerts, sys.argv, sys.stdin, sys.stdout, __name__)
