#!/usr/bin/env python
"""
Cyware CTIX Index to KVStore Migration Command.

This custom Splunk command migrates indicator data from Splunk indexes to KVStore collections.
It processes events from search results and upserts them into appropriate KVStore collections
based on indicator_type.
"""

import ta_cyware_ctix_declare  # noqa: F401

import sys
import json
import traceback
from splunklib.searchcommands import (
    dispatch,
    EventingCommand,
    Configuration,
    Option
)
from typing import Iterator, Dict, Any
from ta_cyware_ctix.kvstore_helper import KvStoreWriter
from ta_cyware_ctix.logging_helper import get_logger
from ta_cyware_ctix.constants import COLLECTION_BASE_NAME, MASTER_LOOKUP_DICT
from splunk import rest

logger = get_logger("cyware_index_to_kvstore_migration")


def normalize_indicator_type(indicator_type):
    """
    Normalize indicator type for collection naming.

    Converts hyphenated types (ipv4-addr) to underscored types (ipv4_addr)
    to match KVStore collection naming conventions.

    Args:
        indicator_type: Raw indicator type from data (e.g., "ipv4-addr", "network-traffic")

    Returns:
        str: Normalized indicator type (e.g., "ipv4_addr", "network_traffic")
    """
    import re
    if not indicator_type or str(indicator_type).strip() == "":
        return "unknown"

    normalized = str(indicator_type).strip().lower()

    # Then replace any other non-alphanumeric characters with underscores
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", normalized)

    # Remove multiple consecutive underscores
    normalized = re.sub(r"_+", "_", normalized)

    # Remove leading/trailing underscores
    normalized = normalized.strip("_")

    if not normalized:
        return "unknown"

    return normalized


@Configuration()
class CywareIndexToKVStoreMigration(EventingCommand):
    """
    Custom Splunk eventing command to migrate Cyware indicator data from indexes to KVStore.

    This command processes Cyware CTIX indicator events from Splunk indexes and migrates them to
    appropriate KVStore collections based on their indicator_type. Uses the _finished flag to
    disable the saved search only after complete command execution.
    """

    saved_search_name = Option(
        doc='Name of the saved search to disable after successful migration',
        require=False
    )

    # Class-level tracking variables
    total_events_processed = 0
    migration_successful = False
    migration_required = False
    _events_by_type = {}

    def disable_saved_search(self, session_key: str, saved_search_name: str) -> bool:
        """
        Disable a saved search after successful migration.

        Args:
            session_key: The session key for authentication
            saved_search_name: Name of the saved search to disable

        Returns:
            bool: True if successfully disabled, False otherwise
        """
        try:
            endpoint = f"/servicesNS/nobody/TA-cyware-ctix/saved/searches/{saved_search_name}"

            response, content = rest.simpleRequest(
                endpoint,
                method='POST',
                sessionKey=session_key,
                postargs={
                    'disabled': '1'
                },
                raiseAllErrors=False
            )

            if response['status'] == '200':
                logger.info(
                    f"Successfully disabled saved search: {saved_search_name}"
                )
                return True
            else:
                logger.error(
                    f"Failed to disable saved search: {saved_search_name}. "
                    f"Status: {response['status']}, Content: {content}"
                )
                return False

        except Exception as disable_error:
            logger.error(
                f"Exception occurred while disabling saved search: {saved_search_name}. "
                f"Error: {str(disable_error)}"
            )
            return False

    def transform(self, records: Iterator[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
        """
        Transform events and migrate data to KVStore.

        Args:
            records: Iterator of search result events

        Yields:
            Dict[str, Any]: Original events (passthrough)
        """
        try:
            logger.info("EventingCommand transform method started")

            # Process each event as it comes in (EventingCommand pattern)
            for event in records:
                try:
                    raw_data = event.get("_raw")

                    if not raw_data:
                        logger.warning("Missing _raw in event")
                        yield event
                        continue

                    try:
                        parsed_event = json.loads(raw_data)
                    except json.JSONDecodeError as json_error:
                        logger.error(f"Invalid JSON in _raw: {str(json_error)}")
                        yield event
                        continue
                    except Exception as general_error:
                        logger.error(f"Error parsing JSON in _raw: {str(general_error)}")
                        yield event
                        continue

                    # Extract indicator_type from the event
                    indicator_type = parsed_event.get("indicator_type")

                    if not indicator_type:
                        logger.warning(f"Missing indicator_type in event: {parsed_event.get('indicator', 'unknown')}")
                        yield event
                        continue

                    # Normalize the indicator type
                    normalized_type = normalize_indicator_type(indicator_type)

                    # Track event for batch migration in finally block
                    self._track_event_for_migration(parsed_event, normalized_type)
                    self.total_events_processed += 1

                except Exception as event_error:
                    logger.error(
                        f"Error processing event: {str(event_error)}"
                    )

                # Always yield the original event
                yield event

        except Exception as ex:
            logger.error(
                f"Error in transform method: {str(ex)}"
            )
        finally:
            # This is where we do the actual migration after ALL events are processed
            if self._finished:
                logger.info(
                    "Command finished, performing migration and cleanup"
                )
                self._perform_final_migration()

    def _track_event_for_migration(self, parsed_event: Dict[str, Any], indicator_type: str) -> None:
        """Track events for batch migration in finally block."""
        if not hasattr(self, '_events_by_type'):
            self._events_by_type = {}

        self._events_by_type.setdefault(indicator_type, []).append(parsed_event)

    def _perform_final_migration(self) -> None:
        """Perform the actual migration in the finally block when command is finished."""
        try:
            session_key = self._metadata.searchinfo.session_key

            if not hasattr(self, '_events_by_type') or not self._events_by_type:
                logger.info(
                    "No events found for migration."
                )
                if self.saved_search_name:
                    if self.disable_saved_search(session_key, self.saved_search_name):
                        logger.info(
                            f"No events found, successfully disabled saved search: {self.saved_search_name}"
                        )
                    else:
                        logger.warning(
                            f"Failed to disable saved search: {self.saved_search_name}"
                        )
                return

            total_migrated = 0
            kv_writer = KvStoreWriter(
                session_key=session_key,
                app_name='TA-cyware-ctix'
            )

            for indicator_type, events in self._events_by_type.items():
                logger.info(
                    f"Migrating {len(events)} events of type {indicator_type}"
                )

                try:
                    # Look up collection name from MASTER_LOOKUP_DICT first
                    # MASTER_LOOKUP_DICT maps: "ipv4_addr" -> "cyware_ti_ipv4_addr"
                    if indicator_type in MASTER_LOOKUP_DICT:
                        collection_name = MASTER_LOOKUP_DICT[indicator_type]
                        logger.debug(
                            f"Found collection mapping: {indicator_type} -> {collection_name}"
                        )
                    else:
                        # Fallback: construct collection name
                        collection_name = f"{COLLECTION_BASE_NAME}_{indicator_type}"
                        logger.warning(
                            f"No predefined collection for '{indicator_type}', using: {collection_name}"
                        )

                    # Write using the KV writer
                    error, error_message = kv_writer.write_single_type_to_kv(
                        collection_name, events
                    )

                    if not error:
                        total_migrated += len(events)
                        logger.info(
                            f"Successfully migrated {len(events)} {indicator_type} events"
                        )
                    else:
                        logger.error(
                            f"Failed to migrate {indicator_type} events: {error_message}"
                        )

                except Exception as upsert_error:
                    logger.error(
                        f"Error migrating {indicator_type} events: {str(upsert_error)}\n{traceback.format_exc()}"
                    )

            if total_migrated > 0:
                self.migration_successful = True
                self.migration_required = True
                logger.info(
                    f"Migration completed successfully. Total events migrated: {total_migrated}"
                )

                # Now disable the saved search if configured
                if self.saved_search_name:
                    logger.info(
                        f"Attempting to disable saved search: {self.saved_search_name}"
                    )
                    if self.disable_saved_search(session_key, self.saved_search_name):
                        logger.info(
                            f"Successfully disabled saved search: {self.saved_search_name}"
                        )
                    else:
                        logger.warning(
                            f"Failed to disable saved search: {self.saved_search_name}"
                        )

        except Exception as migration_error:
            logger.error(
                f"Error in final migration: {str(migration_error)}\n{traceback.format_exc()}"
            )


if __name__ == "__main__":
    dispatch(CywareIndexToKVStoreMigration, sys.argv, sys.stdin, sys.stdout, __name__)
