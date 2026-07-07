#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import csv
import sys
from typing import Dict, Any


def bitmask_lookup(lookup_table: Dict[int, Any]) -> None:
    if len(sys.argv) != 3:
        print("Usage: python <bitmask lookup script name>.py [bitmask] [result]")
        sys.exit(1)

    lookup_bitmask_field = sys.argv[1]
    lookup_result_field = sys.argv[2]

    csv_reader = csv.DictReader(sys.stdin)
    csv_writer = csv.DictWriter(sys.stdout, fieldnames=csv_reader.fieldnames)
    csv_writer.writeheader()

    for row in csv_reader:
        raw_lookup_bitmask = row[lookup_bitmask_field]

        try:
            lookup_bitmask = int(raw_lookup_bitmask)
        except Exception:
            print(
                "ERROR: Failed to convert bitmask value '{}' to number.".format(
                    raw_lookup_bitmask
                )
            )
            continue

        if lookup_bitmask == 0:
            v = lookup_table.get(0)
            if v is not None:
                row[lookup_result_field] = v
                csv_writer.writerow(row)
            continue

        for k, v in lookup_table.items():
            if k & lookup_bitmask != 0:
                row[lookup_result_field] = v
                csv_writer.writerow(row)
