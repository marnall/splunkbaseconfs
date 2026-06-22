#!/usr/bin/env python3
"""
Brandefense Incidents Input for Splunk
Pulls incidents from Brandefense API.
- Strips unnecessary fields (logos, internal flags) to keep events lean
- Outputs indicators as SEPARATE events linked by incident_code
  (avoids massive single events when incidents have 100+ indicators)

Two event types are output (same sourcetype, use event_type to filter):
  event_type=incident   -> the incident itself
  event_type=indicator  -> one per indicator, linked by incident_code
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

def clean_incident(event):
    """
    Flatten and strip unnecessary fields to keep events lean.
    Removes: id, nested objects (asset/org), assignees, attachment_count, comment_count.
    Keeps only what's useful for analysis and alerting.
    """
    asset = event.get('asset') or {}
    org = event.get('organization') or {}
    code = event.get('code', '')

    return {
        'event_type': 'incident',
        'code': code,
        'url': f'https://app.brandefense.io/issues/incidents/all/{code}' if code else '',
        'created_at': event.get('created_at', ''),
        'status': event.get('status', ''),
        'severity': event.get('severity', ''),
        'title': event.get('title', ''),
        'category': event.get('category', ''),
        'module': event.get('module', ''),
        'type': event.get('type', ''),
        'network_type': event.get('network_type', ''),
        'asset_name': asset.get('asset', ''),
        'asset_type': asset.get('type', ''),
        'organization_name': org.get('name', ''),
        'organization_code': org.get('short_code', ''),
        'indicator_count': event.get('indicator_count', 0),
        'tags': event.get('tags', []),
        'mitre_tactics': event.get('mitre_tactics', [])
    }


def main():
    logger = setup_logging('brandefense_incidents')

    try:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config = read_config(app_dir)

        api_key = config.get('api_key')
        if not api_key:
            logger.error("No api_key configured in brandefense.conf")
            sys.exit(1)

        base_url = config.get('base_url', 'https://api.brandefense.io/api/v1')
        interval = int(config.get('collection_interval_incidents', '3600'))

        proxy_config = get_proxy_config(config)
        ssl_verify = config.get('ssl_verify', 'false').lower() == 'true'
        checkpoint = CheckpointManager('incidents', app_dir)

        if not should_run(checkpoint, interval, logger):
            return

        page_size = int(config.get('incidents_page_size', '50'))
        max_pages = int(config.get('incidents_max_pages', '100'))
        collect_indicators = config.get('incidents_collect_indicators', 'true').lower() == 'true'
        max_age_days = int(config.get('incidents_max_age_days', '7'))
        request_delay = config.get('api_request_delay', '2')
        severity_filter_raw = config.get('incidents_severity_filter', 'LOW,MEDIUM,HIGH,CRITICAL')
        severity_filter = set(s.strip().upper() for s in severity_filter_raw.split(',') if s.strip())
        logger.info(f"Severity filter: {severity_filter}")

        client = BrandefenseAPIClient(api_key, base_url, logger, request_delay,
                                      proxy_config=proxy_config, ssl_verify=ssl_verify)

        last_created_at = checkpoint.get('last_created_at', '')
        new_last_created_at = last_created_at
        incident_count = 0
        indicator_count = 0

        logger.info(f"Starting incidents collection, checkpoint={last_created_at}")

        def stop_check(item):
            if not last_created_at:
                return False
            return item.get('created_at', '') <= last_created_at

        # Build date range
        now_utc = datetime.now(timezone.utc)
        range_end = now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

        if last_created_at:
            # Subsequent runs: only query from checkpoint onwards
            range_start = last_created_at
            logger.info(f"Incremental pull from {range_start} to {range_end}")
        else:
            # First run: backfill last N days
            range_start = (now_utc - timedelta(days=max_age_days)).strftime('%Y-%m-%dT00:00:00Z')
            logger.info(f"Initial backfill: {max_age_days} days from {range_start}")

        params = {
            'ordering': '-created_at',
            'page_size': page_size,
            'created_at__range': f'{range_start},{range_end}'
        }

        for event in client.get_paginated_cursor(
            '/incidents', params=params, stop_fn=stop_check, max_pages=max_pages
        ):
            created_at = event.get('created_at', '')
            if last_created_at and created_at <= last_created_at:
                break

            # Apply severity filter
            if event.get('severity', '').upper() not in severity_filter:
                if created_at > new_last_created_at:
                    new_last_created_at = created_at
                continue

            incident_code = event.get('code', '')

            # Output clean incident event (no embedded indicators)
            clean_event = clean_incident(event)
            print(json.dumps(clean_event, ensure_ascii=False))
            sys.stdout.flush()
            incident_count += 1

            # Collect and output indicators as separate events
            if collect_indicators and event.get('indicator_count', 0) > 0:
                if incident_code:
                    try:
                        indicators_data = client.get(f'/incidents/{incident_code}/indicators')
                        if indicators_data and 'results' in indicators_data:
                            for ind in indicators_data['results']:
                                ind_event = {
                                    'event_type': 'indicator',
                                    'incident_code': incident_code,
                                    'incident_url': f'https://app.brandefense.io/issues/incidents/all/{incident_code}',
                                    'incident_severity': event.get('severity', ''),
                                    'incident_title': event.get('title', ''),
                                    'incident_created_at': created_at,
                                }
                                # Include all indicator fields dynamically
                                ind_event.update(ind)
                                print(json.dumps(ind_event, ensure_ascii=False))
                                sys.stdout.flush()
                                indicator_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to get indicators for {incident_code}: {e}")

            if created_at > new_last_created_at:
                new_last_created_at = created_at

        if new_last_created_at > (last_created_at or ''):
            checkpoint.set('last_created_at', new_last_created_at)
            checkpoint.save()
            logger.info(
                f"Updated checkpoint to {new_last_created_at}, "
                f"collected {incident_count} incidents + {indicator_count} indicators"
            )
        else:
            logger.info("No new incidents found")

    except Exception as e:
        logger.error(f"Failed to collect incidents: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
