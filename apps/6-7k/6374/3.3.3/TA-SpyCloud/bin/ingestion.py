#!/usr/bin/env python
# encoding = utf-8

"""
ingestion.py

SpyCloud ingestion logic.
Handles proper since/until/last_run timestamp logic with off-by-one prevention.
Scheduling is handled by JavaScript frontend - backend just does incremental fetch.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple, Optional, Any


class Ingestion:
    """SpyCloud ingestion logic"""

    CHECKPOINT_RETENTION_DAYS = 2
    FIRST_RUN_SINCE = "1970-01-01"

    def __init__(self, helper, kvstore):
        self.helper = helper
        self.kvstore = kvstore

    def _get_current_utc_timestamp(self) -> str:
        """Get current UTC timestamp in ISO-8601 format with second precision"""
        return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    def _add_one_second(self, timestamp: str) -> str:
        """Add one second to ISO-8601 timestamp for off-by-one prevention"""
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        dt_plus_one = dt + timedelta(seconds=1)
        return dt_plus_one.strftime('%Y-%m-%dT%H:%M:%SZ')

    def _load_checkpoint(self) -> Dict[str, Any]:
        """Load checkpoint from KV Store"""
        try:
            kv_checkpoint = self.kvstore.data.query_by_id('checkpoint')
            if kv_checkpoint:
                checkpoint = json.loads(kv_checkpoint['value'])
                self.helper.log_debug(f"Loaded checkpoint: {json.dumps(checkpoint)}")
                return checkpoint
            else:
                self.helper.log_debug("No checkpoint found, creating new one")
                return self._create_empty_checkpoint()
        except Exception as e:
            self.helper.log_debug(f"KV Store checkpoint not found, creating new one: {str(e)}")
            return self._create_empty_checkpoint()

    def _create_empty_checkpoint(self) -> Dict[str, Any]:
        """Create empty checkpoint structure"""
        return {
            "last_run": None,
            "documents": {}
        }

    def _parse_date(self, value: Any) -> Optional[datetime.date]:
        """Parse input into a date object using YYYY-MM-DD from either full ISO or date string."""
        if value is None:
            return None
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    def track_document(self, checkpoint: Dict[str, Any], document_id: str, publish_date: Optional[str] = None) -> None:
        """Track document ID with normalized publish date for deduplication and retention cleanup."""
        if "documents" not in checkpoint or not isinstance(checkpoint["documents"], dict):
            checkpoint["documents"] = {}
        tracked_date = self._parse_date(publish_date)
        if tracked_date is None:
            tracked_date = datetime.now(timezone.utc).date()
        checkpoint["documents"][document_id] = tracked_date.strftime("%Y-%m-%d")

    def prune_documents(self, checkpoint: Dict[str, Any], until: Optional[str]) -> int:
        """Keep only document IDs for the last N retention days, inclusive of the until date."""
        if "documents" not in checkpoint or not isinstance(checkpoint["documents"], dict):
            checkpoint["documents"] = {}
            return 0

        reference_date = self._parse_date(until)
        if reference_date is None:
            reference_date = datetime.now(timezone.utc).date()

        # Last 2 days means keep reference day and one day before.
        cutoff_date = reference_date - timedelta(days=self.CHECKPOINT_RETENTION_DAYS - 1)
        removed = 0
        for doc_id in list(checkpoint["documents"].keys()):
            doc_date = self._parse_date(checkpoint["documents"].get(doc_id))
            if doc_date is None or doc_date < cutoff_date:
                del checkpoint["documents"][doc_id]
                removed += 1
        return removed

    def _save_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """Save checkpoint to KV Store"""
        try:
            checkpoint_json = json.dumps(checkpoint)
            self.kvstore.data.update('checkpoint', json.dumps({"value": checkpoint_json}))
            self.helper.log_debug(f"Saved checkpoint: {checkpoint_json}")
        except Exception as e:
            if "404" in str(e):
                try:
                    self.kvstore.data.insert({'_key': 'checkpoint', "value": json.dumps(checkpoint)})
                    self.helper.log_debug(f"Inserted new checkpoint: {json.dumps(checkpoint)}")
                except Exception as insert_error:
                    self.helper.log_error(f"Failed to insert new checkpoint: {str(insert_error)}")
                    raise
            else:
                self.helper.log_error(f"Failed to update checkpoint in KV Store: {str(e)}")
                raise

    def get_ingestion_params(self) -> Tuple[Optional[str], str]:
        """
        Get ingestion parameters for API call.

        Rules:
        - First run (no checkpoint): since = 1970-01-01, until = NOW
        - Normal incremental run: since = last_run + 1 second, until = NOW

        Reset/reload is handled by spycloud_reset.py which clears the checkpoint first.

        Returns: (since, until)
        """
        checkpoint = self._load_checkpoint()
        until = self._get_current_utc_timestamp()

        if checkpoint["last_run"] is None:
            # First run or post-reload (checkpoint was cleared): start from epoch date.
            since = self.FIRST_RUN_SINCE
            self.helper.log_info(f"mode=first_run since={since} until={until}")
        else:
            # Normal incremental run: last_run + 1 second for off-by-one prevention
            since = self._add_one_second(checkpoint["last_run"])
            self.helper.log_info(f"mode=incremental last_run={checkpoint['last_run']} since={since} until={until}")

        return since, until

    def update_checkpoint_after_success(self, until: str, checkpoint: Optional[Dict[str, Any]] = None) -> None:
        """
        Update checkpoint after successful ingestion.

        Rules:
        - Set last_run = until (the timestamp used for this run's cutoff)
        - Keep only recent document IDs for deduplication (last 2 days)
        """
        if checkpoint is None:
            checkpoint = self._load_checkpoint()
        last_run_before = checkpoint.get("last_run")

        removed = self.prune_documents(checkpoint, until)
        if removed > 0:
            self.helper.log_info(
                f"checkpoint_cleanup removed={removed} retention_days={self.CHECKPOINT_RETENTION_DAYS}"
            )

        # Update last_run to until timestamp
        checkpoint["last_run"] = until

        # Log the update
        self.helper.log_info(f"checkpoint_updated last_run_before={last_run_before} last_run_after={until}")

        # Save to KV Store
        self._save_checkpoint(checkpoint)