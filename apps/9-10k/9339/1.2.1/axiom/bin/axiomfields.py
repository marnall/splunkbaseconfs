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
    AxiomCommandRuntimeMixin,
    AxiomResponseMapper,
)


logger = dcu.getLogger()
logger.setLevel("INFO")


@Configuration(type="events", retainsevents=True, streaming=False)
class AxiomFields(AxiomCommandRuntimeMixin, GeneratingCommand):
    """List fields for an Axiom dataset as Splunk events."""

    command_name = "axfields"

    def __init__(self):
        super(AxiomFields, self).__init__()
        self.initialize_runtime(create_session=False, install_signal_handlers=False)

    dataset = Option(
        doc="""
        **Syntax:** dataset=<string>
        **Description:** Required Axiom dataset ID to inspect.
        """,
        require=True,
        validate=validators.Match("dataset", r".+"),
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

    def generate(self):
        if not self.mgmtPort:
            self.mgmtPort = self.get_mgmt_port()

        axiom_token = self.get_axiom_token()
        api_response = self.get_axiom_fields(axiom_token)
        yield from AxiomResponseMapper.resource_records_to_events(api_response.json())


if __name__ == "__main__":
    dispatch(AxiomFields, sys.argv, sys.stdin, sys.stdout, __name__)
