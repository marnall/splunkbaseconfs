#!/usr/bin/env python
# coding=utf-8

import os
import sys
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
class AxiomSample(AxiomCommandRuntimeMixin, GeneratingCommand):
    """Fetch recent sample events from an Axiom dataset."""

    command_name = "axsample"

    def __init__(self):
        super(AxiomSample, self).__init__()
        self.initialize_runtime()

    dataset = Option(
        doc="""
        **Syntax:** dataset=<string>
        **Description:** Required Axiom dataset ID to sample.
        """,
        require=True,
        validate=validators.Match("dataset", r".+"),
    )

    limit = Option(
        doc="""
        **Syntax:** limit=<integer>
        **Description:** Maximum sample events to return. Defaults to 20.
        """,
        require=False,
        default=20,
        validate=validators.Integer(),
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

    def build_apl(self):
        return AplPipeline.build_sample_apl(
            self.dataset,
            limit=self.limit,
            fields=getattr(self, "fields", None),
        )

    def generate(self):
        if self.exit_requested:
            return

        if not self.mgmtPort:
            self.mgmtPort = self.get_mgmt_port()

        start_time, end_time = self.resolve_query_time_range()
        apl = self.build_apl()
        axiom_token = self.get_axiom_token()
        api_response = self.post_to_axiom(apl, start_time, end_time, axiom_token)
        table = AxiomResponseMapper.get_query_data(api_response.json())

        for row in AxiomResponseMapper.iter_table_rows(table):
            if self.exit_requested:
                break
            yield AxiomResponseMapper.row_to_splunk_event(
                row,
                source="axiomsample.py",
                event_fields={"axiom_dataset": self.dataset},
            )


if __name__ == "__main__":
    dispatch(AxiomSample, sys.argv, sys.stdin, sys.stdout, __name__)
