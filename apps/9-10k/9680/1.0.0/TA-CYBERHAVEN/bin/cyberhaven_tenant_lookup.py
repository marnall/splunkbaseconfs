#!/usr/bin/env python3
"""Custom lookup command to enrich events with the configured Cyberhaven tenant URL."""
import sys
import csv
import splunk.clilib.cli_common as cli


def get_tenant_url():
    """Retrieve the configured Cyberhaven tenant URL from TA settings."""
    try:
        conf = cli.getMergedConf('ta-cyberhaven_settings')
        url = conf.get('hec_settings', {}).get('tenant_url', '').strip().strip('/')
        prefix = 'https://'
        if url.startswith(prefix):
            return url[len(prefix):]
        return url
    except Exception:
        return ''


if __name__ == '__main__':
    tenant_url = get_tenant_url()

    reader = csv.DictReader(sys.stdin)
    fieldnames = list(reader.fieldnames or [])
    if 'cyberhaven_tenant_url' not in fieldnames:
        fieldnames.append('cyberhaven_tenant_url')

    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        row['cyberhaven_tenant_url'] = tenant_url
        writer.writerow(row)
