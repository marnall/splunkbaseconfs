#!/usr/bin/env python

import os
import sys
import types
import unittest
from unittest.mock import Mock, patch


requests_module = sys.modules.setdefault("requests", types.ModuleType("requests"))


class HTTPError(Exception):
    pass


requests_module.HTTPError = HTTPError
requests_exceptions = sys.modules.setdefault("requests.exceptions", types.ModuleType("requests.exceptions"))


class ProxyError(Exception):
    pass


requests_exceptions.ProxyError = ProxyError

solnlib_module = sys.modules.setdefault("solnlib", types.ModuleType("solnlib"))
solnlib_modular_input = sys.modules.setdefault(
    "solnlib.modular_input",
    types.ModuleType("solnlib.modular_input"),
)
solnlib_modular_input.checkpointer = object()
solnlib_module.modular_input = solnlib_modular_input

splunklib_module = sys.modules.setdefault("splunklib", types.ModuleType("splunklib"))
splunklib_client = sys.modules.setdefault("splunklib.client", types.ModuleType("splunklib.client"))
splunklib_client.connect = Mock()
splunklib_module.client = splunklib_client

splunk_module = sys.modules.setdefault("splunk", types.ModuleType("splunk"))
splunk_rest = sys.modules.setdefault("splunk.rest", types.ModuleType("splunk.rest"))
splunk_rest.simpleRequest = Mock()
splunk_module.rest = splunk_rest

splunktaucclib_module = sys.modules.setdefault("splunktaucclib", types.ModuleType("splunktaucclib"))
splunktaucclib_rest_handler = sys.modules.setdefault(
    "splunktaucclib.rest_handler",
    types.ModuleType("splunktaucclib.rest_handler"),
)
splunktaucclib_endpoint = sys.modules.setdefault(
    "splunktaucclib.rest_handler.endpoint",
    types.ModuleType("splunktaucclib.rest_handler.endpoint"),
)
splunktaucclib_endpoint.validator = object()
splunktaucclib_rest_handler.endpoint = splunktaucclib_endpoint
splunktaucclib_module.rest_handler = splunktaucclib_rest_handler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import input_module_spycloud_watchlist as watchlist_input


class TestWatchlistCollectEvents(unittest.TestCase):
    def setUp(self):
        self.helper = Mock()
        self.helper.context_meta = {"session_key": "session-token"}
        self.helper.get_app_name.return_value = "TA-SpyCloud"
        self.helper.get_input_type.return_value = "spycloud_watchlist"
        self.helper.get_output_index.return_value = "main"
        self.helper.get_sourcetype.return_value = "spycloud:watchlist"
        self.helper.new_event.side_effect = lambda **kwargs: kwargs

        self.event_writer = Mock()

        self.kvstore = Mock()
        self.service = Mock()
        self.service.kvstore = {"watchlist_v2_checkpoint": self.kvstore}

        self.ingestion = Mock()
        self.ingestion.get_ingestion_params.return_value = (
            "2026-05-01T00:00:00Z",
            "2026-05-02T00:00:00Z",
        )
        self.checkpoint = {"documents": {}}
        self.ingestion._load_checkpoint.return_value = self.checkpoint

        def track_document(checkpoint, document_id, publish_date):
            checkpoint["documents"][document_id] = str(publish_date)[:10]

        self.ingestion.track_document.side_effect = track_document

    def test_collect_events_runs_modification_query_after_standard_query(self):
        call_order = []

        def standard_results(helper, since, until):
            call_order.append(("standard", since, until))
            return iter([
                {"document_id": "doc-standard", "spycloud_publish_date": "2026-05-01T12:00:00Z"}
            ])

        def modified_results(helper, since_modification_date, until_modification_date):
            call_order.append(("modified", since_modification_date, until_modification_date))
            return iter([
                {"document_id": "doc-modified", "spycloud_publish_date": "2026-05-02T08:00:00Z"}
            ])

        with patch.object(watchlist_input.api, "shouldRunOnThisSystem", return_value=True):
            with patch.object(watchlist_input.common, "check_api_key"):
                with patch.object(watchlist_input.client, "connect", return_value=self.service):
                    with patch.object(watchlist_input, "Ingestion", return_value=self.ingestion):
                        with patch.object(watchlist_input.api, "watchlist", side_effect=standard_results) as watchlist_mock:
                            with patch.object(watchlist_input.api, "modified_watchlist", side_effect=modified_results) as modified_mock:
                                watchlist_input.collect_events(self.helper, self.event_writer)

        self.assertEqual(
            call_order,
            [
                ("standard", "2026-05-01T00:00:00Z", "2026-05-02T00:00:00Z"),
                ("modified", "2026-05-01T00:00:00Z", "2026-05-02T00:00:00Z"),
            ],
        )
        watchlist_mock.assert_called_once_with(
            self.helper,
            "2026-05-01T00:00:00Z",
            "2026-05-02T00:00:00Z",
        )
        modified_mock.assert_called_once_with(
            self.helper,
            "2026-05-01T00:00:00Z",
            "2026-05-02T00:00:00Z",
        )
        self.assertEqual(self.event_writer.write_event.call_count, 2)
        self.ingestion.update_checkpoint_after_success.assert_called_once()
        update_args = self.ingestion.update_checkpoint_after_success.call_args[0]
        self.assertEqual(update_args[0], "2026-05-02T00:00:00Z")
        updated_checkpoint = update_args[1]
        self.assertEqual(updated_checkpoint["last_since"], "2026-05-01T00:00:00Z")
        self.assertEqual(updated_checkpoint["last_until"], "2026-05-02T00:00:00Z")
        self.assertEqual(updated_checkpoint["last_since_modification_date"], "2026-05-01T00:00:00Z")
        self.assertEqual(updated_checkpoint["last_until_modification_date"], "2026-05-02T00:00:00Z")
        self.assertIn("doc-standard", updated_checkpoint["documents"])
        self.assertIn("doc-modified", updated_checkpoint["documents"])


if __name__ == "__main__":
    unittest.main(verbosity=2)