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


@Configuration(type="reporting", streaming=False)
class AxiomTimechart(AxiomCommandRuntimeMixin, GeneratingCommand):
    """Run row-oriented time-series aggregations against Axiom."""

    command_name = "axtimechart"

    def __init__(self):
        super(AxiomTimechart, self).__init__()
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

    agg = Option(
        doc="""
        **Syntax:** agg=<string>
        **Description:** Aggregation such as count, avg(duration), or count as events. Defaults to count.
        """,
        require=False,
        default="count",
        validate=validators.Match("agg", r".*"),
    )

    span = Option(
        doc="""
        **Syntax:** span=<duration>
        **Description:** APL duration for time buckets, such as 30s, 5m, 1h, or 1d.
        """,
        require=False,
        default="1m",
        validate=validators.Match("span", r".+"),
    )

    by = Option(
        doc="""
        **Syntax:** by=<field>
        **Description:** Optional field to split the series by.
        """,
        require=False,
        default=None,
        validate=validators.Match("by", r".*"),
    )

    limit = Option(
        doc="""
        **Syntax:** limit=<integer>
        **Description:** Maximum time-series rows to return. Defaults to 10000.
        """,
        require=False,
        default=10000,
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
        return AplPipeline.build_timechart_apl(
            self.dataset,
            q=getattr(self, "q", None),
            agg=getattr(self, "agg", "count"),
            span=getattr(self, "span", "1m"),
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
            # Reporting output is a stats table, so skip _raw and the host/source/
            # sourcetype metadata: they would show up as columns in every chart.
            yield AxiomResponseMapper.row_to_splunk_event(
                row,
                event_fields={"axiom_dataset": self.dataset},
                include_raw=False,
            )


if __name__ == "__main__":
    dispatch(AxiomTimechart, sys.argv, sys.stdin, sys.stdout, __name__)
