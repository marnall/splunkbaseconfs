#!/usr/bin/env python

import csv
import unicodedata
import sys

def main():
    if len(sys.argv) != 3:
        print("Usage: python category_lookup.py [char] [category]")
        sys.exit(1)

    charfield = sys.argv[1]
    categoryfield = sys.argv[2]

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    for result in r:
        if result[charfield]:
            result[categoryfield] = unicodedata.category(result[charfield])
            w.writerow(result)

main()
