#!/usr/bin/env python

import csv
import json
import sys
import requests
from bei_lookup_wrapper import BEI_Query

def main():
    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()
    q = BEI_Query()
    for result in r:
        susp_addrs = q.lookup_suspicious_addr(result['info_min_time'], result['info_max_time'],result['api_key'],'btc')
        sys.stderr.write(str(q.url))
        #result['susp_addr'] = susp_addrs
        for i in susp_addrs:
            entity = '-' if i['entity'] == "" else i['entity']
            in_btc = round(i['in_val'] / 1e8, 4)
            out_btc = round(i['out_val'] / 1e8, 4)
            result['susp_addr'] = "{}|{}|{}|{}|{}|{}|{}".format(i['addr'], i['category'], entity, i['in_cnt'], in_btc, i['out_cnt'], out_btc)
            w.writerow(result)

main()
