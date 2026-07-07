#!/usr/bin/env python3.9
#
# File: command_amevulnintrealizations.py - Version 3.8.1
# Copyright © Datapunctum AG 2026-04-07
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import annotations

import os
import re
import sys
import time
from collections import defaultdict
from collections.abc import Generator
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import Configuration, GeneratingCommand, Option, dispatch

from ame.command_ame import AmeCommand
from ame.models.observables.fields.ObservableFields import ObservableFields
from ame.models.observables.Observable import Observable
from ame.models.observables.ObservableGroup import ObservableGroup
from ame.models.risks.RiskStatus import RiskStatus
from ame.models.vuln_int.fields.VulnIntCVEFields import VulnIntCVEInternalFields
from ame.models.vuln_int.fields.VulnIntRealizationFields import VulnIntRealizationFields
from ame.models.vuln_int.VulnIntCVE import VulnIntCVE
from ame.services.vuln_int.VulnIntRealizationsQueryService import (
    VulnIntPreprocessingOperators,
    VulnIntPreprocessingQueryElement,
    VulnRealizationQuery,
)
from dpshared.consts.CommonKeys import CommonKeys
from dpshared.consts.LogEntryStatus import LogEntryStatus
from dpshared.exceptions import PublicException

COMMAND_NAME = "amevulnintrealizations"


@Configuration(type="streaming", local=True)
class amevulnintrealizations(GeneratingCommand, AmeCommand):  # noqa: N801
    """
    ##Syntax
    | amevulnintrealizations ...
    ##Description
    Custom search command to fetch vulnerability realizations.
    """

    tenant_uid = Option(require=True)

    time_field = Option(require=False, default=VulnIntRealizationFields.LAST_SEEN)
    state = Option(require=False, default="open")
    limit = Option(require=False, default=10_000)

    realization_filters = Option(require=False, default=None)
    observable_filters = Option(require=False, default=None)
    observable_group_filters = Option(require=False, default=None)
    cve_filters = Option(require=False, default=None)

    def parse_kv_ops_string(self, query: str) -> list[VulnIntPreprocessingQueryElement]:
        results: list[VulnIntPreprocessingQueryElement] = []
        if not query:
            return results

        # Order is relevant, use "longest" first to avoid partial matches
        operators = (
            VulnIntPreprocessingOperators.NOT_EQUALS,
            VulnIntPreprocessingOperators.LOWER_THAN_OR_EQUAL,
            VulnIntPreprocessingOperators.GREATER_THAN_OR_EQUAL,
            VulnIntPreprocessingOperators.EQUALS,
            VulnIntPreprocessingOperators.LOWER_THAN,
            VulnIntPreprocessingOperators.GREATER_THAN,
        )
        operator_pattern = "|".join(re.escape(operator) for operator in operators)
        pattern = re.compile(
            r"^\s*(?P<key>.*?)\s*(?P<operator>" + operator_pattern + r")\s*(?P<value>.*?)\s*$"
        )

        for clause in query.split(","):
            clause = clause.strip()
            if not clause:
                continue

            m = pattern.match(clause)
            if not m:
                raise PublicException(
                    f"Invalid clause in string: {clause}. Expected comma separated format: 'key op value' where op is one of {', '.join(operators)}"
                )

            key = m.group("key").strip()
            operator = m.group("operator")
            value = m.group("value").strip()
            if (
                isinstance(value, str)
                and value.startswith('"')
                and value.endswith('"')
                or isinstance(value, str)
                and value.startswith("'")
                and value.endswith("'")
            ):  # noqa: SIM114
                value = value[1:-1]

            try:
                number = float(value)
                value = int(number) if number.is_integer() else number
            except ValueError as value_error:
                if operator in (
                    VulnIntPreprocessingOperators.LOWER_THAN,
                    VulnIntPreprocessingOperators.GREATER_THAN,
                    VulnIntPreprocessingOperators.LOWER_THAN_OR_EQUAL,
                    VulnIntPreprocessingOperators.GREATER_THAN_OR_EQUAL,
                ):
                    raise PublicException(
                        f"Invalid value for operator {operator}: {value!r}. Expected a number."
                    ) from value_error

            results.append(
                VulnIntPreprocessingQueryElement(
                    field=key,
                    operator=VulnIntPreprocessingOperators(operator),
                    value=value,
                )
            )

        return results

    def __init__(self) -> None:
        GeneratingCommand.__init__(self)
        AmeCommand.__init__(self)

    def setup_query(self) -> None:
        try:
            self.limit = int(self.limit)
        except ValueError as value_error:
            raise PublicException(
                f"Invalid limit value: {self.limit}. It should be an integer."
            ) from value_error

        self.earliest = int(self._metadata.searchinfo.earliest_time)
        self.latest = int(self._metadata.searchinfo.latest_time)

        # If we have a timepicker with "all time" selected, the earliest and latest will be 0
        # to see events that were generated in the future we need to set the latest to the maximum value
        if self.latest == 0:
            self.latest = 2147483647

    def observable_group_to_result_representation(
        self, observable_group: ObservableGroup
    ) -> dict[str, Any]:
        observable_group_result = {}
        observable_group_result["observable_group.name"] = observable_group.name
        observable_group_result["observable_group.scope"] = str(observable_group.scope)
        observable_group_result["observable_group.description"] = observable_group.description
        for additional_field in observable_group.additional_fields:
            observable_group_result[f"observable_group.{additional_field.name}"] = (
                additional_field.value
            )

        return observable_group_result

    def observable_to_result_representation(self, observable: Observable) -> dict[str, Any]:
        observable_result = {}
        observable_dump = observable.model_dump(exclude_unset=True)
        keys = list(observable_dump.keys())

        for key in keys:
            if key in [
                CommonKeys._KEY,
                CommonKeys._USER,
                CommonKeys.DELETED,
                ObservableFields.TENANT_UID,
                ObservableFields.DATA_INFO,
                ObservableFields.OBSERVABLE_GROUP,
            ]:
                continue
            else:
                observable_result[f"observable.{key}"] = observable_dump[key]

        return observable_result

    def cve_to_result_representation(self, cve: VulnIntCVE) -> dict[str, Any]:
        cve_result = {}
        cve_dump = cve.model_dump(exclude={VulnIntCVEInternalFields.SOURCE_TRACKING})

        keys = list(cve_dump.keys())

        for key in keys:
            if key in [
                CommonKeys._KEY,
                CommonKeys._USER,
                CommonKeys.DELETED,
            ]:
                continue
            else:
                cve_result[f"cve.{key}"] = cve_dump[key]

        return cve_result

    def generate(self) -> Generator[dict, None, None]:
        try:
            start_time = time.time()
            self.setup_metadata()
            self.setup_query()

            self._datapunctum_logger.debug(
                {
                    "action": COMMAND_NAME,
                    "status": LogEntryStatus.STARTED,
                    "username": self.username,
                    "earliest": self.earliest,
                    "latest": self.latest,
                    "tenant_uid": self.tenant_uid,
                    "state": self.state,
                    "time_field": self.time_field,
                    "realization_filters": self.realization_filters,
                    "cve_filters": self.cve_filters,
                    "observable_filters": self.observable_filters,
                    "observable_group_filters": self.observable_group_filters,
                }
            )

            self.observables_service = self.service_factory.observables_service
            vuln_int_realizations_query_service = (
                self.service_factory.vuln_int_realizations_query_service
            )

            parsed_realization_filters = (
                self.parse_kv_ops_string(self.realization_filters)
                if self.realization_filters
                else []
            )
            parsed_observable_group_filters = (
                self.parse_kv_ops_string(self.observable_group_filters)
                if self.observable_group_filters
                else []
            )
            parsed_cve_filters = (
                self.parse_kv_ops_string(self.cve_filters) if self.cve_filters else []
            )
            parsed_observable_filters = (
                self.parse_kv_ops_string(self.observable_filters)
                if self.observable_filters
                else []
            )
            if (
                len(parsed_observable_group_filters) == 0
                and len(parsed_cve_filters) == 0
                and len(parsed_observable_filters) == 0
            ):
                self.write_info(
                    f"[{COMMAND_NAME}]: No filters provided, limiting to 10000 realizations"
                )

            time_preprocessing_start = time.time()

            cve_keys, cve_map = vuln_int_realizations_query_service.prepare_cve_keys(
                cve_filters=parsed_cve_filters,
            )
            if len(cve_keys) == 0 and len(parsed_cve_filters) > 0:
                self.write_warning(
                    f"[{COMMAND_NAME}]: No CVEs found for the provided filters: {self.cve_filters}"
                )
                return
            observable_group_keys, observable_group_map = (
                vuln_int_realizations_query_service.prepare_observable_group_keys(
                    tenant_uid=self.tenant_uid,
                    observable_group_filters=parsed_observable_group_filters,
                )
            )
            if len(observable_group_keys) == 0 and len(parsed_observable_group_filters) > 0:
                self.write_warning(
                    f"[{COMMAND_NAME}]: No observable groups found for the provided filters: {self.observable_group_filters}"
                )
                return
            observable_keys, observable_map = (
                vuln_int_realizations_query_service.prepare_observable_keys(
                    tenant_uid=self.tenant_uid,
                    observable_filters=parsed_observable_filters,
                    observable_group_keys=observable_group_keys,
                )
            )
            if len(observable_keys) == 0 and len(parsed_observable_filters) > 0:
                self.write_warning(
                    f"[{COMMAND_NAME}]: No observables found for the provided filters: {self.observable_filters}"
                )
                return

            self.query = VulnRealizationQuery(
                observable_keys=observable_keys,
                cve_keys=cve_keys,
                realization_filters=parsed_realization_filters,
                tenant=self.tenant_uid,
                earliest=self.earliest,
                latest=self.latest,
                state=self.state,
                time_field=self.time_field,
            )
            duration_preprocessing = time.time() - time_preprocessing_start
            self._datapunctum_logger.info(
                {
                    "action": COMMAND_NAME,
                    "status": "success",
                    "duration_preprocessing": duration_preprocessing,
                    "observable_group_keys": len(observable_group_keys),
                    "cve_keys": len(cve_keys),
                    "observable_keys": len(observable_keys),
                }
            )

            time_search_start = time.time()
            realizations = vuln_int_realizations_query_service.query_realizations_from_search(
                query=self.query,
                limit=self.limit,
            )
            if not realizations:
                self.write_info(
                    f"[{COMMAND_NAME}]: No realizations found for the provided filters"
                )
                return
            duration_search = time.time() - time_search_start

            time_enrichment_start = time.time()
            if len(cve_keys) == 0:
                required_cves = list({realization.cve for realization in realizations})
                self._datapunctum_logger.info(
                    {
                        "action": "fetch_cves",
                        "status": LogEntryStatus.STARTED,
                        "cve_keys": len(required_cves),
                    }
                )
                cves = self.service_factory.vuln_int_cve_dataservice.get_cves_by_id_for_tenant(
                    tenant_uid=self.tenant_uid,
                    cve_ids=required_cves,
                )
                for cve in cves:
                    if cve.cve not in cve_map:
                        cve_map[cve.cve] = cve
                self._datapunctum_logger.info(
                    {"action": "fetch_cves", "status": LogEntryStatus.SUCCESS}
                )

            if len(observable_keys) == 0:
                required_observables_by_type = defaultdict(list)
                for realization in realizations:
                    required_observables_by_type[realization.observable_type].append(
                        realization.observable
                    )

                for observable_type, observable_ids in required_observables_by_type.items():
                    self._datapunctum_logger.info(
                        {
                            "action": "fetch_observables",
                            "status": LogEntryStatus.STARTED,
                            "observable_type": observable_type,
                            "observable_ids": len(observable_ids),
                        }
                    )
                    observable_ids = list(set(observable_ids))
                    observables = self.observables_service.get_observables_by_id(
                        tenant_uid=self.tenant_uid,
                        observable_type=observable_type,
                        ids=observable_ids,
                    )
                    observable_map.update(
                        {observable.get_map_key(): observable for observable in observables}
                    )

                    self._datapunctum_logger.info(
                        {"action": "fetch_observables", "status": LogEntryStatus.SUCCESS}
                    )

            realization_keys = [realization.key for realization in realizations]
            risk_event_map = {}
            if len(realization_keys) > 0:
                self._datapunctum_logger.info(
                    {
                        "action": "fetch_risk_events",
                        "status": LogEntryStatus.STARTED,
                        "realization_keys": len(realization_keys),
                    }
                )

                risk_event_total = 0
                for (
                    risk_events
                ) in self.service_factory.risk_event_service.get_risk_events_for_realizations(
                    tenant_uid=self.tenant_uid,
                    realization_keys=realization_keys,
                ):
                    risk_event_total += len(risk_events)
                    self._datapunctum_logger.info(
                        {
                            "action": "fetch_risk_events",
                            "status": LogEntryStatus.COMPLETED,
                            "risk_events_chunk_size": len(risk_events),
                            "risk_events_total_so_far": risk_event_total,
                        }
                    )
                    for risk_event in risk_events:
                        if risk_event.realization not in risk_event_map:
                            risk_event_map[risk_event.realization] = [risk_event]
                        else:
                            risk_event_map[risk_event.realization].append(risk_event)

            time_enrichment_duration = time.time() - time_enrichment_start

            time_yield_start = time.time()
            for realization in realizations:
                dump = realization.model_dump()
                dump = {
                    f"realization.{key}": value
                    for key, value in dump.items()
                    if key
                    not in [
                        CommonKeys._USER,
                        VulnIntRealizationFields.CVE,
                        VulnIntRealizationFields.OBSERVABLE,
                        VulnIntRealizationFields.OBSERVABLE_TYPE,
                    ]
                }
                realization_risk_events = risk_event_map.get(realization.key, [])
                dump["realization.risk_events_count"] = len(realization_risk_events)
                dump["realization.risk_events_active_count"] = len(
                    [
                        risk_event
                        for risk_event in realization_risk_events
                        if risk_event.status == RiskStatus.ACTIVE
                    ]
                )
                dump["realization.risk_events_fixed_count"] = (
                    dump["realization.risk_events_count"]
                    - dump["realization.risk_events_active_count"]
                )
                dump["realization.risk_events"] = [
                    risk_event.model_dump() for risk_event in realization_risk_events
                ]

                observable = observable_map.get(
                    Observable.build_map_key(
                        observable_type=realization.observable_type,
                        observable_key=realization.observable,
                    )
                )
                if observable:
                    dump.update(observable.dump_for_search(prefix="observable"))
                if observable and observable.observable_group:
                    observable_group = observable_group_map.get(
                        ObservableGroup.build_map_key(
                            scope=observable.type,
                            key=observable.observable_group,
                        )
                    )
                    if observable_group:
                        dump.update(
                            self.observable_group_to_result_representation(
                                observable_group=observable_group
                            )
                        )

                dump.update(self.cve_to_result_representation(cve=cve_map[realization.cve]))
                yield self.gen_record(**dump)

            duration_yield = time.time() - time_yield_start
            self.write_info(
                f"[{COMMAND_NAME}]: Finished processing realizations, took {round(time.time() - start_time, 1)} seconds"
            )

            self._datapunctum_logger.info(
                {
                    "action": COMMAND_NAME,
                    "status": "success",
                    "duration_preprocessing": round(duration_preprocessing, 2),
                    "duration_search": round(duration_search, 2),
                    "duration_enrichment": round(time_enrichment_duration, 2),
                    "duration_yield": round(duration_yield, 2),
                    "realizations": len(realizations),
                    "cves": len(cve_map),
                    "observables": len(observable_map),
                    "observable_groups": len(observable_group_map),
                }
            )

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


dispatch(amevulnintrealizations, sys.argv, sys.stdin, sys.stdout, __name__)
