#!/usr/bin/env python3.9
#
# File: command_ameenrich.py - Version 3.8.1
# Copyright © Datapunctum AG 2026-04-07
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from io import StringIO
from typing import TYPE_CHECKING, Callable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import Configuration, EventingCommand, Option, dispatch

from ame.command_ame import AmeCommand
from ame.handlers.payloads.EventHandlerPayloads import EventSearchQuery
from dpshared.consts.CommonKeys import CommonKeys
from dpshared.consts.LogEntryStatus import LogEntryStatus
from dpshared.utilities.TruthyUtility import is_truthy

if TYPE_CHECKING:
    from splunklib.searchcommands.internals import RecordWriter

COMMAND_NAME = "ameenrich"
# the iterator batch size defines how many records are enriched at once, before starting to yield them
# indirectly it determines the size of the LRU Cache
ITR_BATCH_SIZE = 1000
EVENT_KEY_FIELD = "event_key"
FILTER_MATCHED_FIELD = "filter_matched"

FIELD_ALIASES = {"tenant": "tenant_uid"}


@Configuration()
class ameenrich(EventingCommand, AmeCommand):  # noqa: N801
    if TYPE_CHECKING:
        _record_writer: RecordWriter
    """
    ##Syntax
    | ameenrich ...
    ##Description
    Custom search command to enrich the events with the details of the alert.
    """

    assignees = Option(require=False, default=[])
    saved_searches = Option(require=False, default=[])
    priorities = Option(require=False, default=[])
    tags = Option(require=False, default=[])
    tag_mode = Option(require=False, default="OR")
    status = Option(require=False, default=[])
    status_types = Option(require=False, default=[])
    resolutions = Option(require=False, default=[])
    tenants = Option(require=False, default=[])
    fields = Option(require=False, default=None)
    use_time = Option(require=False, default=True)
    sla_info = Option(require=False, default=False)
    has_slas = Option(require=False, default=None)
    has_sla_violations = Option(require=False, default=None)
    has_sla_violations_within = Option(require=False, default=None)

    initial_run = True
    last_run = False

    def __init__(self) -> None:
        EventingCommand.__init__(self)
        AmeCommand.__init__(self)

    def _execute_chunk_v2(self, process: Callable, chunk: tuple) -> None:
        metadata, body = chunk

        if len(body) <= 0 and not self._allow_empty_input:
            raise ValueError(
                "No records found to process. Set allow_empty_input=True in dispatch function to move forward "
                "with empty records."
            )

        if metadata.finished:
            self.last_run = True

        records = self._read_csv_records(StringIO(body))
        self._record_writer.write_records(process(records))

    @property
    def has_filter(self) -> bool:
        if getattr(self, "_has_filter", None) is None:
            nullable_attributed = [
                self.has_sla_violations_within,
                self.has_sla_violations,
                self.has_slas,
            ]
            attributes = [
                self.assignees,
                self.priorities,
                self.tags,
                self.status,
                self.resolutions,
                self.tenants,
                self.saved_searches,
            ]
            self._has_filter = any(len(attr) > 0 for attr in attributes) or any(
                attr is not None for attr in nullable_attributed
            )

        return self._has_filter

    def setup_query(self) -> None:
        if is_truthy(self.use_time):
            earliest = int(self._metadata.searchinfo.earliest_time)
            latest = int(self._metadata.searchinfo.latest_time)

            # If we have a timepicker with "all time" selected, the earliest and latest will be 0
            # to see events that were generated in the future we need to set the latest to the maximum value
            if latest == 0:
                latest = 2147483647
        else:
            earliest = 0
            latest = 2147483647

        if self.has_sla_violations_within is not None:
            self.has_sla_violations_within = int(self.has_sla_violations_within)
        if self.has_sla_violations is not None:
            self.has_sla_violations = is_truthy(self.has_sla_violations)
        if self.has_slas is not None:
            self.has_slas = is_truthy(self.has_slas)
        if self.sla_info is not None:
            self.sla_info = is_truthy(self.sla_info)

        self.query = EventSearchQuery(
            assignees=self.assignees,
            priorities=self.priorities,
            tags=self.tags,
            status=self.status,
            status_types=self.status_types,
            tenants=self.tenants,
            resolutions=self.resolutions,
            tag_mode=self.tag_mode,
            saved_searches=self.saved_searches,
            earliest=earliest,
            latest=latest,
            direction="desc",
        )

    def prepare_fields(self) -> list[str]:
        fields = self.fields.split(",") if self.fields is not None and self.fields != "*" else []
        fields = [field.strip() for field in fields]
        fields = [FIELD_ALIASES.get(field, field) for field in fields]
        fields = [field for field in fields if field and field != ""]
        return fields

    def load_sla_info(self) -> bool:
        return bool(
            self.sla_info
            or self.has_slas
            or self.has_sla_violations
            or self.has_sla_violations_within
        )

    def transform(self, records: list[dict]) -> Generator[dict, None, None]:
        try:
            if self.initial_run:
                self.setup_metadata()
                self.event_report_service = self.service_factory.event_report_service
                self.setup_query()
                self.cleaned_fields = self.prepare_fields()

                self.all_records = []
                self.initial_run = False
                if self.sla_info:
                    self.sla_entry_service = self.service_factory.sla_entry_service

            self.all_records.extend(list(records))

            if self.last_run:
                event_keys = [record.get(EVENT_KEY_FIELD) for record in self.all_records]
                event_keys = list(set(filter(None, event_keys)))

                self.write_info(
                    f"[{COMMAND_NAME}]: Found {len(event_keys)} unique event keys in {len(self.all_records)} records"
                )
                self.write_info(f"[{COMMAND_NAME}]: Starting to process events")

                # Fetch the full event for all found event keys using prefilter_event_keys and prefilter_exclusive
                events_matching_key = self.event_report_service.event_search(
                    query=self.query,
                    prefilter_event_keys=event_keys,
                    fields=self.fields,
                    prefilter_exclusive=True,
                )
                key_matching_by_key = {event[0]: event[1] for event in events_matching_key}
                events_matching_query = None

                self.write_info(
                    f"[{COMMAND_NAME}]: Loaded {len(key_matching_by_key.keys())} events"
                )

                if self.has_filter:
                    events_matching_query = self.event_report_service.event_search(
                        query=self.query,
                        prefilter_event_keys=event_keys,
                        fields=[EVENT_KEY_FIELD],
                        prefilter_exclusive=False,
                    )
                else:
                    events_matching_query = list(key_matching_by_key.items())

                key_event_dict = {event[0]: event[1] for event in events_matching_query}
                key_matching_by_query = set(key_event_dict.keys())
                sla_result = {}
                matching_events = key_event_dict.keys()
                if self.load_sla_info():
                    tenant_uid_events: dict[str, list] = {}
                    for _, event in key_event_dict.items():
                        tenant_uid = event.get(CommonKeys.TENANT_UID)
                        if not tenant_uid:
                            self._datapunctum_logger.warning(
                                {
                                    "action": COMMAND_NAME,
                                    "status": LogEntryStatus.SKIPPED,
                                    "reason": "event missing tenant_uid, skipping SLA enrichment",
                                    "event_key": event.get(CommonKeys._KEY),
                                }
                            )
                            continue
                        if tenant_uid not in tenant_uid_events:
                            tenant_uid_events[tenant_uid] = []
                        tenant_uid_events[tenant_uid].append(event)
                    sla_result = {}
                    matching_events = set()
                    for tenant_uid, events in tenant_uid_events.items():
                        event_key_title_dict = {
                            event[CommonKeys._KEY]: event["event_title"] for event in events
                        }
                        local_sla_result = self.sla_entry_service.get_readable_sla_entries_for_events_from_command(
                            tenant_uid=tenant_uid, events=event_key_title_dict
                        )
                        sla_result.update(local_sla_result)
                        self._datapunctum_logger.debug(
                            {
                                "action": COMMAND_NAME,
                                "status": LogEntryStatus.SUCCESS,
                                "sla_entries": sla_result,
                            }
                        )
                        matching_events |= set(
                            self.sla_entry_service.get_matching_events(
                                event_keys=list(key_event_dict.keys()),
                                sla_entries=local_sla_result,
                                has_slas=self.has_slas,
                                has_sla_violations=self.has_sla_violations,
                                has_sla_violations_within=self.has_sla_violations_within,
                            )
                        )

                for record in self.all_records:
                    event_key = record.get(EVENT_KEY_FIELD)

                    if not event_key:
                        yield record
                        continue

                    event = key_matching_by_key.get(event_key)
                    if not event:
                        self._datapunctum_logger.logger.warning(
                            {
                                "action": "get_event_from_result",
                                "status": "failed",
                                "event_key": event_key,
                            }
                        )
                        yield record
                        continue

                    if len(self.cleaned_fields) == 0:
                        fields = event.keys()
                    else:
                        fields = self.cleaned_fields

                    for field in fields:
                        if field in event:
                            self.add_field(record, field, event[field])

                    if self.has_filter:
                        if event_key in key_matching_by_query and event_key in matching_events:
                            self.add_field(record, FILTER_MATCHED_FIELD, 1)
                        else:
                            self.add_field(record, FILTER_MATCHED_FIELD, 0)
                    else:
                        self.add_field(record, FILTER_MATCHED_FIELD, 1)

                    if self.load_sla_info():
                        readable_sla_entries = sla_result.get(event_key, [])
                        self.add_field(
                            record,
                            "sla_entries",
                            field_value=[entry.model_dump() for entry in readable_sla_entries],
                        )
                        sla_columns = self.sla_entry_service.create_sla_columns(
                            event_key=event_key, readable_sla_entries=readable_sla_entries
                        )
                        for key, value in sla_columns.items():
                            self.add_field(record, key, value)

                    yield record

        except Exception as exc:
            self._datapunctum_logger.exception(
                {
                    "action": COMMAND_NAME,
                    "status": "failed",
                    "exception": exc,
                    "user": self._metadata.searchinfo.username
                    if hasattr(self._metadata.searchinfo, "username")
                    else "unknown",
                }
            )
            self._datapunctum_logger.exception(exc)
            raise exc

        self.write_info(f"[{COMMAND_NAME}]: Finished processing events")


dispatch(ameenrich, sys.argv, sys.stdin, sys.stdout, __name__)
