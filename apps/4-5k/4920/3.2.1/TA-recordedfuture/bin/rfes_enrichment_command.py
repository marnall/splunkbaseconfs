#!/usr/bin/env python
import logging
import sys
from typing import Generator, Tuple, Set

import requests

from vendor.splunklib.searchcommands import (
    StreamingCommand,
    dispatch,
    Configuration,
    Option,
    validators,
)

from recordedfuture.api.rfclient import RFClient
from recordedfuture.core.app_env import RfesAppEnv
from recordedfuture.core.constants import SOAR_LOOKUP_ENTITIES_MAX_COUNT
from recordedfuture.core.logging import setup_logging
from recordedfuture.metrics.timeit import Timeit


MAX_RECORDS = 10000


def generator_to_list_in_chunks(
    generator: Generator, chunk_size: int
) -> Generator[list, None, None]:
    """
    Gather results from generator into a list of specified size and yields the chunks.

    Args:
        generator: to gather results from.
        chunk_size: max size of each chunk.

    Returns:
        list with gathered results from original generator.
    """
    chunk = []
    for item in generator:
        chunk.append(item)
        if len(chunk) == chunk_size:
            yield chunk
            chunk = []
    # The last portion of items
    if chunk:
        yield chunk


ENTITY_TYPES = (
    "ip",
    "domain",
    "url",
    "hash",
    "vulnerability",
)


@Configuration(distributed=False)
class EnrichmentCommand(StreamingCommand):
    """Enrich events based on the entity type and field name."""

    ip = Option(
        doc="""**Syntax:** *ip=<field_name>*
            **Description:** IP field name to enrich with Recorded Future intelligence.""",
        validate=validators.Fieldname(),
    )

    domain = Option(
        doc="""**Syntax:** *domain=<field_name>*
            **Description:** domain field name to enrich with Recorded Future intelligence.""",
        validate=validators.Fieldname(),
    )

    url = Option(
        doc="""**Syntax:** *url=<field_name>*
            **Description:** url field name to enrich with Recorded Future intelligence.""",
        validate=validators.Fieldname(),
    )

    hash = Option(
        doc="""**Syntax:** *hash=<field_name>*
            **Description:** hash field name to enrich with Recorded Future intelligence.""",
        validate=validators.Fieldname(),
    )

    vulnerability = Option(
        doc="""**Syntax:** *vulnerability=<field_name>*
            **Description:** vulnerability field name to enrich with Recorded Future intelligence.""",
        validate=validators.Fieldname(),
    )

    api_key = Option(
        doc="""**Syntax:** *api_key=<string>*
            **Description:** an alternative way to specify Recorded Future API key.""",
    )

    def __init__(self):
        super().__init__()
        self.rf_logger = setup_logging()
        self.cache = {}
        self.records_count = 0

    def stream(
        self, records: Generator[dict, None, None]
    ) -> Generator[dict, None, None]:
        """Enrich records with Recorded Future intelligence"""
        # We need at least WARNING level here in order to see the log
        with Timeit(log_level=logging.WARNING) as timeit:
            timeit.label = "enrichment_command"

            entity_type, field_name = self._get_entity_type_field_name()
            # Simulating in_dict here to properly set session key and server URI for RfesAppEnv
            in_dict = {
                "session_key": self.metadata.searchinfo.session_key,
                "server_uri": self.metadata.searchinfo.splunkd_uri,
            }
            app_env = RfesAppEnv(
                in_dict, self.rf_logger, modalert=True, api_key=self.api_key
            )
            rf_client = RFClient(app_env)

            for chunk in generator_to_list_in_chunks(
                records, SOAR_LOOKUP_ENTITIES_MAX_COUNT
            ):
                iocs = set()
                for record in chunk:
                    if record.get(field_name):  # we don't want empty strings or None
                        iocs.add(record[field_name])

                iocs = (
                    iocs - self.cache.keys()
                )  # filtering out IOCs that are already cached

                self._fetch_soar_and_populate_cache(rf_client, entity_type, iocs)

                for record in chunk:
                    if record.get(field_name) in self.cache:
                        cached_data = self.cache[record.get(field_name)]
                        record["rf_risk"] = cached_data["risk"]
                        record["rf_rules"] = cached_data["rules"]
                    else:
                        # We want to set these field always, otherwise we might lose the fields in other records
                        record["rf_risk"] = ""
                        record["rf_rules"] = ""
                    yield record

                self.records_count += len(chunk)
                if self.records_count >= MAX_RECORDS:
                    break

            for record in records:
                yield record

    def _fetch_soar_and_populate_cache(
        self, rf_client: RFClient, entity_type: str, iocs: Set[str]
    ):
        if not iocs:
            return

        try:
            soar_data = rf_client.lookup.soar_enrichment(
                {entity_type: sorted(list(iocs))}
            )
        except requests.HTTPError as err:
            self.rf_logger.warning(
                f"Failed to get SOAR enrichment data for portion of IOCs: {err}. Proceeding to next events."
            )
            return

        for result in soar_data.get("results", []):
            entity_name = result.get("entity", {}).get("name")
            risk = result.get("risk", {})
            self.cache[entity_name] = {
                "risk": risk.get("score"),
                "rules": [
                    rule_evidence.get("rule")
                    for rule_evidence in risk.get("rule", {})
                    .get("evidence", {})
                    .values()
                ],
            }

    def _get_entity_type_field_name(self) -> Tuple[str, str]:
        for entity_type in ENTITY_TYPES:
            field_name = getattr(self, entity_type)
            if field_name:
                return entity_type, field_name
        raise ValueError(
            f"You must specify one of the entity types: {', '.join(ENTITY_TYPES)}"
        )


dispatch(EnrichmentCommand, sys.argv, sys.stdin, sys.stdout, __name__)
