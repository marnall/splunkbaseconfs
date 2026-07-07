#!/usr/bin/env python3.9
#
# File: command_amevulnintstagedrealizations.py - Version 3.8.1
# Copyright © Datapunctum AG 2026-04-07
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import annotations

import os
import sys
import time
from collections import defaultdict
from collections.abc import Generator
from http import HTTPStatus

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import Configuration, GeneratingCommand, Option, dispatch

from ame.command_ame import AmeCommand
from ame.consts.AppSettings import AppIntSettings
from ame.consts.Handlers import SITEPATH
from ame.handlers.payloads.VulnIntStagedRealizationsHandlerPayloads import (
    VulnInStagedRealizationsQueryPayload,
)
from ame.models.vuln_int.fields.VulnIntCVEFields import (
    VulnIntCVEFields,
    VulnIntCVEInternalFields,
)
from ame.models.vuln_int.fields.VulnIntStagedRealizationFields import (
    VulnIntStagedRealizationFields,
)
from ame.models.vuln_int.VulnIntStagedRealization import (
    VulnIntStagedRealization,
)
from dpshared.consts.CommonKeys import CommonKeys
from dpshared.consts.LogEntryStatus import LogEntryStatus
from dpshared.exceptions import PublicException
from dpshared.models.FastAPIResponse import InternalResponse
from dpshared.utilities.LRUCache import LRUCache
from dpshared.utilities.TruthyUtility import is_truthy

COMMAND_NAME = "amevulnintstagedrealizations"
ENRICHMENT_BATCH_SIZE = 1000
ENRICHMENT_CACHE_SIZE = 10000


@Configuration(type="reporting")
class amevulnintstagedrealizations(GeneratingCommand, AmeCommand):  # noqa: N801
    """
    ##Syntax
    |amevulnintstagedrealizations
    ##Description
    Custom search command to fetch staged vulnerability realizations.
    """

    cves = Option(require=False, default=[])
    tenant_uid = Option(require=True)
    time_field = Option(require=False, default=VulnIntStagedRealizationFields.LAST_SEEN)
    include_fixed = Option(require=False, default=False)
    enrich_cve = Option(require=False, default=False)
    reason = Option(require=False, default="all")

    def __init__(self) -> None:
        GeneratingCommand.__init__(self)
        AmeCommand.__init__(self)
        self.cve_cache: LRUCache[str, dict] = LRUCache[str, dict](
            capacity=ENRICHMENT_CACHE_SIZE, manual=True
        )

    def setup_query(self) -> None:
        earliest = int(self._metadata.searchinfo.earliest_time)
        latest = int(self._metadata.searchinfo.latest_time)
        self.enrich_cve = is_truthy(self.enrich_cve)

        if latest == 0:
            latest = 2147483647

        self.query = VulnInStagedRealizationsQueryPayload(
            cves=self.cves.split(",") if self.cves else [],
            earliest=earliest,
            latest=latest,
            time_field=self.time_field,
            include_fixed=self.include_fixed,
            reason=self.reason,
        )

    def enrich_with_cve(
        self, staged_realizations: list[VulnIntStagedRealization]
    ) -> dict[str, dict]:
        cve_ids = list({realization.payload.cve for realization in staged_realizations})

        uncached_cves = list({cve for cve in cve_ids if cve not in self.cve_cache})
        if len(uncached_cves) > 0:
            cve_ids = self.service_factory.vuln_int_cve_dataservice.get_cves_by_id_for_tenant(
                tenant_uid=self.tenant_uid, cve_ids=uncached_cves
            )
            for cve in cve_ids:
                self.cve_cache[cve.cve] = cve.model_dump(
                    exclude={VulnIntCVEInternalFields.SOURCE_TRACKING}
                )
        enriched_context: dict[str, dict] = defaultdict(dict)
        for realization in staged_realizations:
            if realization.payload.cve in self.cve_cache:
                cve = self.cve_cache[realization.payload.cve]
                for key, value in cve.items():
                    if key in [
                        VulnIntCVEFields.CVE,
                        VulnIntCVEFields.DESCRIPTION,
                        CommonKeys._KEY,
                        CommonKeys.DELETED,
                    ]:
                        continue
                    enriched_context[realization.key][f"cve.{key}"] = value

        self.cve_cache.enforce_cache_size()
        return enriched_context

    def fetch_staged_realizations_generator(
        self,
    ) -> Generator[VulnIntStagedRealization, None, None]:
        skip = 0
        limit = AppIntSettings.VULN_INT_STAGED_REALIZATION_PAGE_SIZE
        processed_batches = 0

        while True:
            response = self.sdk_wrapper.get_internal_endpoint(
                endpoint=SITEPATH.AME_VULN_INT_STAGED_REALIZATIONS,
                payload_type=InternalResponse[list[VulnIntStagedRealization]],
                skip=skip,
                limit=limit,
                tenant_uid=self.tenant_uid,
                **self.query.get_kwargs(),
            )
            if response.status != HTTPStatus.OK or response.payload is None:
                self._datapunctum_logger.error(
                    {
                        "action": "fetch_staged_realizations_generator",
                        "status": LogEntryStatus.FAILED,
                        "response": response.model_dump(),
                        "messages": [message.model_dump() for message in response.messages],
                    }
                )
                raise PublicException(
                    f"Failed to fetch staged realizations: {response.status} - {', '.join([message.text for message in response.messages])}"
                )
            batch = response.payload
            if len(batch) == 0:
                self._datapunctum_logger.debug(
                    {
                        "action": "fetch_staged_realizations_generator",
                        "status": LogEntryStatus.SUCCESS,
                        "username": self.username,
                        "num_batches_processed": processed_batches,
                    }
                )
                break
            skip += limit
            yield from batch
            processed_batches += 1

        self._datapunctum_logger.debug(
            {
                "action": "fetch_staged_realizations_generator",
                "status": LogEntryStatus.SUCCESS,
                "username": self.username,
                "num_batches_processed": processed_batches,
            }
        )

    def dump_staged_realization(
        self, staged_realization: VulnIntStagedRealization, additional_dicts: list[dict]
    ) -> dict:
        dump = staged_realization.model_dump()
        del dump[VulnIntStagedRealizationFields.PAYLOAD]
        dump[VulnIntStagedRealizationFields.PAYLOAD_VALUE] = staged_realization.payload.value
        dump[VulnIntStagedRealizationFields.PAYLOAD_CVE] = staged_realization.payload.cve
        dump[VulnIntStagedRealizationFields.PAYLOAD_STATUS] = staged_realization.payload.status

        for additional_dict in additional_dicts:
            dump.update(additional_dict)
        return dump

    def generate(self) -> Generator[dict, None, None]:
        try:
            start_time = time.time()
            self.setup_metadata()
            self.setup_query()

            self._datapunctum_logger.debug(
                {
                    "action": "generate",
                    "status": "success",
                    "username": self.username,
                    "earliest": self.query.earliest,
                    "latest": self.query.latest,
                    "query": self.query,
                    "enrich_cve": self.enrich_cve,
                }
            )
            num_processed_entries = 0
            enrichment_batch: list[VulnIntStagedRealization] = []
            for staged_realization in self.fetch_staged_realizations_generator():
                if not self.enrich_cve:
                    num_processed_entries += 1
                    yield self.gen_record(
                        **self.dump_staged_realization(
                            staged_realization=staged_realization, additional_dicts=[]
                        )
                    )
                    continue
                if len(enrichment_batch) >= ENRICHMENT_BATCH_SIZE:
                    enrichments = self.enrich_with_cve(staged_realizations=enrichment_batch)
                    for staged_realization in enrichment_batch:
                        dump = self.dump_staged_realization(
                            staged_realization=staged_realization,
                            additional_dicts=[enrichments[staged_realization.key]],
                        )
                        num_processed_entries += 1
                        yield self.gen_record(**dump)
                    enrichment_batch = []
                enrichment_batch.append(staged_realization)

            if len(enrichment_batch) > 0:
                enrichments = self.enrich_with_cve(staged_realizations=enrichment_batch)
                for staged_realization in enrichment_batch:
                    dump = self.dump_staged_realization(
                        staged_realization=staged_realization,
                        additional_dicts=[enrichments[staged_realization.key]],
                    )
                    num_processed_entries += 1
                    yield self.gen_record(**dump)

            self._datapunctum_logger.debug(
                {
                    "action": "generate",
                    "status": LogEntryStatus.SUCCESS,
                    "username": self.username,
                    "num_processed_entries": num_processed_entries,
                }
            )
            self.write_info(
                f"[{COMMAND_NAME}]: Finished processing staged realizations, took {round(time.time() - start_time, 1)} seconds"
            )

        except Exception as exc:
            self._datapunctum_logger.exception(
                {
                    "action": "generate",
                    "status": "failed",
                    "user": self._metadata.searchinfo.username
                    if hasattr(self._metadata.searchinfo, "username")
                    else "unknown",
                }
            )
            raise exc


dispatch(amevulnintstagedrealizations, sys.argv, sys.stdin, sys.stdout, __name__)
