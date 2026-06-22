#!/usr/bin/env python3
"""
Brandefense IOC Input for Splunk
Pulls IOCs (ip_address, domain, hash, url) from Brandefense Threat Intelligence API.
Outputs events to stdout for Splunk indexing.

Incremental collection:
  - Uses period=Nd to limit API-side (e.g. period=7d)
  - Checkpoints on last_seen per IOC type — subsequent runs stop at already-seen data
  - IOC API is ordered by last_seen descending, so new/updated IOCs come first

Field cleanup:
  - Removes: id (UUID, not needed)
  - Flattens to essential fields only
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brandefense_api_client import (
    BrandefenseAPIClient, CheckpointManager, read_config, setup_logging,
    get_proxy_config, should_run
)

IOC_TYPES = ['ip_address', 'domain', 'hash', 'url']


def clean_ioc(ioc):
    """Remove unnecessary fields, keep only essentials."""
    return {
        'data': ioc.get('data', ''),
        'type': ioc.get('type', ''),
        'data_type': ioc.get('data_type', ''),
        'category': ioc.get('category', ''),
        'module': ioc.get('module', ''),
        'severity': ioc.get('severity', ''),
        'first_seen': ioc.get('first_seen', ''),
        'last_seen': ioc.get('last_seen', '')
    }


def main():
    logger = setup_logging('brandefense_iocs')

    try:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config = read_config(app_dir)

        api_key = config.get('api_key')
        if not api_key:
            logger.error("No api_key configured in brandefense.conf")
            sys.exit(1)

        base_url = config.get('base_url', 'https://api.brandefense.io/api/v1')
        interval = int(config.get('collection_interval_iocs', '3600'))

        proxy_config = get_proxy_config(config)
        ssl_verify = config.get('ssl_verify', 'false').lower() == 'true'
        checkpoint = CheckpointManager('iocs', app_dir)

        if not should_run(checkpoint, interval, logger):
            return

        iocs_page_size = int(config.get('iocs_page_size', '100'))
        max_pages_per_type = int(config.get('iocs_max_pages', '50'))
        pull_period_days = int(config.get('iocs_pull_period_days', '7'))
        request_delay = config.get('api_request_delay', '2')

        ioc_types = config.get('ioc_types', ','.join(IOC_TYPES)).split(',')
        ioc_types = [t.strip() for t in ioc_types if t.strip()]

        severity_filter_raw = config.get('ioc_severity_filter', 'LOW,MEDIUM,HIGH,CRITICAL')
        severity_filter = set(s.strip().upper() for s in severity_filter_raw.split(',') if s.strip())
        logger.info(f"Severity filter: {severity_filter}")

        client = BrandefenseAPIClient(api_key, base_url, logger, request_delay,
                                      proxy_config=proxy_config, ssl_verify=ssl_verify)

        for ioc_type in ioc_types:
            logger.info(f"Collecting IOCs of type: {ioc_type}")

            last_seen_ckpt = checkpoint.get(f'{ioc_type}_last_seen', '')
            new_last_seen = last_seen_ckpt
            event_count = 0

            if last_seen_ckpt:
                logger.info(f"Incremental pull, checkpoint last_seen={last_seen_ckpt}")
            else:
                logger.info(f"Initial pull with period={pull_period_days}d")

            def stop_check(item, _ckpt=last_seen_ckpt):
                if not _ckpt:
                    return False
                return item.get('last_seen', '') <= _ckpt

            params = {'ioc_type': ioc_type, 'size': iocs_page_size}
            if pull_period_days > 0:
                params['period'] = f'{pull_period_days}d'

            for ioc in client.get_paginated_search_after(
                '/threat-intelligence/iocs',
                params=params,
                stop_fn=stop_check,
                max_pages=max_pages_per_type
            ):
                ioc_last_seen = ioc.get('last_seen', '')
                if last_seen_ckpt and ioc_last_seen <= last_seen_ckpt:
                    break

                # Apply severity filter
                if ioc.get('severity', '').upper() not in severity_filter:
                    if ioc_last_seen > new_last_seen:
                        new_last_seen = ioc_last_seen
                    continue

                clean_event = clean_ioc(ioc)
                print(json.dumps(clean_event, ensure_ascii=False))
                sys.stdout.flush()
                event_count += 1

                if ioc_last_seen > new_last_seen:
                    new_last_seen = ioc_last_seen

            if new_last_seen > (last_seen_ckpt or ''):
                checkpoint.set(f'{ioc_type}_last_seen', new_last_seen)
                logger.info(f"IOC type {ioc_type}: collected {event_count} new IOCs")
            else:
                logger.info(f"IOC type {ioc_type}: no new IOCs")

        checkpoint.save()

    except Exception as e:
        logger.error(f"Failed to collect IOCs: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
