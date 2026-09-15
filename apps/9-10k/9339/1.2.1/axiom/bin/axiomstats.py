#!/usr/bin/env python
# coding=utf-8

import os
import sys
from time import time

import requests
import splunk.mining.dcutils as dcu

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    GeneratingCommand,
    Option,
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


@Configuration(type="events", retainsevents=True, streaming=False)
class AxiomStats(AxiomCommandRuntimeMixin, GeneratingCommand):
    """Run pushed-down Axiom aggregations using Splunk-shaped options."""

    command_name = "axstats"

    def __init__(self):
        super(AxiomStats, self).__init__()
        self.initialize_runtime()

    dataset = Option(
        doc="""
        **Syntax:** dataset=<string>
        **Description:** Required Axiom dataset ID to aggregate.
        """,
        require=True,
        validate=validators.Match("dataset", r".+"),
    )

    q = Option(
        doc="""
        **Syntax:** q=<string>
        **Description:** Optional Splunk-like search expression compiled to APL search syntax.
        """,
        require=False,
        default=None,
        validate=validators.Match("q", r".*"),
    )

    stats = Option(
        doc="""
        **Syntax:** stats=<string>
        **Description:** Aggregations such as count, avg(duration), sum(bytes) as total_bytes.
        """,
        require=False,
        default="count",
        validate=validators.Match("stats", r".*"),
    )

    by = Option(
        doc="""
        **Syntax:** by=<comma-separated-list>
        **Description:** Optional fields to group by.
        """,
        require=False,
        default=None,
        validate=validators.Match("by", r".*"),
    )

    limit = Option(
        doc="""
        **Syntax:** limit=<integer>
        **Description:** Maximum grouped rows to return. Defaults to 1000.
        """,
        require=False,
        default=1000,
        validate=validators.Integer(),
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

    startTime = Option(require=False)
    endTime = Option(require=False)
    earliest = Option(require=False)
    latest = Option(require=False)

    explain = Option(
        doc="""
        **Syntax:** explain=<bool>
        **Description:** Return the compiled APL and resolved context without querying Axiom.
        """,
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    def build_apl(self):
        return AplPipeline.build_stats_apl(
            self.dataset,
            q=getattr(self, "q", None),
            stats=getattr(self, "stats", "count"),
            by=getattr(self, "by", None),
            limit=self.limit,
        )

    def generate(self):
        if self.exit_requested:
            return

        if not self.mgmtPort:
            self.mgmtPort = self.get_mgmt_port()

        start_time, end_time = self.resolve_query_time_range()
        apl = self.build_apl()
        if self.explain:
            yield {
                "_time": int(time()),
                "command": self.command_name,
                "dataset": self.dataset,
                "compiled_apl": apl,
                "startTime": start_time,
                "endTime": end_time,
                "explain": True,
            }
            return

        axiom_token = self.get_axiom_token()
        api_response = self.post_to_axiom(apl, start_time, end_time, axiom_token)
        table = AxiomResponseMapper.get_query_data(api_response.json())

        for row in AxiomResponseMapper.iter_table_rows(table):
            if self.exit_requested:
                break
            yield AxiomResponseMapper.row_to_splunk_event(
                row,
                source="axiomstats.py",
                event_fields={"axiom_dataset": self.dataset},
            )


if __name__ == "__main__":
    dispatch(AxiomStats, sys.argv, sys.stdin, sys.stdout, __name__)
