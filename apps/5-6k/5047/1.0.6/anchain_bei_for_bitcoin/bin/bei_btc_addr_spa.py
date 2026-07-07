#!/usr/bin/env python

import csv
import sys
from bei_lookup_wrapper import BEI_Query

def main():
    if len(sys.argv) != 2:
        print("Usage: python bei_btc_addr_spa.py [address]")
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
            spa = q.lookup_spa(result['address'],result['api_key'])
            if spa is None:
                result['spa'] = None
                w.writerow(result)
            else:
                for i in spa:
                    result['spa'] = "{},{}".format(i['label'], i['probability'])
                    w.writerow(result)

main()
