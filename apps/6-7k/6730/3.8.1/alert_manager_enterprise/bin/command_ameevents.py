#!/usr/bin/env python3.9
#
# File: command_ameevents.py - Version 3.8.1
# Copyright © Datapunctum AG 2026-04-07
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import annotations

import os
import sys
from collections import defaultdict
from collections.abc import Generator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import Configuration, GeneratingCommand, Option, dispatch

from ame.command_ame import AmeCommand
from ame.handlers.payloads.EventHandlerPayloads import EventSearchQuery
from ame.models.fields.EventEntryFields import EventEntryFields
from ame.models.risks.RiskEvent import EnrichedRiskEvent
from ame.models.SLAEntry import ReadableSLAEntry
from dpshared.consts.CommonKeys import CommonKeys
from dpshared.utilities.TruthyUtility import is_truthy

COMMAND_NAME = "ameevents"


@Configuration(type="reporting")
class ameevents(GeneratingCommand, AmeCommand):  # noqa: N801
    """
    ##Syntax
    | ameevents ...
    ##Description
    Custom search command to get the events stored for ame.
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
    has_slas = Option(require=False, default=None)
    has_sla_violations = Option(require=False, default=None)
    has_sla_violations_within = Option(require=False, default=None)
    sla_info = Option(require=False, default=False)
    observable_info = Option(require=False, default=False)
    risk_event_info = Option(require=False, default=False)

    def __init__(self) -> None:
        GeneratingCommand.__init__(self)
        AmeCommand.__init__(self)

    def setup_query(self) -> tuple[int, int]:
        earliest = int(self._metadata.searchinfo.earliest_time)
        latest = int(self._metadata.searchinfo.latest_time)
        if self.has_sla_violations_within is not None:
            self.has_sla_violations_within = int(self.has_sla_violations_within)
        if self.has_sla_violations is not None:
            self.has_sla_violations = is_truthy(self.has_sla_violations)
        if self.has_slas is not None:
            self.has_slas = is_truthy(self.has_slas)
        if self.sla_info is not None:
            self.sla_info = is_truthy(self.sla_info)
        if self.observable_info is not None:
            self.observable_info = is_truthy(self.observable_info)
        if self.risk_event_info is not None:
            self.risk_event_info = is_truthy(self.risk_event_info)
            if self.risk_event_info and not self.observable_info:
                raise ValueError(
                    "The 'risk_event_info' parameter requires 'observable_info' to be set to true."
                )

        # If we have a timepicker with "all time" selected, the earliest and latest will be 0
        # to see events that were generated in the future we need to set the latest to the maximum value
        if latest == 0:
            latest = 2147483647

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

        return earliest, latest

    def load_sla_info(self) -> bool:
        return any(
            [
                self.has_slas,
                self.has_sla_violations,
                self.has_sla_violations_within,
                self.sla_info,
            ]
        )

    def enrich_with_sla(self, event_by_key: dict[str, dict]) -> dict[str, dict]:
        tenant_uid_events: defaultdict[str, list] = defaultdict(list)
        for _, event in event_by_key.items():
            tenant_uid = event.get(CommonKeys.TENANT_UID)
            if not tenant_uid:
                continue
            tenant_uid_events[tenant_uid].append(event)

        sla_entry_service = self.service_factory.sla_entry_service
        event_to_sla_entries: dict[str, list[ReadableSLAEntry]] = {}
        matching_events = set()

        for tenant_uid, tenant_events in tenant_uid_events.items():
            tenant_event_key_to_event_title: dict[str, str] = {
                event[CommonKeys._KEY]: event[EventEntryFields.EVENT_TITLE]
                for event in tenant_events
            }
            tenant_event_key_to_sla_entries = (
                sla_entry_service.get_readable_sla_entries_for_events_from_command(
                    tenant_uid=tenant_uid,
                    events=tenant_event_key_to_event_title,
                )
            )
            event_to_sla_entries.update(tenant_event_key_to_sla_entries)
            matching_events |= set(
                sla_entry_service.get_matching_events(
                    event_keys=list(tenant_event_key_to_event_title.keys()),
                    sla_entries=tenant_event_key_to_sla_entries,
                    has_slas=self.has_slas,
                    has_sla_violations=self.has_sla_violations,
                    has_sla_violations_within=self.has_sla_violations_within,
                )
            )

        for event_key, readable_sla_entries in event_to_sla_entries.items():
            if event_key not in matching_events:
                event_by_key.pop(event_key, None)
                continue

            sla_columns = sla_entry_service.create_sla_columns(
                event_key=event_key,
                readable_sla_entries=readable_sla_entries,
            )

            event = event_by_key[event_key]
            event["sla_entries"] = [entry.model_dump() for entry in readable_sla_entries]
            event.update(sla_columns)

        return event_by_key

    def enrich_with_observables(self, event_by_key: dict[str, dict]) -> dict[str, dict]:
        risk_event_service = self.service_factory.risk_event_service
        tenant_uid_events: defaultdict[str, list] = defaultdict(list)
        for _, event in event_by_key.items():
            tenant_uid = event.get(CommonKeys.TENANT_UID)
            if not tenant_uid:
                continue
            tenant_uid_events[tenant_uid].append(event)

        for tenant_uid, tenant_events in tenant_uid_events.items():
            tenant_event_keys: list[str] = [event[CommonKeys._KEY] for event in tenant_events]
            risk_events = risk_event_service.get_risk_events_for_events(
                tenant_uid=tenant_uid,
                event_keys=tenant_event_keys,
            )

            enriched_risk_events = []
            for risk_event in risk_events:
                if not risk_event.related_event:
                    continue
                enriched_risk_events.append(
                    EnrichedRiskEvent.from_risk_event(risk_event=risk_event)
                )

            enriched_risk_events = risk_event_service.enrich_risk_events_with_observable(
                tenant_uid=tenant_uid, risk_events=enriched_risk_events
            )
            enriched_risk_events_by_event: dict[str, list[EnrichedRiskEvent]] = defaultdict(list)
            for enriched_risk_event in enriched_risk_events:
                if enriched_risk_event.related_event:
                    enriched_risk_events_by_event[enriched_risk_event.related_event].append(
                        enriched_risk_event
                    )

            for event in tenant_events:
                event_key = event.get(CommonKeys._KEY)
                if not event_key:
                    continue

                enriched_risk_events_for_event = enriched_risk_events_by_event.get(event_key, [])
                observables = list(
                    {
                        enriched_risk_event.observable.key: enriched_risk_event.observable
                        for enriched_risk_event in enriched_risk_events_for_event
                        if enriched_risk_event.observable
                    }.values()
                )

                if enriched_risk_events_for_event:
                    event["observables"] = [
                        observable.dump_for_search() for observable in observables
                    ]
                    if self.risk_event_info:
                        event["risk_events"] = [
                            risk_event.dump_for_search()
                            for risk_event in enriched_risk_events_for_event
                        ]
                else:
                    event["observables"] = []
                    if self.risk_event_info:
                        event["risk_events"] = []

        return event_by_key

    def generate(self) -> Generator[dict, None, None]:
        try:
            self.setup_metadata()
            self.event_report_service = self.service_factory.event_report_service
            self.setup_query()

            self._datapunctum_logger.debug(
                {
                    "action": COMMAND_NAME,
                    "status": "success",
                    "username": self.username,
                    "earliest": self.query.earliest,
                    "latest": self.query.latest,
                    "query": self.query,
                    "sla_info": self.sla_info,
                }
            )

            events_tuples_list = list(self.event_report_service.event_search(query=self.query))
            event_by_key: dict[str, dict] = {  # noqa: C416
                event_key: event for event_key, event in events_tuples_list
            }

            if self.load_sla_info():
                event_by_key = self.enrich_with_sla(event_by_key=event_by_key)
            if self.observable_info:
                event_by_key = self.enrich_with_observables(event_by_key=event_by_key)

            for _, event in event_by_key.items():
                yield self.gen_record(**event)

            self.write_info(f"[{COMMAND_NAME}]: Finished processing events")
        except Exception as exc:
            self._datapunctum_logger.exception(
                {
                    "action": COMMAND_NAME,
                    "status": "failed",
                    "user": self._metadata.searchinfo.username
                    if hasattr(self._metadata.searchinfo, "username")
                    else "unknown",
                }
            )
            raise exc


dispatch(ameevents, sys.argv, sys.stdin, sys.stdout, __name__)
