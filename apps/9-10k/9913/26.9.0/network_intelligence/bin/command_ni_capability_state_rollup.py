"""Splunk search-command entry point for capability current-state rollups."""

import os
import sys
from itertools import chain

sys.path.insert(0, os.path.dirname(__file__))

import import_declare_test  # noqa: E402,F401
from health.capability_state_rollup import (  # noqa: E402
    latest_capability_records,
    rollup_capability_states,
)
from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    ReportingCommand,
    dispatch,
)


@Configuration(requires_preop=True)
class NiCapabilityStateRollupCommand(ReportingCommand):
    """Create one current-state row per subject and capability."""

    def __init__(self):
        super().__init__()
        self._reduce_candidates = []

    @Configuration(local=True)
    def map(self, records):
        yield from latest_capability_records(records)

    def reduce(self, records):
        self._reduce_candidates = latest_capability_records(chain(self._reduce_candidates, records))
        # The SDK invokes reduce for each protocol chunk; only the final chunk has the complete input.
        if not self._finished:
            return
        yield from rollup_capability_states(self._reduce_candidates)


dispatch(NiCapabilityStateRollupCommand, sys.argv, sys.stdin, sys.stdout, __name__)
