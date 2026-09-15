#!/usr/bin/env python
# coding=utf-8

import os
import sys
import requests

import splunk.mining.dcutils as dcu

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    Option,
    StreamingCommand,
    dispatch,
    validators,
)
import splunklib.client as client  # noqa: E402

from axiom_common import (  # noqa: E402
    AplPipeline,
    AxiomCommandRuntimeMixin,
    AxiomResponseMapper,
)


logger = dcu.getLogger()
logger.setLevel("INFO")


@Configuration(local=True, distributed=False)
class AxiomLookup(AxiomCommandRuntimeMixin, StreamingCommand):
    """Look up Axiom context rows and add selected fields to incoming Splunk events."""

    command_name = "axlookup"

    def __init__(self):
        super(AxiomLookup, self).__init__()
        self.initialize_runtime()
        self._enrichment_cache = {}

    dataset = Option(
        doc="""
        **Syntax:** dataset=<string>
        **Description:** Required Axiom dataset ID to use as the lookup source.
        """,
        require=True,
        validate=validators.Match("dataset", r".+"),
    )

    on = Option(
        doc="""
        **Syntax:** on=<field>|<splunk-field>=<axiom-field>
        **Description:** Required join key. Use one field name for matching names, or map Splunk to Axiom field names.
        """,
        require=True,
        validate=validators.Match("on", r".+"),
    )

    fields = Option(
        doc="""
        **Syntax:** fields=<comma-separated-list>
        **Description:** Required Axiom fields to add to each matching Splunk event.
        """,
        require=True,
        validate=validators.Match("fields", r".+"),
    )

    prefix = Option(
        doc="""
        **Syntax:** prefix=<string>
        **Description:** Prefix for fields added by the lookup. Defaults to axiom_.
        """,
        require=False,
        default="axiom_",
        validate=validators.Match("prefix", r".*"),
    )

    overwrite = Option(
        doc="""
        **Syntax:** overwrite=<boolean>
        **Description:** Whether lookup fields may replace existing Splunk event fields.
        """,
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    batchSize = Option(
        doc="""
        **Syntax:** batchSize=<integer>
        **Description:** Maximum distinct join values per Axiom lookup query. Defaults to 250.
        """,
        require=False,
        default=250,
        validate=validators.Integer(),
    )

    maxFields = Option(
        doc="""
        **Syntax:** maxFields=<integer>
        **Description:** Maximum fields to add when fields=* is used. Defaults to 50.
        """,
        require=False,
        default=50,
        validate=validators.Integer(),
    )

    strict = Option(
        doc="""
        **Syntax:** strict=<boolean>
        **Description:** Whether Axiom lookup failures should fail the Splunk search. Defaults to true.
        """,
        require=False,
        default=True,
        validate=validators.Boolean(),
    )

    tokenName = Option(
        doc="""
        **Syntax:** tokenName=<string>
        **Description:** Optional Axiom API token name in Splunk storage/passwords.
        """,
        require=False,
        default="axiom_token",
        validate=validators.Match("tokenName", r".*"),
    )

    mgmtPort = Option(
        doc="""
        **Syntax:** mgmtPort=<integer>
        **Description:** Optional Splunk management port. Defaults to autodetection, then 8089.
        """,
        require=False,
        default=None,
        validate=validators.Integer(),
    )

    startTime = Option(
        doc="""
        **Syntax:** startTime=<string>
        **Description:** Optional Axiom lookup query start time.
        """,
        require=False,
    )

    endTime = Option(
        doc="""
        **Syntax:** endTime=<string>
        **Description:** Optional Axiom lookup query end time.
        """,
        require=False,
    )

    earliest = Option(
        doc="""
        **Syntax:** earliest=<string>
        **Description:** Optional Splunk-style alias for startTime.
        """,
        require=False,
    )

    latest = Option(
        doc="""
        **Syntax:** latest=<string>
        **Description:** Optional Splunk-style alias for endTime.
        """,
        require=False,
    )

    def build_apl(self, axiom_key_field, values):
        return AplPipeline.build_enrich_apl(
            self.dataset,
            axiom_key_field,
            values,
            self.fields,
        )

    def fetch_enrichment(self, token, axiom_key_field, values, start_time, end_time):
        enrichment = {}
        axiom_key_output = AplPipeline.output_field_name(axiom_key_field)

        for batch in AplPipeline.iter_value_batches(values, self.batchSize):
            if self.exit_requested:
                break
            apl = self.build_apl(axiom_key_field, batch)
            api_response = self.post_to_axiom(apl, start_time, end_time, token)
            table = AxiomResponseMapper.get_query_data(api_response.json())
            enrichment.update(AxiomResponseMapper.rows_by_key(table, axiom_key_output))

        return enrichment

    def get_enrichment_cache(self):
        cache = getattr(self, "_enrichment_cache", None)
        if cache is None:
            cache = {}
            self._enrichment_cache = cache
        return cache

    def enrichment_cache_key(self, axiom_key_field, value, start_time, end_time):
        return (
            self.dataset,
            axiom_key_field,
            type(value).__name__,
            repr(value),
            self.fields,
            start_time,
            end_time,
        )

    def get_cached_enrichment(self, axiom_key_field, values, start_time, end_time):
        cache = self.get_enrichment_cache()
        enrichment = {}
        missing_values = []

        for value in values:
            cache_key = self.enrichment_cache_key(axiom_key_field, value, start_time, end_time)
            if cache_key not in cache:
                missing_values.append(value)
                continue

            row = cache[cache_key]
            if row:
                enrichment[str(value)] = row

        return enrichment, missing_values

    def cache_enrichment(self, axiom_key_field, values, start_time, end_time, fetched_rows):
        cache = self.get_enrichment_cache()
        for value in values:
            cache_key = self.enrichment_cache_key(axiom_key_field, value, start_time, end_time)
            cache[cache_key] = fetched_rows.get(str(value))

    def is_strict(self):
        strict = getattr(self, "strict", True)
        return True if strict is None else bool(strict)

    def get_max_fields(self):
        return AplPipeline.validate_limit(
            getattr(self, "maxFields", None),
            default_limit=50,
            max_limit=500,
        )

    def lookup_output_field(self, field, used_fields):
        safe_field = AplPipeline.splunk_field_name(field)
        output_field = f"{self.prefix}{safe_field}" if self.prefix else safe_field
        base_field = output_field
        suffix = 2
        while output_field in used_fields:
            output_field = f"{base_field}_{suffix}"
            suffix += 1
        used_fields.add(output_field)
        return output_field

    def add_lookup_metadata(self, record):
        for field, value in (
            ("axiom_dataset", self.dataset),
            ("axiom_lookup_dataset", self.dataset),
        ):
            if self.overwrite or field not in record:
                record[field] = value

    def enrich_record(self, record, enrichment_row):
        requested_fields = AplPipeline.field_list(self.fields)
        if "*" in requested_fields:
            output_fields = [field for field in enrichment_row.keys() if field != "_time"]
            max_fields = self.get_max_fields()
            if len(output_fields) > max_fields:
                logger.warning(
                    f"{self.log_prefix()}, axlookup_fields_truncated={len(output_fields)}, maxFields={max_fields}"
                )
                output_fields = output_fields[:max_fields]
        else:
            output_fields = [AplPipeline.output_field_name(field) for field in requested_fields]

        used_fields = {"axiom_dataset", "axiom_lookup_dataset"}
        for field in output_fields:
            if field not in enrichment_row:
                continue
            output_field = self.lookup_output_field(field, used_fields)
            if self.overwrite or output_field not in record:
                record[output_field] = enrichment_row[field]

        self.add_lookup_metadata(record)
        return record

    def stream(self, records):
        records = list(records)
        if not records:
            return

        if self.exit_requested:
            for record in records:
                yield record
            return

        if not self.mgmtPort:
            self.mgmtPort = self.get_mgmt_port()

        local_key_field, axiom_key_field = AplPipeline.parse_field_mapping(self.on)
        values = [record.get(local_key_field) for record in records]
        unique_values = AplPipeline.unique_values(values)
        if not unique_values:
            for record in records:
                yield record
            return

        start_time, end_time = self.resolve_query_time_range()
        enrichment, missing_values = self.get_cached_enrichment(
            axiom_key_field,
            unique_values,
            start_time,
            end_time,
        )
        if missing_values:
            axiom_token = self.get_axiom_token()
            try:
                fetched_enrichment = self.fetch_enrichment(
                    axiom_token,
                    axiom_key_field,
                    missing_values,
                    start_time,
                    end_time,
                )
            except Exception as err:
                if self.is_strict():
                    raise
                logger.warning(f"{self.log_prefix()}, axlookup_failure_ignored={err}")
                fetched_enrichment = {}

            self.cache_enrichment(
                axiom_key_field,
                missing_values,
                start_time,
                end_time,
                fetched_enrichment,
            )
            enrichment.update(fetched_enrichment)

        for record in records:
            if self.exit_requested:
                yield record
                continue

            key = record.get(local_key_field)
            enrichment_row = enrichment.get(str(key))
            if enrichment_row:
                record = self.enrich_record(record, enrichment_row)
            yield record


if __name__ == "__main__":
    dispatch(AxiomLookup, sys.argv, sys.stdin, sys.stdout, __name__)
