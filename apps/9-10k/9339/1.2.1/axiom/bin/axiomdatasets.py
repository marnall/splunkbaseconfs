#!/usr/bin/env python
# coding=utf-8

import os
import sys
import requests

# Splunk Libraries
import splunk.mining.dcutils as dcu
# add splunklib to lib path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (
    dispatch, GeneratingCommand, Configuration, Option, validators
)
import splunklib.client as client

from axiom_common import (
    AxiomCommandRuntimeMixin,
    AxiomResponseMapper,
    dict_to_kv_str,
)

# initialise logger
logger = dcu.getLogger()
logger.setLevel('INFO')

@Configuration(type='events', retainsevents=True, streaming=False)
class AxiomGetDatasets(AxiomCommandRuntimeMixin, GeneratingCommand):
    command_name = "axdatasets"

    def __init__(self):
        """Initialise the AxiomGetDatasets command with a unique per-instance job ID."""
        super(AxiomGetDatasets, self).__init__()
        self.initialize_runtime(create_session=False, install_signal_handlers=False)

    tokenName = Option(
        doc='''
        **Syntax:** tokenName=<string>
        **Description:** Optional argument. This field should contain the name for the Axiom API key.
        **Default:** Default is no option given. To make it easier, if you call your token axiom_token, you will not need to specify this argument.''',
        require=False,  # tokenName is optional
        default="axiom_token",  # Default value is "axiom_token"
        validate=validators.Match("tokenName", r'.*')  # Accept any string for token
    )
    
    mgmtPort = Option(
        doc='''
        **Syntax:** mgmtPort=<integer>
        **Description:** Optional argument. Instructs this instance which management port Splunk is running on
        **Default:** 8089
        ''',
        require=False,
        default=None,
        validate=validators.Integer()   # check argument is an integer
    )
    
    def dict_to_kv_str(self, d):
        """Convert a dictionary to a comma-separated 'key=value' string for logging."""
        return dict_to_kv_str(d)

    def generate(self):
        """Fetch all accessible Axiom datasets and yield each as a Splunk event."""
        if not self.mgmtPort:
            self.mgmtPort = self.get_mgmt_port()

        axiom_token = self.get_axiom_token()    # get the Axiom API token from Splunk cred store.

        api_response = self.get_axiom_datasets(axiom_token)
        data = api_response.json()
        yield from AxiomResponseMapper.resource_records_to_events(data)

if __name__ == "__main__":
    # Dispatch the command to Splunk
    dispatch(AxiomGetDatasets, sys.argv, sys.stdin, sys.stdout, __name__)
