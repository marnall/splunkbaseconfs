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
class AxiomSearch(AxiomCommandRuntimeMixin, GeneratingCommand):
    """Run a simple generated APL search for an Axiom dataset."""

    command_name = "axsearch"

    def __init__(self):
        super(AxiomSearch, self).__init__()
        self.initialize_runtime()

    dataset = Option(
        doc="""
        **Syntax:** dataset=<string>
        **Description:** Required Axiom dataset ID to search.
        """,
        require=True,
        validate=validators.Match("dataset", r".+"),
    )

    search = Option(
        doc="""
        **Syntax:** search=<string>
        **Description:** Optional full-event search text.
        """,
        require=False,
        default=None,
        validate=validators.Match("search", r".*"),
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

    where = Option(
        doc="""
        **Syntax:** where=<string>
        **Description:** Optional APL where expression for structured filtering.
        """,
        require=False,
        default=None,
        validate=validators.Match("where", r".*"),
    )

    fields = Option(
        doc="""
        **Syntax:** fields=<comma-separated-list>
        **Description:** Optional fields to keep in returned events.
        """,
        require=False,
        default=None,
        validate=validators.Match("fields", r".*"),
    )

    sort = Option(
        doc="""
        **Syntax:** sort=<string>
        **Description:** Optional APL sort expression. Defaults to _time desc.
        """,
        require=False,
        default="_time desc",
        validate=validators.Match("sort", r".*"),
    )

    limit = Option(
        doc="""
        **Syntax:** limit=<integer>
        **Description:** Maximum events to return. Defaults to 100.
        """,
        require=False,
        default=100,
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

    startTime = Option(
        doc="""
        **Syntax:** startTime=<string>
        **Description:** Optional Axiom query start time.
        """,
        require=False,
    )

    endTime = Option(
        doc="""
        **Syntax:** endTime=<string>
        **Description:** Optional Axiom query end time.
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
        return AplPipeline.build_search_apl(
            self.dataset,
            q=getattr(self, "q", None),
            search=getattr(self, "search", None),
            where=getattr(self, "where", None),
            fields=getattr(self, "fields", None),
            sort=getattr(self, "sort", "_time desc"),
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
                source="axiomsearch.py",
                event_fields={"axiom_dataset": self.dataset},
            )


if __name__ == "__main__":
    dispatch(AxiomSearch, sys.argv, sys.stdin, sys.stdout, __name__)
