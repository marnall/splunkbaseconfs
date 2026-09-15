#!/usr/bin/env python3
"""Custom lookup command to build a base64-encoded Cyberhaven lineage URL parameter."""
import sys
import csv
import json
import base64


def build_lineage_b64(start_id, end_id, start_time, end_time):
    """Build a base64-encoded lineage filter string for the Cyberhaven UI."""
    lineage = {
        "selectedCategories": ["all_categories"],
        "time-filter": {
            "start_time": start_time,
            "end_time": end_time
        },
        "global-filter": "(e.source.raw_id == '{}' && e.destination.raw_id == '{}')".format(
            start_id, end_id
        )
    }
    lineage_json = json.dumps(lineage, separators=(',', ':'))
    return base64.b64encode(lineage_json.encode('utf-8')).decode('utf-8')


if __name__ == '__main__':
    reader = csv.DictReader(sys.stdin)
    fieldnames = list(reader.fieldnames or [])
    if 'cyberhaven_lineage_b64' not in fieldnames:
        fieldnames.append('cyberhaven_lineage_b64')

    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        row['cyberhaven_lineage_b64'] = build_lineage_b64(
            start_id=row.get('start_id', ''),
            end_id=row.get('end_id', ''),
            start_time=row.get('start_time', ''),
            end_time=row.get('end_time', '')
        )
        writer.writerow(row)
