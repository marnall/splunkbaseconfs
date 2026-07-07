#!/usr/bin/env python
# encoding = utf-8

"""
test_ingestion.py

Unit tests for SpyCloud ingestion logic.
"""

import unittest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingestion import Ingestion


class TestIngestion(unittest.TestCase):
    """Test cases for ingestion logic"""

    def setUp(self):
        """Set up mock objects for testing"""
        self.mock_helper = Mock()
        self.mock_kvstore = Mock()
        self.mock_kvstore.data.query_by_id = Mock()
        self.mock_kvstore.data.update = Mock()
        self.mock_kvstore.data.insert = Mock()
        self.mock_kvstore.data.delete = Mock()

        # Test timestamp
        self.test_timestamp = "2025-12-16T15:57:05Z"

    def test_add_one_second(self):
        """Test off-by-one second addition"""
        ingestion = Ingestion(self.mock_helper, self.mock_kvstore)

        # Test examples from requirements
        input_timestamp = "2025-12-16T14:57:04Z"
        expected = "2025-12-16T14:57:05Z"
        result = ingestion._add_one_second(input_timestamp)
        self.assertEqual(result, expected)

        # Test second example
        input_timestamp = "2025-12-16T15:57:05Z"
        expected = "2025-12-16T15:57:06Z"
        result = ingestion._add_one_second(input_timestamp)
        self.assertEqual(result, expected)

    def test_first_run(self):
        """Test first run (no checkpoint exists)"""
        # Mock no existing checkpoint
        self.mock_kvstore.data.query_by_id.return_value = None

        ingestion = Ingestion(self.mock_helper, self.mock_kvstore)
        ingestion._get_current_utc_timestamp = Mock(return_value=self.test_timestamp)

        since, until = ingestion.get_ingestion_params()

        # First run should start from epoch date
        self.assertEqual(since, "1970-01-01")
        self.assertEqual(until, self.test_timestamp)

    def test_incremental_run(self):
        """Test normal incremental run"""
        # Mock existing checkpoint
        last_run = "2025-12-16T14:57:04Z"
        checkpoint_data = {"last_run": last_run, "documents": {}}
        self.mock_kvstore.data.query_by_id.return_value = {
            'value': json.dumps(checkpoint_data)
        }

        ingestion = Ingestion(self.mock_helper, self.mock_kvstore)
        ingestion._get_current_utc_timestamp = Mock(return_value=self.test_timestamp)

        since, until = ingestion.get_ingestion_params()

        # Should add 1 second to last_run
        expected_since = "2025-12-16T14:57:05Z"
        self.assertEqual(since, expected_since)
        self.assertEqual(until, self.test_timestamp)

    def test_reload_run_no_checkpoint(self):
        """Test reload behavior (checkpoint cleared by spycloud_reset.py)"""
        # Mock no checkpoint (reset script cleared it)
        self.mock_kvstore.data.query_by_id.return_value = None

        ingestion = Ingestion(self.mock_helper, self.mock_kvstore)
        ingestion._get_current_utc_timestamp = Mock(return_value=self.test_timestamp)

        since, until = ingestion.get_ingestion_params()

        # Should behave like first run (epoch date)
        self.assertEqual(since, "1970-01-01")
        self.assertEqual(until, self.test_timestamp)

    def test_update_checkpoint_after_success(self):
        """Test checkpoint update after successful ingestion"""
        # Mock existing checkpoint
        old_checkpoint = {"last_run": "old_value", "documents": {"doc1": "2025-12-15"}}
        self.mock_kvstore.data.query_by_id.return_value = {
            'value': json.dumps(old_checkpoint)
        }

        ingestion = Ingestion(self.mock_helper, self.mock_kvstore)
        until = self.test_timestamp

        ingestion.update_checkpoint_after_success(until)

        # Should have updated last_run and preserved documents in retention window
        self.mock_kvstore.data.update.assert_called_once()
        call_args = self.mock_kvstore.data.update.call_args[0]
        updated_checkpoint = json.loads(json.loads(call_args[1])['value'])

        self.assertEqual(updated_checkpoint['last_run'], until)
        self.assertEqual(updated_checkpoint['documents'], {"doc1": "2025-12-15"})

    def test_update_checkpoint_prunes_documents_older_than_2_days(self):
        """Test checkpoint cleanup retains only last 2 days of document IDs."""
        old_checkpoint = {
            "last_run": "old_value",
            "documents": {
                "doc_old": "2025-12-14",
                "doc_keep_1": "2025-12-15",
                "doc_keep_2": "2025-12-16"
            }
        }
        self.mock_kvstore.data.query_by_id.return_value = {
            'value': json.dumps(old_checkpoint)
        }

        ingestion = Ingestion(self.mock_helper, self.mock_kvstore)
        until = self.test_timestamp

        ingestion.update_checkpoint_after_success(until)

        call_args = self.mock_kvstore.data.update.call_args[0]
        updated_checkpoint = json.loads(json.loads(call_args[1])['value'])

        self.assertEqual(updated_checkpoint['last_run'], until)
        self.assertEqual(
            updated_checkpoint['documents'],
            {"doc_keep_1": "2025-12-15", "doc_keep_2": "2025-12-16"}
        )

    def test_empty_checkpoint_structure(self):
        """Test empty checkpoint creation"""
        ingestion = Ingestion(self.mock_helper, self.mock_kvstore)

        checkpoint = ingestion._create_empty_checkpoint()
        expected = {"last_run": None, "documents": {}}
        self.assertEqual(checkpoint, expected)

    def test_requirement_examples(self):
        """Test using exact examples from requirements"""
        ingestion = Ingestion(self.mock_helper, self.mock_kvstore)

        # Example: If last_run = 2025-12-16T14:57:04Z, then next since = 2025-12-16T14:57:05Z
        last_run = "2025-12-16T14:57:04Z"
        expected_since = "2025-12-16T14:57:05Z"
        actual_since = ingestion._add_one_second(last_run)
        self.assertEqual(actual_since, expected_since)

        # Example: If until = 2025-12-16T15:57:05Z, then store last_run = 2025-12-16T15:57:05Z
        until = "2025-12-16T15:57:05Z"

        # Mock checkpoint for update
        old_checkpoint = {"last_run": last_run, "documents": {}}
        self.mock_kvstore.data.query_by_id.return_value = {
            'value': json.dumps(old_checkpoint)
        }

        ingestion.update_checkpoint_after_success(until)

        # Verify last_run was set to until (not +1 second)
        call_args = self.mock_kvstore.data.update.call_args[0]
        updated_checkpoint = json.loads(json.loads(call_args[1])['value'])
        self.assertEqual(updated_checkpoint['last_run'], until)

        # Example: Next run since = 2025-12-16T15:57:06Z
        next_since = ingestion._add_one_second(until)
        expected_next = "2025-12-16T15:57:06Z"
        self.assertEqual(next_since, expected_next)

if __name__ == '__main__':
    unittest.main(verbosity=2)