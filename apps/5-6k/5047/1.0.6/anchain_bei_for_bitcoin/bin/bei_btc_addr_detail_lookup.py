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
            q.lookup(result['address'],result['api_key'])
            result['category'] = q.category
            result['entity_name'] = q.entity_name
            result['risk_score'] = q.risk_score
            result['risk_level'] = q.risk_level
            result['suspicious_activity'] = q.suspicious_activity
            result['activeness'] = q.activeness
            result['balance'] = q.balance
            result['balance_usd'] = q.balance_usd
            result['first_txn'] = q.first_txn
            result['last_txn'] = q.last_txn
            result['total_received'] = q.total_received
            result['total_sent'] = q.total_sent
            w.writerow(result)

main()
