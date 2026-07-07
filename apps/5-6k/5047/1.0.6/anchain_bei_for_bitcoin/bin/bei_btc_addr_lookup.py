#!/usr/bin/env python

import csv
import sys
from multiprocessing_wrapper import multiprocessor
from bei_lookup_wrapper import BEI_Query

q = BEI_Query()

def process_result(result):
    if result['address']:
        q.lookup(result['address'],result['api_key'],'POST')
        result['category'] = q.category
        result['entity_name'] = q.entity_name
        result['risk_score'] = q.risk_score
    return result

def main():
    if len(sys.argv) != 2:
        print("Usage: python bei_lookup.py [address]")
        sys.exit(1)
    infile = sys.stdin
    outfile = sys.stdout
    r = csv.DictReader(infile)
    header = r.fieldnames
    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()
    csv_data = []
    for row in r:
        csv_data.append(row)
    output = multiprocessor(4, process_result, [csv_data])
    for result in output:
        w.writerow(result)

main()
