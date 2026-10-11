#!/usr/bin/env python3
"""Splunk external lookup: no network, writes, credentials or external dependencies."""

import csv
import sys
from vmware_vision_parser import OUTPUT_FIELDS, parse


def main():
    csv.field_size_limit(4 * 1024 * 1024)
    reader = csv.DictReader(sys.stdin)
    inputs = reader.fieldnames or ["_raw", "host", "sourcetype"]
    fields = list(dict.fromkeys(inputs + OUTPUT_FIELDS))
    writer = csv.DictWriter(sys.stdout, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in reader:
        try:
            row.update(
                parse(
                    row.get("_raw", ""), row.get("host", ""), row.get("sourcetype", "")
                )
            )
        except (ValueError, TypeError, RecursionError):
            row.update(dict.fromkeys(OUTPUT_FIELDS, ""))
            row["parser_status"] = "parse_error"
        writer.writerow(row)


if __name__ == "__main__":
    main()
