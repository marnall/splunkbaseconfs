#!/usr/bin/env python3
"""
Brandefense Audit Logs Input for Splunk
Pulls audit logs from Brandefense API and outputs to stdout for Splunk indexing.

Incremental collection:
  - First run: backfill last N days (audit_logs_max_age_days)
  - Subsequent runs: only pull from checkpoint timestamp onwards

Field cleanup:
  - Flattens actor object (removes actor.id)
  - Keeps data object as-is (varies by action type)
"""

import sys
import os
import json
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brandefense_api_client import (
    BrandefenseAPIClient, CheckpointManager, read_config, setup_logging,
    get_proxy_config, should_run
)


def clean_audit_event(event):
    """Flatten and strip unnecessary fields."""
    actor = event.get('actor') or {}

    return {
        'id': event.get('id', 0),
        'created_at': event.get('created_at', ''),
        'type': event.get('type', ''),
        'note': event.get('note', ''),
        'actor_name': actor.get('name', ''),
        'actor_email': actor.get('email', ''),
        'actor_role': actor.get('role', ''),
        'ip_address': event.get('ip_address', ''),
        'data': event.get('data', {})
    }


def main():
    logger = setup_logging('brandefense_audit_logs')

    try:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config = read_config(app_dir)

        api_key = config.get('api_key')
        if not api_key:
            logger.error("No api_key configured in brandefense.conf")
            sys.exit(1)

        base_url = config.get('base_url', 'https://api.brandefense.io/api/v1')
        interval = int(config.get('collection_interval_audit_logs', '3600'))

        proxy_config = get_proxy_config(config)
        ssl_verify = config.get('ssl_verify', 'false').lower() == 'true'
        checkpoint = CheckpointManager('audit_logs', app_dir)

        if not should_run(checkpoint, interval, logger):
            return

        page_size = int(config.get('audit_logs_page_size', '100'))
        max_pages = int(config.get('audit_logs_max_pages', '100'))
        max_age_days = int(config.get('audit_logs_max_age_days', '7'))
        request_delay = config.get('api_request_delay', '2')

        client = BrandefenseAPIClient(api_key, base_url, logger, request_delay,
                                      proxy_config=proxy_config, ssl_verify=ssl_verify)

        last_id = checkpoint.get('last_id', 0)
        last_created_at = checkpoint.get('last_created_at', '')
        new_last_id = last_id
        new_last_created_at = last_created_at
        event_count = 0

        logger.info(f"Starting audit logs collection, checkpoint id={last_id}")

        def stop_check(item):
            return item.get('id', 0) <= last_id

        # Build date range for API-side filtering
        now_utc = datetime.now(timezone.utc)
        range_end = now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

        if last_created_at:
            range_start = last_created_at
            logger.info(f"Incremental pull from {range_start} to {range_end}")
        else:
            range_start = (now_utc - timedelta(days=max_age_days)).strftime('%Y-%m-%dT00:00:00Z')
            logger.info(f"Initial backfill: {max_age_days} days from {range_start}")

        params = {
            'ordering': '-id',
            'page_size': page_size,
            'created_at__range': f'{range_start},{range_end}'
        }

        for event in client.get_paginated_cursor(
            '/audit-logs', params=params, stop_fn=stop_check, max_pages=max_pages
        ):
            event_id = event.get('id', 0)
            if event_id <= last_id:
                break

            clean_event = clean_audit_event(event)
            print(json.dumps(clean_event, ensure_ascii=False))
            sys.stdout.flush()
            event_count += 1

            if event_id > new_last_id:
                new_last_id = event_id
            created_at = event.get('created_at', '')
            if created_at > new_last_created_at:
                new_last_created_at = created_at

        if new_last_id > last_id:
            checkpoint.set('last_id', new_last_id)
            checkpoint.set('last_created_at', new_last_created_at)
            checkpoint.save()
            logger.info(f"Updated checkpoint to id={new_last_id}, collected {event_count} events")
        else:
            logger.info(f"No new audit logs found (checkpoint id={last_id})")

    except Exception as e:
        logger.error(f"Failed to collect audit logs: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
