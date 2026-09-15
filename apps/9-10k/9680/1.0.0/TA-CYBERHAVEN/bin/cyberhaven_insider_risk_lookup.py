#!/usr/bin/env python3
"""Custom lookup command to build a base64-encoded Cyberhaven Insider Risk UI state parameter."""
import sys
import csv
import json
import base64


def build_insider_risk_b64(user_id):
    """Build a base64-encoded Insider Risk UI grid state string for the given user."""
    state = {
        "GRID_risky-users": {
            "search": user_id,
            "columnVisibilityModel": {},
            "sortModel": [],
            "pinnedColumns": {"left": [], "right": []},
            "columnsOrder": [],
            "columnsWidths": {},
            "density": "standard",
            "filters": {},
            "paginationModel": {"page": 0, "pageSize": 20},
        }
    }
    state_json = json.dumps(state, separators=(',', ':'))
    return base64.b64encode(state_json.encode('utf-8')).decode('utf-8')


if __name__ == '__main__':
    reader = csv.DictReader(sys.stdin)
    fieldnames = list(reader.fieldnames or [])
    if 'cyberhaven_insider_risk_b64' not in fieldnames:
        fieldnames.append('cyberhaven_insider_risk_b64')

    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        row['cyberhaven_insider_risk_b64'] = build_insider_risk_b64(
            user_id=row.get('user_id', '')
        )
        writer.writerow(row)
