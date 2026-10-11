#!/usr/bin/env python
"""Terminal graph materialization command for normalized vertex or edge rows."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import import_declare_test  # noqa: F401,E402
from graph.edge_materializer import EdgeMaterializer  # noqa: E402
from graph.materializer import VertexMaterializer  # noqa: E402
from model.kvstore import KvStoreClient  # noqa: E402
from model.repository import TopologyKvRepository  # noqa: E402
from ni_app_logging import configure_component_logger  # noqa: E402
from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    Option,
    StreamingCommand,
    dispatch,
    validators,
)

logger = configure_component_logger("nigraphmaterialize")


# This SCP2 command writes KV Store state and must execute only on the search head.
@Configuration(distributed=False)
class NiGraphMaterializeCommand(StreamingCommand):
    target = Option(require=True, validate=validators.Set("vertex", "edge"))

    def __init__(self):
        super().__init__()
        self._total_events = 0
        self._cumulative_stats = {}
        self._active_edge_materializer = None

    @staticmethod
    def _materializer(target, repository, client):
        materializer_class = {
            "vertex": VertexMaterializer,
            "edge": EdgeMaterializer,
        }[target]
        return materializer_class(repository, client, logger=logger)

    def stream(self, records):
        events = list(records)
        searchinfo = self._metadata.searchinfo
        session_key = searchinfo.session_key
        sid = getattr(searchinfo, "sid", "") or ""
        total_num_of_events_so_far = self._total_events + len(events)
        logger.info(
            "action=materialization status=stream_start target=%s sid=%s "
            "num_of_events=%d total_num_of_events_so_far=%d",
            self.target,
            sid or "-",
            len(events),
            total_num_of_events_so_far,
        )
        if self.target == "edge" and self._active_edge_materializer is not None:
            materializer = self._active_edge_materializer
        else:
            client = KvStoreClient(logger=logger)
            repository = TopologyKvRepository(client, logger=logger)
            materializer = self._materializer(self.target, repository, client)
            if self.target == "edge":
                self._active_edge_materializer = materializer
        try:
            if self.target == "edge":
                materializer.process(session_key, events, final=self._finished)
            else:
                materializer.process(session_key, events)
        except Exception:
            for message in materializer.warnings:
                self.write_warning(message)
            logger.exception(
                "action=materialization status=failed target=%s sid=%s "
                "num_of_events=%d total_num_of_events_so_far=%d",
                self.target,
                sid or "-",
                len(events),
                total_num_of_events_so_far,
            )
            raise
        self._total_events = total_num_of_events_so_far
        if self.target == "edge":
            self._cumulative_stats = dict(getattr(materializer, "stats", {}))
        else:
            for name, value in getattr(materializer, "stats", {}).items():
                self._cumulative_stats[name] = self._cumulative_stats.get(name, 0) + value
        for message in materializer.warnings:
            self.write_warning(message)
        logger.info(
            "action=materialization status=stream_completed target=%s sid=%s "
            "num_of_events=%d num_of_warnings=%d total_num_of_events_so_far=%d cumulative_stats=%s",
            self.target,
            sid or "-",
            len(events),
            len(materializer.warnings),
            self._total_events,
            json.dumps(self._cumulative_stats, sort_keys=True, separators=(",", ":")),
        )
        return
        yield  # pragma: no cover - makes this a generator per StreamingCommand contract


dispatch(NiGraphMaterializeCommand, sys.argv, sys.stdin, sys.stdout, __name__)
