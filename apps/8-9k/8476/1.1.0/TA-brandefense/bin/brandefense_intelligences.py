#!/usr/bin/env python3
"""
Brandefense Intelligences Input for Splunk
Pulls intelligence reports from Brandefense API.

Incremental collection:
  - First run: backfill last N days (intelligences_max_age_days)
  - Subsequent runs: only pull from checkpoint timestamp onwards

Field cleanup:
  - Removes: id, is_draft, attachment_count, attachments, rule_count
  - Flattens: created_by (keeps name only), sectors (keeps names only), country (keeps names)
  - HTML content: strips tags, keeps plain text version
"""

import sys
import os
import json
import re
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brandefense_api_client import (
    BrandefenseAPIClient, CheckpointManager, read_config, setup_logging,
    get_proxy_config, should_run
)


def strip_html(html):
    """Remove HTML tags, returning plain text."""
    if not html:
        return ''
    text = re.sub(r'<br\s*/?>', '\n', html)
    text = re.sub(r'<li[^>]*>', '- ', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def clean_intelligence(event, do_strip_html=True):
    """Flatten and strip unnecessary fields."""
    created_by = event.get('created_by') or {}
    countries = event.get('country') or []
    sectors = event.get('sectors') or []

    content = event.get('content', '')
    content_text = strip_html(content) if do_strip_html else ''

    return {
        'code': event.get('code', ''),
        'created_at': event.get('created_at', ''),
        'title': event.get('title', ''),
        'content_text': content_text,
        'language': event.get('language', ''),
        'countries': [c.get('name', '') for c in countries if c.get('name')],
        'network_type': event.get('network_type', ''),
        'created_by': created_by.get('name', ''),
        'sectors': [s.get('name', '') for s in sectors if s.get('name')],
        'categories': event.get('categories', []),
        'tags': event.get('tags', []),
        'source_url': event.get('source_url', ''),
        'source_platform': event.get('source_platform', ''),
        'platform_type': event.get('platform_type', ''),
        'threat_actor': event.get('threat_actor', ''),
        'indicator_count': event.get('indicator_count', 0),
        'mitre_tactics': event.get('mitre_tactics', [])
    }


def main():
    logger = setup_logging('brandefense_intelligences')

    try:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config = read_config(app_dir)

        api_key = config.get('api_key')
        if not api_key:
            logger.error("No api_key configured in brandefense.conf")
            sys.exit(1)

        base_url = config.get('base_url', 'https://api.brandefense.io/api/v1')
        interval = int(config.get('collection_interval_intelligences', '3600'))

        proxy_config = get_proxy_config(config)
        ssl_verify = config.get('ssl_verify', 'false').lower() == 'true'
        checkpoint = CheckpointManager('intelligences', app_dir)

        if not should_run(checkpoint, interval, logger):
            return

        page_size = int(config.get('intelligences_page_size', '20'))
        max_pages = int(config.get('intelligences_max_pages', '50'))
        max_age_days = int(config.get('intelligences_max_age_days', '7'))
        do_strip_html = config.get('intelligences_strip_html', 'true').lower() == 'true'
        request_delay = config.get('api_request_delay', '2')

        client = BrandefenseAPIClient(api_key, base_url, logger, request_delay,
                                      proxy_config=proxy_config, ssl_verify=ssl_verify)

        last_created_at = checkpoint.get('last_created_at', '')
        new_last_created_at = last_created_at
        event_count = 0

        logger.info(f"Starting intelligences collection, checkpoint={last_created_at}")

        def stop_check(item):
            if not last_created_at:
                return False
            return item.get('created_at', '') <= last_created_at

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
            'page_size': page_size,
            'created_at__range': f'{range_start},{range_end}'
        }

        for event in client.get_paginated_cursor(
            '/intelligences', params=params, stop_fn=stop_check, max_pages=max_pages
        ):
            created_at = event.get('created_at', '')
            if last_created_at and created_at <= last_created_at:
                break

            clean_event = clean_intelligence(event, do_strip_html)
            print(json.dumps(clean_event, ensure_ascii=False))
            sys.stdout.flush()
            event_count += 1

            if created_at > new_last_created_at:
                new_last_created_at = created_at

        if new_last_created_at > (last_created_at or ''):
            checkpoint.set('last_created_at', new_last_created_at)
            checkpoint.save()
            logger.info(f"Updated checkpoint to {new_last_created_at}, collected {event_count} events")
        else:
            logger.info("No new intelligences found")

    except Exception as e:
        logger.error(f"Failed to collect intelligences: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
