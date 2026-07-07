#!/usr/bin/env python

import csv
import sys
from bei_lookup_wrapper import BEI_Query

def main():
    if len(sys.argv) != 2:
        print("Usage: python bei_btc_addr_detail_lookup.py [address]")
        sys.exit(1)
    infile = sys.stdin
    outfile = sys.stdout
    r = csv.DictReader(infile)
    header = r.fieldnames
    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()
    q = BEI_Query()
    for result in r:
        if result['address']:
            suspicious_activity = q.lookup_suspicious_activity(result['address'],result['api_key'])
            result['suspicious_activity'] = suspicious_activity
            w.writerow(result)

main()
