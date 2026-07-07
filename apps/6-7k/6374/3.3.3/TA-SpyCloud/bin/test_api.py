#!/usr/bin/env python

import os
import sys
import types
import unittest
from unittest.mock import Mock, patch


sys.modules.setdefault("requests", types.ModuleType("requests"))
sys.modules.setdefault("splunk", types.ModuleType("splunk"))
sys.modules.setdefault("splunk.rest", types.ModuleType("splunk.rest"))
sys.modules.setdefault("splunktaucclib", types.ModuleType("splunktaucclib"))
sys.modules.setdefault("splunktaucclib.rest_handler", types.ModuleType("splunktaucclib.rest_handler"))
sys.modules.setdefault(
    "splunktaucclib.rest_handler.endpoint",
    types.ModuleType("splunktaucclib.rest_handler.endpoint"),
)
sys.modules["splunktaucclib.rest_handler.endpoint"].validator = object()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import api


class TestWatchlistQueryParameters(unittest.TestCase):
    def setUp(self):
        self.helper = Mock()

    def test_watchlist_includes_since_and_until_only(self):
        response = Mock()
        response.json.return_value = {
            "results": [{"document_id": "doc-1"}],
            "cursor": "",
        }

        with patch.object(api, "make_headers", return_value={}):
            with patch.object(api, "_send_with_retry", return_value=(response, 1.1)) as send_mock:
                results = list(api.watchlist(self.helper, "2026-05-01T00:00:00Z", "2026-05-02T00:00:00Z"))

        self.assertEqual(results, [{"document_id": "doc-1"}])
        url = send_mock.call_args[0][1]
        self.assertIn("since=2026-05-01T00:00:00Z", url)
        self.assertIn("until=2026-05-02T00:00:00Z", url)
        self.assertNotIn("since_modification_date=", url)
        self.assertNotIn("until_modification_date=", url)

    def test_modified_watchlist_includes_modification_date_window(self):
        response = Mock()
        response.json.return_value = {
            "results": [{"document_id": "doc-2"}],
            "cursor": "",
        }

        with patch.object(api, "make_headers", return_value={}):
            with patch.object(api, "_send_with_retry", return_value=(response, 1.1)) as send_mock:
                results = list(api.modified_watchlist(self.helper, "2026-05-01T00:00:00Z", "2026-05-02T00:00:00Z"))

        self.assertEqual(results, [{"document_id": "doc-2"}])
        url = send_mock.call_args[0][1]
        self.assertIn("since_modification_date=2026-05-01T00:00:00Z", url)
        self.assertIn("until_modification_date=2026-05-02T00:00:00Z", url)

    def test_modified_watchlist_omits_until_when_missing(self):
        response = Mock()
        response.json.return_value = {
            "results": [],
            "cursor": "",
        }

        with patch.object(api, "make_headers", return_value={}):
            with patch.object(api, "_send_with_retry", return_value=(response, 1.1)) as send_mock:
                list(api.modified_watchlist(self.helper, "2026-05-01T00:00:00Z"))

        url = send_mock.call_args[0][1]
        self.assertIn("since_modification_date=2026-05-01T00:00:00Z", url)
        self.assertNotIn("until_modification_date=", url)


if __name__ == "__main__":
    unittest.main(verbosity=2)